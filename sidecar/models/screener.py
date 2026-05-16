"""Screener / scanner Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/screener.ts``.

The criteria union uses a Pydantic-2 discriminated union by ``operator``,
matching the TypeScript discriminated union on the same field.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Universe
# ---------------------------------------------------------------------------

ScreenerUniverseId = Literal["sp500", "nifty50", "crypto-top50", "custom"]
ScreenerAssetClass = Literal["equity", "crypto"]


class ScreenerUniverse(BaseModel):
    """A universe definition the screener fans out across."""

    model_config = ConfigDict(extra="forbid")

    id: ScreenerUniverseId
    label: str
    symbols: list[str]
    asset_class: ScreenerAssetClass


# ---------------------------------------------------------------------------
# Criteria
# ---------------------------------------------------------------------------

ScreenerNumericField = Literal[
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "dividend_yield",
    "eps",
    "beta",
    "fifty_two_week_high",
    "fifty_two_week_low",
    "price",
    "change_percent_1d",
    "volume",
]

ScreenerStringField = Literal["sector", "industry", "currency"]
ScreenerSetField = Literal["symbol", "sector", "industry"]


class NumericThresholdCriterion(BaseModel):
    """``> | < | >= | <=`` against a numeric field."""

    model_config = ConfigDict(extra="forbid")

    field: ScreenerNumericField
    operator: Literal["gt", "lt", "gte", "lte"]
    value: float


class NumericRange(BaseModel):
    """Inclusive numeric range for the ``between`` operator."""

    model_config = ConfigDict(extra="forbid")

    min: float
    max: float


class NumericBetweenCriterion(BaseModel):
    """``between`` against a numeric field."""

    model_config = ConfigDict(extra="forbid")

    field: ScreenerNumericField
    operator: Literal["between"]
    value: NumericRange


class StringEqCriterion(BaseModel):
    """``= `` against a string field — sector / industry / currency."""

    model_config = ConfigDict(extra="forbid")

    field: ScreenerStringField
    operator: Literal["eq"]
    value: str


class SetInCriterion(BaseModel):
    """``in`` against a set of string values."""

    model_config = ConfigDict(extra="forbid")

    field: ScreenerSetField
    operator: Literal["in"]
    value: list[str]


ScreenerCriterion = (
    NumericThresholdCriterion | NumericBetweenCriterion | StringEqCriterion | SetInCriterion
)


# ---------------------------------------------------------------------------
# Request / response
# ---------------------------------------------------------------------------


class ScreenerRequest(BaseModel):
    """Request shape for ``POST /screener/run``."""

    model_config = ConfigDict(extra="forbid")

    universe: ScreenerUniverseId
    custom_symbols: list[str] | None = None
    criteria: list[ScreenerCriterion]
    limit: int = 200


class ScreenerResultRow(BaseModel):
    """One row in the screener results table."""

    model_config = ConfigDict(extra="forbid")

    symbol: str
    name: str | None = None
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    pe_ratio: float | None = None
    price: float | None = None
    change_percent_1d: float | None = None
    volume: float | None = None
    matched_criteria: list[int] = []


class ScreenerResult(BaseModel):
    """Response shape from ``POST /screener/run``."""

    model_config = ConfigDict(extra="forbid")

    universe: ScreenerUniverseId
    evaluated_count: int
    result_count: int
    rows: list[ScreenerResultRow]
    duration_ms: float
