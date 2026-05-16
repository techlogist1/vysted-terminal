"""Tests for the /brokers/* router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import DATA_DIR_ENV
from models.safety import StaticIpStatus
from routers import brokers as brokers_router
from services import audit_log, kill_switch
from services.brokers import registry as brokers_registry


@pytest.fixture
def broker_client(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    kill_switch.reset_bus_for_tests()
    brokers_registry.reset_for_tests()
    brokers_router._reset_pending_proposals_for_tests()
    # create_app() now bootstraps the three India broker adapters as part of
    # the v0.5.0 runtime-extension hook.
    client = TestClient(create_app())
    yield client
    brokers_registry.reset_for_tests()
    kill_switch.reset_bus_for_tests()


# ---------------------------------------------------------------------------
# Listing + state
# ---------------------------------------------------------------------------


def test_list_brokers_returns_three_india_adapters(broker_client: TestClient) -> None:
    response = broker_client.get("/brokers")
    assert response.status_code == 200
    body = response.json()
    ids = sorted(b["broker"] for b in body["brokers"])
    assert ids == ["angelone", "dhan", "kite"]
    for b in body["brokers"]:
        assert b["mode"] == "paper"
        assert b["status"] == "disconnected"


def test_get_state_for_kite_reports_static_ip_capability(broker_client: TestClient) -> None:
    response = broker_client.get("/brokers/kite/state")
    assert response.status_code == 200
    body = response.json()
    assert body["broker"] == "kite"
    assert body["capabilities"]["requiresStaticIp"] is True


def test_get_state_unknown_broker_returns_404(broker_client: TestClient) -> None:
    response = broker_client.get("/brokers/alpaca/state")
    # 422 from pydantic on invalid BrokerId literal, OR 404 from registry —
    # both signal "not Teammate I's broker"; the router uses Literal[BrokerId]
    # so FastAPI will reject before the registry check.
    assert response.status_code in (404, 422)


# ---------------------------------------------------------------------------
# Mode + read-only
# ---------------------------------------------------------------------------


def test_set_mode_to_live_for_dhan(broker_client: TestClient, monkeypatch) -> None:
    response = broker_client.post("/brokers/dhan/mode", json={"mode": "live"})
    assert response.status_code == 200
    assert response.json()["mode"] == "live"


def test_set_read_only_for_angelone(broker_client: TestClient) -> None:
    response = broker_client.post("/brokers/angelone/read-only", json={"readOnly": True})
    assert response.status_code == 200
    assert response.json()["readOnly"] is True


def test_invalid_mode_rejected(broker_client: TestClient) -> None:
    response = broker_client.post("/brokers/dhan/mode", json={"mode": "lethal"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Order flow — propose -> confirm
# ---------------------------------------------------------------------------


def test_propose_order_returns_proposal_and_caches_it(broker_client: TestClient) -> None:
    response = broker_client.post(
        "/brokers/dhan/orders",
        json={
            "symbol": "RELIANCE",
            "side": "buy",
            "type": "limit",
            "quantity": 5,
            "limitPrice": 100.0,
            "currency": "INR",
            "source": "manual",
            "sourceDetails": {},
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "RELIANCE"
    assert body["broker"] == "dhan"
    assert body["source"] == "manual"
    proposal_id = body["proposalId"]
    assert proposal_id


def test_confirm_paper_order_returns_filled_result(broker_client: TestClient) -> None:
    propose = broker_client.post(
        "/brokers/dhan/orders",
        json={
            "symbol": "RELIANCE",
            "side": "buy",
            "type": "limit",
            "quantity": 5,
            "limitPrice": 100.0,
            "currency": "INR",
            "source": "manual",
            "sourceDetails": {},
        },
    )
    proposal_id = propose.json()["proposalId"]

    confirm = broker_client.post(
        f"/brokers/dhan/orders/{proposal_id}/confirm",
        json={"humanConfirmed": True},
    )
    assert confirm.status_code == 200
    body = confirm.json()
    assert body["status"] == "filled"
    assert body["broker"] == "dhan"
    assert body["brokerOrderId"].startswith("paper-dhan-")


def test_decline_order_returns_400_and_writes_declined_audit(
    broker_client: TestClient,
) -> None:
    propose = broker_client.post(
        "/brokers/dhan/orders",
        json={
            "symbol": "RELIANCE",
            "side": "buy",
            "type": "limit",
            "quantity": 5,
            "limitPrice": 100.0,
            "currency": "INR",
            "source": "manual",
            "sourceDetails": {},
        },
    )
    proposal_id = propose.json()["proposalId"]
    confirm = broker_client.post(
        f"/brokers/dhan/orders/{proposal_id}/confirm",
        json={"humanConfirmed": False, "confirmNote": "changed mind"},
    )
    assert confirm.status_code == 400
    actions = [r.action for r in audit_log.tail(limit=10)]
    assert "order-declined" in actions


def test_confirm_unknown_proposal_returns_404(broker_client: TestClient) -> None:
    confirm = broker_client.post(
        "/brokers/dhan/orders/does-not-exist/confirm",
        json={"humanConfirmed": True},
    )
    assert confirm.status_code == 404


def test_position_limit_rejection_returns_400(broker_client: TestClient) -> None:
    response = broker_client.post(
        "/brokers/dhan/orders",
        json={
            "symbol": "RELIANCE",
            "side": "buy",
            "type": "limit",
            "quantity": 200,
            "limitPrice": 100.0,
            "currency": "INR",
            "source": "manual",
            "sourceDetails": {},
        },
    )
    assert response.status_code == 400
    assert "exceeds limit" in response.json()["detail"]


def test_kill_switch_fired_blocks_propose(broker_client: TestClient) -> None:
    # Fire the global kill switch — every registered adapter acks.
    kill_response = broker_client.post(
        "/safety/kill-switch", json={"reason": "test", "firedBy": "user-toolbar"}
    )
    assert kill_response.status_code == 200

    response = broker_client.post(
        "/brokers/angelone/orders",
        json={
            "symbol": "HDFCBANK",
            "side": "buy",
            "type": "limit",
            "quantity": 5,
            "limitPrice": 100.0,
            "currency": "INR",
            "source": "manual",
            "sourceDetails": {},
        },
    )
    assert response.status_code == 400
    assert "kill switch" in response.json()["detail"]


# ---------------------------------------------------------------------------
# AI-proposed order routes through the same path
# ---------------------------------------------------------------------------


def test_ai_proposed_order_flows_through_propose_confirm(
    broker_client: TestClient,
) -> None:
    propose = broker_client.post(
        "/brokers/dhan/orders",
        json={
            "symbol": "RELIANCE",
            "side": "buy",
            "type": "limit",
            "quantity": 5,
            "limitPrice": 100.0,
            "currency": "INR",
            "source": "ai-agent",
            "sourceDetails": {
                "originatorId": "buffett",
                "originatorName": "Warren Buffett",
            },
        },
    )
    assert propose.status_code == 200
    body = propose.json()
    assert body["source"] == "ai-agent"

    confirm = broker_client.post(
        f"/brokers/dhan/orders/{body['proposalId']}/confirm",
        json={"humanConfirmed": True},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "filled"


# ---------------------------------------------------------------------------
# Account info
# ---------------------------------------------------------------------------


def test_paper_account_info_returns_summary(broker_client: TestClient) -> None:
    response = broker_client.get("/brokers/kite/account")
    assert response.status_code == 200
    body = response.json()
    assert body["broker"] == "kite"
    assert body["currency"] == "INR"
    assert body["positions"] == []


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


def test_cancel_paper_order(broker_client: TestClient) -> None:
    response = broker_client.post(
        "/brokers/dhan/orders/cancel",
        json={"brokerOrderId": "paper-dhan-xyz"},
    )
    assert response.status_code == 200
    assert response.json()["cancelled"] == "paper-dhan-xyz"


# ---------------------------------------------------------------------------
# Kite static-IP routes
# ---------------------------------------------------------------------------


def test_kite_static_ip_get_default_is_null(broker_client: TestClient) -> None:
    response = broker_client.get("/brokers/kite/static-ip")
    assert response.status_code == 200
    assert response.json()["configuredIp"] is None


def test_kite_static_ip_set_and_get(broker_client: TestClient) -> None:
    set_response = broker_client.post("/brokers/kite/static-ip", json={"staticIp": "203.0.113.5"})
    assert set_response.status_code == 200
    assert set_response.json()["configuredIp"] == "203.0.113.5"

    get_response = broker_client.get("/brokers/kite/static-ip")
    assert get_response.json()["configuredIp"] == "203.0.113.5"


def test_kite_live_mode_records_static_ip_audit(broker_client: TestClient, monkeypatch) -> None:
    """The Kite live-mode toggle writes a static-IP-status audit row."""
    broker_client.post("/brokers/kite/static-ip", json={"staticIp": "203.0.113.5"})

    from services.brokers import kite as kite_module

    async def _fake_status(configured, *args, **kwargs):
        return StaticIpStatus(
            detectedIp="203.0.113.5",
            configuredIp=configured,
            matches=True,
            message="match",
            detectedAt=1,
        )

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _fake_status)

    response = broker_client.post("/brokers/kite/mode", json={"mode": "live"})
    assert response.status_code == 200
    assert response.json()["mode"] == "live"

    static_ip_rows = [
        r
        for r in audit_log.tail(limit=20)
        if r.action == "mode-changed" and "staticIpStatus" in r.payload
    ]
    assert len(static_ip_rows) == 1
    assert static_ip_rows[0].payload["staticIpStatus"]["matches"] is True
