"""Greeks helper tests — analytic vs. finite-difference parity.

The Greeks dashboard endpoint always uses the analytic engine, so the
test checks the public surface :func:`services.quant.greeks.compute_greeks`
against a finite-difference re-pricing via the BS pricer.
"""

from __future__ import annotations

from datetime import date

import pytest

from models.quant import GreeksRequest, OptionPricingRequest
from services.quant import greeks, options


def _make_greeks_req(**overrides: object) -> GreeksRequest:
    base = {
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.02,
        "volatility": 0.20,
        "valuation_date": date(2026, 5, 16),
        "expiry_date": date(2027, 5, 16),
    }
    base.update(overrides)
    return GreeksRequest.model_validate(base)


def _make_option_req(**overrides: object) -> OptionPricingRequest:
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


def test_analytic_delta_matches_finite_difference() -> None:
    g = greeks.compute_greeks(_make_greeks_req())
    h = 0.01
    up = options.price(_make_option_req(spot=100.0 + h))
    dn = options.price(_make_option_req(spot=100.0 - h))
    fd_delta = (up.price - dn.price) / (2.0 * h)
    assert g.greeks.delta == pytest.approx(fd_delta, abs=1e-3)


def test_analytic_gamma_matches_finite_difference() -> None:
    g = greeks.compute_greeks(_make_greeks_req())
    h = 0.5
    base = options.price(_make_option_req())
    up = options.price(_make_option_req(spot=100.0 + h))
    dn = options.price(_make_option_req(spot=100.0 - h))
    fd_gamma = (up.price - 2.0 * base.price + dn.price) / (h * h)
    assert g.greeks.gamma == pytest.approx(fd_gamma, abs=1e-4)


def test_analytic_vega_matches_finite_difference() -> None:
    g = greeks.compute_greeks(_make_greeks_req())
    h = 0.0005
    up = options.price(_make_option_req(volatility=0.20 + h))
    dn = options.price(_make_option_req(volatility=0.20 - h))
    fd_vega = (up.price - dn.price) / (2.0 * h)
    # QuantLib's vega is per unit-vol; allow a 0.1 % tolerance.
    assert g.greeks.vega == pytest.approx(fd_vega, rel=1e-3)


def test_call_delta_in_unit_interval() -> None:
    g = greeks.compute_greeks(_make_greeks_req())
    assert 0.0 <= g.greeks.delta <= 1.0


def test_put_delta_in_negative_unit_interval() -> None:
    g = greeks.compute_greeks(_make_greeks_req(payoff="put"))
    assert -1.0 <= g.greeks.delta <= 0.0


def test_gamma_positive() -> None:
    """Vanilla European long-only options always have positive gamma."""
    g_call = greeks.compute_greeks(_make_greeks_req())
    g_put = greeks.compute_greeks(_make_greeks_req(payoff="put"))
    assert g_call.greeks.gamma > 0
    assert g_put.greeks.gamma > 0


def test_vega_positive() -> None:
    """Vanilla options always have positive vega."""
    g_call = greeks.compute_greeks(_make_greeks_req())
    g_put = greeks.compute_greeks(_make_greeks_req(payoff="put"))
    assert g_call.greeks.vega > 0
    assert g_put.greeks.vega > 0


def test_call_theta_negative_for_atm() -> None:
    """ATM call theta is negative (time decay) for r-q > 0 conditions."""
    g = greeks.compute_greeks(_make_greeks_req())
    assert g.greeks.theta < 0


def test_price_returned_alongside_greeks() -> None:
    g = greeks.compute_greeks(_make_greeks_req())
    assert g.price > 0
    # Sanity: matches the BS pricer for the same inputs.
    bs = options.price(_make_option_req())
    assert g.price == pytest.approx(bs.price, rel=1e-8)
