"""Screener / scanner Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/screener.ts``.

The criteria union uses a Pydantic-2 discriminated union by ``operator``,
matching the TypeScript discriminated union on the same field.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _reject_non_finite(value: float, name: str) -> float:
    """Reject NaN / ±Inf — they silently break numeric comparisons (Phase 9.5)."""
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{name} must be a finite number (got {value})")
    return value


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

    @field_validator("value")
    @classmethod
    def _value_finite(cls, v: float) -> float:
        return _reject_non_finite(v, "value")


class NumericRange(BaseModel):
    """Inclusive numeric range for the ``between`` operator."""

    model_config = ConfigDict(extra="forbid")

    min: float
    max: float

    @field_validator("min", "max")
    @classmethod
    def _bound_finite(cls, v: float) -> float:
        return _reject_non_finite(v, "range bound")

    @model_validator(mode="after")
    def _min_le_max(self) -> NumericRange:
        if self.min > self.max:
            raise ValueError(f"range min ({self.min}) must be <= max ({self.max})")
        return self


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
    # Upper-bounded to match types/screener.ts ("max 1000") and the runtime
    # clamp in services/screener.py (_MAX_LIMIT=1000) — Phase 9.5.
    limit: int = Field(default=200, ge=1, le=1000)

    @model_validator(mode="after")
    def _custom_requires_symbols(self) -> ScreenerRequest:
        """An explicit ``custom`` universe must carry a non-empty symbol list
        (Phase 9.5). Note: a non-empty ``custom_symbols`` is honoured with ANY
        universe (it overrides — see services.screener.resolve_universe); this
        validator only rejects the contradictory ``custom`` + empty case."""
        if self.universe == "custom":
            cleaned = [s for s in (self.custom_symbols or []) if s and s.strip()]
            if not cleaned:
                raise ValueError("universe 'custom' requires a non-empty custom_symbols list")
        return self


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


class SkipDetail(BaseModel):
    """One itemized dropped symbol (FR-126 / SC-034 — zero silent drops).

    The screener never silently drops a universe member: every symbol that does
    not make it into the evaluation set is recorded here with a ``reason`` the UI
    renders as a skip ledger. ``reason`` is one of a fixed vocabulary:

      * ``timeout`` — the upstream fetch (batch chunk or per-symbol) timed out;
      * ``not_found`` — the provider did not return the symbol (delisted /
        unknown ticker / wrong suffix);
      * ``no_data`` — the provider returned the symbol but with no usable data
        (e.g. no positive price);
      * ``rate_limited`` — the upstream throttled us (HTTP 429);
      * ``correctness_gate`` — the per-symbol enrichment fetch errored / was
        rejected;
      * ``missing_field:<field>`` — a screened criterion needs a field the fast
        path does not carry and per-symbol enrichment could not supply it.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str
    reason: str


class ScreenerResult(BaseModel):
    """Response shape from ``POST /screener/run``."""

    model_config = ConfigDict(extra="forbid")

    universe: ScreenerUniverseId
    evaluated_count: int
    # Symbols that were dropped (timeout / provider error) before evaluation —
    # so a low evaluated_count no longer silently misrepresents coverage
    # (Phase 9.5). Defaulted for backward compatibility.
    skipped_count: int = 0
    # Itemized skip ledger (FR-126 / SC-034): every dropped symbol with a reason,
    # so a skip is never silent. ``len(skip_details) == skipped_count`` once the
    # fast path is wired; defaulted to ``[]`` for backward compatibility with
    # older serialized blobs / fixtures that predate the ledger.
    skip_details: list[SkipDetail] = []
    result_count: int
    rows: list[ScreenerResultRow]
    duration_ms: float
