"""Standalone Greeks dashboard helper — always Black-Scholes analytic.

The Greeks Dashboard panel hits this surface independently of the
generic option pricer so the user can sweep inputs without picking
"black-scholes" each time. The analytic engine is the natural fit —
delta/gamma/vega/theta/rho are exact closed-form values, and the BS
price comes along for free so the panel can display both.
"""

from __future__ import annotations

from models.quant import GreeksRequest, GreeksResult, OptionPricingRequest

from ._common import holds_ql_lock
from .options import price_european_bs


@holds_ql_lock
def compute_greeks(req: GreeksRequest) -> GreeksResult:
    """Compute analytic Greeks for a European vanilla option.

    Delegates to :func:`.options.price_european_bs` — the Greeks Dashboard
    panel hits this surface independently of the generic option pricer so
    the user can sweep inputs without picking "black-scholes" each time
    (:class:`GreeksRequest` is the option-pricer's request shape minus
    ``exercise``/``method``), but the engine call itself must stay one
    definition (R15-CODE-PLATFORM-042). Returns Greeks per the QuantLib
    internal convention (vega per unit-vol, theta per year); the panels
    convert to vega per 1 vol point and theta per calendar day
    (src/modules/quant/units.ts).
    """
    req.validate_domain()
    option_req = OptionPricingRequest(
        exercise="european",
        payoff=req.payoff,
        spot=req.spot,
        strike=req.strike,
        risk_free_rate=req.risk_free_rate,
        dividend_yield=req.dividend_yield,
        volatility=req.volatility,
        valuation_date=req.valuation_date,
        expiry_date=req.expiry_date,
        method="black-scholes",
    )
    result = price_european_bs(option_req)
    assert result.greeks is not None  # black-scholes always populates greeks

    return GreeksResult(
        greeks=result.greeks,
        price=result.price,
        duration_ms=result.duration_ms,
    )


__all__ = ["compute_greeks"]
