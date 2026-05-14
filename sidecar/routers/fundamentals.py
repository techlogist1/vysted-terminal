"""Fundamentals router — valuation ratios, financial statements, analyst ratings.

Backs the equity-overview panel. Phase 1.A serves these from yfinance; the
Phase 2 OpenBB ODP wrap plugin can deepen the coverage without router changes.
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
def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``."""
    return provider_registry.get_fundamentals(symbol)


@router.get("/{symbol}/income")
def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    return provider_registry.get_income_statement(symbol)


@router.get("/{symbol}/balance")
def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    return provider_registry.get_balance_sheet(symbol)


@router.get("/{symbol}/cashflow")
def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    return provider_registry.get_cash_flow(symbol)


@router.get("/{symbol}/ratings")
def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings and price targets for ``symbol``."""
    return provider_registry.get_analyst_rating(symbol)
