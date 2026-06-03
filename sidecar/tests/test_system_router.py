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
