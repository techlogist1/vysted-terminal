"""Anthropic provider adapter.

Wraps ``anthropic.AsyncAnthropic(...).messages.stream(...)`` (anthropic
SDK 0.100.0). The SDK's streaming context manager yields typed events with a
discriminated ``type`` field; we translate them into the host's neutral
:class:`LLMStreamEvent` shape so the SSE wire protocol is provider-agnostic.

Anthropic uses a separate top-level ``system`` parameter rather than a
``"system"`` role in the messages array, so the adapter splits ``messages``
into the system string and the remaining user/assistant turns at the call
site.
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
    LLMThinkingEvent,
    LLMToolUseEvent,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent

#: Conservative default — anthropic SDK requires ``max_tokens`` on every call.
DEFAULT_MAX_TOKENS = 4_096


def _split_system_and_messages(
    messages: list[LLMMessage],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Pull leading system messages out and convert the rest to API shape.

    Anthropic uses a top-level ``system`` parameter, not a ``"system"`` role
    inside the messages list. Multiple system messages concatenate with
    newlines so the agent runtime's "system prompt + context preamble"
    composition still works.
    """
    system_chunks: list[str] = []
    rest: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            system_chunks.append(message.content)
            continue
        if message.role == "tool":
            # Anthropic tool results are a content block, not a top-level role.
            rest.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": message.tool_call_id or "",
                            "content": message.content,
                        }
                    ],
                }
            )
            continue
        rest.append({"role": message.role, "content": message.content})
    system = "\n\n".join(system_chunks) if system_chunks else None
    return system, rest


class AnthropicProvider(LLMProvider):
    """Anthropic messages API adapter."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = base_url

    def _client(self, api_key: str | None) -> anthropic.AsyncAnthropic:
        return anthropic.AsyncAnthropic(api_key=api_key, base_url=self._base_url)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        max_tokens = int(kwargs.pop("max_tokens", DEFAULT_MAX_TOKENS))
        system, rest = _split_system_and_messages(messages)
        client = self._client(api_key)
        stream_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": rest,
        }
        if system is not None:
            stream_kwargs["system"] = system
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
            yield LLMErrorEvent(message=str(exc))
        except Exception as exc:  # pragma: no cover — defensive
            yield LLMErrorEvent(message=f"anthropic stream failed: {exc}")

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


# ---------------------------------------------------------------------------
# Event translation
# ---------------------------------------------------------------------------


def _translate_event(event: Any) -> LLMStreamEvent | None:
    """Map an anthropic SDK stream event to a host :class:`LLMStreamEvent`.

    Anthropic's SDK emits granular events (``message_start``,
    ``content_block_start``, ``content_block_delta`` for text/thinking,
    ``content_block_stop``, ``message_delta``, ``message_stop``). The host
    only cares about text deltas, thinking deltas, and tool-use blocks — the
    rest are filtered out and the surrounding context manager terminator
    becomes our ``done``.
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
    if event_type == "content_block_start":
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
    )
