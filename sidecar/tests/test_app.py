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
