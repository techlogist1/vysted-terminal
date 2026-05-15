"""Google Gemini provider adapter.

Wraps ``google.genai.Client(...).aio.models.generate_content_stream(...)``
(unified ``google-genai`` SDK; the legacy ``google-generativeai`` package is
deprecated). The streaming API yields ``GenerateContentResponse`` objects
whose ``candidates[0].content.parts`` carry the text deltas.

Gemini's role enum is ``"user"`` / ``"model"``, distinct from the OpenAI
``"user"`` / ``"assistant"`` shape; the adapter translates at the boundary.
System instructions go on the top-level ``system_instruction`` field rather
than into the messages list.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from google import genai
from google.genai import errors as genai_errors

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent


def _split_system_and_contents(
    messages: list[LLMMessage],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Split out system messages and translate the rest to ``contents`` shape."""
    system_chunks: list[str] = []
    contents: list[dict[str, Any]] = []
    for message in messages:
        if message.role == "system":
            system_chunks.append(message.content)
            continue
        # Gemini uses "model" for assistant turns and "user" for everything
        # else (including tool results, which are folded into the user turn
        # by upstream code that opts into function calling).
        role = "model" if message.role == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": message.content}]})
    system = "\n\n".join(system_chunks) if system_chunks else None
    return system, contents


class GeminiProvider(LLMProvider):
    """Google Gemini adapter via the unified ``google-genai`` SDK."""

    def _client(self, api_key: str | None) -> genai.Client:
        return genai.Client(api_key=api_key)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        model: str,
        api_key: str | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[LLMStreamEvent]:
        system, contents = _split_system_and_contents(messages)
        config: dict[str, Any] = {}
        if system is not None:
            config["system_instruction"] = system
        config.update(kwargs.pop("config", {}) or {})
        client = self._client(api_key)
        try:
            stream = await client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config or None,
                **kwargs,
            )
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            async for response in stream:
                # Text deltas — Gemini packs them into candidates[i].content.parts.
                candidates = getattr(response, "candidates", None) or []
                for candidate in candidates:
                    content = getattr(candidate, "content", None)
                    if content is None:
                        continue
                    parts = getattr(content, "parts", None) or []
                    for part in parts:
                        text = getattr(part, "text", None)
                        if text:
                            yield LLMDeltaEvent(text=text)
                    reason = getattr(candidate, "finish_reason", None)
                    if reason:
                        finish_reason = str(reason)
                # Usage arrives on every chunk; the final value wins.
                meta = getattr(response, "usage_metadata", None)
                if meta is not None:
                    usage = LLMUsage(
                        input_tokens=getattr(meta, "prompt_token_count", 0) or 0,
                        output_tokens=getattr(meta, "candidates_token_count", 0) or 0,
                    )
            yield LLMDoneEvent(usage=usage, finish_reason=finish_reason)
        except genai_errors.APIError as exc:  # pragma: no cover — network path
            yield LLMErrorEvent(message=f"gemini stream failed: {exc}")
        except Exception as exc:  # pragma: no cover — defensive
            yield LLMErrorEvent(message=f"gemini stream failed: {exc}")

    async def validate_key(self, api_key: str | None = None) -> bool:
        """Probe ``models.list`` — the cheapest authenticated call."""
        if not api_key:
            return False
        try:
            client = self._client(api_key)
            # ``models.list`` returns a pager; resolving it triggers a network
            # round-trip. The SDK does not surface a synchronous "1 page" knob,
            # so we iterate at most one entry.
            async for _ in await client.aio.models.list():
                break
            return True
        except genai_errors.ClientError as exc:
            status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
            if status in {401, 403}:
                return False
            raise
        except genai_errors.APIError:
            raise
