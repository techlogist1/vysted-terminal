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
from fastapi.testclient import TestClient

from models.llm import LLMMessage
from services.llm.ollama import OllamaProvider


async def _iter(items: list[Any]) -> AsyncIterator[Any]:
    for item in items:
        yield item


class _FakeAsyncClient:
    def __init__(self, chunks: list[Any], list_raises: BaseException | None = None) -> None:
        self._chunks = chunks
        self._list_raises = list_raises
        self.chat_calls: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> AsyncIterator[Any]:
        assert kwargs["stream"] is True
        self.chat_calls.append(kwargs)
        return _iter(self._chunks)

    async def list(self) -> Any:
        if self._list_raises is not None:
            raise self._list_raises
        return {"models": [{"model": name} for name in self.pulled]}

    pulled: tuple[str, ...] = ()


def _patch(
    monkeypatch: pytest.MonkeyPatch,
    *,
    chunks: list[Any] | None = None,
    list_raises: BaseException | None = None,
) -> _FakeAsyncClient:
    fake = _FakeAsyncClient(chunks or [], list_raises=list_raises)
    monkeypatch.setattr(ollama, "AsyncClient", lambda **_: fake)
    return fake


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
        model="qwen2.5:7b",
    ):
        out.append(event)
    kinds = [e.kind for e in out]
    assert kinds == ["delta", "delta", "done"]
    assert out[2].usage is not None
    assert out[2].usage.input_tokens == 9
    assert out[2].usage.output_tokens == 6
    assert out[2].finish_reason == "stop"


@pytest.mark.asyncio
async def test_stream_chat_sets_num_ctx_floor(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15 stage0 root cause: Ollama's baked-in 4096 default truncates the
    tool-schema-laden prompt before the user's message gets a turn (empty
    output on qwen2.5:7b, fabrication on llama3.1:8b). Every request must
    carry an explicit options.num_ctx floor high enough to hold the copilot
    agent's ~50 tool schemas plus the prompt."""
    chunks = [
        {
            "message": {"content": ""},
            "done": True,
            "done_reason": "stop",
            "prompt_eval_count": 9,
            "eval_count": 6,
        },
    ]
    fake = _patch(monkeypatch, chunks=chunks)
    provider = OllamaProvider()
    out = [
        e
        async for e in provider.stream_chat(
            messages=[LLMMessage(role="user", content="hi")],
            model="qwen2.5:7b",
        )
    ]
    assert out[-1].kind == "done"
    assert len(fake.chat_calls) == 1
    options = fake.chat_calls[0].get("options")
    assert options is not None
    assert options.get("num_ctx", 0) >= 8192


@pytest.mark.asyncio
async def test_validate_key_true_when_daemon_reachable(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch(monkeypatch)
    provider = OllamaProvider()
    # Ollama is BYOK-free; key is irrelevant.
    assert await provider.validate_key(None) is True


@pytest.mark.asyncio
async def test_validate_key_raises_when_daemon_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stopped daemon is not "no key": it raises so the route says unreachable
    (R15-UI-013; this test used to pin the old ``False`` that erased why)."""
    _patch(monkeypatch, list_raises=ConnectionError("connection refused"))
    provider = OllamaProvider()
    with pytest.raises(ConnectionError):
        await provider.validate_key(None)


def test_validate_route_daemon_down_is_unreachable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch(monkeypatch, list_raises=ConnectionError("connection refused"))
    body = client.post(
        "/llm/keys/validate", json={"provider": "ollama", "model": "qwen2.5:7b"}
    ).json()
    assert body["ok"] is False
    assert body["reason"] == "unreachable"


def test_validate_route_model_not_pulled(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-AGENT-028: a running daemon with the selected model absent is not ready."""
    _patch(monkeypatch)  # daemon up, nothing pulled
    body = client.post(
        "/llm/keys/validate", json={"provider": "ollama", "model": "qwen2.5:7b"}
    ).json()
    assert body["ok"] is False
    assert body["reason"] == "model_not_pulled"
    assert "qwen2.5:7b" in body["detail"]


def test_validate_route_model_pulled_is_ok(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _patch(monkeypatch)
    fake.pulled = ("qwen2.5:7b", "llama3.1:latest")
    for model in ("qwen2.5:7b", "llama3.1"):
        body = client.post("/llm/keys/validate", json={"provider": "ollama", "model": model}).json()
        assert body == {"ok": True, "reason": None, "detail": None}


@pytest.mark.asyncio
async def test_stream_chat_humanizes_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """E9: a stream crash routes through humanize — plain message + machine code,
    raw text behind detail, never a naked provider blob."""

    class _Boom(_FakeAsyncClient):
        async def chat(self, **_: Any) -> Any:
            raise RuntimeError("ollama exploded: connection refused")

    monkeypatch.setattr(ollama, "AsyncClient", lambda **_: _Boom([]))
    provider = OllamaProvider()
    out = [
        e
        async for e in provider.stream_chat(
            messages=[LLMMessage(role="user", content="hi")],
            model="qwen2.5:7b",
        )
    ]
    err = next(e for e in out if e.kind == "error")
    assert err.message and "ollama exploded" not in err.message
    assert err.detail is not None and "ollama exploded" in err.detail
    assert err.code is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ('{"symbol": "RELI', None),  # truncated JSON string -> sentinel
        ('["RELIANCE.NS"]', None),  # valid JSON, not an object -> sentinel
        ('{"symbol": "RELIANCE.NS"}', {"symbol": "RELIANCE.NS"}),
        ({"symbol": "TCS.NS"}, {"symbol": "TCS.NS"}),
        ("", {}),  # a no-argument call
    ],
)
async def test_native_tool_call_arguments_never_coerce_to_empty(
    monkeypatch: pytest.MonkeyPatch, arguments: Any, expected: dict[str, Any] | None
) -> None:
    # R15-AGENT-047 (adapter half): malformed arguments carry the invalid-args
    # sentinel so the model learns its call was wrong.
    from services.llm.base import INVALID_ARGS_SENTINEL

    chunks = [
        {
            "message": {
                "content": "",
                "tool_calls": [{"function": {"name": "price_data", "arguments": arguments}}],
            },
            "done": True,
            "done_reason": "stop",
        },
    ]
    _patch(monkeypatch, chunks=chunks)
    out = [
        e
        async for e in OllamaProvider().stream_chat(
            messages=[LLMMessage(role="user", content="quote RELIANCE")],
            model="llama3.1:8b",
            tool_ids=["price_data"],
        )
    ]
    tool_use = [e for e in out if e.kind == "tool_use"]
    assert len(tool_use) == 1
    if expected is None:
        assert set(tool_use[0].input) == {INVALID_ARGS_SENTINEL}
    else:
        assert tool_use[0].input == expected


async def _ollama_text_round(
    monkeypatch: pytest.MonkeyPatch, text: str, step: int | None = None
) -> list[Any]:
    """A round where the model streams ``text`` as content and no tool_calls,
    in two halves or in ``step``-character tokens."""
    if step is None:
        pieces = [text[: len(text) // 2], text[len(text) // 2 :]]
    else:
        pieces = [text[i : i + step] for i in range(0, len(text), step)]
    chunks: list[dict[str, Any]] = [
        {"message": {"content": piece}, "done": False} for piece in pieces
    ]
    chunks.append({"message": {"content": ""}, "done": True, "done_reason": "stop"})
    _patch(monkeypatch, chunks=chunks)
    return [
        e
        async for e in OllamaProvider().stream_chat(
            messages=[LLMMessage(role="user", content="note that Cochin looks stretched")],
            model="llama3.1:8b",
            tool_ids=["write_note", "price_data"],
        )
    ]


@pytest.mark.asyncio
async def test_leaked_text_tool_call_is_rescued(monkeypatch: pytest.MonkeyPatch) -> None:
    # R15-AGENT-018: the captured llama3.1:8b turn (composer-chat 13) wrote the
    # call as literal JSON text with "parameters"; it must become a tool_use.
    leaked = (
        '{"name": "write_note", "parameters": {"scope": "COCHINSHIP.NS", '
        '"text": "Valuation looks stretched at ~54x trailing P/E."}}'
    )
    out = await _ollama_text_round(monkeypatch, leaked)
    # The rescued call's text is held, not shown (rc1-drive-onboarding-stranger:1).
    assert [e.kind for e in out] == ["tool_use", "done"]
    call = out[0]
    assert call.name == "write_note"
    assert call.input == {
        "scope": "COCHINSHIP.NS",
        "text": "Valuation looks stretched at ~54x trailing P/E.",
    }
    assert call.tool_call_id
    # Two rescued calls never share an id.
    again = await _ollama_text_round(monkeypatch, leaked)
    assert again[0].tool_call_id != call.tool_call_id


_ZOMATO_ROUND = """There is no Zomato data in the market overview. Let me fetch it.

**Tool call:** `price_data(symbol="ZOMATO.NS")`

Result:
```json
{"symbol": "ZOMATO.NS", "name": "Zomato Ltd.", "current_price": 164.4, "currency": "INR"}
```
As per the live data, Zomato's stock price is currently ₹164.4."""


@pytest.mark.asyncio
async def test_rescued_leak_hides_the_call_and_its_made_up_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # rc1-drive-onboarding-stranger:1: the leaked call and the hand-typed
    # "live data" after it streamed before the rescue ran at stream end.
    out = await _ollama_text_round(monkeypatch, _ZOMATO_ROUND, step=3)
    shown = "".join(e.text for e in out if e.kind == "delta")
    assert "164.4" not in shown
    assert shown.startswith("There is no Zomato data in the market overview. Let me fetch it.")
    calls = [e for e in out if e.kind == "tool_use"]
    assert [(c.name, c.input) for c in calls] == [("price_data", {"symbol": "ZOMATO.NS"})]
    assert out[-1].kind == "done"


@pytest.mark.asyncio
async def test_text_that_is_not_a_rescued_call_streams_whole(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prose = 'Try get_quote(symbol="TCS.NS") elsewhere; {"name": "screener_run"} is not mine.'
    out = await _ollama_text_round(monkeypatch, prose, step=4)
    # Unoffered names: the chunks pass through byte for byte.
    assert [e.text for e in out if e.kind == "delta"] == [
        prose[i : i + 4] for i in range(0, len(prose), 4)
    ]
    # An offered name that never parses as a call is held, then shown whole.
    held = 'Pricing works like price_data(symbol=lookup("TCS")) under the hood.'
    out = await _ollama_text_round(monkeypatch, held, step=4)
    assert "".join(e.text for e in out if e.kind == "delta") == held
    assert [e.kind for e in out if e.kind != "delta"] == ["done"]


@pytest.mark.asyncio
async def test_leaked_json_for_a_tool_not_offered_stays_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = await _ollama_text_round(
        monkeypatch, '{"name": "screener_run", "parameters": {"sector": "Defence"}}'
    )
    assert [e.kind for e in out] == ["delta", "delta", "done"]


@pytest.mark.asyncio
async def test_think_span_split_across_three_chunks_is_folded_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-LEAD-018 class pin: a qwen3-style ``<think>`` block in content, its
    tags cut across three chunks, reaches the UI as thinking, not as the answer."""
    _patch(
        monkeypatch,
        chunks=[
            {"message": {"content": "<thi"}, "done": False},
            {"message": {"content": "nk>The user wants the P/E.</thi"}, "done": False},
            {"message": {"content": "nk>\n\nThe P/E is 30."}, "done": False},
            {"message": {"content": ""}, "done": True, "done_reason": "stop"},
        ],
    )
    out = [
        event
        async for event in OllamaProvider().stream_chat(
            messages=[LLMMessage(role="user", content="P/E?")], model="qwen3:8b"
        )
    ]
    assert "".join(e.text for e in out if e.kind == "delta") == "\n\nThe P/E is 30."
    assert "".join(e.text for e in out if e.kind == "thinking") == "The user wants the P/E."
