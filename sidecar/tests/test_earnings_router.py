"""Tests for the /earnings router.

Stubs out ``earnings_provider`` so the router's caching + serialisation
path is exercised without the real yfinance backend.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient

from config import DATA_DIR_ENV
from models.earnings import (
    EarningsEstimateDetail,
    EarningsEvent,
    EarningsHistoryEntry,
    EarningsHistoryResponse,
    EarningsSurprise,
    EarningsSurprisesResponse,
    EarningsUpcomingResponse,
    FiscalPeriod,
)
from services import data_cache


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Pin the cache db to a per-test temp path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    data_cache.reset_for_tests()
    yield tmp_path
    data_cache.reset_for_tests()


def _stub_upcoming(
    start: date, end: date, _watchlist: list[str] | None = None
) -> EarningsUpcomingResponse:
    return EarningsUpcomingResponse(
        start_date=start,
        end_date=end,
        events=[
            EarningsEvent(
                symbol="AAPL",
                company_name="Apple Inc.",
                scheduled_date=start,
                time_of_day="after-close",
                fiscal_period=FiscalPeriod(quarter="Q2", year=2026),
                eps_estimate_mean=1.5,
                eps_estimate_stddev=0.05,
                estimate_analyst_count=20,
                currency="USD",
                provider="yfinance",
            )
        ],
    )


def _stub_history(symbol: str) -> EarningsHistoryResponse:
    return EarningsHistoryResponse(
        symbol=symbol.upper(),
        history=[
            EarningsHistoryEntry(
                fiscal_period=FiscalPeriod(quarter="Q1", year=2026),
                reported_date=date(2026, 2, 1),
                eps_actual=1.32,
                eps_estimate_mean=1.30,
                revenue_actual=99_000_000.0,
                revenue_estimate_mean=98_000_000.0,
                currency="USD",
            )
        ],
    )


def _stub_surprises(symbol: str) -> EarningsSurprisesResponse:
    return EarningsSurprisesResponse(
        symbol=symbol.upper(),
        surprises=[
            EarningsSurprise(
                symbol=symbol.upper(),
                reported_date=date(2026, 2, 1),
                fiscal_period=FiscalPeriod(quarter="Q1", year=2026),
                eps_actual=1.32,
                eps_estimate_mean=1.30,
                eps_surprise=0.02,
                eps_surprise_pct=0.015,
                revenue_actual=99_000_000.0,
                revenue_estimate_mean=98_000_000.0,
                revenue_surprise_pct=0.0102,
                currency="USD",
                provider="yfinance",
            )
        ],
    )


def _stub_estimates(symbol: str) -> EarningsEstimateDetail:
    return EarningsEstimateDetail(
        symbol=symbol.upper(),
        fiscal_period=FiscalPeriod(quarter="Q2", year=2026),
        eps_estimate_mean=1.5,
        eps_estimate_median=1.5,
        eps_estimate_high=1.6,
        eps_estimate_low=1.4,
        eps_estimate_stddev=0.05,
        estimate_analyst_count=21,
        revenue_estimate_mean=100_000_000.0,
        revenue_estimate_median=100_000_000.0,
        revenue_estimate_high=105_000_000.0,
        revenue_estimate_low=95_000_000.0,
        revenue_analyst_count=21,
        currency="USD",
        provider="yfinance",
        as_of=datetime(2026, 5, 16, tzinfo=UTC),
    )


@pytest.fixture
def stub_provider(monkeypatch: pytest.MonkeyPatch) -> Any:
    from services import earnings_provider

    async def _upcoming(start: date, end: date, watchlist: list[str] | None = None):
        return _stub_upcoming(start, end, watchlist)

    async def _history(symbol: str):
        return _stub_history(symbol)

    async def _surprises(symbol: str):
        return _stub_surprises(symbol)

    async def _estimates(symbol: str):
        return _stub_estimates(symbol)

    monkeypatch.setattr(earnings_provider, "get_upcoming", _upcoming)
    monkeypatch.setattr(earnings_provider, "get_history", _history)
    monkeypatch.setattr(earnings_provider, "get_surprises", _surprises)
    monkeypatch.setattr(earnings_provider, "get_estimate_detail", _estimates)


def test_upcoming(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/earnings/upcoming?days=7&watchlist=AAPL,MSFT").json()
    assert body["events"][0]["symbol"] == "AAPL"
    assert body["events"][0]["eps_estimate_mean"] == 1.5
    assert body["events"][0]["estimate_analyst_count"] == 20


def test_upcoming_rejects_out_of_range_days(client: TestClient, stub_provider: Any) -> None:
    response = client.get("/earnings/upcoming?days=999")
    assert response.status_code == 422  # FastAPI Query(ge=1, le=60) validation


def test_history(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/earnings/AAPL/history").json()
    assert body["symbol"] == "AAPL"
    assert len(body["history"]) == 1
    assert body["history"][0]["eps_actual"] == 1.32


def test_surprises(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/earnings/AAPL/surprises").json()
    assert body["symbol"] == "AAPL"
    assert body["surprises"][0]["eps_surprise"] == 0.02


def test_estimates(client: TestClient, stub_provider: Any) -> None:
    body = client.get("/earnings/AAPL/estimates").json()
    assert body["symbol"] == "AAPL"
    assert body["eps_estimate_high"] == 1.6
    assert body["estimate_analyst_count"] == 21


def test_history_caches(
    client: TestClient,
    stub_provider: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Second call within the TTL hits the cache, not the provider."""
    call_count = {"n": 0}
    from services import earnings_provider

    async def _counting(symbol: str):
        call_count["n"] += 1
        return _stub_history(symbol)

    monkeypatch.setattr(earnings_provider, "get_history", _counting)

    client.get("/earnings/AAPL/history")
    client.get("/earnings/AAPL/history")
    assert call_count["n"] == 1
