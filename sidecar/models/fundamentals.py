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
    #: Basis of the growth fields above (R11 / D55). yfinance's
    #: ``revenueGrowth``/``earningsGrowth`` are MOST-RECENT-QUARTER vs the same
    #: quarter a year ago — NOT annual/TTM growth. Every surface rendering the
    #: growth fields must disclose this basis; a provider supplying a different
    #: basis must set this field accordingly.
    growth_basis: str | None = "mrq_yoy"
    # --- Ownership (fractions) — promoter / institutional proxies (esp. IN) ---
    held_percent_insiders: float | None = None
    held_percent_institutions: float | None = None
    #: Trailing-12-month dividends ACTUALLY PAID per share (summed from the
    #: corporate-action history, in ``currency``) — the deterministic
    #: cross-check for ``dividend_per_share`` (R11 / D56): Yahoo's
    #: ``dividendRate`` can omit a special dividend; the paid history cannot.
    #: ``None`` when the history was unavailable.
    dividend_per_share_ttm: float | None = None
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


class UnverifiedClaim(BaseModel):
    """One numeric figure in the LLM narrative that did NOT match the source data.

    The narrative service extracts every numeric claim from the model's output
    and matches each against the real fundamentals/quote it was given. A claim
    that matches no source value (a likely hallucination) is recorded here and
    REDACTED from the prose before it reaches the UI — a fabricated figure must
    never render as fact.
    """

    text: str
    """The literal numeric token as the model wrote it (e.g. ``"$4.2T"``, ``"31.5"``)."""
    reason: str
    """Why it failed verification (no source field matched within tolerance)."""


class CompanyNarrative(BaseModel):
    """An LLM-written, numerically-verified company overview for one symbol.

    Every number that survives into ``summary`` / ``insights`` has been matched
    against the real :class:`Fundamentals` + :class:`~models.market.Quote` the
    service fetched (the same source the panel renders). Unverified figures are
    redacted from the prose and listed in ``unverified_claims`` for transparency.

    When no model/key is available the route still returns ``200`` with
    ``summary=None`` + ``insights=[]`` + a ``reason`` — the UI renders a quiet
    "AI narrative unavailable" state, never an error.
    """

    symbol: str
    summary: str | None = None
    """The 2–4 sentence narrative, with any unverified number redacted. ``None``
    when no narrative was produced (no key, empty model output, or all prose
    redacted)."""
    insights: list[str] = Field(default_factory=list)
    """2–4 short key-insight bullets, each verified the same way as ``summary``."""
    verified: bool = False
    """``True`` when a narrative was produced AND every numeric claim in it
    matched a source value. ``False`` when nothing was produced or at least one
    claim was redacted."""
    unverified_claims: list[UnverifiedClaim] = Field(default_factory=list)
    """Numeric claims that failed verification and were redacted from the prose."""
    source_provider: str | None = None
    """The data provider that served the fundamentals/quote the narrative is
    grounded in (e.g. ``"yfinance"``) — the UI's "verified against {provider}"
    label."""
    model: str | None = None
    """The LLM model id that wrote the narrative, when one ran."""
    generated_at: str | None = None
    """ISO-8601 UTC timestamp of generation, or ``None`` when no narrative ran."""
    reason: str | None = None
    """Human-readable explanation when ``summary`` is ``None`` (no key, no model
    output, no fundamentals) — surfaced verbatim in the quiet empty state."""
