"""Tests for the /health liveness endpoint."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_health_payload_shape(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "vysted-sidecar"


def test_health_reports_active_providers(client: TestClient) -> None:
    # FR-053: active_providers() is now DERIVED from the provider-declaration
    # table and keyed by STANDARD MODEL KEY (quote/ohlcv/fundamentals/…), not by
    # the old hardcoded asset-class keys.
    providers = client.get("/health").json()["providers"]
    # The crypto market-data provider (ccxt, rank 10) wins the quote/ohlcv keys.
    assert "ccxt" in providers["quote"]
    assert "ccxt" in providers["ohlcv"]
    # yfinance is always available for fundamentals (openbb-mcp may front it).
    assert "yfinance" in providers["fundamentals"]
    # Phase 3: OpenBB-via-MCP ships bundled; the registry reports either
    # "available" (production with the openbb-mcp subprocess running) or
    # "unavailable" (no-MCP rebuild, the dev path without the build script).
    # Both are valid, so this assertion only checks the key is present.
    assert providers["openbb-mcp"] in {"available", "unavailable"}


def test_health_names_agent_files_the_roster_skipped(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R15-LIFECYCLE-014: a bad agent JSON shrinks the roster visibly on /health;
    the shipping roster loads whole (``[]``)."""
    from services import agent_runtime

    assert client.get("/health").json()["agents_degraded"] == []
    (tmp_path / "bad.json").write_text("{ not valid json", encoding="utf-8")
    monkeypatch.setattr(agent_runtime, "_degraded", [])
    monkeypatch.setattr(agent_runtime, "_specs", {})
    agent_runtime.reload(tmp_path)
    degraded = client.get("/health").json()["agents_degraded"]
    assert [d["file"] for d in degraded] == ["bad.json"]
    assert "failed to read JSON" in degraded[0]["reason"]
