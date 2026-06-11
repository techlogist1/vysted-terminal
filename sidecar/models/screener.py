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

ScreenerUniverseId = Literal[
    "sp500",
    "nifty50",
    "crypto-top50",
    "custom",
    # R10 (D40): full-market India universes resolved from the bundled resolver
    # masters — nse-all (~2.7k EQ/BE/SME rows), bse-all (4.9k Active scrips),
    # india-all (union, NSE listing preferred on dual-listings).
    "nse-all",
    "bse-all",
    "india-all",
]
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
    # Valuation
    "market_cap",
    "pe_ratio",
    "forward_pe",
    "peg_ratio",
    "price_to_book",
    "price_to_sales",
    "ev_to_ebitda",
    "book_value",
    "dividend_yield",
    "eps",
    "beta",
    # Profitability (fractions: 0.20 = 20%)
    "roe",
    "roa",
    "gross_margin",
    "operating_margin",
    "profit_margin",
    # Financial health
    "debt_to_equity",
    "current_ratio",
    "quick_ratio",
    # Growth (fractions)
    "revenue_growth",
    "earnings_growth",
    # Range / ownership
    "fifty_two_week_high",
    "fifty_two_week_low",
    "fifty_two_week_change",
    "held_percent_insiders",
    "held_percent_institutions",
    # Price-derived (from the live quote)
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


class CriterionGroup(BaseModel):
    """A boolean combinator node — AND/OR over leaf criteria or nested groups.

    Enables OR + nested logic (e.g. ``(P/E < 15 AND ROE > 0.2) OR dividend_yield >
    0.04``) beyond the flat AND-only ``criteria`` list. An EMPTY group matches
    everything (no filter) regardless of combinator, mirroring the "no criteria =
    show all" behaviour of the flat path. Recursive: a child may itself be a group.
    """

    model_config = ConfigDict(extra="forbid")

    combinator: Literal["and", "or"] = "and"
    # ``from __future__ import annotations`` makes this whole annotation a string,
    # so the recursive self-reference resolves at ``model_rebuild()`` below — do
    # NOT quote ``CriterionGroup`` inline (``UnionType | str`` fails to eval).
    criteria: list[
        NumericThresholdCriterion
        | NumericBetweenCriterion
        | StringEqCriterion
        | SetInCriterion
        | CriterionGroup
    ] = Field(default_factory=list)


CriterionGroup.model_rebuild()


# ---------------------------------------------------------------------------
# Request / response
# ---------------------------------------------------------------------------


class ScreenerRequest(BaseModel):
    """Request shape for ``POST /screener/run``."""

    model_config = ConfigDict(extra="forbid")

    universe: ScreenerUniverseId
    custom_symbols: list[str] | None = None
    criteria: list[ScreenerCriterion]
    # Optional boolean tree (AND/OR, nestable). When present it SUPERSEDES the flat
    # ``criteria`` (which stays AND-combined for back-compat). Lets the UI / agent
    # express OR + grouped logic without breaking the old wire shape.
    group: CriterionGroup | None = None
    # Optional free-text boolean expression evaluated SERVER-SIDE per universe
    # member, AND-combined with the criteria/group (R7 Pillar 3). The grammar is
    # services.screener_formula (field refs + arithmetic + comparisons +
    # and/or/not + abs/min/max — no eval). A row missing a referenced field is
    # skipped and itemized ``missing_field:<f>`` in the skip ledger.
    formula: str | None = None
    # Upper-bounded to match types/screener.ts ("max 1000") and the runtime
    # clamp in services/screener.py (_MAX_LIMIT=1000) — Phase 9.5.
    limit: int = Field(default=200, ge=1, le=1000)

    @field_validator("formula")
    @classmethod
    def _formula_parses(cls, v: str | None) -> str | None:
        """Reject an unparseable formula at the request boundary (422 with the
        parser's message + 1-based column). Blank normalizes to ``None``. The
        import is lazy to keep ``models`` free of import-time service deps."""
        if v is None or not v.strip():
            return None
        from services.screener_formula import FormulaError, compile_formula

        try:
            compile_formula(v)
        except FormulaError as exc:
            col = f" (col {exc.position + 1})" if exc.position is not None else ""
            raise ValueError(f"invalid formula: {exc}{col}") from exc
        return v

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
    forward_pe: float | None = None
    peg_ratio: float | None = None
    price_to_book: float | None = None
    dividend_yield: float | None = None
    roe: float | None = None
    debt_to_equity: float | None = None
    price: float | None = None
    change_percent_1d: float | None = None
    volume: float | None = None
    matched_criteria: list[int] = []


class SkipDetail(BaseModel):
    """One itemized skip — a universe member that never reached evaluation.

    The R4 batch fast path (FR-126 / SC-034) replaced the old "silently drop
    242/506" behaviour with a complete ledger: every symbol the screener could
    not evaluate is itemized here with a machine-readable ``reason`` so the UI
    can surface coverage honestly. ``skipped_count == len(skip_details)`` always.

    ``reason`` is one of:
      - ``"timeout"`` — the upstream fetch (batch chunk or per-symbol) timed out.
      - ``"not_found"`` — Yahoo did not return a row for the symbol.
      - ``"no_data"`` — a row came back but carried no usable price / payload.
      - ``"rate_limited"`` — the upstream throttled the request (HTTP 429).
      - ``"correctness_gate"`` — the provider raised a ``ProviderError`` (a
        deliberate refusal to fabricate a value).
      - ``"missing_field:<field>"`` — a criterion or the custom ``formula``
        referenced a field neither the batch row nor the per-symbol enrichment
        could supply for this symbol.
    """

    model_config = ConfigDict(extra="forbid")

    symbol: str
    reason: str


class FormulaValidation(BaseModel):
    """Response shape from ``POST /screener/formula/validate`` (R7 Pillar 3).

    The inline-validation surface for the custom formula grammar
    (:mod:`services.screener_formula`) — never a 4xx/5xx for a bad formula;
    the error + 0-based caret ``position`` ride the body so an editor (or the
    agent) can render `^` at the offending column.
    """

    model_config = ConfigDict(extra="forbid")

    ok: bool
    error: str | None = None
    #: 0-based character offset of the error in the formula text.
    position: int | None = None
    #: Canonical (snake_case) fields the formula references, sorted.
    fields: list[str] = Field(default_factory=list)


class ScreenerResult(BaseModel):
    """Response shape from ``POST /screener/run``."""

    model_config = ConfigDict(extra="forbid")

    universe: ScreenerUniverseId
    evaluated_count: int
    # Symbols that were dropped (timeout / provider error) before evaluation —
    # so a low evaluated_count no longer silently misrepresents coverage
    # (Phase 9.5). Defaulted for backward compatibility.
    skipped_count: int = 0
    # Itemized skip ledger (R4 / FR-126 / SC-034) — one entry per dropped symbol
    # with a machine-readable reason. ``skipped_count == len(skip_details)``.
    # Defaulted so older callers / fixtures that omit it still validate.
    skip_details: list[SkipDetail] = Field(default_factory=list)
    result_count: int
    rows: list[ScreenerResultRow]
    duration_ms: float
    # R10 (D40) honest-coverage block — additive, defaulted for back-compat.
    # ``partial`` is True when the wall budget or a cancellation cut the run
    # before the whole universe was evaluated; ``coverage`` is the one human
    # line the UI/agent surface ("screened 1,840 of 2,100 — 260 unavailable");
    # ``freshness`` stamps the data tiers the rows were served from (epoch
    # seconds: {"quotes_as_of": …, "valuation_as_of": …, "deep_as_of": …}).
    partial: bool = False
    coverage: str | None = None
    freshness: dict[str, float] | None = None
