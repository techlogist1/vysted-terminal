"""Groq provider adapter tests.

Groq's SDK is OpenAI-shaped but lives in the ``groq`` namespace with its
own error hierarchy. The mock follows the same chunk shape — choices with
``delta.content`` and an optional terminal usage block — plus Groq's
``x_groq.usage`` provenance shape.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import groq
import pytest

from models.llm import LLMMessage
from services.llm.groq import GroqProvider


class _Delta:
    def __init__(self, content: str | None = None) -> None:
        self.content = content


class _Choice:
    def __init__(self, delta: _Delta, finish_reason: str | None = None) -> None:
        self.delta = delta
        self.finish_reason = finish_reason


class _Usage:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class _XGroq:
    def __init__(self, usage: _Usage | None = None) -> None:
        self.usage = usage


class _Chunk:
    def __init__(
        self,
        choices: list[_Choice] | None = None,
        x_groq: _XGroq | None = None,
    ) -> None:
        self.choices = choices or []
        self.x_groq = x_groq


async def _iter(items: list[Any]) -> AsyncIterator[Any]:
    for item in items:
        yield item


class _FakeCompletions:
    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks

    async def create(self, **kwargs: Any) -> AsyncIterator[Any]:
        assert kwargs["stream"] is True
        return _iter(self._chunks)


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeModels:
    def __init__(self, raise_error: BaseException | None = None) -> None:
        self._raise = raise_error

    async def list(self) -> Any:
        if self._raise is not None:
            raise self._raise
        return object()


class _FakeGroq:
    def __init__(self, chunks: list[Any] | None = None, models: _FakeModels | None = None) -> None:
        self.chat = _FakeChat(_FakeCompletions(chunks or []))
        self.models = models or _FakeModels()


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    chunks: list[Any] | None = None,
    models: _FakeModels | None = None,
) -> None:
    monkeypatch.setattr(groq, "AsyncGroq", lambda **_: _FakeGroq(chunks=chunks, models=models))


@pytest.mark.asyncio
async def test_stream_chat_emits_deltas_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        _Chunk([_Choice(_Delta(content="Hello"))]),
        _Chunk([_Choice(_Delta(content=", world"), finish_reason="stop")]),
        _Chunk([], x_groq=_XGroq(usage=_Usage(prompt=5, completion=2))),
    ]
    _patch(monkeypatch, chunks=chunks)
    provider = GroqProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="hi")],
        model="llama-3.3-70b-versatile",
        api_key="gsk-test",
    ):
        out.append(event)
    kinds = [e.kind for e in out]
    assert kinds == ["delta", "delta", "done"]
    assert out[2].usage is not None
    assert out[2].usage.input_tokens == 5
    assert out[2].usage.output_tokens == 2
    assert out[2].finish_reason == "stop"


@pytest.mark.asyncio
async def test_validate_key_false_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    provider = GroqProvider()
    assert await provider.validate_key(None) is False


@pytest.mark.asyncio
async def test_validate_key_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    provider = GroqProvider()
    assert await provider.validate_key("gsk-test") is True


@pytest.mark.asyncio
async def test_validate_key_false_on_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    err = groq.AuthenticationError.__new__(groq.AuthenticationError)
    Exception.__init__(err, "unauthorized")
    _patch(monkeypatch, models=_FakeModels(raise_error=err))
    provider = GroqProvider()
    assert await provider.validate_key("bad") is False
