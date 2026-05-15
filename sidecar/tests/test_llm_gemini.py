"""Google Gemini provider adapter tests.

The ``google-genai`` SDK is mocked at the ``Client`` level; the async
``generate_content_stream`` is replaced by an async iterator of fake
response objects whose shape matches the SDK's real output
(``candidates[0].content.parts[i].text``, ``usage_metadata``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from google import genai

from models.llm import LLMMessage
from services.llm.gemini import GeminiProvider


class _Part:
    def __init__(self, text: str | None = None) -> None:
        self.text = text


class _Content:
    def __init__(self, parts: list[_Part]) -> None:
        self.parts = parts


class _Candidate:
    def __init__(self, content: _Content, finish_reason: str | None = None) -> None:
        self.content = content
        self.finish_reason = finish_reason


class _UsageMetadata:
    def __init__(self, prompt: int, candidates: int) -> None:
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates


class _Response:
    def __init__(
        self,
        candidates: list[_Candidate] | None = None,
        usage: _UsageMetadata | None = None,
    ) -> None:
        self.candidates = candidates or []
        self.usage_metadata = usage


async def _iter(items: list[Any]) -> AsyncIterator[Any]:
    for item in items:
        yield item


class _FakeAioModels:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = responses
        self.last_kwargs: dict[str, Any] | None = None

    async def generate_content_stream(self, **kwargs: Any) -> AsyncIterator[Any]:
        self.last_kwargs = kwargs
        return _iter(self._responses)

    async def list(self) -> AsyncIterator[Any]:
        return _iter([object()])


class _FakeAio:
    def __init__(self, models: _FakeAioModels) -> None:
        self.models = models


class _FakeClient:
    def __init__(self, responses: list[Any] | None = None, **_: Any) -> None:
        self.aio = _FakeAio(_FakeAioModels(responses or []))


def _patch_client(monkeypatch: pytest.MonkeyPatch, responses: list[Any] | None = None) -> dict:
    state: dict[str, Any] = {"last": None}

    def factory(**kwargs: Any) -> _FakeClient:
        client = _FakeClient(responses=responses, **kwargs)
        state["last"] = client
        return client

    monkeypatch.setattr(genai, "Client", factory)
    return state


@pytest.mark.asyncio
async def test_stream_chat_emits_text_deltas(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        _Response([_Candidate(_Content([_Part("Hello")]))]),
        _Response(
            [_Candidate(_Content([_Part(", world")]), finish_reason="STOP")],
            usage=_UsageMetadata(8, 3),
        ),
    ]
    state = _patch_client(monkeypatch, responses=responses)
    provider = GeminiProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[
            LLMMessage(role="system", content="be brief"),
            LLMMessage(role="user", content="hi"),
        ],
        model="gemini-2.5-pro",
        api_key="key",
    ):
        out.append(event)
    kinds = [e.kind for e in out]
    assert kinds == ["delta", "delta", "done"]
    assert out[0].text == "Hello"
    assert out[1].text == ", world"
    assert out[2].usage is not None
    assert out[2].usage.input_tokens == 8
    assert out[2].usage.output_tokens == 3
    assert out[2].finish_reason == "STOP"
    aio_models = state["last"].aio.models
    # System lifted to system_instruction; user maps to user role with parts.
    assert aio_models.last_kwargs is not None
    config = aio_models.last_kwargs["config"]
    assert config is not None
    assert config["system_instruction"] == "be brief"
    assert aio_models.last_kwargs["contents"] == [
        {"role": "user", "parts": [{"text": "hi"}]},
    ]


@pytest.mark.asyncio
async def test_assistant_role_maps_to_model_role(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _patch_client(monkeypatch, responses=[])
    provider = GeminiProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[
            LLMMessage(role="user", content="user-one"),
            LLMMessage(role="assistant", content="ack"),
            LLMMessage(role="user", content="user-two"),
        ],
        model="gemini-2.5-pro",
        api_key="key",
    ):
        out.append(event)
    aio_models = state["last"].aio.models
    assert aio_models.last_kwargs is not None
    contents = aio_models.last_kwargs["contents"]
    assert [c["role"] for c in contents] == ["user", "model", "user"]


@pytest.mark.asyncio
async def test_stream_chat_handles_api_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.genai import errors as genai_errors

    class _Failing(_FakeAioModels):
        async def generate_content_stream(self, **_: Any) -> AsyncIterator[Any]:
            raise genai_errors.APIError(500, {"error": {"message": "boom"}})

    class _FailingClient:
        def __init__(self, **_: Any) -> None:
            self.aio = _FakeAio(_Failing([]))

    monkeypatch.setattr(genai, "Client", lambda **kw: _FailingClient(**kw))
    provider = GeminiProvider()
    out: list[Any] = []
    async for event in provider.stream_chat(
        messages=[LLMMessage(role="user", content="hi")],
        model="gemini-2.5-pro",
        api_key="key",
    ):
        out.append(event)
    assert any(e.kind == "error" for e in out)


@pytest.mark.asyncio
async def test_validate_key_false_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch)
    provider = GeminiProvider()
    assert await provider.validate_key(None) is False
