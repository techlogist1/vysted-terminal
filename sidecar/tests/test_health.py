"""Tests for the /health liveness endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_returns_200(client: TestClient) -> None:
    assert client.get("/health").status_code == 200


def test_health_payload_shape(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["service"] == "vysted-sidecar"


def test_health_reports_active_providers(client: TestClient) -> None:
    providers = client.get("/health").json()["providers"]
    assert providers["equity"] == "yfinance"
    assert "ccxt" in providers["crypto"]
    # Phase 3: OpenBB-via-MCP ships bundled; the registry reports either
    # "available" (production with the openbb-mcp subprocess running) or
    # "unavailable" (no-MCP rebuild, the dev path without the build script).
    # Both are valid, so this assertion only checks the key is present.
    assert providers["openbb-mcp"] in {"available", "unavailable"}
