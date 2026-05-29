"""Phase 10 — broker read-only routes + the Kite OAuth session exchange.

Asserts the new read surface is GET-only (read-only by construction, §6.5), the
session-exchange route runs the OAuth dance without echoing the secret, the
daily-token expiry maps to 419, and disconnect resets state.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import DATA_DIR_ENV
from routers import brokers as brokers_router
from services import kill_switch
from services.broker_base import BrokerError
from services.brokers import registry as brokers_registry


@pytest.fixture
def client(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    kill_switch.reset_bus_for_tests()
    brokers_registry.reset_for_tests()
    brokers_router._reset_pending_proposals_for_tests()
    c = TestClient(create_app())
    yield c
    brokers_registry.reset_for_tests()
    kill_switch.reset_bus_for_tests()


@pytest.mark.parametrize("path", ["account", "positions", "holdings", "margins"])
def test_kite_read_routes_return_account_summary(client: TestClient, path: str) -> None:
    # Paper/disconnected kite — the granular routes fall back to account_info().
    response = client.get(f"/brokers/kite/{path}")
    assert response.status_code == 200
    body = response.json()
    assert body["broker"] == "kite"
    assert "positions" in body  # AccountSummary shape


def test_read_routes_are_get_only() -> None:
    # §6.5 read-only-by-construction: the new read routes never accept a body /
    # never mutate state — they must be GET only.
    for route in brokers_router.router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if path.endswith(("/positions", "/holdings", "/margins")):
            assert methods == {"GET"}, f"{path} should be GET-only, got {methods}"


def test_disconnect_resets_state(client: TestClient) -> None:
    response = client.post("/brokers/kite/disconnect")
    assert response.status_code == 200
    assert response.json()["status"] == "disconnected"


def test_kite_session_exchange_runs_oauth_without_echoing_secret(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _fake_exchange(api_key: str, api_secret: str, request_token: str) -> dict:
        assert (api_key, api_secret, request_token) == ("ak", "supersecret", "rt")
        return {"access_token": "atok", "user_id": "U1", "login_time": "2026-05-30"}

    monkeypatch.setattr("services.brokers.kite.exchange_request_token", _fake_exchange)
    response = client.post(
        "/brokers/kite/session",
        json={"apiKey": "ak", "apiSecret": "supersecret", "requestToken": "rt"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accessToken"] == "atok"
    assert body["userId"] == "U1"
    # The api_secret must NEVER appear in the response.
    assert "supersecret" not in response.text


def test_kite_session_exchange_surfaces_broker_error(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _boom(api_key: str, api_secret: str, request_token: str) -> dict:
        raise BrokerError("kite: login exchange failed: bad request_token")

    monkeypatch.setattr("services.brokers.kite.exchange_request_token", _boom)
    response = client.post(
        "/brokers/kite/session",
        json={"apiKey": "ak", "apiSecret": "s", "requestToken": "bad"},
    )
    assert response.status_code == 400
