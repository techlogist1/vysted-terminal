"""Fundamentals Pydantic models — ratios, financial statements, analyst ratings.

Mirrored by hand in ``types/data.ts`` — keep in sync (see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Fundamentals(BaseModel):
    """Snapshot of valuation ratios, profitability, health, and profile for one
    symbol. All new screener-grade fields are optional (``None`` when the source
    does not carry them) so the panel renders a reason, never a fabricated value.

    Units are documented per field: ``*_margin``/``roe``/``roa``/``*_growth``/
    ``held_percent_*``/``fifty_two_week_change`` are FRACTIONS (0.21 = 21%);
    ``dividend_yield`` is a fraction; ``debt_to_equity`` is a RATIO (yfinance's
    percent form divided by 100, so 1.5 = 150%); currency-denominated sizes
    (``revenue_ttm``/``net_income_ttm``/``free_cash_flow``/``dividend_per_share``)
    are in ``currency``.
    """

    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    currency: str | None = None
    # --- Valuation ---
    market_cap: float | None = None
    pe_ratio: float | None = None
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    price_to_sales: float | None = None
    ev_to_ebitda: float | None = None
    book_value: float | None = None
    dividend_yield: float | None = None
    dividend_per_share: float | None = None
    eps: float | None = None
    beta: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    fifty_two_week_change: float | None = None
    # --- Profitability (fractions) ---
    roe: float | None = None
    roa: float | None = None
    gross_margin: float | None = None
    operating_margin: float | None = None
    profit_margin: float | None = None
    # --- Financial health ---
    debt_to_equity: float | None = None
    current_ratio: float | None = None
    quick_ratio: float | None = None
    # --- Size & growth ---
    revenue_ttm: float | None = None
    net_income_ttm: float | None = None
    free_cash_flow: float | None = None
    shares_outstanding: float | None = None
    revenue_growth: float | None = None
    earnings_growth: float | None = None
    # --- Ownership (fractions) — promoter / institutional proxies (esp. IN) ---
    held_percent_insiders: float | None = None
    held_percent_institutions: float | None = None
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
    strong_buy: int = Field(default=0, ge=0)  # counts, never negative — Phase 9.5
    buy: int = Field(default=0, ge=0)
    hold: int = Field(default=0, ge=0)
    sell: int = Field(default=0, ge=0)
    strong_sell: int = Field(default=0, ge=0)
    provider: str
