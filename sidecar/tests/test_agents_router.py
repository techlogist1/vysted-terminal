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


def test_list_agents_returns_twelve(client: TestClient) -> None:
    response = client.get("/agents")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 12
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
