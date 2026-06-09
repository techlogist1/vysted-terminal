"""Tests for the honest T1 status surface (``GET /search/status``)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from services.search.breaker import breaker_for, reset_breakers
from services.search.keyless import ENGINE_CHAIN


@pytest.fixture(autouse=True)
def _fresh_breakers():
    reset_breakers()
    yield
    reset_breakers()


def test_status_endpoint_reports_all_engines(client: TestClient) -> None:
    resp = client.get("/search/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "t1_keyless"
    assert body["available"] is True
    assert [e["id"] for e in body["engines"]] == list(ENGINE_CHAIN)
    for engine in body["engines"]:
        assert set(engine) >= {
            "id",
            "label",
            "state",
            "cooldown_remaining_s",
            "min_interval_s",
            "detail",
        }
        assert engine["state"] == "closed"


def test_status_endpoint_surfaces_a_benched_engine(client: TestClient) -> None:
    breaker_for("ddg").record_failure()
    breaker_for("ddg").record_failure()
    body = client.get("/search/status").json()
    ddg_row = next(e for e in body["engines"] if e["id"] == "ddg")
    assert ddg_row["state"] == "open"
    assert ddg_row["cooldown_remaining_s"] > 0
    assert "cooling down" in ddg_row["detail"]
    # Honesty: one benched engine does not declare the tier down.
    assert body["available"] is True
