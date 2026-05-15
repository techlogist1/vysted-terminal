"""LLM router tests — provider catalog, key validation, chat streaming.

All seven providers are validated against the catalog endpoint. The chat
endpoint is exercised via a fake adapter installed at the
``services.llm.get_provider`` boundary so SSE framing is stable and no
real network call is made.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMUsage
from routers import llm as llm_router


class _FakeProvider:
    def __init__(self, validate_returns: bool = True) -> None:
        self._validate_returns = validate_returns
        self.last_messages: list[Any] | None = None
        self.last_api_key: str | None = None

    async def stream_chat(
        self,
        messages: list[Any],
        model: str,  # noqa: ARG002
        api_key: str | None = None,
        **kwargs: Any,  # noqa: ARG002
    ) -> AsyncIterator[Any]:
        self.last_messages = messages
        self.last_api_key = api_key
        yield LLMDeltaEvent(text="one")
        yield LLMDeltaEvent(text=" two")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2), finish_reason="stop")

    async def validate_key(self, api_key: str | None = None) -> bool:  # noqa: ARG002
        return self._validate_returns


def test_get_providers_returns_seven(client: TestClient) -> None:
    response = client.get("/llm/providers")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    ids = {row["id"] for row in body}
    assert ids == {
        "anthropic",
        "openai",
        "gemini",
        "groq",
        "ollama",
        "deepseek",
        "xai",
    }
    # Ollama is the only one that does not require a key.
    ollama_row = next(row for row in body if row["id"] == "ollama")
    assert ollama_row["requires_key"] is False
    assert ollama_row["default_base_url"]


def test_validate_key_ok(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm_router, "get_provider", lambda *_a, **_k: _FakeProvider(True))
    response = client.post(
        "/llm/keys/validate",
        json={"provider": "anthropic", "api_key": "sk-test"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["detail"] is None


def test_validate_key_unauthorized(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(llm_router, "get_provider", lambda *_a, **_k: _FakeProvider(False))
    response = client.post(
        "/llm/keys/validate",
        json={"provider": "anthropic", "api_key": "sk-bad"},
    )
    assert response.json() == {"ok": False, "detail": "unauthorized or no key supplied"}


def test_validate_key_transport_error_surfaces_detail(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _RaisingProvider:
        async def stream_chat(self, *_a: Any, **_kw: Any) -> AsyncIterator[Any]:  # pragma: no cover
            if False:
                yield None

        async def validate_key(self, api_key: str | None = None) -> bool:
            raise RuntimeError("network down")

    monkeypatch.setattr(llm_router, "get_provider", lambda *_a, **_k: _RaisingProvider())
    response = client.post(
        "/llm/keys/validate",
        json={"provider": "anthropic", "api_key": "sk-test"},
    )
    body = response.json()
    assert body["ok"] is False
    assert "network down" in body["detail"]


def test_chat_streams_sse_frames(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeProvider()
    monkeypatch.setattr(llm_router, "get_provider", lambda *_a, **_k: fake)
    with client.stream(
        "POST",
        "/llm/chat",
        json={
            "provider": "anthropic",
            "model": "claude-opus-4-7",
            "messages": [{"role": "user", "content": "hi"}],
            "api_key": "sk-routed",
        },
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        body = b"".join(response.iter_bytes())
    text = body.decode("utf-8")
    import json

    frames = [
        json.loads(line.removeprefix("data: ")) for line in text.split("\n\n") if line.strip()
    ]
    assert [f["kind"] for f in frames] == ["delta", "delta", "done"]
    assert fake.last_api_key == "sk-routed"


def test_chat_invalid_provider_returns_400(client: TestClient) -> None:
    response = client.post(
        "/llm/chat",
        json={
            "provider": "not-real",
            "model": "x",
            "messages": [],
        },
    )
    # Pydantic rejects the literal at the input boundary, so we get 422 not 400.
    assert response.status_code in {400, 422}
