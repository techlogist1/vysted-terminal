"""Google Gemini provider adapter tests.

The ``google-genai`` SDK is mocked at the ``Client`` level; the async
``generate_content_stream`` is replaced by an async iterator of fake
response objects whose shape matches the SDK's real output
(``candidates[0].content.parts[i].text``, ``usage_metadata``).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from google import genai
from google.genai import types

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent
from services.llm.base import is_length_finish
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
    def __init__(
        self,
        prompt: int,
        candidates: int,
        thoughts: int | None = None,
        tool_use_prompt: int | None = None,
    ) -> None:
        self.prompt_token_count = prompt
        self.candidates_token_count = candidates
        self.thoughts_token_count = thoughts
        self.tool_use_prompt_token_count = tool_use_prompt


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
async def test_usage_meters_thinking_and_tool_use_prompt_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-CODE-AGENT-004: a thinking round bills its thoughts as output and the
    tool-use prompt as input, so the BudgetGuard token ceiling sees them."""
    from services.budget_guard import BudgetGuard

    responses = [
        _Response(
            [_Candidate(_Content([_Part("ok")]), finish_reason="STOP")],
            usage=_UsageMetadata(100, 800, thoughts=6000, tool_use_prompt=40),
        ),
    ]
    _patch_client(monkeypatch, responses=responses)
    out = [
        e
        async for e in GeminiProvider().stream_chat(
            messages=[LLMMessage(role="user", content="hi")],
            model="gemini-2.5-pro",
            api_key="key",
        )
    ]
    usage = out[-1].usage
    assert (usage.input_tokens, usage.output_tokens) == (140, 6800)
    guard = BudgetGuard(max_tokens=5000)
    guard.record(usage, provider="gemini", model="gemini-2.5-pro")
    assert guard.breach() is not None


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
    err = next(e for e in out if e.kind == "error")
    # E9: the adapter routed through humanize — raw text behind detail,
    # a stable machine code, and a plain message (not the raw blob).
    assert err.detail is not None
    assert err.code is not None
    assert err.message


@pytest.mark.asyncio
async def test_validate_key_false_when_no_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_client(monkeypatch)
    provider = GeminiProvider()
    assert await provider.validate_key(None) is False


def _patch_list_error(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    class _Models:
        async def list(self) -> Any:
            raise exc

    class _Client:
        def __init__(self, **_: Any) -> None:
            self.aio = type("_Aio", (), {"models": _Models()})()

    monkeypatch.setattr(genai, "Client", _Client)


#: The body Gemini returned for a bogus key (live probe, R15 error-layer-2).
_GEMINI_BAD_KEY_BODY = {
    "error": {
        "code": 400,
        "message": "API key not valid. Please pass a valid API key.",
        "status": "INVALID_ARGUMENT",
        "details": [
            {
                "@type": "type.googleapis.com/google.rpc.ErrorInfo",
                "reason": "API_KEY_INVALID",
                "domain": "googleapis.com",
            }
        ],
    }
}


@pytest.mark.asyncio
async def test_validate_key_false_on_400_invalid_key(monkeypatch: pytest.MonkeyPatch) -> None:
    # R15-CODE-AGENT-003: Gemini says "bad key" with 400, not 401/403; that is a
    # failed validation, not a transport error.
    from google.genai import errors as genai_errors

    _patch_list_error(monkeypatch, genai_errors.ClientError(400, _GEMINI_BAD_KEY_BODY))
    assert await GeminiProvider().validate_key("AIzaSyNOTAREALKEY") is False


@pytest.mark.asyncio
async def test_validate_key_raises_on_other_400(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.genai import errors as genai_errors

    body = {"error": {"code": 400, "message": "Bad request.", "status": "FAILED_PRECONDITION"}}
    _patch_list_error(monkeypatch, genai_errors.ClientError(400, body))
    with pytest.raises(genai_errors.ClientError):
        await GeminiProvider().validate_key("AIzaSyREAL")


def test_gemini_tools_build_a_valid_config_for_every_internal_tool() -> None:
    # R15-LEAD-007: the catalog's JSON Schema (int enums, list-valued ``type``)
    # failed google-genai's OpenAPI-subset ``parameters`` validation, so every
    # Gemini tool turn died before the request left the process.
    from google.genai import types

    from services.agent_tools.schemas import TOOL_SCHEMAS, gemini_tools

    types.GenerateContentConfig(tools=gemini_tools(list(TOOL_SCHEMAS)))


def test_gemini_tools_accept_json_schema_outside_the_openapi_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from google.genai import types

    from services.agent_tools import schemas

    monkeypatch.setitem(
        schemas.TOOL_SCHEMAS,
        "probe_tool",
        {
            "description": "probe",
            "input_schema": {
                "type": "object",
                "properties": {
                    "when": {"type": ["string", "null"]},
                    "target": {"oneOf": [{"type": "string"}, {"type": "integer"}]},
                },
            },
        },
    )
    types.GenerateContentConfig(tools=schemas.gemini_tools(["probe_tool"]))


# ---------------------------------------------------------------------------
# Wire cassettes (R15-AGENT-007): recorded-shape ``streamGenerateContent?alt=sse``
# bodies replayed through the REAL SDK parser over an httpx mock transport, so
# the adapter sees the SDK's own objects (enums, bytes signatures), not fakes.
# ---------------------------------------------------------------------------

_CASSETTES = Path(__file__).parent / "fixtures" / "llm"


def _serve_cassettes(monkeypatch: pytest.MonkeyPatch, *names: str) -> list[dict[str, Any]]:
    """Answer each Gemini request with the next cassette; return the sent bodies."""
    real_client = genai.Client
    bodies = [(_CASSETTES / name).read_bytes() for name in names]
    sent: list[dict[str, Any]] = []

    def _handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith(":streamGenerateContent")
        sent.append(json.loads(request.content))
        body = bodies[len(sent) - 1]
        return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)

    options = types.HttpOptions(async_client_args={"transport": httpx.MockTransport(_handler)})
    monkeypatch.setattr(genai, "Client", lambda **kw: real_client(**kw, http_options=options))
    return sent


async def _replay(monkeypatch: pytest.MonkeyPatch, cassette: str) -> list[Any]:
    _serve_cassettes(monkeypatch, cassette)
    return [
        event
        async for event in GeminiProvider().stream_chat(
            messages=[LLMMessage(role="user", content="check RELIANCE")],
            model="gemini-3-pro-preview",
            api_key="key",
        )
    ]


@pytest.mark.asyncio
async def test_cassette_parallel_calls_arrive_with_args_and_signature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = await _replay(monkeypatch, "gemini_parallel_calls.sse")

    assert [type(e) for e in events] == [
        LLMDeltaEvent,
        LLMToolUseEvent,
        LLMToolUseEvent,
        LLMDoneEvent,
    ]
    first, second = events[1], events[2]
    assert (first.name, first.input) == ("get_terminal_state", {})
    assert first.provider_meta == {"thought_signature": "Q2lJQlZLaHZjM2xuTFdFPQ=="}
    assert (second.name, second.input) == ("read_notes", {"scope": "RELIANCE"})
    assert second.provider_meta is None
    assert first.tool_call_id != second.tool_call_id
    done = events[-1]
    assert done.usage.input_tokens == 2143 + 10
    assert done.usage.output_tokens == 31 + 118
    assert not is_length_finish(done.finish_reason)


@pytest.mark.asyncio
async def test_cassette_contentless_max_tokens_stop_is_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Gemini 2.5 can spend the whole budget thinking and close on a candidate
    # with a MAX_TOKENS finish and no content; the truncation must still surface.
    events = await _replay(monkeypatch, "gemini_max_tokens_contentless.sse")

    assert [e.text for e in events if isinstance(e, LLMDeltaEvent)] == ["RELIANCE trades at"]
    done = events[-1]
    assert isinstance(done, LLMDoneEvent)
    assert is_length_finish(done.finish_reason)
