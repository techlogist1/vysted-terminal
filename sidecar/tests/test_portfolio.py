"""Tests for the /portfolio router and the SQLite legacy positions ledger.

The ``temp_data_dir`` fixture points ``VYSTED_DATA_DIR`` at a ``tmp_path`` so no
test ever touches the real application data directory. ``portfolio_db`` resolves
the database path per call, so setting the env var is enough to isolate each
test's database.

R15-CODE-PLATFORM-021: holdings live in the workspace blob, so the ledger is a
read-once legacy-import source. The write routes and their writers are gone;
the former write tests now pin that (405/404, no writers), and the rows a
v0.8 install left behind are seeded straight into SQLite.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from config import DATA_DIR_ENV
from models.portfolio import PositionInput
from routers import portfolio as portfolio_router
from services import portfolio_db

_SRC = Path(__file__).resolve().parents[2] / "src"

_ROW = {
    "symbol": "AAPL",
    "quantity": 10.0,
    "cost_basis": 150.0,
    "asset_class": "equity",
    "opened_at": None,
    "note": None,
}


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Redirect the sidecar data directory to an isolated temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def _seed_legacy_row(symbol: str, quantity: float, cost_basis: float, asset_class: str) -> None:
    """Write a row the way a v0.8 install left it (no writer exists any more)."""
    with portfolio_db._connect() as conn:
        conn.execute(
            "INSERT INTO positions (symbol, quantity, cost_basis, asset_class, opened_at, note)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (symbol, quantity, cost_basis, asset_class, "2025-01-02T00:00:00", "initial entry"),
        )


# --------------------------------------------------------------------------
# portfolio_db service — the read-once legacy ledger
# --------------------------------------------------------------------------


def test_connect_is_idempotent(temp_data_dir: object) -> None:
    with portfolio_db._connect():
        pass
    with portfolio_db._connect():
        pass
    assert portfolio_db.list_positions() == []


def test_list_reads_legacy_rows_oldest_first(temp_data_dir: object) -> None:
    _seed_legacy_row("AAPL", 10.0, 150.0, "equity")
    _seed_legacy_row("BTC", 0.5, 60000.0, "crypto")

    positions = portfolio_db.list_positions()

    assert [(p.symbol, p.quantity, p.cost_basis, p.asset_class) for p in positions] == [
        ("AAPL", 10.0, 150.0, "equity"),
        ("BTC", 0.5, 60000.0, "crypto"),
    ]
    assert positions[0].id is not None and positions[0].note == "initial entry"
    assert positions[0].opened_at is not None


def test_the_ledger_has_no_writers() -> None:
    for name in ("create_position", "update_position", "delete_position", "get_position"):
        assert not hasattr(portfolio_db, name), name


# --------------------------------------------------------------------------
# /portfolio router — GET-only
# --------------------------------------------------------------------------


def test_list_positions_empty(client: TestClient, temp_data_dir: object) -> None:
    response = client.get("/portfolio/positions")
    assert response.status_code == 200
    assert response.json() == []


def test_list_positions_endpoint_serves_the_legacy_import(
    client: TestClient, temp_data_dir: object
) -> None:
    _seed_legacy_row("BTC", 0.5, 60000.0, "crypto")
    body = client.get("/portfolio/positions").json()
    assert len(body) == 1
    assert body[0]["symbol"] == "BTC"
    assert body[0]["asset_class"] == "crypto"


def test_create_position_endpoint_is_gone(client: TestClient, temp_data_dir: object) -> None:
    assert client.post("/portfolio/positions", json=_ROW).status_code == 405
    assert portfolio_db.list_positions() == []


def test_update_position_endpoint_is_gone(client: TestClient, temp_data_dir: object) -> None:
    _seed_legacy_row("AAPL", 10.0, 150.0, "equity")
    [row] = client.get("/portfolio/positions").json()

    response = client.put(f"/portfolio/positions/{row['id']}", json={**_ROW, "quantity": 20.0})

    assert response.status_code == 404  # no /positions/{id} route at all
    assert portfolio_db.list_positions()[0].quantity == 10.0


def test_delete_position_endpoint_is_gone(client: TestClient, temp_data_dir: object) -> None:
    _seed_legacy_row("AAPL", 10.0, 150.0, "equity")
    [row] = client.get("/portfolio/positions").json()

    assert client.delete(f"/portfolio/positions/{row['id']}").status_code == 404
    assert len(portfolio_db.list_positions()) == 1


def test_the_portfolio_router_is_get_only() -> None:
    methods = {m for route in portfolio_router.router.routes for m in route.methods}
    assert methods == {"GET"}


def test_no_frontend_fetch_writes_the_portfolio_ledger() -> None:
    """Every src/ fetch of a /portfolio path is a plain GET (no method override)."""
    call = re.compile(r"fetch\(\s*new URL\(\s*[\"'`]/portfolio[^)]*\)[^;]*;", re.S)
    seen = 0
    for path in _SRC.rglob("*.ts*"):
        if ".test." in path.name:
            continue
        for match in call.finditer(path.read_text(encoding="utf-8")):
            seen += 1
            assert "method" not in match.group(0), f"{path}: {match.group(0)}"
    assert seen >= 1  # the legacy import read (src/modules/portfolio/api.ts)


# --------------------------------------------------------------------------
# PositionInput field validation — bounds on quantity and cost_basis
# (was exercised through POST/PUT; the model keeps its types/data.ts mirror)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "qty",
    [
        0.0,  # zero — not positive
        -1.0,  # negative
        -0.001,  # small negative
        1e15,  # absurdly large — above le=1e12 cap
        1e13,  # above cap
    ],
)
def test_position_input_rejects_invalid_quantity(qty: float) -> None:
    """quantity must be > 0 and <= 1e12."""
    with pytest.raises(ValidationError):
        PositionInput(**{**_ROW, "quantity": qty})


def test_position_input_rejects_negative_cost_basis() -> None:
    """cost_basis must be >= 0."""
    with pytest.raises(ValidationError):
        PositionInput(**{**_ROW, "cost_basis": -5.0})


def test_position_input_accepts_zero_cost_basis() -> None:
    """cost_basis=0 is valid (e.g. vested shares with zero strike)."""
    assert PositionInput(**{**_ROW, "cost_basis": 0.0}).cost_basis == 0.0


def test_position_input_accepts_max_valid_quantity() -> None:
    """quantity at exactly the upper cap (1e12) is accepted."""
    assert PositionInput(**{**_ROW, "quantity": 1e12, "cost_basis": 0.0001}).quantity == 1e12
