"""Tests for the extended /fundamentals/{symbol}/ratings/* router endpoints.

Stubs ``analyst_ratings_extended`` to exercise the router's caching +
serialisation paths without the yfinance backend.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.analyst_extended import (
    IndividualAnalystForecast,
    IndividualAnalystResponse,
    PriceTargetEntry,
    PriceTargetHistoryResponse,
    RatingsHistoryEntry,
    RatingsHistoryResponse,
)
from services import data_cache


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield tmp_path
    data_cache.reset_for_tests()


def _stub_history(symbol: str) -> RatingsHistoryResponse:
    return RatingsHistoryResponse(
        symbol=symbol.upper(),
        history=[
            RatingsHistoryEntry(
                symbol=symbol.upper(),
                date=date(2026, 5, 1),
                firm="Morgan Stanley",
                analyst_name=None,
                rating_from="hold",
                rating_to="buy",
                raw_rating="Overweight",
                note="up",
                provider="yfinance",
            )
        ],
    )


def _stub_price_targets(symbol: str) -> PriceTargetHistoryResponse:
    return PriceTargetHistoryResponse(
        symbol=symbol.upper(),
        history=[
            PriceTargetEntry(
                symbol=symbol.upper(),
                date=date(2026, 5, 1),
                firm="Morgan Stanley",
                analyst_name=None,
                target_from=200.0,
                target_to=230.0,
                currency="USD",
                provider="yfinance",
            )
        ],
    )


def _stub_individual(symbol: str) -> IndividualAnalystResponse:
    return IndividualAnalystResponse(
        symbol=symbol.upper(),
        analysts=[
            IndividualAnalystForecast(
                symbol=symbol.upper(),
                firm="Goldman Sachs",
                analyst_name="Goldman Sachs",
                current_rating="buy",
                current_price_target=225.0,
                currency="USD",
                rating_issued_date=date(2026, 4, 15),
                one_year_accuracy=None,
                star_rating=None,
                provider="yfinance",
            )
        ],
    )


@pytest.fixture
def stub_provider(monkeypatch: pytest.MonkeyPatch) -> Any:
    from services import analyst_ratings_extended

    async def _history(symbol: str):
        return _stub_history(symbol)

    async def _targets(symbol: str):
        return _stub_price_targets(symbol)

    async def _individual(symbol: str):
        return _stub_individual(symbol)

    monkeypatch.setattr(analyst_ratings_extended, "get_ratings_history", _history)
    monkeypatch.setattr(analyst_ratings_extended, "get_price_target_history", _targets)
    monkeypatch.setattr(analyst_ratings_extended, "get_individual_analysts", _individual)


def test_ratings_history(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/fundamentals/AAPL/ratings/history").json()
    assert body["symbol"] == "AAPL"
    assert body["history"][0]["firm"] == "Morgan Stanley"
    assert body["history"][0]["rating_to"] == "buy"


def test_price_target_history(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/fundamentals/AAPL/ratings/price-target-history").json()
    assert body["history"][0]["target_to"] == 230.0
    assert body["history"][0]["target_from"] == 200.0


def test_individual_analysts(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/fundamentals/AAPL/ratings/individual").json()
    assert body["analysts"][0]["firm"] == "Goldman Sachs"
    assert body["analysts"][0]["current_rating"] == "buy"
    assert body["analysts"][0]["current_price_target"] == 225.0


def test_ratings_history_caches(
    client: TestClient,
    stub_provider: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import analyst_ratings_extended

    call_count = {"n": 0}

    async def _counting(symbol: str):
        call_count["n"] += 1
        return _stub_history(symbol)

    monkeypatch.setattr(analyst_ratings_extended, "get_ratings_history", _counting)

    client.get("/fundamentals/AAPL/ratings/history")
    client.get("/fundamentals/AAPL/ratings/history")
    assert call_count["n"] == 1
