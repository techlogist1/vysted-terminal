"""Tests for the Phase 6 (Teammate E) workflow nodes."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from models.analyst_extended import (
    PriceTargetEntry,
    PriceTargetHistoryResponse,
    RatingsHistoryEntry,
    RatingsHistoryResponse,
)
from models.earnings import (
    EarningsEvent,
    EarningsHistoryEntry,
    EarningsHistoryResponse,
    EarningsUpcomingResponse,
    FiscalPeriod,
)
from services import (
    analyst_ratings_extended,
    earnings_provider,
    workflow_engine,
)
from services.workflow_nodes import research_nodes


@pytest.fixture(autouse=True)
def isolated_registry() -> None:
    workflow_engine.reset_registry_for_tests()
    yield
    workflow_engine.reset_registry_for_tests()


@pytest.fixture
def register_nodes() -> None:
    research_nodes.register()


@pytest.mark.asyncio
async def test_register_adds_four_node_types(register_nodes: None) -> None:
    registered = workflow_engine.registered_node_types()
    assert "data.fetch_earnings_calendar" in registered
    assert "data.fetch_earnings_history" in registered
    assert "data.fetch_analyst_history" in registered
    assert "data.fetch_price_target_history" in registered


@pytest.mark.asyncio
async def test_fetch_earnings_calendar(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _upcoming(start: date, end: date, watchlist: list[str] | None = None):
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

    monkeypatch.setattr(earnings_provider, "get_upcoming", _upcoming)
    out = await research_nodes.fetch_earnings_calendar(
        {"days": 7, "watchlist": "AAPL,MSFT"}, {}
    )
    assert len(out["events"]) == 1
    assert out["events"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_fetch_earnings_calendar_rejects_bad_days() -> None:
    with pytest.raises(ValueError, match="days"):
        await research_nodes.fetch_earnings_calendar({"days": 999}, {})


@pytest.mark.asyncio
async def test_fetch_earnings_history(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _history(symbol: str):
        return EarningsHistoryResponse(
            symbol=symbol.upper(),
            history=[
                EarningsHistoryEntry(
                    fiscal_period=FiscalPeriod(quarter="Q1", year=2026),
                    reported_date=date(2026, 2, 1),
                    eps_actual=1.32,
                    eps_estimate_mean=1.30,
                    revenue_actual=None,
                    revenue_estimate_mean=None,
                    currency="USD",
                )
            ],
        )

    monkeypatch.setattr(earnings_provider, "get_history", _history)
    out = await research_nodes.fetch_earnings_history({"symbol": "AAPL"}, {})
    assert out["symbol"] == "AAPL"
    assert out["history"][0]["eps_actual"] == 1.32


@pytest.mark.asyncio
async def test_fetch_earnings_history_missing_symbol() -> None:
    with pytest.raises(ValueError, match="symbol"):
        await research_nodes.fetch_earnings_history({}, {})


@pytest.mark.asyncio
async def test_fetch_analyst_history(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _history(symbol: str):
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
                    note=None,
                    provider="yfinance",
                )
            ],
        )

    monkeypatch.setattr(analyst_ratings_extended, "get_ratings_history", _history)
    out = await research_nodes.fetch_analyst_history({"symbol": "AAPL"}, {})
    assert out["symbol"] == "AAPL"
    assert out["history"][0]["firm"] == "Morgan Stanley"


@pytest.mark.asyncio
async def test_fetch_price_target_history(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _targets(symbol: str):
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

    monkeypatch.setattr(analyst_ratings_extended, "get_price_target_history", _targets)
    out = await research_nodes.fetch_price_target_history({"symbol": "AAPL"}, {})
    assert out["symbol"] == "AAPL"
    assert out["history"][0]["target_to"] == 230.0
