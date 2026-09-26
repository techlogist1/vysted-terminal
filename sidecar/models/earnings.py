"""Earnings calendar + estimates + surprises Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/earnings.ts``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Event identity
# ---------------------------------------------------------------------------

EarningsTimeOfDay = Literal["before-open", "during-market", "after-close", "unknown"]

QuarterLabel = Literal["Q1", "Q2", "Q3", "Q4", "FY"]


class FiscalPeriod(BaseModel):
    """Fiscal-period label — e.g. ``"Q1 2026"``, ``"FY 2025"``.

    Every ``fiscal_period`` field is ``None`` unless the provider supplies the
    period — it is never inferred from a report date (R15-DATA-067)."""

    model_config = ConfigDict(extra="forbid")

    quarter: QuarterLabel
    year: int


class EarningsEvent(BaseModel):
    """One scheduled earnings event in the upcoming-calendar view."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    company_name: str | None = None
    scheduled_date: date
    time_of_day: EarningsTimeOfDay
    fiscal_period: FiscalPeriod | None = None
    eps_estimate_mean: float | None = None
    #: Measured dispersion only — None unless the provider supplies it.
    eps_estimate_stddev: float | None = None
    #: None when the provider gives no count (never a 0 standing in for unknown).
    estimate_analyst_count: int | None = Field(default=None, ge=0)
    currency: str = "USD"
    provider: str


# ---------------------------------------------------------------------------
# Surprise (post-report)
# ---------------------------------------------------------------------------


class EarningsSurprise(BaseModel):
    """Actual reported result paired with the pre-report consensus estimate."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    #: The fiscal quarter end (R15-LEAD-016) — the sort key and the chart's
    #: x-axis; unlike ``reported_date`` it is never ``None``.
    period_end: date
    #: The actual announcement date, when one was found within 0-120 days of
    #: ``period_end`` — ``None`` otherwise. Distinct from ``period_end``: a
    #: company can report weeks after its quarter closes.
    reported_date: date | None = None
    fiscal_period: FiscalPeriod | None = None
    eps_actual: float
    eps_estimate_mean: float
    eps_surprise: float
    eps_surprise_pct: float | None = None
    revenue_actual: float | None = None
    revenue_estimate_mean: float | None = None
    revenue_surprise_pct: float | None = None
    currency: str = "USD"
    #: The revenue fields' own currency — a foreign reporter's statement-size
    #: revenue is denominated in the reporting currency, not the trading
    #: currency ``currency`` carries. Scale-checked against ``totalRevenue``
    #: before trusting Yahoo's ``financialCurrency``; ``None`` when neither
    #: the scale check nor a home-market fallback determines it — never a
    #: guessed label (R15-DATA-113).
    revenue_currency: str | None = None
    provider: str


# ---------------------------------------------------------------------------
# Estimate detail (pre-report)
# ---------------------------------------------------------------------------


class EarningsEstimateDetail(BaseModel):
    """Detailed estimate breakdown for one upcoming earnings event."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    fiscal_period: FiscalPeriod | None = None
    #: R15-LEAD-039: nullable, same shape as the revenue triple below — Yahoo's
    #: calendar payload omits these for several liquid non-US names (RDY, TM,
    #: SONY); each field is independently nullable, never a raise.
    eps_estimate_mean: float | None = None
    eps_estimate_median: float | None = None
    eps_estimate_high: float | None = None
    eps_estimate_low: float | None = None
    eps_estimate_stddev: float | None = None
    estimate_analyst_count: int | None = Field(default=None, ge=0)
    revenue_estimate_mean: float | None = None
    revenue_estimate_median: float | None = None
    revenue_estimate_high: float | None = None
    revenue_estimate_low: float | None = None
    #: The revenue frame's own count — never the EPS count (R15-DATA-032).
    revenue_analyst_count: int | None = Field(default=None, ge=0)
    currency: str = "USD"
    #: See ``EarningsSurprise.revenue_currency`` (R15-DATA-113).
    revenue_currency: str | None = None
    provider: str
    as_of: datetime


# ---------------------------------------------------------------------------
# Response envelopes
# ---------------------------------------------------------------------------


class EarningsUpcomingResponse(BaseModel):
    """Returned by ``GET /earnings/upcoming``."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date
    events: list[EarningsEvent]
    #: When this window was actually fetched from the provider (R15-DATA-068)
    #: — a cache hit carries the ORIGINAL fetch time, not the read time.
    as_of: datetime | None = None


class EarningsSurprisesResponse(BaseModel):
    """Returned by ``GET /earnings/{symbol}/surprises``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    surprises: list[EarningsSurprise]
    #: R15-DATA-068 — see ``EarningsUpcomingResponse.as_of``.
    as_of: datetime | None = None


class EarningsHistoryEntry(BaseModel):
    """One past earnings result in the symbol history grid."""

    model_config = ConfigDict(extra="forbid")

    fiscal_period: FiscalPeriod | None = None
    #: The fiscal quarter end (R15-LEAD-016) — the sort key, NOT the
    #: announcement date (a company reports weeks after its quarter closes).
    period_end: date
    #: The actual announcement date, when one was found within 0-120 days of
    #: ``period_end`` — ``None`` otherwise (was: silently the same as
    #: ``period_end``, the R15-LEAD-016 defect).
    reported_date: date | None = None
    eps_actual: float
    eps_estimate_mean: float | None = None
    revenue_actual: float | None = None
    revenue_estimate_mean: float | None = None
    currency: str = "USD"
    #: See ``EarningsSurprise.revenue_currency`` (R15-DATA-113).
    revenue_currency: str | None = None


class EarningsHistoryResponse(BaseModel):
    """Returned by ``GET /earnings/{symbol}/history``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    history: list[EarningsHistoryEntry]
    #: R15-DATA-068 — see ``EarningsUpcomingResponse.as_of``.
    as_of: datetime | None = None
