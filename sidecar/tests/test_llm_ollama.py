"""Ollama provider adapter tests.

Ollama's SDK returns dict-shaped chunks rather than typed objects. The
mock matches that shape exactly so the adapter's dict-or-attr tolerance is
genuinely exercised.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import ollama
import pytest

from models.llm import LLMMessage
from services.llm.ollama import OllamaProvider


async def _iter(items: list[Any]) -> AsyncIterator[Any]:
    for item in items:
        yield item


class _FakeAsyncClient:
    def __init__(self, chunks: list[Any], list_raises: BaseException | None = None) -> None:
        self._chunks = chunks
        self._list_raises = list_raises

    async def chat(self, **kwargs: Any) -> AsyncIterator[Any]:
        assert kwargs["stream"] is True
        return _iter(self._chunks)

    async def list(self) -> Any:
        if self._list_raises is not None:
            raise self._list_raises
        return {"models": []}


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    chunks: list[Any] | None = None,
    list_raises: BaseException | None = None,
) -> None:
    monkeypatch.setattr(
        ollama,
        "AsyncClient",
        lambda **_: _FakeAsyncClient(chunks or [], list_raises=list_raises),
    )


@pytest.mark.asyncio
async def test_stream_chat_emits_dict_deltas_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        {"message": {"content": "Hello"}, "done": False},
        {"message": {"content": ", world"}, "done": False},
        {
            "message": {"content": ""},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 9,
            "eval_count": 6,
        },
    ]
    _patch(monkeypatch, chunks=chunks)
    provider = OllamaProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="hi")],
        model="llama3.1:8b",
    ):
        out.append(event)
    kinds = [e.kind for e in out]
    assert kinds == ["delta", "delta", "done"]
    assert out[2].usage is not None
    assert out[2].usage.input_tokens == 9
    assert out[2].usage.output_tokens == 6
    assert out[2].finish_reason == "stop"


@pytest.mark.asyncio
async def test_validate_key_true_when_daemon_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    provider = OllamaProvider()
    # Ollama is BYOK-free; key is irrelevant.
    assert await provider.validate_key(None) is True


@pytest.mark.asyncio
async def test_validate_key_false_when_daemon_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch, list_raises=RuntimeError("connection refused"))
    provider = OllamaProvider()
    assert await provider.validate_key(None) is False
