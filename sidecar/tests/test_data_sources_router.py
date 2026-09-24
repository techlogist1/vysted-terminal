"""Tests for GET /data-sources (C19 — R15-CODE-PLATFORM-072 / R15-DATA-077).

The route is a thin serialization of ``provider_registry.declarations()`` — the
same table the resolver dispatches against — so these tests assert the wire
shape and that a live provider (yfinance) round-trips its full served-key set,
not a re-test of the resolver's own dispatch logic (covered by
``test_provider_registry.py``).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(create_app())


def test_data_sources_wire_shape(client: TestClient) -> None:
    resp = client.get("/data-sources")
    assert resp.status_code == 200
    body = resp.json()
    assert "providers" in body
    rows = {row["id"]: row for row in body["providers"]}
    assert "yfinance" in rows
    row = rows["yfinance"]
    assert set(row.keys()) == {"id", "keys", "rank", "available", "asset_classes", "region"}
    assert set(row["keys"]) == {
        "quote",
        "ohlcv",
        "fundamentals",
        "income_statement",
        "balance_sheet",
        "cash_flow",
        "analyst_rating",
    }
    assert row["available"] is True


def test_data_sources_includes_india_keyless_lanes(client: TestClient) -> None:
    resp = client.get("/data-sources")
    rows = {row["id"]: row for row in resp.json()["providers"]}
    for provider_id in ("nse_direct", "nse", "bse"):
        assert rows[provider_id]["region"] == ["IN"]
