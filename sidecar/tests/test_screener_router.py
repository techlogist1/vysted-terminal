"""Tests for the ``/screener/*`` router."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from models.fundamentals import Fundamentals
from models.market import Quote
from services import data_cache


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Point the data cache at a tmp file per test."""
    data_cache.reset_for_tests(tmp_path / "router_test_cache.db")
    yield
    data_cache.reset_for_tests(None)


def _make_fundamentals(symbol: str, **overrides: Any) -> Fundamentals:
    payload: dict[str, Any] = {
        "symbol": symbol,
        "name": f"{symbol} Inc.",
        "sector": "Technology",
        "industry": "Software",
        "market_cap": 200_000_000_000.0,
        "pe_ratio": 15.0,
        "provider": "test",
    }
    payload.update(overrides)
    return Fundamentals(**payload)


def _make_quote(symbol: str) -> Quote:
    return Quote(
        symbol=symbol,
        price=100.0,
        change=1.5,
        change_percent=1.5,
        volume=1_000_000.0,
        currency="USD",
        market_state="open",
        timestamp=datetime.now(tz=UTC),
        provider="test",
    )


def test_screener_universe_sp500(client: TestClient) -> None:
    response = client.get("/screener/universe", params={"id": "sp500"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "sp500"
    assert body["asset_class"] == "equity"
    assert isinstance(body["symbols"], list)
    assert "AAPL" in body["symbols"]


def test_screener_universe_nifty50(client: TestClient) -> None:
    response = client.get("/screener/universe", params={"id": "nifty50"})
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "nifty50"
    assert len(body["symbols"]) == 50


def test_screener_universe_custom_rejected(client: TestClient) -> None:
    response = client.get("/screener/universe", params={"id": "custom"})
    assert response.status_code == 400


def test_screener_universe_unknown_id_validation_error(client: TestClient) -> None:
    response = client.get("/screener/universe", params={"id": "no-such-universe"})
    # Pydantic literal validation hands this back as a 422 (Unprocessable Entity).
    assert response.status_code == 422


def test_screener_run_end_to_end(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: POST /screener/run drives the engine + returns rows."""

    fake_fundamentals = {
        "AAA": _make_fundamentals("AAA", sector="Technology", market_cap=500e9, pe_ratio=15.0),
        "BBB": _make_fundamentals("BBB", sector="Technology", market_cap=50e9, pe_ratio=15.0),
        "CCC": _make_fundamentals("CCC", sector="Healthcare", market_cap=500e9, pe_ratio=15.0),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake_fundamentals[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    response = client.post(
        "/screener/run",
        json={
            "universe": "custom",
            "custom_symbols": ["AAA", "BBB", "CCC"],
            "criteria": [
                {"field": "sector", "operator": "eq", "value": "Technology"},
                {"field": "market_cap", "operator": "gt", "value": 100_000_000_000},
            ],
            "limit": 10,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["universe"] == "custom"
    assert body["result_count"] == 1
    assert [row["symbol"] for row in body["rows"]] == ["AAA"]


def test_screener_run_invalid_request_400(client: TestClient) -> None:
    """A malformed criterion produces a 422 (Pydantic), not a 500."""
    response = client.post(
        "/screener/run",
        json={
            "universe": "custom",
            "custom_symbols": ["AAA"],
            "criteria": [{"field": "sector", "operator": "wat", "value": "Tech"}],
        },
    )
    # Pydantic discriminated-union mismatch is 422.
    assert response.status_code == 422
