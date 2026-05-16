"""QuantLib pricing router — Phase 6 (Teammate Q).

In-process pricing — every endpoint is a thin wrapper over one of
:mod:`services.quant.options`, :mod:`services.quant.greeks`,
:mod:`services.quant.bonds`, :mod:`services.quant.yield_curve`. The
service modules return the Pydantic response shapes directly, so the
router is pure dispatch.

Endpoints:

* ``POST /quant/option/price``   — dispatches to BS / Binomial / MC.
* ``POST /quant/option/greeks``  — analytic Greeks dashboard helper.
* ``POST /quant/bond/price``     — fixed-rate bond clean/dirty/duration.
* ``POST /quant/yield-curve``    — depo+swap bootstrap of a zero curve.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.quant import (
    BondPricingRequest,
    BondPricingResult,
    GreeksRequest,
    GreeksResult,
    OptionPricingRequest,
    OptionPricingResult,
    YieldCurveRequest,
    YieldCurveResult,
)
from services.quant import bonds, greeks, options, yield_curve

router = APIRouter(prefix="/quant", tags=["quant"])


@router.post("/option/price", response_model=OptionPricingResult)
def option_price(req: OptionPricingRequest) -> OptionPricingResult:
    """Price one option via the engine named in ``req.method``."""
    try:
        return options.price(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/option/greeks", response_model=GreeksResult)
def option_greeks(req: GreeksRequest) -> GreeksResult:
    """Compute analytic Greeks (and price) for a European vanilla option."""
    try:
        return greeks.compute_greeks(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bond/price", response_model=BondPricingResult)
def bond_price(req: BondPricingRequest) -> BondPricingResult:
    """Price a fixed-rate bond at a given YTM."""
    try:
        return bonds.price_bond(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/yield-curve", response_model=YieldCurveResult)
def yield_curve_bootstrap(req: YieldCurveRequest) -> YieldCurveResult:
    """Bootstrap and sample a zero curve from depo + swap instruments."""
    try:
        return yield_curve.bootstrap_curve(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


__all__ = ["router"]
