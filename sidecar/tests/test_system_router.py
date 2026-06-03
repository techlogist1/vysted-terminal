"""System router tests (Track D) — /system/hardware.

The device profile is detected from the host, so assertions stay host-independent
(shape + invariants). The ollama probe is mocked so the test is deterministic and
never depends on a running daemon.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

import app as app_module
from routers import system


@pytest.fixture
def client() -> TestClient:
    return TestClient(app_module.create_app())


def test_hardware_reports_device_and_reference_candidates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # No ollama daemon → empty model list, never an error.
    async def _no_ollama(_device: Any) -> list[dict[str, Any]]:
        return []

    monkeypatch.setattr(system, "_score_ollama_models", _no_ollama)

    resp = client.get("/system/hardware")
    assert resp.status_code == 200
    body = resp.json()

    dev = body["device"]
    assert dev["ramGib"] > 0
    assert 0 < dev["gpuBudgetGib"] <= dev["ramGib"]
    assert dev["totalCores"] >= 1
    assert body["ollama"]["models"] == []

    # The reference candidates always score; each carries a verdict + ctx_max.
    refs = body["referenceCandidates"]
    assert any("Tongyi" in c["name"] for c in refs)
    for c in refs:
        assert c["verdict"] in ("green", "marginal", "red")
        assert "ctxMax" in c and "reason" in c
        # Tongyi is MoE — its throughput note must call that out.
        if "Tongyi" in c["name"]:
            assert "moe" in c["signals"]


def test_ollama_models_are_scored_when_present(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "models": [
                    {
                        "name": "qwen2.5:7b",
                        "size": 4_683_087_332,
                        "details": {"parameter_size": "7.6B", "quantization_level": "Q4_K_M"},
                    }
                ]
            }

    class _Client:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        async def get(self, _url: str) -> _Resp:
            return _Resp()

    monkeypatch.setattr(system.httpx, "AsyncClient", _Client)

    resp = client.get("/system/hardware")
    assert resp.status_code == 200
    models = resp.json()["ollama"]["models"]
    assert len(models) == 1
    assert models[0]["name"] == "qwen2.5:7b"
    assert models[0]["verdict"] in ("green", "marginal", "red")


def test_ollama_probe_failure_is_silent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Boom:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> _Boom:
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        async def get(self, _url: str) -> Any:
            raise OSError("connection refused")

    monkeypatch.setattr(system.httpx, "AsyncClient", _Boom)
    resp = client.get("/system/hardware")
    assert resp.status_code == 200
    assert resp.json()["ollama"]["models"] == []


# --- onboarding: local-model recommendation + ollama status/pull (Track 2) ---


def test_local_model_recommendation_shape(client: TestClient) -> None:
    resp = client.get("/system/local-model-recommendation")
    assert resp.status_code == 200
    body = resp.json()
    assert body["device"]["ramGib"] > 0
    # Every onboarding candidate is scored with a verdict.
    names = {c["name"] for c in body["candidates"]}
    assert {"qwen3:8b", "qwen2.5-coder:7b", "llama3.1:8b"} <= names
    for c in body["candidates"]:
        assert c["verdict"] in ("green", "marginal", "red")
    # recommended is a green/marginal candidate or null (device can't host any).
    rec = body["recommended"]
    assert rec is None or (rec["verdict"] in ("green", "marginal") and rec["name"] in names)


def test_ollama_status_not_running_when_daemon_absent(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Boom:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> _Boom:
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        async def get(self, _url: str) -> Any:
            raise OSError("connection refused")

    monkeypatch.setattr(system.httpx, "AsyncClient", _Boom)
    resp = client.get("/system/ollama/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["running"] is False
    assert body["models"] == []


def test_ollama_status_lists_models_when_running(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Resp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"models": [{"name": "qwen3:8b"}, {"name": "llama3.1:8b"}]}

    class _Client:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def __aenter__(self) -> _Client:
            return self

        async def __aexit__(self, *a: Any) -> None:
            return None

        async def get(self, _url: str) -> _Resp:
            return _Resp()

    monkeypatch.setattr(system.httpx, "AsyncClient", _Client)
    resp = client.get("/system/ollama/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["running"] is True
    assert body["models"] == ["qwen3:8b", "llama3.1:8b"]


def test_ollama_pull_streams_progress(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    import ollama

    class _FakeClient:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def pull(self, model: str, *, stream: bool) -> Any:
            async def _gen() -> Any:
                yield {"status": "pulling manifest", "total": None, "completed": None}
                yield {"status": "downloading", "total": 100, "completed": 100}

            return _gen()

    monkeypatch.setattr(ollama, "AsyncClient", _FakeClient)
    resp = client.post("/system/ollama/pull", params={"model": "qwen3:8b"})
    assert resp.status_code == 200
    # SSE frames: the progress events plus a terminal done event.
    assert "downloading" in resp.text
    assert '"done": true' in resp.text


def test_ollama_pull_reports_error_as_stream_event(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ollama

    class _BoomClient:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        async def pull(self, model: str, *, stream: bool) -> Any:
            raise RuntimeError("daemon down")

    monkeypatch.setattr(ollama, "AsyncClient", _BoomClient)
    resp = client.post("/system/ollama/pull", params={"model": "qwen3:8b"})
    assert resp.status_code == 200
    assert '"error"' in resp.text
    assert "daemon down" in resp.text


# --- deep-research routing probe (Track 5) -----------------------------------


def test_deepresearch_probe_without_key_is_unconfigured(client: TestClient) -> None:
    # No OpenRouter key → Tongyi is unconfigured (no network call), native always on.
    resp = client.get("/system/deepresearch/probe")
    assert resp.status_code == 200
    body = resp.json()
    assert body["native"]["available"] is True
    assert body["tongyi"]["configured"] is False
    assert body["tongyi"]["live"] is False
    assert body["tongyi"]["resolvedModel"] is None


def test_deepresearch_probe_reports_live_when_slug_routes(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _resolve(_key: str, **_kw: Any) -> str:
        return system.tongyi.TONGYI_SLUG

    monkeypatch.setattr(system.tongyi, "resolve_model", _resolve)
    resp = client.get("/system/deepresearch/probe", headers={"X-OpenRouter-Key": "sk-or-test"})
    assert resp.status_code == 200
    tongyi = resp.json()["tongyi"]
    assert tongyi["configured"] is True
    assert tongyi["live"] is True
    assert tongyi["usingFallback"] is False
    assert tongyi["resolvedModel"] == system.tongyi.TONGYI_SLUG


def test_deepresearch_probe_reports_fallback_when_slug_unrouted(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    fallback = system.tongyi.FALLBACK_SLUGS[0]

    async def _resolve(_key: str, **_kw: Any) -> str:
        return fallback

    monkeypatch.setattr(system.tongyi, "resolve_model", _resolve)
    resp = client.get("/system/deepresearch/probe", headers={"X-OpenRouter-Key": "sk-or-test"})
    assert resp.status_code == 200
    tongyi = resp.json()["tongyi"]
    assert tongyi["configured"] is True
    assert tongyi["live"] is False
    assert tongyi["usingFallback"] is True
    assert tongyi["resolvedModel"] == fallback
    assert fallback in tongyi["note"]


def test_deepresearch_probe_never_echoes_the_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _resolve(_key: str, **_kw: Any) -> str:
        return system.tongyi.FALLBACK_SLUGS[0]

    monkeypatch.setattr(system.tongyi, "resolve_model", _resolve)
    resp = client.get("/system/deepresearch/probe", headers={"X-OpenRouter-Key": "sk-or-SECRET"})
    assert "sk-or-SECRET" not in resp.text
