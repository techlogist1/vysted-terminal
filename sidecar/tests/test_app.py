"""Tests for application wiring — every Phase 1 router is mounted.

Phase 1.A-2 scaffolded four stub routers; Phase 1.B replaced them with the real
chart/portfolio/news/workspace endpoints. This test confirms each router still
contributes its endpoints to the running app by checking the OpenAPI schema.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

# One representative path per mounted router.
_EXPECTED_PATHS = [
    "/health",
    "/quotes/{symbol}",
    "/history/{symbol}",
    "/crypto/exchanges",
    "/fundamentals/{symbol}",
    "/macro/{series_id}",
    "/indicators/{symbol}",
    "/portfolio/positions",
    "/news",
    "/workspace",
]


@pytest.mark.parametrize("path", _EXPECTED_PATHS)
def test_router_mounted(client: TestClient, path: str) -> None:
    """Each Phase 1 router contributes its endpoints to the OpenAPI schema."""
    paths = client.get("/openapi.json").json()["paths"]
    assert path in paths


# ---------------------------------------------------------------------------
# Origin guard (R15-CODE-AGENT-001)
# ---------------------------------------------------------------------------

_EVIL = {"Origin": "https://evil.example"}


def test_unlisted_origin_is_refused_on_mcp_and_rest(client: TestClient) -> None:
    mcp = client.post(
        "/mcp/",
        headers={**_EVIL, "Accept": "application/json, text/event-stream"},
        json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )
    assert mcp.status_code == 403
    assert "access-control-allow-origin" not in mcp.headers
    assert client.get("/mcp/status", headers=_EVIL).status_code == 403
    preflight = client.options("/mcp/", headers={**_EVIL, "Access-Control-Request-Method": "POST"})
    assert preflight.status_code == 403


@pytest.mark.parametrize("origin", ["tauri://localhost", "http://tauri.localhost"])
def test_webview_origin_is_served_with_its_cors_header(client: TestClient, origin: str) -> None:
    response = client.get("/mcp/status", headers={"Origin": origin})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_request_without_origin_passes(client: TestClient) -> None:
    assert client.get("/mcp/status").status_code == 200
