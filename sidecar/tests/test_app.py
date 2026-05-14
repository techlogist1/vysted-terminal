"""Tests for application wiring — every router mounts, including the 1.B stubs."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize(
    ("router", "owner"),
    [
        ("indicators", "teammate-a"),
        ("portfolio", "teammate-b"),
        ("news", "teammate-c"),
        ("workspace", "teammate-d"),
    ],
)
def test_stub_router_mounted(client: TestClient, router: str, owner: str) -> None:
    """Each Phase 1.B stub router is mounted and reachable."""
    body = client.get(f"/{router}/_status").json()
    assert body == {"status": "stub", "router": router, "owner": owner}
