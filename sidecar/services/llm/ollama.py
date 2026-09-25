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
import logging
from collections.abc import AsyncIterator
from typing import Any

import ollama
import pydantic

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMModelOption,
    LLMResearchStepEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services.errors import humanize

from .base import (
    LOCAL_IDLE_TIMEOUT_S,
    LLMProvider,
    LLMStreamEvent,
    client_timeout,
    invalid_tool_args,
)
from .reasoning_split import ReasoningSplitter
from .tool_call_rescue import LeakHold, rescue_leaked_tool_call

logger = logging.getLogger(__name__)

#: Ollama's per-model default (4096) silently truncates the prompt once the
#: copilot agent's ~50 tool schemas are serialized into it, before the user's
#: own message gets a turn — root cause of R15 stage0 local-lane failures
#: (empty output on qwen2.5:7b, fabrication on llama3.1:8b; see
#: docs/redesign/verification/r15/stage0/LOCAL_LANE_PROOF.md). 16384 fits a
#: 7-8B q4 model's KV cache (measured ~0.95 GiB extra resident VRAM going
#: 4096→16384 via `ollama ps` size_vram delta on a real qwen2.5:7b-q4 load:
#: 4,806,766,592 → 5,828,081,664 bytes) alongside the rest of the app on a
#: 16 GB Mac (model weight ~4.5 GiB + ~1 GiB KV cache at this ceiling still
#: leaves headroom for the OS + Tauri/Next.js UI). Overridable per-call via
#: an explicit ``options={"num_ctx": ...}`` kwarg; this is only the floor
#: default.
DEFAULT_NUM_CTX = 16384


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
    raise. Absent or empty arguments are a no-argument call (``{}``); a
    malformed or non-object payload is stamped with the invalid-args sentinel
    so the model is told its arguments were wrong, never run on ``{}``.
    """
    if isinstance(arguments, dict):
        return arguments
    if arguments is None or arguments == "":
        return {}
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments)
        except (ValueError, TypeError):
            return invalid_tool_args("arguments were not valid JSON", arguments)
        if isinstance(parsed, dict):
            return parsed
    return invalid_tool_args("arguments were not a JSON object", str(arguments))


class OllamaProvider(LLMProvider):
    """Ollama local-server adapter."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def context_window(self, model: str) -> int | None:  # noqa: ARG002
        """Every request runs at ``num_ctx``; past it Ollama drops the prompt's head."""
        return DEFAULT_NUM_CTX

    def _client(self) -> ollama.AsyncClient:
        # The SDK keyword is ``host``, not ``base_url``; its default timeout is
        # none at all, so a wedged local server would hold the chat forever.
        return ollama.AsyncClient(host=self._base_url, timeout=client_timeout(LOCAL_IDLE_TIMEOUT_S))

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

        # Always set num_ctx — Ollama's baked-in per-model default (4096 for
        # every model we've seen) truncates before the prompt is fully read
        # once tool schemas are attached. Merge rather than overwrite so an
        # explicit caller-supplied options dict still wins on a conflicting key.
        request_options = dict(kwargs.pop("options", None) or {})
        request_options.setdefault("num_ctx", DEFAULT_NUM_CTX)
        kwargs["options"] = request_options

        tools: list[dict[str, Any]] | None = None
        if tool_ids:
            from services.agent_tools.schemas import openai_tools

            built = openai_tools(tool_ids)
            if built:
                # Ollama accepts OpenAI-style tool definitions on recent
                # models. Older/local models don't — keep the list to one side
                # so we can retry without it if the tools path fails.
                tools = built

        # Open the stream. ``client.chat(stream=True)`` sends nothing when
        # awaited: a daemon/HTTP error (500, model without tool support) surfaces
        # while iterating and is humanized below. The only failure here is the
        # SDK rejecting a tool schema client-side (``Tool.model_validate``); the
        # round then answers without tools and says so (R15-AGENT-076).
        stream = None
        # Tool names actually sent this round: the only names a leaked
        # text-JSON call may be rescued for.
        offered: set[str] = set()
        try:
            if tools is not None:
                try:
                    stream = await client.chat(
                        model=model,
                        messages=api_messages,
                        stream=True,
                        tools=tools,
                        **kwargs,
                    )
                    offered = {tool["function"]["name"] for tool in tools}
                except pydantic.ValidationError as exc:
                    logger.warning(
                        "ollama rejected the tool schemas for %s; this round runs without "
                        "tools: %s",
                        model,
                        exc,
                    )
                    yield LLMResearchStepEvent(
                        tool_call_id="",
                        tool="ollama_tools",
                        step_kind="notice",
                        detail=f"Tools could not be sent to {model}; it answered without them.",
                        status="error",
                    )
            if stream is None:
                stream = await client.chat(
                    model=model,
                    messages=api_messages,
                    stream=True,
                    **kwargs,
                )
        except Exception as exc:  # noqa: BLE001 — every failure ends as a humanized error
            _h = humanize("ollama", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )
            return

        try:
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            # Text from a leaked call's marker on is held until the rescue
            # decides whether it was a call (rc1-drive-onboarding-stranger:1).
            hold = LeakHold(offered)
            emitted_tool_call = False
            # <think> spans in content come out as thinking (R15-LEAD-018).
            splitter = ReasoningSplitter()
            async for chunk in stream:
                message = _attr(chunk, "message")
                if message is not None:
                    content = _attr(message, "content", "") or ""
                    for event in splitter.content(content) if content else []:
                        if isinstance(event, LLMDeltaEvent):
                            for shown in hold.feed(event.text):
                                yield LLMDeltaEvent(text=shown)
                            continue
                        yield event
                    # Ollama returns tool calls on the (non-streamed) assistant
                    # message rather than as token deltas: emit one tool_use
                    # event per call so the runtime can resolve them before the
                    # round's done event.
                    tool_calls = _attr(message, "tool_calls") or []
                    for tool_call in tool_calls:
                        function = _attr(tool_call, "function")
                        if function is None:
                            continue
                        emitted_tool_call = True
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
            for event in splitter.flush():
                if isinstance(event, LLMDeltaEvent):
                    for shown in hold.feed(event.text):
                        yield LLMDeltaEvent(text=shown)
                    continue
                yield event
            # Local models often write the call as JSON text instead of using
            # tool_calls (llama3.1:8b: ``{"name": "write_note", "parameters":
            # {...}}``). Rescue it so the call runs instead of rendering as
            # prose; the held call text and its made-up result are dropped.
            rescued = None if emitted_tool_call else rescue_leaked_tool_call(hold.text, offered)
            if rescued is not None:
                yield rescued
            elif hold.held():
                yield LLMDeltaEvent(text=hold.held())
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except ollama.ResponseError as exc:  # pragma: no cover — network path
            _h = humanize("ollama", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )
        except Exception as exc:  # pragma: no cover — defensive
            _h = humanize("ollama", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )

    async def validate_key(self, api_key: str | None = None) -> bool:  # noqa: ARG002
        """Ollama needs no key — a successful ``list`` proves the daemon is reachable.

        A stopped daemon (connection refused) or one answering with an error
        raises, so the router reports ``unreachable`` rather than a bad key;
        there is no key to reject, so this never returns ``False``.
        """
        await self._client().list()
        return True

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
