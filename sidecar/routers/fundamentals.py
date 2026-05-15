"""Fundamentals router — valuation ratios, financial statements, analyst ratings.

Backs the equity-overview panel. Phase 1.A served these from yfinance; Phase 3
prefers openbb-mcp (the replacement for the retired Phase-2 OpenBB plugin)
with a yfinance fallback. The registry handles the dispatch; the router only
awaits the resulting coroutine.
"""

from __future__ import annotations

from fastapi import APIRouter

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from services import provider_registry

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])


@router.get("/{symbol}")
async def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``."""
    return await provider_registry.get_fundamentals(symbol)


@router.get("/{symbol}/income")
async def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    return await provider_registry.get_income_statement(symbol)


@router.get("/{symbol}/balance")
async def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    return await provider_registry.get_balance_sheet(symbol)


@router.get("/{symbol}/cashflow")
async def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    return await provider_registry.get_cash_flow(symbol)


@router.get("/{symbol}/ratings")
async def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings and price targets for ``symbol``."""
    return await provider_registry.get_analyst_rating(symbol)
