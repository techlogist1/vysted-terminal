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
# Input-domain bounds (Phase 9.5 F4-1)
# ---------------------------------------------------------------------------
#
# The quant endpoints previously did ZERO input-domain validation: negative
# volatility, strike 0, expiry<=valuation, and absurd ytm all returned 200 with
# degenerate/garbage output. Each request model now exposes ``validate_domain()``
# raising a clear ``ValueError`` for economically-invalid inputs; the quant
# router already maps ``ValueError`` -> HTTP 400. These bounds are deliberately
# generous (any real-world scenario fits) — they reject only nonsense that would
# otherwise produce garbage prices or a DoS-grade compute load.

MIN_RATE = -1.0  # a yield / rate below -100% is economically meaningless
MAX_RATE = 10.0  # 1000% — far above any real rate, rejects 1e6-style garbage
MAX_VOLATILITY = 100.0  # 10000% annualised vol ceiling
MAX_BINOMIAL_STEPS = 100_000  # guard against runaway lattice compute
MAX_MC_PATHS = 10_000_000  # guard against runaway Monte-Carlo compute
MAX_CURVE_SAMPLES = 10_000  # guard against runaway curve sampling


def _validate_option_inputs(
    *,
    spot: float,
    strike: float,
    volatility: float,
    risk_free_rate: float,
    dividend_yield: float,
    valuation_date: date,
    expiry_date: date,
) -> None:
    """Shared domain checks for option / Greeks requests (raises ValueError)."""
    if spot <= 0:
        raise ValueError(f"spot must be positive (got {spot})")
    if strike <= 0:
        raise ValueError(f"strike must be positive (got {strike})")
    if not 0 <= volatility <= MAX_VOLATILITY:
        raise ValueError(f"volatility must be between 0 and {MAX_VOLATILITY} (got {volatility})")
    if not MIN_RATE <= risk_free_rate <= MAX_RATE:
        raise ValueError(
            f"risk_free_rate must be between {MIN_RATE} and {MAX_RATE} (got {risk_free_rate})"
        )
    if not 0 <= dividend_yield <= MAX_RATE:
        raise ValueError(f"dividend_yield must be between 0 and {MAX_RATE} (got {dividend_yield})")
    if expiry_date <= valuation_date:
        raise ValueError("expiry_date must be after valuation_date")


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

    def validate_domain(self) -> None:
        """Reject economically-invalid inputs (surfaced as HTTP 400). F4-1."""
        _validate_option_inputs(
            spot=self.spot,
            strike=self.strike,
            volatility=self.volatility,
            risk_free_rate=self.risk_free_rate,
            dividend_yield=self.dividend_yield,
            valuation_date=self.valuation_date,
            expiry_date=self.expiry_date,
        )
        if self.binomial_steps is not None and not 1 <= self.binomial_steps <= MAX_BINOMIAL_STEPS:
            raise ValueError(
                f"binomial_steps must be between 1 and {MAX_BINOMIAL_STEPS} "
                f"(got {self.binomial_steps})"
            )
        if self.monte_carlo_paths is not None and not 1 <= self.monte_carlo_paths <= MAX_MC_PATHS:
            raise ValueError(
                f"monte_carlo_paths must be between 1 and {MAX_MC_PATHS} "
                f"(got {self.monte_carlo_paths})"
            )


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

    def validate_domain(self) -> None:
        """Reject economically-invalid numeric inputs (surfaced as HTTP 400).

        Date ordering (issue/settlement/maturity) is enforced separately in
        ``services.quant.bonds.price_bond`` — this covers only the numeric
        domain the catalog flagged (face/coupon/ytm). F4-1.
        """
        if self.face_value <= 0:
            raise ValueError(f"face_value must be positive (got {self.face_value})")
        if not 0 <= self.coupon_rate <= MAX_RATE:
            raise ValueError(
                f"coupon_rate must be between 0 and {MAX_RATE} (got {self.coupon_rate})"
            )
        if not MIN_RATE < self.yield_to_maturity <= MAX_RATE:
            raise ValueError(
                f"yield_to_maturity must be greater than {MIN_RATE} and at most {MAX_RATE} "
                f"(got {self.yield_to_maturity})"
            )


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

    def validate_domain(self) -> None:
        """Reject invalid bootstrap inputs (surfaced as HTTP 400). F4-1."""
        if not self.instruments:
            raise ValueError("yield-curve bootstrap requires at least one instrument")
        if not 2 <= self.sample_count <= MAX_CURVE_SAMPLES:
            raise ValueError(
                f"sample_count must be between 2 and {MAX_CURVE_SAMPLES} (got {self.sample_count})"
            )
        for inst in self.instruments:
            if inst.tenor <= 0:
                raise ValueError(f"instrument tenor must be positive (got {inst.tenor})")
            if not MIN_RATE <= inst.rate <= MAX_RATE:
                raise ValueError(
                    f"instrument rate must be between {MIN_RATE} and {MAX_RATE} (got {inst.rate})"
                )


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

    def validate_domain(self) -> None:
        """Reject economically-invalid inputs (surfaced as HTTP 400). F4-1."""
        _validate_option_inputs(
            spot=self.spot,
            strike=self.strike,
            volatility=self.volatility,
            risk_free_rate=self.risk_free_rate,
            dividend_yield=self.dividend_yield,
            valuation_date=self.valuation_date,
            expiry_date=self.expiry_date,
        )


class GreeksResult(BaseModel):
    """Output of ``POST /quant/option/greeks``."""

    model_config = ConfigDict(extra="forbid")

    greeks: Greeks
    price: float
    duration_ms: float
