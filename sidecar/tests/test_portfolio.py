"""Tests for the /portfolio router and the SQLite positions store.

The ``temp_data_dir`` fixture points ``VYSTED_DATA_DIR`` at a ``tmp_path`` so no
test ever touches the real application data directory. ``portfolio_db`` resolves
the database path per call, so setting the env var is enough to isolate each
test's database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.portfolio import PositionInput
from services import portfolio_db


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Redirect the sidecar data directory to an isolated temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def _sample_input(symbol: str = "AAPL") -> PositionInput:
    return PositionInput(
        symbol=symbol,
        quantity=10.0,
        cost_basis=150.0,
        asset_class="equity",
        opened_at=None,
        note="initial entry",
    )


# --------------------------------------------------------------------------
# portfolio_db service — CRUD against a temp database
# --------------------------------------------------------------------------


def test_ensure_schema_is_idempotent(temp_data_dir: object) -> None:
    portfolio_db._ensure_schema()
    portfolio_db._ensure_schema()
    assert portfolio_db.list_positions() == []


def test_create_and_list_position(temp_data_dir: object) -> None:
    created = portfolio_db.create_position(_sample_input())
    assert created.id is not None
    assert created.symbol == "AAPL"
    assert created.quantity == 10.0
    assert created.cost_basis == 150.0
    assert created.note == "initial entry"

    positions = portfolio_db.list_positions()
    assert len(positions) == 1
    assert positions[0].id == created.id


def test_get_position_roundtrip(temp_data_dir: object) -> None:
    created = portfolio_db.create_position(_sample_input("NVDA"))
    assert created.id is not None
    fetched = portfolio_db.get_position(created.id)
    assert fetched is not None
    assert fetched.symbol == "NVDA"


def test_get_missing_position_returns_none(temp_data_dir: object) -> None:
    assert portfolio_db.get_position(999) is None


def test_update_position(temp_data_dir: object) -> None:
    created = portfolio_db.create_position(_sample_input())
    assert created.id is not None
    updated = portfolio_db.update_position(
        created.id,
        PositionInput(
            symbol="AAPL",
            quantity=25.0,
            cost_basis=160.0,
            asset_class="equity",
            opened_at=None,
            note="averaged up",
        ),
    )
    assert updated is not None
    assert updated.quantity == 25.0
    assert updated.cost_basis == 160.0
    assert updated.note == "averaged up"


def test_update_missing_position_returns_none(temp_data_dir: object) -> None:
    assert portfolio_db.update_position(999, _sample_input()) is None


def test_delete_position(temp_data_dir: object) -> None:
    created = portfolio_db.create_position(_sample_input())
    assert created.id is not None
    assert portfolio_db.delete_position(created.id) is True
    assert portfolio_db.list_positions() == []


def test_delete_missing_position_returns_false(temp_data_dir: object) -> None:
    assert portfolio_db.delete_position(999) is False


# --------------------------------------------------------------------------
# /portfolio router — CRUD over HTTP
# --------------------------------------------------------------------------


def test_list_positions_empty(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/portfolio/positions")
    assert response.status_code == 200
    assert response.json() == []


def test_create_position_endpoint(client: TestClient, temp_data_dir: object) -> None:
    response = client.post(
        "/portfolio/positions",
        json={
            "symbol": "MSFT",
            "quantity": 5.0,
            "cost_basis": 300.0,
            "asset_class": "equity",
            "opened_at": None,
            "note": None,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] is not None
    assert body["symbol"] == "MSFT"


def test_create_then_list_endpoint(client: TestClient, temp_data_dir: object) -> None:
    client.post(
        "/portfolio/positions",
        json={
            "symbol": "BTC",
            "quantity": 0.5,
            "cost_basis": 60000.0,
            "asset_class": "crypto",
            "opened_at": None,
            "note": None,
        },
    )
    body = client.get("/portfolio/positions").json()
    assert len(body) == 1
    assert body[0]["symbol"] == "BTC"
    assert body[0]["asset_class"] == "crypto"


def test_update_position_endpoint(client: TestClient, temp_data_dir: object) -> None:
    created = client.post(
        "/portfolio/positions",
        json={
            "symbol": "AAPL",
            "quantity": 10.0,
            "cost_basis": 150.0,
            "asset_class": "equity",
            "opened_at": None,
            "note": None,
        },
    ).json()
    response = client.put(
        f"/portfolio/positions/{created['id']}",
        json={
            "symbol": "AAPL",
            "quantity": 20.0,
            "cost_basis": 155.0,
            "asset_class": "equity",
            "opened_at": None,
            "note": "added",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["quantity"] == 20.0
    assert body["note"] == "added"


def test_update_unknown_position_returns_404(client: TestClient, temp_data_dir: object) -> None:
    response = client.put(
        "/portfolio/positions/999",
        json={
            "symbol": "AAPL",
            "quantity": 1.0,
            "cost_basis": 1.0,
            "asset_class": "equity",
            "opened_at": None,
            "note": None,
        },
    )
    assert response.status_code == 404


def test_delete_position_endpoint(client: TestClient, temp_data_dir: object) -> None:
    created = client.post(
        "/portfolio/positions",
        json={
            "symbol": "AAPL",
            "quantity": 10.0,
            "cost_basis": 150.0,
            "asset_class": "equity",
            "opened_at": None,
            "note": None,
        },
    ).json()
    response = client.delete(f"/portfolio/positions/{created['id']}")
    assert response.status_code == 204
    assert client.get("/portfolio/positions").json() == []


def test_delete_unknown_position_returns_404(client: TestClient, temp_data_dir: object) -> None:
    assert client.delete("/portfolio/positions/999").status_code == 404
