"""OpenAI (and OpenAI-shaped) provider adapter.

Wraps ``openai.AsyncOpenAI(...).chat.completions.create(stream=True, ...)``
(openai SDK 2.36.0). The same adapter handles DeepSeek and xAI via
``base_url`` override — both speak the OpenAI chat-completions wire format
end-to-end. The dispatch lives in ``services.llm.__init__`` so the adapter
file count stays at five (per the Phase 3 plan).

The streaming chunks carry text deltas in ``choices[0].delta.content`` and
tool-call deltas in ``choices[0].delta.tool_calls`` (function-calling shape).
The final chunk's ``finish_reason`` and the optional terminal chunk's
``usage`` (set via ``stream_options={"include_usage": True}``) round out the
:class:`LLMDoneEvent` payload.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import openai

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMToolUseEvent,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent
from .native_search import openai_web_search_tool, xai_search_parameters


def _to_api_messages(messages: list[LLMMessage]) -> list[dict[str, Any]]:
    """Convert host messages to OpenAI chat-completions shape.

    ``role="tool"`` carries the result of a host-resolved call keyed by
    ``tool_call_id``. An assistant turn with ``metadata["tool_calls"]`` is
    reconstructed into the native ``tool_calls`` array (arguments re-serialised
    to a JSON string) so the provider associates each following tool result
    with the call that produced it.
    """
    api_messages: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "tool":
            api_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": message.tool_call_id,
                    "content": message.content,
                }
            )
            continue
        if message.role == "assistant" and message.metadata and message.metadata.get("tool_calls"):
            api_messages.append(
                {
                    "role": "assistant",
                    "content": message.content or None,
                    "tool_calls": [
                        {
                            "id": tc.get("id", ""),
                            "type": "function",
                            "function": {
                                "name": tc.get("name", ""),
                                "arguments": json.dumps(tc.get("input", {})),
                            },
                        }
                        for tc in message.metadata["tool_calls"]
                    ],
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


def _flush_tool_buffers(buffers: dict[int, dict[str, str]]) -> list[LLMToolUseEvent]:
    """Drain accumulated tool-call buffers into ``tool_use`` events.

    One event per buffered call, with ``arguments`` parsed from the
    concatenated JSON fragments. Empty/invalid argument strings fall back to
    ``{}`` rather than aborting the round. The dict is cleared so a later flush
    (stream-end safety net) never re-emits the same call.
    """
    events: list[LLMToolUseEvent] = []
    for index in sorted(buffers):
        buffer = buffers[index]
        args = buffer.get("args") or ""
        try:
            parsed = json.loads(args) if args else {}
        except json.JSONDecodeError:
            parsed = {}
        if not isinstance(parsed, dict):
            parsed = {}
        events.append(
            LLMToolUseEvent(
                tool_call_id=buffer.get("id", "") or "",
                name=buffer.get("name", "") or "",
                input=parsed,
            )
        )
    buffers.clear()
    return events


class OpenAIProvider(LLMProvider):
    """OpenAI chat-completions adapter; also serves DeepSeek and xAI.

    ``provider_id`` is informational — it lets DeepSeek/xAI adapter instances
    surface the right error provenance without changing the wire shape.
    """

    def __init__(self, base_url: str | None = None, provider_id: str = "openai") -> None:
        self._base_url = base_url
        self._provider_id = provider_id

    def _client(self, api_key: str | None) -> openai.AsyncOpenAI:
        # OpenRouter takes optional attribution headers (leaderboard/analytics
        # only; safe to send). They identify the app, carry no secret.
        default_headers: dict[str, str] | None = None
        if self._provider_id == "openrouter":
            default_headers = {
                "HTTP-Referer": "https://vysted.app",
                "X-Title": "Vysted Terminal",
            }
        return openai.AsyncOpenAI(
            api_key=api_key, base_url=self._base_url, default_headers=default_headers
        )

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        tool_ids = kwargs.pop("tool_ids", None)
        web_search = bool(kwargs.pop("web_search", False))
        # ``web_search_max_uses`` is Anthropic-only; pop it so it never reaches
        # the OpenAI/xAI SDK (the runtime caps these providers loop-side).
        kwargs.pop("web_search_max_uses", None)
        client = self._client(api_key)
        api_messages = _to_api_messages(messages)
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        tools: list[dict[str, Any]] = []
        if tool_ids:
            from services.agent_tools.schemas import openai_tools

            tools.extend(openai_tools(tool_ids))
        # Native server-side web search (FR-081), opt-in via ``web_search``.
        # OpenAI takes a ``{"type": "web_search"}`` tools entry; xAI (dispatched
        # through this adapter via the x.ai base_url) speaks Live Search through
        # a top-level ``search_parameters`` block instead of a tool — gate on the
        # provider id. DeepSeek has no native search, so it is left untouched
        # (graceful no-op; the runtime falls back to a BYOK search plugin).
        if web_search:
            if self._provider_id == "xai":
                request_kwargs["extra_body"] = {
                    **request_kwargs.get("extra_body", {}),
                    "search_parameters": xai_search_parameters(),
                }
            elif self._provider_id == "openai":
                tools.append(openai_web_search_tool())
        if tools:
            request_kwargs["tools"] = tools
        # OpenRouter cheapest-capable routing (FINDINGS §2.2): pick the cheapest
        # PROVIDER of the chosen model, and — when we send tools — refuse a
        # provider that would silently drop them (so multi-round tool use never
        # breaks). Sent as ``extra_body.provider`` (OpenRouter-specific; ignored
        # by vanilla OpenAI, but only openrouter instances reach this branch).
        if self._provider_id == "openrouter":
            or_provider: dict[str, Any] = {"sort": "price"}
            if tools:
                or_provider["require_parameters"] = True
            request_kwargs["extra_body"] = {
                **request_kwargs.get("extra_body", {}),
                "provider": or_provider,
            }
        request_kwargs.update(kwargs)
        try:
            stream = await client.chat.completions.create(**request_kwargs)
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            # Function-call streaming sends the id/name once and the arguments
            # JSON in fragments across many chunks, keyed by the tool_call
            # index. Accumulate per index, then emit ONE tool_use event per
            # call with the parsed arguments dict when the round finishes.
            tool_buffers: dict[int, dict[str, str]] = {}
            async for chunk in stream:
                # Some providers (DeepSeek, occasionally OpenAI) emit a
                # terminal chunk with no choices but populated usage. Guard
                # both branches independently.
                choices = getattr(chunk, "choices", None) or []
                for choice in choices:
                    delta = getattr(choice, "delta", None)
                    if delta is not None:
                        content = getattr(delta, "content", None)
                        if content:
                            yield LLMDeltaEvent(text=content)
                        tool_calls = getattr(delta, "tool_calls", None) or []
                        for tool_call in tool_calls:
                            index = getattr(tool_call, "index", 0) or 0
                            buffer = tool_buffers.setdefault(
                                index, {"id": "", "name": "", "args": ""}
                            )
                            tc_id = getattr(tool_call, "id", None)
                            if tc_id:
                                buffer["id"] = tc_id
                            function = getattr(tool_call, "function", None)
                            if function is not None:
                                name = getattr(function, "name", None)
                                if name:
                                    buffer["name"] = name
                                args_raw = getattr(function, "arguments", None)
                                if args_raw:
                                    buffer["args"] += args_raw
                    reason = getattr(choice, "finish_reason", None)
                    if reason:
                        finish_reason = reason
                    if reason == "tool_calls":
                        for event in _flush_tool_buffers(tool_buffers):
                            yield event
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    usage = LLMUsage(
                        input_tokens=getattr(chunk_usage, "prompt_tokens", 0) or 0,
                        output_tokens=getattr(chunk_usage, "completion_tokens", 0) or 0,
                    )
            # Stream ended with buffers still pending (no explicit
            # ``tool_calls`` finish_reason from this provider) — flush them so
            # the call is never dropped.
            for event in _flush_tool_buffers(tool_buffers):
                yield event
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except openai.OpenAIError as exc:  # pragma: no cover — network path
            yield LLMErrorEvent(message=f"{self._provider_id} stream failed: {exc}")
        except Exception as exc:  # pragma: no cover — defensive
            yield LLMErrorEvent(message=f"{self._provider_id} stream failed: {exc}")

    async def validate_key(self, api_key: str | None = None) -> bool:
        """Probe ``/v1/models`` — works for OpenAI, DeepSeek, and xAI alike."""
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            await client.models.list()
            return True
        except openai.AuthenticationError:
            return False
        except openai.PermissionDeniedError:
            return False
        except openai.OpenAIError:
            raise
