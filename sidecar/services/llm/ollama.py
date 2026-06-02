"""Ollama provider adapter.

Wraps ``ollama.AsyncClient(...).chat(stream=True, ...)`` (ollama SDK 0.6.2).
Ollama runs locally — no BYOK key is required. The default endpoint is
``http://127.0.0.1:11434``; tests and remote-Ollama setups can override via
the constructor's ``base_url``.

The streaming chunks are dict-shaped (``{"message": {"content": "..."}, "done": bool, ...}``)
unlike the other adapters' typed chunk objects. We tolerate either shape so
the SDK can swap to a dataclass-based response in a future release without
breaking this adapter.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import ollama

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMModelOption,
    LLMToolUseEvent,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent


def _attr(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a dict or an attr-styled SDK object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _to_api_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert host messages to Ollama's chat shape.

    Ollama speaks the OpenAI-flavoured message array, so ``tool`` results are a
    top-level ``{"role": "tool", "content": ...}`` turn and the assistant
    tool-call turn carries an OpenAI-style ``tool_calls`` list. The runtime
    carries the prior round's calls in ``metadata["tool_calls"]`` (a list of
    ``{id, name, input}``) so the following tool result turns associate with
    their call — rebuild that here in Ollama's native shape.
    """
    api_messages: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "assistant" and message.metadata and message.metadata.get("tool_calls"):
            tool_calls = [
                {
                    "id": tc.get("id", ""),
                    "type": "function",
                    "function": {
                        "name": tc.get("name", ""),
                        "arguments": tc.get("input", {}),
                    },
                }
                for tc in message.metadata["tool_calls"]
            ]
            api_messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": tool_calls,
                }
            )
            continue
        if message.role == "tool":
            api_messages.append({"role": "tool", "content": message.content})
            continue
        api_messages.append({"role": message.role, "content": message.content})
    return api_messages


def _parse_tool_input(arguments: Any) -> dict[str, Any]:
    """Coerce a tool-call ``arguments`` field to a dict.

    Recent Ollama models return ``arguments`` already parsed as a dict, but
    some emit a JSON string (the OpenAI convention). Tolerate both, and never
    raise — a malformed payload degrades to ``{}`` so the round still closes.
    """
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str) and arguments:
        try:
            parsed = json.loads(arguments)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class OllamaProvider(LLMProvider):
    """Ollama local-server adapter."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def _client(self) -> ollama.AsyncClient:
        # The SDK keyword is ``host``, not ``base_url``.
        if self._base_url:
            return ollama.AsyncClient(host=self._base_url)
        return ollama.AsyncClient()

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,  # noqa: ARG002 — Ollama is BYOK-free.
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        tool_ids = kwargs.pop("tool_ids", None)
        client = self._client()
        api_messages = _to_api_messages(messages)

        tools: list[dict[str, Any]] | None = None
        if tool_ids:
            from services.agent_tools.schemas import openai_tools

            built = openai_tools(tool_ids)
            if built:
                # Ollama accepts OpenAI-style tool definitions on recent
                # models. Older/local models don't — keep the list to one side
                # so we can retry without it if the tools path fails.
                tools = built

        # Open the stream. Tool support is best-effort: many local models reject
        # or ignore a ``tools=`` kwarg, so if opening the tools stream raises we
        # transparently retry without tools rather than surfacing an error —
        # text must always stream.
        stream = None
        if tools is not None:
            try:
                stream = await client.chat(
                    model=model,
                    messages=api_messages,
                    stream=True,
                    tools=tools,
                    **kwargs,
                )
            except Exception:  # noqa: BLE001 — degrade gracefully, retry below.
                stream = None
        if stream is None:
            try:
                stream = await client.chat(
                    model=model,
                    messages=api_messages,
                    stream=True,
                    **kwargs,
                )
            except ollama.ResponseError as exc:  # pragma: no cover — network path
                yield LLMErrorEvent(message=f"ollama stream failed: {exc}")
                return
            except Exception as exc:  # pragma: no cover — defensive
                yield LLMErrorEvent(message=f"ollama stream failed: {exc}")
                return

        try:
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            async for chunk in stream:
                message = _attr(chunk, "message")
                if message is not None:
                    content = _attr(message, "content", "") or ""
                    if content:
                        yield LLMDeltaEvent(text=content)
                    # Ollama returns tool calls on the (non-streamed) assistant
                    # message rather than as token deltas: emit one tool_use
                    # event per call so the runtime can resolve them before the
                    # round's done event.
                    tool_calls = _attr(message, "tool_calls") or []
                    for tool_call in tool_calls:
                        function = _attr(tool_call, "function")
                        if function is None:
                            continue
                        yield LLMToolUseEvent(
                            tool_call_id=_attr(tool_call, "id", "") or "",
                            name=_attr(function, "name", "") or "",
                            input=_parse_tool_input(_attr(function, "arguments")),
                        )
                done = _attr(chunk, "done", False)
                done_reason = _attr(chunk, "done_reason")
                if done_reason:
                    finish_reason = str(done_reason)
                if done:
                    prompt_eval = _attr(chunk, "prompt_eval_count", 0) or 0
                    eval_count = _attr(chunk, "eval_count", 0) or 0
                    usage = LLMUsage(
                        input_tokens=int(prompt_eval),
                        output_tokens=int(eval_count),
                    )
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except ollama.ResponseError as exc:  # pragma: no cover — network path
            yield LLMErrorEvent(message=f"ollama stream failed: {exc}")
        except Exception as exc:  # pragma: no cover — defensive
            yield LLMErrorEvent(message=f"ollama stream failed: {exc}")

    async def validate_key(self, api_key: str | None = None) -> bool:  # noqa: ARG002
        """Ollama needs no key — a successful ``list`` proves the daemon is reachable."""
        try:
            client = self._client()
            await client.list()
            return True
        except ollama.ResponseError:
            return False
        except Exception:  # pragma: no cover — connection refused, etc.
            return False

    async def list_models(self, api_key: str | None = None) -> list[LLMModelOption]:  # noqa: ARG002
        """Live catalog = whatever the user has actually pulled locally.

        The static two-name fallback is useless for Ollama — the real list is
        the local daemon's installed models, which ``client.list()`` returns.
        """
        try:
            client = self._client()
            resp = await client.list()
        except Exception:  # pragma: no cover — daemon not running / unreachable
            return []
        options: list[LLMModelOption] = []
        for model in _attr(resp, "models", None) or []:
            name = _attr(model, "model", None) or _attr(model, "name", None)
            if name:
                options.append(LLMModelOption(id=str(name), label=str(name)))
        options.sort(key=lambda opt: opt.id.lower())
        return options
