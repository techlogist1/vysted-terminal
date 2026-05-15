"""Anthropic provider adapter tests.

The SDK is mocked end-to-end — no live API calls. The mock simulates the
``messages.stream`` async-context-manager iterator shape with realistic
event types (``content_block_delta``/``text_delta``, ``thinking_delta``,
``content_block_start``/``tool_use``) so the adapter's event translation
is genuinely exercised.
"""

from __future__ import annotations

from typing import Any

import anthropic
import pytest

from models.llm import LLMMessage
from services.llm.anthropic import AnthropicProvider


class _FakeFinalMessage:
    def __init__(self) -> None:
        self.stop_reason = "end_turn"

        class _Usage:
            input_tokens = 42
            output_tokens = 17
            cache_read_input_tokens = 3
            cache_creation_input_tokens = None

        self.usage = _Usage()


class _Delta:
    def __init__(self, **fields: Any) -> None:
        for key, value in fields.items():
            setattr(self, key, value)


class _Event:
    def __init__(self, type_: str, **fields: Any) -> None:
        self.type = type_
        for key, value in fields.items():
            setattr(self, key, value)


class _FakeStream:
    def __init__(self, events: list[Any], final: Any) -> None:
        self._events = events
        self._final = final

    async def __aenter__(self) -> _FakeStream:
        return self

    async def __aexit__(self, *_: Any) -> None:
        return None

    def __aiter__(self) -> _FakeStream:
        self._iter = iter(self._events)
        return self

    async def __anext__(self) -> Any:
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc

    async def get_final_message(self) -> Any:
        return self._final


class _FakeMessages:
    def __init__(self, stream: _FakeStream) -> None:
        self._stream = stream
        self.last_kwargs: dict[str, Any] | None = None

    def stream(self, **kwargs: Any) -> _FakeStream:
        self.last_kwargs = kwargs
        return self._stream


class _FakeModels:
    def __init__(self, raise_error: BaseException | None = None) -> None:
        self._raise = raise_error
        self.called = False

    async def list(self, limit: int = 1) -> Any:  # noqa: ARG002
        self.called = True
        if self._raise is not None:
            raise self._raise
        return object()


class _FakeAnthropic:
    def __init__(
        self,
        stream: _FakeStream | None = None,
        models: _FakeModels | None = None,
        **_: Any,
    ) -> None:
        self.messages = _FakeMessages(stream) if stream is not None else None
        self.models = models or _FakeModels()


def _patch_client(monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> _FakeAnthropic:
    fake = _FakeAnthropic(**kwargs)
    monkeypatch.setattr(
        anthropic,
        "AsyncAnthropic",
        lambda **_: fake,
    )
    return fake


# ---------------------------------------------------------------------------
# stream_chat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_chat_emits_text_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        _Event(
            "content_block_delta",
            delta=_Delta(type="text_delta", text="Hello"),
        ),
        _Event(
            "content_block_delta",
            delta=_Delta(type="text_delta", text=", world!"),
        ),
    ]
    fake = _patch_client(monkeypatch, stream=_FakeStream(events, _FakeFinalMessage()))
    provider = AnthropicProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[
            LLMMessage(role="system", content="be brief"),
            LLMMessage(role="user", content="hi"),
        ],
        model="claude-opus-4-7",
        api_key="sk-test",
    ):
        out.append(event)
    assert [e.kind for e in out] == ["delta", "delta", "done"]
    assert out[0].text == "Hello"
    assert out[1].text == ", world!"
    assert out[2].usage is not None
    assert out[2].usage.input_tokens == 42
    assert out[2].usage.output_tokens == 17
    assert out[2].finish_reason == "end_turn"
    # The system message must be lifted into the top-level system slot.
    assert fake.messages is not None
    assert fake.messages.last_kwargs is not None
    assert fake.messages.last_kwargs["system"] == "be brief"
    assert fake.messages.last_kwargs["messages"] == [{"role": "user", "content": "hi"}]


@pytest.mark.asyncio
async def test_stream_chat_emits_thinking_and_tool_use(monkeypatch: pytest.MonkeyPatch) -> None:
    events = [
        _Event(
            "content_block_delta",
            delta=_Delta(type="thinking_delta", thinking="Let me consider..."),
        ),
        _Event(
            "content_block_start",
            content_block=_Delta(
                type="tool_use",
                id="tool-1",
                name="get_quote",
                input={"symbol": "AAPL"},
            ),
        ),
        _Event(
            "content_block_delta",
            delta=_Delta(type="text_delta", text="ok"),
        ),
    ]
    _patch_client(monkeypatch, stream=_FakeStream(events, _FakeFinalMessage()))
    provider = AnthropicProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="quote AAPL")],
        model="claude-opus-4-7",
        api_key="sk-test",
    ):
        out.append(event)
    kinds = [e.kind for e in out]
    assert kinds == ["thinking", "tool_use", "delta", "done"]
    assert out[1].name == "get_quote"
    assert out[1].input == {"symbol": "AAPL"}


@pytest.mark.asyncio
async def test_stream_chat_handles_anthropic_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailingMessages:
        def stream(self, **_: Any) -> Any:
            raise anthropic.APIConnectionError(request=object())  # type: ignore[arg-type]

    class _FailingClient:
        def __init__(self, **_: Any) -> None:
            self.messages = _FailingMessages()
            self.models = _FakeModels()

    monkeypatch.setattr(anthropic, "AsyncAnthropic", lambda **_: _FailingClient())
    provider = AnthropicProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="hi")],
        model="claude-opus-4-7",
        api_key="sk-test",
    ):
        out.append(event)
    assert any(e.kind == "error" for e in out)


# ---------------------------------------------------------------------------
# validate_key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_key_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _patch_client(monkeypatch, models=_FakeModels())
    provider = AnthropicProvider()
    assert await provider.validate_key("sk-good") is True
    assert fake.models.called


@pytest.mark.asyncio
async def test_validate_key_false_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch)
    provider = AnthropicProvider()
    assert await provider.validate_key(None) is False


@pytest.mark.asyncio
async def test_validate_key_false_on_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    err = anthropic.AuthenticationError.__new__(anthropic.AuthenticationError)
    Exception.__init__(err, "unauthorized")
    _patch_client(monkeypatch, models=_FakeModels(raise_error=err))
    provider = AnthropicProvider()
    assert await provider.validate_key("sk-bad") is False
