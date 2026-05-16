"""Tests for the Phase 6 earnings agent tools.

Patches the provider so the tools exercise their argument-parsing +
error-shaping paths without the yfinance backend.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

import pytest

from models.earnings import (
    EarningsEstimateDetail,
    EarningsEvent,
    EarningsHistoryEntry,
    EarningsHistoryResponse,
    EarningsUpcomingResponse,
    FiscalPeriod,
)
from services import agent_tools, earnings_provider


@pytest.fixture(autouse=True)
def register_tools() -> None:
    """Register the Phase 6 tools on the agent-tool registry."""
    agent_tools.register_v0_6_0_tools()


def _stub_upcoming_response() -> EarningsUpcomingResponse:
    return EarningsUpcomingResponse(
        start_date=date(2026, 5, 16),
        end_date=date(2026, 5, 23),
        events=[
            EarningsEvent(
                symbol="AAPL",
                company_name="Apple Inc.",
                scheduled_date=date(2026, 5, 20),
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


@pytest.mark.asyncio
async def test_earnings_upcoming_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _upcoming(start: date, end: date, watchlist: list[str] | None = None):
        return _stub_upcoming_response()

    monkeypatch.setattr(earnings_provider, "get_upcoming", _upcoming)
    result = await agent_tools.invoke_tool(
        "earnings_upcoming", {"days": 7, "watchlist": "AAPL,MSFT"}
    )
    assert result["ok"] is True
    assert result["count"] == 1
    assert result["events"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_earnings_upcoming_rejects_bad_days() -> None:
    out = await agent_tools.invoke_tool("earnings_upcoming", {"days": 200})
    assert out["ok"] is False


@pytest.mark.asyncio
async def test_earnings_history_tool(monkeypatch: pytest.MonkeyPatch) -> None:
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
    result = await agent_tools.invoke_tool("earnings_history", {"symbol": "AAPL"})
    assert result["ok"] is True
    assert result["count"] == 1


@pytest.mark.asyncio
async def test_earnings_history_missing_symbol() -> None:
    out = await agent_tools.invoke_tool("earnings_history", {})
    assert out["ok"] is False


@pytest.mark.asyncio
async def test_earnings_estimates_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _estimate(symbol: str):
        return EarningsEstimateDetail(
            symbol=symbol.upper(),
            fiscal_period=FiscalPeriod(quarter="Q2", year=2026),
            eps_estimate_mean=1.5,
            eps_estimate_median=1.5,
            eps_estimate_high=1.6,
            eps_estimate_low=1.4,
            eps_estimate_stddev=0.05,
            estimate_analyst_count=21,
            revenue_estimate_mean=None,
            revenue_estimate_median=None,
            revenue_estimate_high=None,
            revenue_estimate_low=None,
            revenue_analyst_count=0,
            currency="USD",
            provider="yfinance",
            as_of=datetime(2026, 5, 16, tzinfo=UTC),
        )

    monkeypatch.setattr(earnings_provider, "get_estimate_detail", _estimate)
    result = await agent_tools.invoke_tool("earnings_estimates", {"symbol": "AAPL"})
    assert result["ok"] is True
    assert result["estimate"]["eps_estimate_high"] == 1.6
