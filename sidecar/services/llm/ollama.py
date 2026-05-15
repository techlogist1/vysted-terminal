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

from collections.abc import AsyncIterator
from typing import Any

import ollama

from models.llm import (
    LLMDeltaEvent,
    LLMDoneEvent,
    LLMErrorEvent,
    LLMMessage,
    LLMUsage,
)

from .base import LLMProvider, LLMStreamEvent


def _attr(obj: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a dict or an attr-styled SDK object."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


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
        client = self._client()
        api_messages = [{"role": m.role, "content": m.content} for m in messages]
        try:
            stream = await client.chat(
                model=model,
                messages=api_messages,
                stream=True,
                **kwargs,
            )
            usage: LLMUsage | None = None
            finish_reason: str | None = None
            async for chunk in stream:
                message = _attr(chunk, "message")
                if message is not None:
                    content = _attr(message, "content", "") or ""
                    if content:
                        yield LLMDeltaEvent(text=content)
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
