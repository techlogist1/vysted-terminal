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


@pytest.mark.asyncio
async def test_stream_chat_humanizes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """E9: a stream crash routes through humanize — plain message + machine code,
    raw text behind detail, never a naked provider blob."""

    class _Boom(_FakeCompletions):
        async def create(self, **_: Any) -> Any:
            raise RuntimeError("groq exploded: 429 rate limit")

    def _factory(**_: Any) -> Any:
        client = _FakeGroq()
        client.chat = _FakeChat(_Boom([]))
        return client

    monkeypatch.setattr(groq, "AsyncGroq", _factory)
    provider = GroqProvider()
    out = [
        e
        async for e in provider.stream_chat(
            messages=[LLMMessage(role="user", content="hi")],
            model="llama-3.3-70b-versatile",
        )
    ]
    err = next(e for e in out if e.kind == "error")
    assert err.message and "groq exploded" not in err.message
    assert err.detail is not None and "groq exploded" in err.detail
    assert err.code is not None


class _Fn:
    def __init__(self, name: str | None, arguments: str | None) -> None:
        self.name = name
        self.arguments = arguments


class _ToolCallDelta:
    def __init__(self, index: int, fn: _Fn, id_: str | None = None) -> None:
        self.index = index
        self.id = id_
        self.function = fn


class _ToolDelta:
    def __init__(self, tool_calls: list[_ToolCallDelta]) -> None:
        self.content = None
        self.tool_calls = tool_calls


async def _groq_tool_round(monkeypatch: pytest.MonkeyPatch, fragments: list[str]) -> Any:
    """One streamed Groq round whose single tool call's args arrive in fragments."""
    first, *rest = fragments
    head = _ToolDelta([_ToolCallDelta(0, _Fn("price_data", first), "call_1")])
    chunks = [
        _Chunk([_Choice(head)]),  # type: ignore[arg-type]
        *(_Chunk([_Choice(_ToolDelta([_ToolCallDelta(0, _Fn(None, f))]))]) for f in rest),  # type: ignore[arg-type]
        _Chunk([_Choice(_Delta(), finish_reason="tool_calls")]),
    ]
    _patch(monkeypatch, chunks=chunks)
    out = [
        e
        async for e in GroqProvider().stream_chat(
            messages=[LLMMessage(role="user", content="quote RELIANCE")],
            model="llama-3.3-70b-versatile",
            api_key="gsk-test",
        )
    ]
    return next(e for e in out if e.kind == "tool_use")


@pytest.mark.asyncio
async def test_truncated_tool_args_stamp_the_sentinel_not_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R15-AGENT-047 (adapter half): a truncated argument fragment must reach the
    # runtime as an invalid-args result, never as a silent {} call.
    from services.llm.base import INVALID_ARGS_SENTINEL

    event = await _groq_tool_round(monkeypatch, ['{"symbol": "RELI'])
    assert event.name == "price_data"
    assert set(event.input) == {INVALID_ARGS_SENTINEL}
    assert '{"symbol": "RELI' in event.input[INVALID_ARGS_SENTINEL]


@pytest.mark.asyncio
async def test_fragmented_tool_args_parse_and_empty_args_stay_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event = await _groq_tool_round(monkeypatch, ['{"symbol": "RELI', 'ANCE.NS"}'])
    assert event.input == {"symbol": "RELIANCE.NS"}
    # A no-argument call streams no fragments: {} is legal there.
    event = await _groq_tool_round(monkeypatch, [""])
    assert event.input == {}
