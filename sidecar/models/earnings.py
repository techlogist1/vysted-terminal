"""Earnings calendar + estimates + surprises Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/earnings.ts``.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Event identity
# ---------------------------------------------------------------------------

EarningsTimeOfDay = Literal["before-open", "during-market", "after-close", "unknown"]

QuarterLabel = Literal["Q1", "Q2", "Q3", "Q4", "FY"]


class FiscalPeriod(BaseModel):
    """Fiscal-period label — e.g. ``"Q1 2026"``, ``"FY 2025"``."""

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
    fiscal_period: FiscalPeriod
    eps_estimate_mean: float | None = None
    eps_estimate_stddev: float | None = None
    estimate_analyst_count: int = 0
    currency: str = "USD"
    provider: str


# ---------------------------------------------------------------------------
# Surprise (post-report)
# ---------------------------------------------------------------------------


class EarningsSurprise(BaseModel):
    """Actual reported result paired with the pre-report consensus estimate."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    reported_date: date
    fiscal_period: FiscalPeriod
    eps_actual: float
    eps_estimate_mean: float
    eps_surprise: float
    eps_surprise_pct: float | None = None
    revenue_actual: float | None = None
    revenue_estimate_mean: float | None = None
    revenue_surprise_pct: float | None = None
    currency: str = "USD"
    provider: str


# ---------------------------------------------------------------------------
# Estimate detail (pre-report)
# ---------------------------------------------------------------------------


class EarningsEstimateDetail(BaseModel):
    """Detailed estimate breakdown for one upcoming earnings event."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    fiscal_period: FiscalPeriod
    eps_estimate_mean: float
    eps_estimate_median: float | None = None
    eps_estimate_high: float
    eps_estimate_low: float
    eps_estimate_stddev: float | None = None
    estimate_analyst_count: int
    revenue_estimate_mean: float | None = None
    revenue_estimate_median: float | None = None
    revenue_estimate_high: float | None = None
    revenue_estimate_low: float | None = None
    revenue_analyst_count: int = 0
    currency: str = "USD"
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


class EarningsSurprisesResponse(BaseModel):
    """Returned by ``GET /earnings/{symbol}/surprises``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    surprises: list[EarningsSurprise]


class EarningsHistoryEntry(BaseModel):
    """One past earnings result in the symbol history grid."""

    model_config = ConfigDict(extra="forbid")

    fiscal_period: FiscalPeriod
    reported_date: date
    eps_actual: float
    eps_estimate_mean: float | None = None
    revenue_actual: float | None = None
    revenue_estimate_mean: float | None = None
    currency: str = "USD"


class EarningsHistoryResponse(BaseModel):
    """Returned by ``GET /earnings/{symbol}/history``."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    history: list[EarningsHistoryEntry]
