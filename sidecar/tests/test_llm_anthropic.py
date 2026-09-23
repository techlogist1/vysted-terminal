"""Anthropic provider adapter tests.

The SDK is mocked end-to-end — no live API calls. The mock simulates the
``messages.stream`` async-context-manager iterator shape with realistic
event types (``content_block_delta``/``text_delta``, ``thinking_delta``,
``content_block_start``/``tool_use``) so the adapter's event translation
is genuinely exercised. Tool-use tests replay real SSE bytes through the real
SDK parser (httpx mock transport), because a hand-built event can carry a
shape the API never sends.
"""

from __future__ import annotations

import json
from typing import Any

import anthropic
import httpx
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
        model="claude-opus-4-8",
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


def _sse(*frames: dict[str, Any]) -> bytes:
    """Encode Messages-API frames as the SSE bytes the API sends."""
    return "".join(
        "event: " + frame["type"] + "\ndata: " + json.dumps(frame) + "\n\n" for frame in frames
    ).encode()


_MESSAGE_START = {
    "type": "message_start",
    "message": {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-opus-4-8",
        "content": [],
        "stop_reason": None,
        "stop_sequence": None,
        "usage": {"input_tokens": 42, "output_tokens": 1},
    },
}

_MESSAGE_END = [
    {
        "type": "message_delta",
        "delta": {"stop_reason": "tool_use", "stop_sequence": None},
        "usage": {"output_tokens": 30},
    },
    {"type": "message_stop"},
]


def _tool_block(index: int, tool_id: str, name: str, fragments: list[str]) -> list[dict[str, Any]]:
    """A streamed tool_use block: the start frame carries ``input: {}``."""
    return [
        {
            "type": "content_block_start",
            "index": index,
            "content_block": {"type": "tool_use", "id": tool_id, "name": name, "input": {}},
        },
        *(
            {
                "type": "content_block_delta",
                "index": index,
                "delta": {"type": "input_json_delta", "partial_json": fragment},
            }
            for fragment in fragments
        ),
        {"type": "content_block_stop", "index": index},
    ]


async def _stream_real_sdk(monkeypatch: pytest.MonkeyPatch, body: bytes) -> list[Any]:
    """Run the adapter over ``body`` through the real SDK stream parser."""
    real_client = anthropic.AsyncAnthropic

    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    monkeypatch.setattr(
        anthropic,
        "AsyncAnthropic",
        lambda **kw: real_client(
            **kw, http_client=httpx.AsyncClient(transport=httpx.MockTransport(_handler))
        ),
    )
    provider = AnthropicProvider()
    return [
        event
        async for event in provider.stream_chat(
            messages=[LLMMessage(role="user", content="quote RELIANCE")],
            model="claude-opus-4-8",
            api_key="sk-test",
        )
    ]


@pytest.mark.asyncio
async def test_stream_chat_tool_use_carries_streamed_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R15-AGENT-004: the API starts a tool_use block with ``input: {}`` and
    # streams the arguments as input_json_delta fragments; the event must
    # carry the accumulated arguments. (This replaced a hand-built fixture
    # whose start block was pre-filled, a shape the API never sends.)
    body = _sse(
        _MESSAGE_START,
        {
            "type": "content_block_start",
            "index": 0,
            "content_block": {"type": "thinking", "thinking": "", "signature": ""},
        },
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "thinking_delta", "thinking": "Let me consider..."},
        },
        {"type": "content_block_stop", "index": 0},
        *_tool_block(1, "toolu_01", "get_quote", ['{"symbol": "RELI', 'ANCE.NS"}']),
        *_MESSAGE_END,
    )
    out = await _stream_real_sdk(monkeypatch, body)
    assert [e.kind for e in out] == ["thinking", "tool_use", "done"]
    assert out[1].tool_call_id == "toolu_01"
    assert out[1].name == "get_quote"
    assert out[1].input == {"symbol": "RELIANCE.NS"}
    assert out[2].finish_reason == "tool_use"


@pytest.mark.asyncio
async def test_stream_chat_two_tool_blocks_arrive_complete_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = _sse(
        _MESSAGE_START,
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": "Checking both."},
        },
        {"type": "content_block_stop", "index": 0},
        *_tool_block(1, "toolu_a", "price_data", ['{"symbol": "TCS.NS", ', '"period": "1y"}']),
        *_tool_block(2, "toolu_b", "news", ['{"sym', 'bol": "INFY.NS", "limit"', ": 5}"]),
        *_MESSAGE_END,
    )
    out = await _stream_real_sdk(monkeypatch, body)
    assert [e.kind for e in out] == ["delta", "tool_use", "tool_use", "done"]
    assert [(e.tool_call_id, e.name, e.input) for e in out[1:3]] == [
        ("toolu_a", "price_data", {"symbol": "TCS.NS", "period": "1y"}),
        ("toolu_b", "news", {"symbol": "INFY.NS", "limit": 5}),
    ]


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
        model="claude-opus-4-8",
        api_key="sk-test",
    ):
        out.append(event)
    assert any(e.kind == "error" for e in out)
    err = next(e for e in out if e.kind == "error")
    # E9: the adapter routed through humanize — raw text behind detail,
    # a stable machine code, and a plain message (not the raw blob).
    assert err.detail is not None
    assert err.code is not None
    assert err.message


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
