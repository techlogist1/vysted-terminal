"""Tests for the Phase 6 analyst-ratings agent tools."""

from __future__ import annotations

from datetime import date

import pytest

from models.analyst_extended import (
    IndividualAnalystForecast,
    IndividualAnalystResponse,
    PriceTargetEntry,
    PriceTargetHistoryResponse,
    RatingsHistoryEntry,
    RatingsHistoryResponse,
)
from services import agent_tools, analyst_ratings_extended


@pytest.fixture(autouse=True)
def register_tools() -> None:
    agent_tools.register_v0_6_0_tools()


@pytest.mark.asyncio
async def test_analyst_history_tool(monkeypatch: pytest.MonkeyPatch) -> None:
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
    result = await agent_tools.invoke_tool("analyst_history", {"symbol": "AAPL"})
    assert result["ok"] is True
    assert result["history"][0]["rating_to"] == "buy"


@pytest.mark.asyncio
async def test_analyst_individual_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _individual(symbol: str):
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

    monkeypatch.setattr(analyst_ratings_extended, "get_individual_analysts", _individual)
    result = await agent_tools.invoke_tool("analyst_individual", {"symbol": "AAPL"})
    assert result["ok"] is True
    assert result["analysts"][0]["firm"] == "Goldman Sachs"


@pytest.mark.asyncio
async def test_price_target_history_tool(monkeypatch: pytest.MonkeyPatch) -> None:
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
    result = await agent_tools.invoke_tool("price_target_history", {"symbol": "AAPL"})
    assert result["ok"] is True
    assert result["history"][0]["target_to"] == 230.0


@pytest.mark.asyncio
async def test_price_target_history_missing_symbol() -> None:
    out = await agent_tools.invoke_tool("price_target_history", {})
    assert out["ok"] is False


@pytest.mark.asyncio
async def test_no_order_placing_tools_registered() -> None:
    """Sanity: defense-in-depth check matching the §6.5 audit grep.

    The Phase 6 plan guarantees no agent tool can place an order. The
    safety-audit suite asserts this at the suite level by grepping the
    sidecar source; this test asserts it from inside the registry.
    """
    forbidden = {"place_order", "submit_order", "execute_order", "auto_approve"}
    registered = set(agent_tools.registered_tools())
    assert forbidden.isdisjoint(registered)
