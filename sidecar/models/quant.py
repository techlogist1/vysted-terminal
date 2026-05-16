"""QuantLib-backed pricing Pydantic models — Phase 6.

Hand-maintained Python mirror of ``types/quant.ts``.

These shapes are framework-neutral on purpose — no QuantLib types appear on
the wire. The QuantLib backend in ``services/quant/`` converts these inputs
into its internal C++ object model and back to plain dataclasses for the
HTTP boundary.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

# ---------------------------------------------------------------------------
# Options
# ---------------------------------------------------------------------------

OptionExercise = Literal["european", "american"]
OptionPayoff = Literal["call", "put"]
OptionPricingMethod = Literal["black-scholes", "binomial", "monte-carlo"]


class OptionPricingRequest(BaseModel):
    """Inputs for an option-pricing call."""

    model_config = ConfigDict(extra="forbid")

    exercise: OptionExercise
    payoff: OptionPayoff
    spot: float
    strike: float
    risk_free_rate: float
    dividend_yield: float
    volatility: float
    valuation_date: date
    expiry_date: date
    method: OptionPricingMethod
    binomial_steps: int | None = None
    monte_carlo_paths: int | None = None
    monte_carlo_seed: int | None = None


class Greeks(BaseModel):
    """First / second-order option sensitivities."""

    model_config = ConfigDict(extra="forbid")

    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float


class OptionPricingResult(BaseModel):
    """Output of an option-pricing call."""

    model_config = ConfigDict(extra="forbid")

    price: float
    greeks: Greeks | None = None
    method: OptionPricingMethod
    monte_carlo_std_error: float | None = None
    duration_ms: float


# ---------------------------------------------------------------------------
# Bonds
# ---------------------------------------------------------------------------

CouponFrequency = Literal[1, 2, 4]


class BondPricingRequest(BaseModel):
    """Inputs for a fixed-rate bond pricing call."""

    model_config = ConfigDict(extra="forbid")

    face_value: float = 1000.0
    coupon_rate: float
    coupons_per_year: CouponFrequency
    issue_date: date
    maturity_date: date
    settlement_date: date
    yield_to_maturity: float


class BondPricingResult(BaseModel):
    """Output of a bond-pricing call."""

    model_config = ConfigDict(extra="forbid")

    clean_price: float
    dirty_price: float
    accrued_interest: float
    duration: float
    modified_duration: float
    convexity: float
    duration_ms: float


# ---------------------------------------------------------------------------
# Yield curve
# ---------------------------------------------------------------------------

YieldCurveInstrumentType = Literal["deposit", "swap"]
TenorUnit = Literal["months", "years"]


class YieldCurveInstrument(BaseModel):
    """One instrument used to bootstrap a yield curve."""

    model_config = ConfigDict(extra="forbid")

    type: YieldCurveInstrumentType
    tenor: int
    tenor_unit: TenorUnit
    rate: float


class YieldCurveRequest(BaseModel):
    """Bootstrap a yield curve from the given instruments."""

    model_config = ConfigDict(extra="forbid")

    valuation_date: date
    instruments: list[YieldCurveInstrument]
    sample_count: int


class YieldCurvePoint(BaseModel):
    """One sampled point on a bootstrapped curve."""

    model_config = ConfigDict(extra="forbid")

    date: date
    tenor_years: float
    zero_rate: float
    discount_factor: float


class YieldCurveResult(BaseModel):
    """Output of ``POST /quant/yield-curve``."""

    model_config = ConfigDict(extra="forbid")

    valuation_date: date
    curve: list[YieldCurvePoint]
    duration_ms: float


# ---------------------------------------------------------------------------
# Greeks-only (dashboard helper)
# ---------------------------------------------------------------------------


class GreeksRequest(BaseModel):
    """Subset of :class:`OptionPricingRequest` for the standalone Greeks endpoint."""

    model_config = ConfigDict(extra="forbid")

    payoff: OptionPayoff
    spot: float
    strike: float
    risk_free_rate: float
    dividend_yield: float
    volatility: float
    valuation_date: date
    expiry_date: date


class GreeksResult(BaseModel):
    """Output of ``POST /quant/option/greeks``."""

    model_config = ConfigDict(extra="forbid")

    greeks: Greeks
    price: float
    duration_ms: float
