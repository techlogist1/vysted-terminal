"""Agents router tests — ``GET /agents`` and ``POST /agents/{id}/invoke`` SSE.

The provider factory is replaced with a fake that yields a deterministic
short stream so the SSE-framing assertions are stable.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMUsage
from services import agent_runtime


class _FakeProvider:
    async def stream_chat(
        self,
        messages: list[Any],  # noqa: ARG002
        model: str,  # noqa: ARG002
        api_key: str | None = None,  # noqa: ARG002
        **kwargs: Any,  # noqa: ARG002
    ) -> AsyncIterator[Any]:
        yield LLMDeltaEvent(text="Hi")
        yield LLMDeltaEvent(text=" there")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=2))


@pytest.fixture(autouse=True)
def _reload_runtime() -> None:
    agent_runtime.reload()


def test_list_agents_returns_roster(client: TestClient) -> None:
    response = client.get("/agents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 13
    ids = {row["id"] for row in body}
    assert "buffett" in ids
    assert "strategy_critic" in ids
    # The wire shape should NOT include the system_prompt field; the summary
    # surface is deliberately narrower than the full spec.
    for row in body:
        assert "system_prompt" not in row
        assert "systemPrompt" not in row
        assert "philosophy" in row
        assert "default_provider" in row


def test_invoke_unknown_agent_returns_404(client: TestClient) -> None:
    response = client.post(
        "/agents/does-not-exist/invoke",
        json={"prompt": "hi"},
    )
    assert response.status_code == 404


def test_action_ack_records_to_the_ledger(client: TestClient) -> None:
    """R10 E3.3: the frontend's host-action read-back lands in the ack ledger
    keyed by tool_call_id, with the optional applied-brief identity."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    resp = client.post(
        "/agents/actions/ack",
        json={
            "tool_call_id": "call-7",
            "status": "kept_previous",
            "brief": {"run_id": "r1", "symbol": "NVDA", "source_count": 5},
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    entry = action_ledger.get("call-7")
    assert entry is not None
    assert entry["status"] == "kept_previous"
    assert entry["brief"]["symbol"] == "NVDA"
    # camelCase spelling resolves too (populate_by_name).
    assert (
        client.post(
            "/agents/actions/ack", json={"toolCallId": "call-8", "status": "applied"}
        ).status_code
        == 200
    )
    assert action_ledger.get("call-8") is not None
    action_ledger.reset_for_tests()


def test_action_ack_rejects_unknown_status(client: TestClient) -> None:
    resp = client.post("/agents/actions/ack", json={"tool_call_id": "call-9", "status": "exploded"})
    assert resp.status_code == 422


def test_action_ledger_entries_expire(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ledger entries honour the TTL — an abandoned stream never leaks acks."""
    from services import action_ledger

    action_ledger.reset_for_tests()
    monkeypatch.setattr(action_ledger, "TTL_SECONDS", -1.0)  # expires immediately
    action_ledger.record("call-old", "applied")
    assert action_ledger.get("call-old") is None
    action_ledger.reset_for_tests()


def test_invoke_last_resort_guard_yields_human_error_frame(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """E9 seam: the router's last-resort guard humanizes the crash — a plain
    ``message`` + ``action`` + machine ``code``, with the RAW text in ``detail``
    (behind the UI's "Show details" toggle), never a naked blob in the message —
    and still closes the stream with a done frame."""

    async def _boom(**_kwargs: object):  # noqa: ANN202
        raise RuntimeError("provider exploded mid-stream")
        yield  # pragma: no cover — makes this an async generator

    monkeypatch.setattr(agent_runtime, "invoke_agent", _boom)
    with client.stream("POST", "/agents/buffett/invoke", json={"prompt": "x"}) as response:
        body = b"".join(response.iter_bytes())
    import json

    frames = [
        json.loads(line.removeprefix("data: "))
        for line in body.decode().split("\n\n")
        if line.strip()
    ]
    assert [f["kind"] for f in frames] == ["error", "done"]
    err = frames[0]
    # Plain-language message — NOT the raw provider blob.
    assert err["message"] and "provider exploded mid-stream" not in err["message"]
    assert err["action"]  # a next step is offered
    assert err["code"]  # a stable machine tag
    # The raw text is preserved for the "Show details" toggle.
    assert "provider exploded mid-stream" in err["detail"]


def test_invoke_streams_sse_frames(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: _FakeProvider())
    with client.stream(
        "POST",
        "/agents/buffett/invoke",
        json={"prompt": "is AAPL cheap?"},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = b"".join(response.iter_bytes())
    text = body.decode("utf-8")
    # Each frame is one ``data: <json>\n\n`` line.
    frames = [line for line in text.split("\n\n") if line.strip()]
    assert len(frames) == 3
    assert frames[0].startswith("data: ")
    import json

    parsed = [json.loads(f.removeprefix("data: ")) for f in frames]
    assert [p["kind"] for p in parsed] == ["delta", "delta", "done"]
    assert parsed[0]["text"] == "Hi"
    assert parsed[1]["text"] == " there"
    assert parsed[2]["usage"]["input_tokens"] == 5
