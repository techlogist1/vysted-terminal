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

from collections.abc import AsyncIterator
from typing import Any

import groq

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent


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
        client = self._client(api_key)
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        request_kwargs: dict[str, Any] = {
            "model": model,
            "messages": api_messages,
            "stream": True,
        }
        request_kwargs.update(kwargs)
        try:
            stream = await client.chat.completions.create(**request_kwargs)
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            async for chunk in stream:
                choices = getattr(chunk, "choices", None) or []
                for choice in choices:
                    delta = getattr(choice, "delta", None)
                    if delta is None:
                        continue
                    content = getattr(delta, "content", None)
                    if content:
                        yield LLMDeltaEvent(text=content)
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
