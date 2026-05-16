"""Tests for the /safety/* router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import DATA_DIR_ENV
from models.safety import AuditLogAppendRequest
from services import audit_log, disclaimer_session, kill_switch


@pytest.fixture
def safety_client(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Fresh TestClient with isolated data dir + reset kill-switch bus."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    kill_switch.reset_bus_for_tests()
    disclaimer_session.reset_for_tests()
    return TestClient(create_app())


# ---------------------------------------------------------------------------
# Audit log routes
# ---------------------------------------------------------------------------


def test_audit_log_endpoint_returns_recent_entries(safety_client: TestClient) -> None:
    audit_log.append(
        AuditLogAppendRequest(
            timestampMs=1000,
            broker="alpaca",
            accountId="acct-1",
            action="order-proposed",
            payload={"x": 1},
            source="manual",
            outcome="ok",
        )
    )
    response = safety_client.get("/safety/audit-log?limit=10")
    assert response.status_code == 200
    body = response.json()
    assert len(body["entries"]) == 1
    assert body["entries"][0]["action"] == "order-proposed"


def test_audit_log_limit_validated(safety_client: TestClient) -> None:
    response = safety_client.get("/safety/audit-log?limit=0")
    assert response.status_code == 400


def test_audit_log_export_csv(safety_client: TestClient) -> None:
    audit_log.append(
        AuditLogAppendRequest(
            timestampMs=1000,
            broker="alpaca",
            accountId="acct-1",
            action="order-placed",
            payload={},
            source="manual",
            outcome="ok",
        )
    )
    response = safety_client.get("/safety/audit-log/export.csv")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "id,timestamp_ms,broker" in response.text


def test_audit_log_export_csv_half_set_range_rejected(safety_client: TestClient) -> None:
    response = safety_client.get("/safety/audit-log/export.csv?start_ms=1000")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Kill-switch routes
# ---------------------------------------------------------------------------


def test_kill_switch_fire_and_status(safety_client: TestClient) -> None:
    assert safety_client.get("/safety/kill-switch/status").json()["fired"] is False

    response = safety_client.post(
        "/safety/kill-switch", json={"reason": "test", "firedBy": "user-toolbar"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "maxAckMs" in body
    assert "event" in body
    assert body["event"]["firedBy"] == "user-toolbar"

    status = safety_client.get("/safety/kill-switch/status").json()
    assert status["fired"] is True


def test_kill_switch_reset_requires_ack(safety_client: TestClient) -> None:
    safety_client.post("/safety/kill-switch", json={"reason": "x", "firedBy": "user-toolbar"})

    bad = safety_client.post("/safety/kill-switch/reset", json={"acknowledged": False})
    assert bad.status_code == 400
    assert safety_client.get("/safety/kill-switch/status").json()["fired"] is True

    ok = safety_client.post("/safety/kill-switch/reset", json={"acknowledged": True})
    assert ok.status_code == 200
    assert safety_client.get("/safety/kill-switch/status").json()["fired"] is False


# ---------------------------------------------------------------------------
# Disclaimer routes
# ---------------------------------------------------------------------------


def test_disclaimer_status_starts_empty(safety_client: TestClient) -> None:
    response = safety_client.get("/safety/disclaimer-status")
    assert response.status_code == 200
    assert response.json()["sessionAcks"] == []


def test_disclaimer_ack_records_and_audit_logs(safety_client: TestClient) -> None:
    response = safety_client.post(
        "/safety/disclaimer-ack",
        json={"kind": "first-live-order-this-session", "broker": "alpaca"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["kind"] == "first-live-order-this-session"
    assert body["broker"] == "alpaca"

    # Session list now contains the ack
    status = safety_client.get("/safety/disclaimer-status").json()
    assert len(status["sessionAcks"]) == 1

    # Audit log has the disclaimer-ack entry
    audit_response = safety_client.get("/safety/audit-log?limit=5").json()
    assert any(e["action"] == "disclaimer-ack" for e in audit_response["entries"])


# ---------------------------------------------------------------------------
# Static-IP route
# ---------------------------------------------------------------------------


def test_static_ip_status_no_configured(
    safety_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Patch the detector to skip the network call.
    async def _fake_detect(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr("services.static_ip_detector.detect_public_ip", _fake_detect)
    response = safety_client.get("/safety/static-ip-status")
    assert response.status_code == 200
    body = response.json()
    assert body["matches"] is False
    assert "No static IP configured" in body["message"]


def test_static_ip_status_match(safety_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_detect(**_kwargs: object) -> str:
        return "203.0.113.42"

    monkeypatch.setattr("services.static_ip_detector.detect_public_ip", _fake_detect)
    response = safety_client.get("/safety/static-ip-status?configured=203.0.113.42")
    assert response.status_code == 200
    body = response.json()
    assert body["matches"] is True
    assert body["detectedIp"] == "203.0.113.42"
