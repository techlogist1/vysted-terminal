"""Standalone Greeks dashboard helper — always Black-Scholes analytic.

The Greeks Dashboard panel hits this surface independently of the
generic option pricer so the user can sweep inputs without picking
"black-scholes" each time. The analytic engine is the natural fit —
delta/gamma/vega/theta/rho are exact closed-form values, and the BS
price comes along for free so the panel can display both.
"""

from __future__ import annotations

import time

import QuantLib as ql

from models.quant import Greeks, GreeksRequest, GreeksResult

from ._common import build_bsm_process, ql_option_type, to_ql_date


def compute_greeks(req: GreeksRequest) -> GreeksResult:
    """Compute analytic Greeks for a European vanilla option.

    Uses :class:`ql.AnalyticEuropeanEngine` over the same flat-BSM
    process the option pricer uses (:func:`._common.build_bsm_process`).
    Returns Greeks per the QuantLib internal convention (vega per
    unit-vol, theta per year); the panel relabels for display.
    """
    started = time.perf_counter()

    process = build_bsm_process(
        req.spot,
        req.risk_free_rate,
        req.dividend_yield,
        req.volatility,
        req.valuation_date,
    )
    payoff = ql.PlainVanillaPayoff(ql_option_type(req.payoff), req.strike)
    exercise = ql.EuropeanExercise(to_ql_date(req.expiry_date))
    option = ql.VanillaOption(payoff, exercise)
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))

    greeks = Greeks(
        delta=option.delta(),
        gamma=option.gamma(),
        vega=option.vega(),
        theta=option.theta(),
        rho=option.rho(),
    )
    price = option.NPV()

    return GreeksResult(
        greeks=greeks,
        price=price,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )


__all__ = ["compute_greeks"]
