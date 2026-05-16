"""Golden-value tests for the option pricing engines.

Reference values come from the closed-form Black-Scholes formula:

    d1 = (ln(S/K) + (r - q + σ²/2)·T) / (σ·√T)
    d2 = d1 - σ·√T
    Call = S·e⁻ᵠᵀ·Φ(d1) - K·e⁻ʳᵀ·Φ(d2)
    Put  = K·e⁻ʳᵀ·Φ(-d2) - S·e⁻ᵠᵀ·Φ(-d1)

We compute the reference Python-side via :mod:`math` so the tests are
self-contained and the engine output is compared against a known
analytic value, not against itself.
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from models.quant import OptionPricingRequest
from services.quant import options


def _bs_reference(
    spot: float,
    strike: float,
    r: float,
    q: float,
    vol: float,
    T: float,
    payoff: str,
) -> float:
    """Closed-form Black-Scholes price for a European vanilla option."""
    if T <= 0.0:
        intrinsic = max(spot - strike, 0.0) if payoff == "call" else max(strike - spot, 0.0)
        return intrinsic
    d1 = (math.log(spot / strike) + (r - q + 0.5 * vol * vol) * T) / (vol * math.sqrt(T))
    d2 = d1 - vol * math.sqrt(T)
    n = lambda x: 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))  # noqa: E731
    if payoff == "call":
        return spot * math.exp(-q * T) * n(d1) - strike * math.exp(-r * T) * n(d2)
    return strike * math.exp(-r * T) * n(-d2) - spot * math.exp(-q * T) * n(-d1)


def _make_req(**overrides: object) -> OptionPricingRequest:
    base = {
        "exercise": "european",
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.02,
        "volatility": 0.20,
        "valuation_date": date(2026, 5, 16),
        "expiry_date": date(2027, 5, 16),
        "method": "black-scholes",
    }
    base.update(overrides)
    return OptionPricingRequest.model_validate(base)


# ---------------------------------------------------------------------------
# Black-Scholes analytic
# ---------------------------------------------------------------------------


def test_atm_call_bs_matches_closed_form() -> None:
    req = _make_req()
    result = options.price(req)
    T = (req.expiry_date - req.valuation_date).days / 365.0
    reference = _bs_reference(
        req.spot, req.strike, req.risk_free_rate, req.dividend_yield, req.volatility, T, "call"
    )
    assert result.method == "black-scholes"
    assert result.price == pytest.approx(reference, rel=1e-4)
    assert result.greeks is not None
    assert 0.4 < result.greeks.delta < 0.7
    assert result.greeks.gamma > 0
    assert result.greeks.vega > 0
    assert result.duration_ms > 0


def test_atm_put_bs_matches_closed_form() -> None:
    req = _make_req(payoff="put")
    result = options.price(req)
    T = (req.expiry_date - req.valuation_date).days / 365.0
    reference = _bs_reference(
        req.spot, req.strike, req.risk_free_rate, req.dividend_yield, req.volatility, T, "put"
    )
    assert result.price == pytest.approx(reference, rel=1e-4)
    assert result.greeks is not None
    assert -0.7 < result.greeks.delta < -0.3


def test_otm_call_bs_low_price_and_low_delta() -> None:
    req = _make_req(strike=120.0)
    result = options.price(req)
    assert result.price < 5.0
    assert result.greeks is not None
    assert result.greeks.delta < 0.4


def test_bs_rejects_american_exercise() -> None:
    req = _make_req(exercise="american")
    with pytest.raises(ValueError, match="european"):
        options.price_european_bs(req)


# ---------------------------------------------------------------------------
# Binomial CRR
# ---------------------------------------------------------------------------


def test_binomial_converges_to_bs_for_european() -> None:
    req_bs = _make_req()
    bs = options.price(req_bs)
    req_bn = _make_req(method="binomial", binomial_steps=500)
    bn = options.price(req_bn)
    # 500-step CRR European converges to Black-Scholes within 0.1 % at ATM.
    assert bn.price == pytest.approx(bs.price, rel=2e-3)
    assert bn.method == "binomial"


def test_american_put_premium_over_european() -> None:
    """American put has early-exercise premium vs. European put."""
    eu = options.price(_make_req(payoff="put", method="black-scholes"))
    am = options.price(
        _make_req(payoff="put", exercise="american", method="binomial", binomial_steps=500)
    )
    # American put strictly >= European put (early-exercise option).
    assert am.price >= eu.price


def test_binomial_greeks_populated() -> None:
    req = _make_req(method="binomial", binomial_steps=200)
    result = options.price(req)
    assert result.greeks is not None
    assert 0.4 < result.greeks.delta < 0.7
    assert result.greeks.gamma > 0
    assert result.greeks.vega > 0


def test_binomial_default_steps() -> None:
    """Omitting ``binomial_steps`` should fall back to DEFAULT_BINOMIAL_STEPS."""
    req = _make_req(method="binomial")
    result = options.price(req)
    assert result.price > 0


# ---------------------------------------------------------------------------
# Monte Carlo European
# ---------------------------------------------------------------------------


def test_mc_mean_within_two_std_errors_of_bs() -> None:
    req_bs = _make_req()
    bs = options.price(req_bs)
    req_mc = _make_req(method="monte-carlo", monte_carlo_paths=100_000, monte_carlo_seed=42)
    mc = options.price(req_mc)
    assert mc.method == "monte-carlo"
    assert mc.monte_carlo_std_error is not None and mc.monte_carlo_std_error > 0
    # MC mean should land within 2 std errors of BS at 100k paths.
    assert abs(mc.price - bs.price) <= 2.0 * mc.monte_carlo_std_error


def test_mc_seed_reproducibility() -> None:
    """Same seed → same MC price (modulo QuantLib RNG determinism)."""
    a = options.price(
        _make_req(method="monte-carlo", monte_carlo_paths=20_000, monte_carlo_seed=42)
    )
    b = options.price(
        _make_req(method="monte-carlo", monte_carlo_paths=20_000, monte_carlo_seed=42)
    )
    assert a.price == pytest.approx(b.price)


def test_mc_rejects_american_exercise() -> None:
    req = _make_req(exercise="american", method="monte-carlo")
    with pytest.raises(ValueError, match="european"):
        options.price_european_mc(req)


def test_mc_rejects_too_few_paths() -> None:
    req = _make_req(method="monte-carlo", monte_carlo_paths=50)
    with pytest.raises(ValueError, match="at least 100"):
        options.price_european_mc(req)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def test_dispatcher_rejects_unknown_method() -> None:
    req = _make_req()
    object.__setattr__(req, "method", "fft")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="unknown pricing method"):
        options.price(req)


def test_put_call_parity_holds_under_bs() -> None:
    """C - P = S·e⁻ᵠᵀ - K·e⁻ʳᵀ for European options on a flat-vol BSM process."""
    call = options.price(_make_req(payoff="call"))
    put = options.price(_make_req(payoff="put"))
    req = _make_req()
    T = (req.expiry_date - req.valuation_date).days / 365.0
    rhs = req.spot * math.exp(-req.dividend_yield * T) - req.strike * math.exp(
        -req.risk_free_rate * T
    )
    assert (call.price - put.price) == pytest.approx(rhs, rel=1e-3)
