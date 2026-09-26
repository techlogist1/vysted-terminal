"""QuantLib pricing router — Phase 6 (Teammate Q).

Every endpoint prices in the :mod:`services.quant.pool` worker process
(off the event loop) and is a thin wrapper over one of
:mod:`services.quant.options`, :mod:`services.quant.greeks`,
:mod:`services.quant.bonds`, :mod:`services.quant.yield_curve`. The
service modules return the Pydantic response shapes directly, so the
router is pure dispatch.

Endpoints:

* ``POST /quant/option/price``   — dispatches to BS / Binomial / MC.
* ``POST /quant/option/greeks``  — analytic Greeks dashboard helper.
* ``POST /quant/bond/price``     — fixed-rate bond clean/dirty/duration.
* ``POST /quant/yield-curve``    — depo+swap bootstrap of a zero curve.
* ``GET  /quant/option/chain/{symbol}`` — the listed chain with exchange OI
  (NSE F&O bhavcopy / yfinance), EOD research data (R15-DATA-079).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException

from models.market import OptionChain
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
from services import option_chain
from services.quant import bonds, greeks, options, yield_curve
from services.quant.pool import run_quant

router = APIRouter(prefix="/quant", tags=["quant"])


@router.post("/option/price", response_model=OptionPricingResult)
async def option_price(req: OptionPricingRequest) -> OptionPricingResult:
    """Price one option via the engine named in ``req.method``."""
    try:
        return await run_quant(options.price, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/option/greeks", response_model=GreeksResult)
async def option_greeks(req: GreeksRequest) -> GreeksResult:
    """Compute analytic Greeks (and price) for a European vanilla option."""
    try:
        return await run_quant(greeks.compute_greeks, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/bond/price", response_model=BondPricingResult)
async def bond_price(req: BondPricingRequest) -> BondPricingResult:
    """Price a fixed-rate bond at a given YTM."""
    try:
        return await run_quant(bonds.price_bond, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/yield-curve", response_model=YieldCurveResult)
async def yield_curve_bootstrap(req: YieldCurveRequest) -> YieldCurveResult:
    """Bootstrap and sample a zero curve from depo + swap instruments."""
    try:
        return await run_quant(yield_curve.bootstrap_curve, req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        # QuantLib's PiecewiseLinearZero raises a RuntimeError (not a
        # ValueError) for a bootstrap it can't build — e.g. two instruments
        # at the same pillar (maturity date) — which otherwise surfaces as
        # an uncaught 500 with no CORS headers (R15-UI-077).
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/option/chain/{symbol}", response_model=OptionChain)
async def option_chain_view(symbol: str, expiry: date | None = None) -> OptionChain:
    """One expiry of the listed option chain (nearest when ``expiry`` is omitted)."""
    try:
        chain = await option_chain.get_option_chain(symbol, expiry)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except option_chain.OptionChainUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if chain is None:
        raise HTTPException(
            status_code=404, detail=f"{symbol.upper()} has no listed options (not_found)"
        )
    return chain


__all__ = ["router"]
