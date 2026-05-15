"""OpenAI provider adapter tests (also exercises DeepSeek + xAI dispatch).

The SDK is mocked end-to-end via a simple async iterator returning chunk
objects shaped like the real ``ChatCompletionChunk``. Authentication
errors and permission errors map to ``validate_key=False`` without
raising; transport errors propagate.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import openai
import pytest

from models.llm import LLMMessage
from services.llm import (
    DEEPSEEK_BASE_URL,
    XAI_BASE_URL,
    get_provider,
)
from services.llm.openai import OpenAIProvider


class _Delta:
    def __init__(self, **fields: Any) -> None:
        for key, value in fields.items():
            setattr(self, key, value)


class _Choice:
    def __init__(self, delta: _Delta, finish_reason: str | None = None) -> None:
        self.delta = delta
        self.finish_reason = finish_reason


class _Usage:
    def __init__(self, prompt: int, completion: int) -> None:
        self.prompt_tokens = prompt
        self.completion_tokens = completion


class _Chunk:
    def __init__(
        self,
        choices: list[_Choice] | None = None,
        usage: _Usage | None = None,
    ) -> None:
        self.choices = choices or []
        self.usage = usage


async def _make_iter(chunks: list[Any]) -> AsyncIterator[Any]:
    for chunk in chunks:
        yield chunk


class _FakeCompletions:
    def __init__(self, chunks: list[Any]) -> None:
        self._chunks = chunks
        self.last_kwargs: dict[str, Any] | None = None

    async def create(self, **kwargs: Any) -> AsyncIterator[Any]:
        self.last_kwargs = kwargs
        assert kwargs["stream"] is True
        return _make_iter(self._chunks)


class _FakeChat:
    def __init__(self, completions: _FakeCompletions) -> None:
        self.completions = completions


class _FakeModels:
    def __init__(self, raise_error: BaseException | None = None) -> None:
        self._raise = raise_error
        self.called = False

    async def list(self) -> Any:
        self.called = True
        if self._raise is not None:
            raise self._raise
        return object()


class _FakeOpenAI:
    def __init__(
        self,
        chunks: list[Any] | None = None,
        models: _FakeModels | None = None,
        **kwargs: Any,
    ) -> None:
        self.base_url = kwargs.get("base_url")
        self.chat = _FakeChat(_FakeCompletions(chunks or []))
        self.models = models or _FakeModels()


def _patch_client(
    monkeypatch: pytest.MonkeyPatch,
    *,
    chunks: list[Any] | None = None,
    models: _FakeModels | None = None,
) -> dict[str, Any]:
    state: dict[str, Any] = {"last": None}

    def factory(**kwargs: Any) -> _FakeOpenAI:
        client = _FakeOpenAI(chunks=chunks, models=models, **kwargs)
        state["last"] = client
        return client

    monkeypatch.setattr(openai, "AsyncOpenAI", factory)
    return state


# ---------------------------------------------------------------------------
# stream_chat
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_chat_emits_text_deltas_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    chunks = [
        _Chunk([_Choice(_Delta(content="Hello"))]),
        _Chunk([_Choice(_Delta(content=", "), finish_reason=None)]),
        _Chunk([_Choice(_Delta(content="world"), finish_reason="stop")]),
        _Chunk([], usage=_Usage(prompt=12, completion=4)),
    ]
    state = _patch_client(monkeypatch, chunks=chunks)
    provider = OpenAIProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4.1-mini",
        api_key="sk-test",
    ):
        out.append(event)
    kinds = [e.kind for e in out]
    assert kinds == ["delta", "delta", "delta", "done"]
    assert out[3].usage is not None
    assert out[3].usage.input_tokens == 12
    assert out[3].usage.output_tokens == 4
    assert out[3].finish_reason == "stop"
    completions = state["last"].chat.completions
    assert completions.last_kwargs is not None
    assert completions.last_kwargs["model"] == "gpt-4.1-mini"


@pytest.mark.asyncio
async def test_stream_chat_emits_tool_use_for_function_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _ToolFunction:
        def __init__(self, name: str, arguments: str) -> None:
            self.name = name
            self.arguments = arguments

    class _ToolCall:
        def __init__(self, id_: str, function: _ToolFunction) -> None:
            self.id = id_
            self.function = function

    chunks = [
        _Chunk(
            [
                _Choice(
                    _Delta(
                        content=None,
                        tool_calls=[
                            _ToolCall("call-1", _ToolFunction("get_quote", '{"symbol":'))
                        ],
                    )
                )
            ]
        ),
        _Chunk(
            [
                _Choice(
                    _Delta(
                        content=None,
                        tool_calls=[_ToolCall("call-1", _ToolFunction("get_quote", '"AAPL"}'))],
                    )
                )
            ]
        ),
        _Chunk([_Choice(_Delta(content=""), finish_reason="tool_calls")]),
    ]
    _patch_client(monkeypatch, chunks=chunks)
    provider = OpenAIProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="quote AAPL")],
        model="gpt-4.1-mini",
        api_key="sk-test",
    ):
        out.append(event)
    tool_use_events = [e for e in out if e.kind == "tool_use"]
    assert len(tool_use_events) == 2
    assert tool_use_events[0].name == "get_quote"
    assert tool_use_events[0].input == {"arguments_delta": '{"symbol":'}
    assert tool_use_events[1].input == {"arguments_delta": '"AAPL"}'}


@pytest.mark.asyncio
async def test_stream_chat_emits_error_on_openai_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FailingClient:
        def __init__(self, **_: Any) -> None:
            class _FC:
                async def create(self, **_: Any) -> Any:
                    raise openai.APIConnectionError(request=object())  # type: ignore[arg-type]

            class _FChat:
                completions = _FC()

            self.chat = _FChat()
            self.models = _FakeModels()

    monkeypatch.setattr(openai, "AsyncOpenAI", lambda **_: _FailingClient())
    provider = OpenAIProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="hi")],
        model="gpt-4.1-mini",
        api_key="sk-test",
    ):
        out.append(event)
    assert any(e.kind == "error" for e in out)


# ---------------------------------------------------------------------------
# validate_key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_key_true_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_client(monkeypatch)
    provider = OpenAIProvider()
    assert await provider.validate_key("sk-good") is True
    assert state["last"].models.called


@pytest.mark.asyncio
async def test_validate_key_false_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch)
    provider = OpenAIProvider()
    assert await provider.validate_key(None) is False


@pytest.mark.asyncio
async def test_validate_key_false_on_auth_error(monkeypatch: pytest.MonkeyPatch) -> None:
    err = openai.AuthenticationError.__new__(openai.AuthenticationError)
    Exception.__init__(err, "unauthorized")
    _patch_client(monkeypatch, models=_FakeModels(raise_error=err))
    provider = OpenAIProvider()
    assert await provider.validate_key("sk-bad") is False


# ---------------------------------------------------------------------------
# DeepSeek + xAI dispatch (factory wires base_url correctly)
# ---------------------------------------------------------------------------


def test_get_provider_dispatches_deepseek_through_openai_base_url() -> None:
    provider = get_provider("deepseek")
    assert isinstance(provider, OpenAIProvider)
    # ``_base_url`` and ``_provider_id`` are deliberately private but stable.
    assert provider._base_url == DEEPSEEK_BASE_URL
    assert provider._provider_id == "deepseek"


def test_get_provider_dispatches_xai_through_openai_base_url() -> None:
    provider = get_provider("xai")
    assert isinstance(provider, OpenAIProvider)
    assert provider._base_url == XAI_BASE_URL
    assert provider._provider_id == "xai"


def test_get_provider_unknown_raises() -> None:
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_provider("not-real")  # type: ignore[arg-type]
