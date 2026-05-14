"""Fundamentals Pydantic models — ratios, financial statements, analyst ratings.

Mirrored by hand in ``types/data.ts`` — keep in sync (see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from pydantic import BaseModel


class Fundamentals(BaseModel):
    """Snapshot of valuation ratios and company profile for one symbol."""

    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    dividend_yield: float | None = None
    eps: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    provider: str


class StatementLine(BaseModel):
    """One labelled row of a financial statement, keyed by period label."""

    label: str
    values: dict[str, float | None]


class FinancialStatement(BaseModel):
    """Shared shape for the three financial statements."""

    symbol: str
    periods: list[str]
    lines: list[StatementLine]
    provider: str


class IncomeStatement(FinancialStatement):
    """Income statement excerpt."""


class BalanceSheet(FinancialStatement):
    """Balance sheet excerpt."""


class CashFlowStatement(FinancialStatement):
    """Cash-flow statement excerpt."""


class AnalystRating(BaseModel):
    """Aggregated analyst ratings and price targets for one symbol."""

    symbol: str
    consensus: str | None = None
    target_mean: float | None = None
    target_high: float | None = None
    target_low: float | None = None
    strong_buy: int = 0
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_sell: int = 0
    provider: str
