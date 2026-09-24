"""Anthropic provider adapter.

Wraps ``anthropic.AsyncAnthropic(...).messages.stream(...)`` (anthropic
SDK 0.100.0). The SDK's streaming context manager yields typed events with a
discriminated ``type`` field; we translate them into the host's neutral
:class:`LLMStreamEvent` shape so the SSE wire protocol is provider-agnostic.

Anthropic uses a separate top-level ``system`` parameter rather than a
``"system"`` role in the messages array, so the adapter splits ``messages``
into system blocks (with prompt-cache breakpoints) and the remaining
user/assistant turns at the call site.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import anthropic

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMModelOption,
    LLMThinkingEvent,
    LLMToolUseEvent,
    LLMUsage,
)
from services.errors import humanize

from .base import LLMProvider, LLMStreamEvent, client_timeout
from .native_search import DEFAULT_WEB_SEARCH_MAX_USES, anthropic_web_search_tool

#: Output ceiling (max ``max_tokens``) per Claude model family; the longest
#: matching id prefix wins. The SDK requires ``max_tokens`` on every call, and a
#: fixed 4,096 cut long answers and research syntheses mid-sentence
#: (R15-RESEARCH-014); the stream never hits an HTTP timeout, so the default is
#: the model's own ceiling.
_OUTPUT_CEILINGS: dict[str, int] = {
    "claude-fable": 128_000,
    "claude-mythos": 128_000,
    "claude-opus-5": 128_000,
    "claude-opus-4-8": 128_000,
    "claude-opus-4-7": 128_000,
    "claude-opus-4-6": 128_000,
    "claude-opus-4-5": 64_000,
    "claude-opus-4": 32_000,
    "claude-sonnet-5": 128_000,
    "claude-sonnet-4-6": 128_000,
    "claude-sonnet-4": 64_000,
    "claude-haiku-4-5": 64_000,
}
#: The ceiling for an id no prefix above matches (every Claude 4 model allows it).
_FALLBACK_OUTPUT_CEILING = 32_000


def max_output_tokens(model: str) -> int:
    """The model's output ceiling, the default ``max_tokens`` for a call."""
    prefixes = [p for p in _OUTPUT_CEILINGS if model.startswith(p)]
    return _OUTPUT_CEILINGS[max(prefixes, key=len)] if prefixes else _FALLBACK_OUTPUT_CEILING


#: A prompt-cache breakpoint (R15-AGENT-050): everything before it is cached.
_CACHE_BREAKPOINT = {"type": "ephemeral"}


def _split_system_and_messages(
    messages: list[LLMMessage],
) -> tuple[list[dict[str, Any]] | None, list[dict[str, Any]]]:
    """Pull system messages out as ``system`` blocks and convert the rest.

    Anthropic uses a top-level ``system`` parameter, not a ``"system"`` role
    inside the messages list. Each system message is its own text block so
    the stable first one (the agent's persona and capabilities) carries a
    cache breakpoint and the per-turn date and terminal preamble after it
    never invalidate it (R15-AGENT-050). A second breakpoint sits on the last
    tool result, so each tool round reads the previous rounds from cache.
    """
    system_blocks: list[dict[str, Any]] = []
    rest: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            if message.content:  # the API rejects an empty text block
                system_blocks.append({"type": "text", "text": message.content})
            continue
        if message.role == "tool":
            # Anthropic tool results are a content block, not a top-level role.
            block = {
                "type": "tool_result",
                "tool_use_id": message.tool_call_id or "",
                "content": message.content,
            }
            # Parallel calls: every result of one call turn rides ONE user
            # message; one message per result teaches Claude to stop calling
            # tools in parallel (Anthropic's parallel tool use guidance).
            if rest and _is_tool_result_turn(rest[-1]):
                rest[-1]["content"].append(block)
            else:
                rest.append({"role": "user", "content": [block]})
            continue
        if message.role == "assistant" and message.metadata and message.metadata.get("tool_calls"):
            # Reconstruct the assistant tool_use turn so the following
            # tool_result blocks associate by id (runtime carries the calls in
            # metadata).
            blocks: list[dict[str, Any]] = []
            if message.content:
                blocks.append({"type": "text", "text": message.content})
            for tc in message.metadata["tool_calls"]:
                blocks.append(
                    {
                        "type": "tool_use",
                        "id": tc.get("id", ""),
                        "name": tc.get("name", ""),
                        "input": tc.get("input", {}),
                    }
                )
            rest.append({"role": "assistant", "content": blocks})
            continue
        rest.append({"role": message.role, "content": message.content})
    if system_blocks:
        system_blocks[0]["cache_control"] = _CACHE_BREAKPOINT
    last_result = next(
        (m["content"][-1] for m in reversed(rest) if _is_tool_result_turn(m)),
        None,
    )
    if last_result is not None:
        last_result["cache_control"] = _CACHE_BREAKPOINT
    return system_blocks or None, rest


def _is_tool_result_turn(message: dict[str, Any]) -> bool:
    content = message["content"]
    return isinstance(content, list) and content[-1].get("type") == "tool_result"


class AnthropicProvider(LLMProvider):
    """Anthropic messages API adapter."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def _client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(
            api_key=api_key, base_url=self._base_url, timeout=client_timeout()
        )

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        max_tokens = int(kwargs.pop("max_tokens", None) or max_output_tokens(model))
        tool_ids = kwargs.pop("tool_ids", None)
        web_search = bool(kwargs.pop("web_search", False))
        web_search_max_uses = int(kwargs.pop("web_search_max_uses", DEFAULT_WEB_SEARCH_MAX_USES))
        system, rest = _split_system_and_messages(messages)
        client = self._client(api_key)
        stream_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": rest,
        }
        if system is not None:
            stream_kwargs["system"] = system
        tools: list[dict[str, Any]] = []
        if tool_ids:
            from services.agent_tools.schemas import anthropic_tools

            tools.extend(anthropic_tools(tool_ids))
        # Native server-side web search (FR-081): opt-in via ``web_search``.
        # Anthropic supports it on every current model, so no model gate is
        # needed; if a future model rejects it the runtime falls back.
        if web_search:
            tools.append(anthropic_web_search_tool(web_search_max_uses))
        if tools:
            stream_kwargs["tools"] = tools
        stream_kwargs.update(kwargs)
        try:
            async with client.messages.stream(**stream_kwargs) as stream:
                async for event in stream:
                    translated = _translate_event(event)
                    if translated is not None:
                        yield translated
                final = await stream.get_final_message()
                yield LLMDoneEvent(
                    usage=_usage_from_final(final),
                    finish_reason=getattr(final, "stop_reason", None),
                )
        except anthropic.AnthropicError as exc:  # pragma: no cover — network path
            _h = humanize("anthropic", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )
        except Exception as exc:  # pragma: no cover — defensive
            _h = humanize("anthropic", exc)
            yield LLMErrorEvent(
                message=_h.message, action=_h.action, detail=_h.detail, code=_h.code
            )

    async def validate_key(self, api_key: str | None = None) -> bool:
        """Probe ``/v1/models`` — the cheapest authenticated request."""
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            await client.models.list(limit=1)
            return True
        except anthropic.AuthenticationError:
            return False
        except anthropic.PermissionDeniedError:
            return False
        except anthropic.AnthropicError:
            # Any other API-level error is a real transport issue — propagate
            # so the router can surface "provider unreachable".
            raise

    async def list_models(self, api_key: str | None = None) -> list[LLMModelOption]:
        """Live catalog via ``/v1/models``. Every Claude model is tool-capable."""
        if not api_key:
            return []
        try:
            client = self._client(api_key)
            page = await client.models.list(limit=100)
        except anthropic.AuthenticationError:
            return []
        except anthropic.PermissionDeniedError:
            return []
        return [
            LLMModelOption(
                id=str(model.id),
                label=str(getattr(model, "display_name", None) or model.id),
                supports_tools=True,
            )
            for model in (getattr(page, "data", None) or [])
            if getattr(model, "id", None)
        ]


# ---------------------------------------------------------------------------
# Event translation
# ---------------------------------------------------------------------------


def _translate_event(event: Any) -> LLMStreamEvent | None:
    """Map an anthropic SDK stream event to a host :class:`LLMStreamEvent`.

    Anthropic's SDK emits granular events (``message_start``,
    ``content_block_start``, ``content_block_delta`` for text/thinking,
    ``content_block_stop``, ``message_delta``, ``message_stop``). The host
    only cares about text deltas, thinking deltas, and completed tool-use
    blocks — the rest are filtered out and the surrounding context manager
    terminator becomes our ``done``.
    """
    event_type = getattr(event, "type", None)
    if event_type == "content_block_delta":
        delta = getattr(event, "delta", None)
        delta_type = getattr(delta, "type", None)
        if delta_type == "text_delta":
            text = getattr(delta, "text", "") or ""
            if text:
                return LLMDeltaEvent(text=text)
        elif delta_type == "thinking_delta":
            thinking = getattr(delta, "thinking", "") or ""
            if thinking:
                return LLMThinkingEvent(text=thinking)
        return None
    if event_type == "content_block_stop":
        # A streamed tool_use block starts with ``input: {}``; its arguments
        # arrive afterwards as ``input_json_delta`` fragments. The SDK hands the
        # accumulated block back on ``content_block_stop``, so emit it there.
        block = getattr(event, "content_block", None)
        if block is not None and getattr(block, "type", None) == "tool_use":
            return LLMToolUseEvent(
                tool_call_id=getattr(block, "id", ""),
                name=getattr(block, "name", ""),
                input=getattr(block, "input", {}) or {},
            )
        return None
    return None


def _usage_from_final(final: Any) -> LLMUsage | None:
    """Extract :class:`LLMUsage` from an anthropic final message, if present."""
    usage = getattr(final, "usage", None)
    if usage is None:
        return None
    return LLMUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", None),
        cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", None),
        # Native searches priced + capped per run (R15-AGENT-049).
        web_search_requests=getattr(
            getattr(usage, "server_tool_use", None), "web_search_requests", None
        ),
    )
