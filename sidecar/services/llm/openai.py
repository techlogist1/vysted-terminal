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


class OpenAIProvider(LLMProvider):
    """OpenAI chat-completions adapter; also serves DeepSeek and xAI.

    ``provider_id`` is informational — it lets DeepSeek/xAI adapter instances
    surface the right error provenance without changing the wire shape.
    """

    def __init__(self, base_url: str | None = None, provider_id: str = "openai") -> None:
        self._base_url = base_url
        self._provider_id = provider_id

    def _client(self, api_key: str | None) -> openai.AsyncOpenAI:
        return openai.AsyncOpenAI(api_key=api_key, base_url=self._base_url)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        client = self._client(api_key)
        api_messages = [
            {
                "role": message.role,
                "content": message.content,
                **({"tool_call_id": message.tool_call_id} if message.tool_call_id else {}),
            }
            for message in messages
        ]
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        request_kwargs.update(kwargs)
        try:
            stream = await client.chat.completions.create(**request_kwargs)
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            async for chunk in stream:
                # Some providers (DeepSeek, occasionally OpenAI) emit a
                # terminal chunk with no choices but populated usage. Guard
                # both branches independently.
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
                        function = getattr(tool_call, "function", None)
                        if function is None:
                            continue
                        # Function-call streaming sends incremental arguments;
                        # we forward each delta as a separate tool_use event
                        # the host can re-assemble on the frontend.
                        args_raw = getattr(function, "arguments", "") or ""
                        yield LLMToolUseEvent(
                            tool_call_id=getattr(tool_call, "id", "") or "",
                            name=getattr(function, "name", "") or "",
                            input={"arguments_delta": args_raw},
                        )
                    reason = getattr(choice, "finish_reason", None)
                    if reason:
                        finish_reason = reason
                chunk_usage = getattr(chunk, "usage", None)
                if chunk_usage is not None:
                    usage = LLMUsage(
                        input_tokens=getattr(chunk_usage, "prompt_tokens", 0) or 0,
                        output_tokens=getattr(chunk_usage, "completion_tokens", 0) or 0,
                    )
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
