"""Groq provider adapter.

Wraps ``groq.AsyncGroq(...).chat.completions.create(stream=True, ...)``
(groq SDK 1.1.1). Groq is OpenAI-shaped at the wire level — same chunk
schema, same finish-reason values, same usage block — but ships its own
SDK with its own error hierarchy, so we keep a dedicated adapter rather
than dispatching through ``OpenAIProvider``.

Models: ``llama-3.3-70b-versatile``, ``mixtral-8x7b-32768``, etc. The host
does not enumerate them — the chat sidebar's model dropdown is populated
from ``GET /llm/models?provider=groq`` (out of scope here; not used yet).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import groq

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMModelOption,
    LLMToolUseEvent,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent, is_chat_model


def _parse_tool_args(raw: str) -> dict[str, Any]:
    """Parse accumulated tool-call argument JSON into a dict.

    A no-argument call streams an empty string; a malformed fragment (rare,
    but possible on a truncated stream) degrades to an empty dict rather than
    aborting the round — the host surfaces the call with whatever it has.
    """
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _to_api_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert host messages to the OpenAI/Groq chat-completions shape.

    Groq is OpenAI-shaped, so tool results carry ``role="tool"`` +
    ``tool_call_id`` and the assistant turn that triggered them carries a
    ``tool_calls`` array. The runtime stashes those calls in
    ``message.metadata["tool_calls"]`` (it has no native place for them on the
    neutral :class:`LLMMessage`); rebuild them here so each tool result
    associates with its call by id.
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
                        # OpenAI/Groq carry tool-call args as a JSON string.
                        "arguments": json.dumps(tc.get("input", {})),
                    },
                }
                for tc in message.metadata["tool_calls"]
            ]
            api_messages.append(
                {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": tool_calls,
                }
            )
            continue
        api_messages.append(
            {
                "role": message.role,
                "content": message.content,
                **({"tool_call_id": message.tool_call_id} if message.tool_call_id else {}),
            }
        )
    return api_messages


class GroqProvider(LLMProvider):
    """Groq chat-completions adapter."""

    def _client(self, api_key: str | None) -> groq.AsyncGroq:
        return groq.AsyncGroq(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        tool_ids = kwargs.pop("tool_ids", None)
        # Native server-side web search (FR-081): on Groq, search is handled by
        # the Compound system server-side — a Compound model (``compound-*`` /
        # ``groq/compound*``) runs web search automatically, so there is no
        # explicit tool to inject; pass through. On a non-Compound Groq model
        # there is no native search, so this is a graceful no-op (the runtime
        # falls back to a BYOK search plugin). Either way, pop the kwargs so they
        # never reach the SDK.
        kwargs.pop("web_search", None)
        kwargs.pop("web_search_max_uses", None)
        client = self._client(api_key)
        api_messages = _to_api_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": True,
        }
        if tool_ids:
            from services.agent_tools.schemas import openai_tools

            tools = openai_tools(tool_ids)
            if tools:
                request_kwargs["tools"] = tools
        request_kwargs.update(kwargs)
        try:
            stream = await client.chat.completions.create(**request_kwargs)
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            # Groq streams tool-call arguments the OpenAI way: one tool call
            # arrives across many chunks, identified by ``tool_call.index``,
            # with the JSON arguments split into string fragments. Accumulate
            # per index, then emit one parsed-dict tool_use event per call
            # before the round's done event.
            tool_acc: dict[int, dict[str, Any]] = {}
            async for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                for choice in choices:
                    delta = getattr(choice, "delta", None)
                    if delta is None:
                        continue
                    content = getattr(delta, "content", None)
                    if content:
                        yield LLMDeltaEvent(text=content)
                    tool_calls = getattr(delta, "tool_calls", None) or []
                    for tool_call in tool_calls:
                        index = getattr(tool_call, "index", 0) or 0
                        slot = tool_acc.setdefault(index, {"id": "", "name": "", "args": ""})
                        tc_id = getattr(tool_call, "id", None)
                        if tc_id:
                            slot["id"] = tc_id
                        function = getattr(tool_call, "function", None)
                        if function is not None:
                            name = getattr(function, "name", None)
                            if name:
                                slot["name"] = name
                            args_raw = getattr(function, "arguments", None)
                            if args_raw:
                                slot["args"] += args_raw
                    reason = getattr(choice, "finish_reason", None)
                    if reason:
                        finish_reason = reason
                # Groq surfaces usage via the OpenAI-shaped x_groq.usage block
                # on the final chunk.
                x_groq = getattr(chunk, "x_groq", None)
                usage_block = getattr(x_groq, "usage", None) if x_groq is not None else None
                if usage_block is not None:
                    usage = LLMUsage(
                        input_tokens=getattr(usage_block, "prompt_tokens", 0) or 0,
                        output_tokens=getattr(usage_block, "completion_tokens", 0) or 0,
                    )
            for slot in tool_acc.values():
                yield LLMToolUseEvent(
                    tool_call_id=slot["id"],
                    name=slot["name"],
                    input=_parse_tool_args(slot["args"]),
                )
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except groq.GroqError as exc:  # pragma: no cover — network path
            yield LLMErrorEvent(message=f"groq stream failed: {exc}")
        except Exception as exc:  # pragma: no cover — defensive
            yield LLMErrorEvent(message=f"groq stream failed: {exc}")

    async def validate_key(self, api_key: str | None = None) -> bool:
        """Probe ``/openai/v1/models`` — the cheapest authenticated call."""
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            await client.models.list()
            return True
        except groq.AuthenticationError:
            return False
        except groq.PermissionDeniedError:
            return False
        except groq.GroqError:
            raise

    async def list_models(self, api_key: str | None = None) -> list[LLMModelOption]:
        """Live catalog via ``/openai/v1/models``, filtered to chat models.

        Groq rotates and decommissions models often, so a static list silently
        goes wrong — and it also serves whisper (audio) models the chat picker
        must drop.
        """
        if not api_key:
            return []
        try:
            client = self._client(api_key)
            page = await client.models.list()
        except groq.AuthenticationError:
            return []
        except groq.PermissionDeniedError:
            return []
        options = [
            LLMModelOption(id=str(model.id), label=str(model.id))
            for model in (getattr(page, "data", None) or [])
            if getattr(model, "id", None) and is_chat_model(str(model.id))
        ]
        options.sort(key=lambda opt: opt.id.lower())
        return options
