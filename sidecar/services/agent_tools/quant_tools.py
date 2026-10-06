"""Phase 6 agent tools — QuantLib pricing surface (Teammate Q).

Each tool is a thin wrapper over the :mod:`services.quant` service
module. The wrappers parse the agent's JSON-shaped args into the
Pydantic request, dispatch, and return ``model_dump(mode="json")`` so
the LLM sees plain-JSON.

These are read-only / math-only tools with no side effects. The Gate-8
test (``test_no_trading_surface.py``) confirms none of the ids below collide
with ``place_order`` / ``submit_order`` / ``execute_order``.

Registered tool ids:

* ``price_option``        — black-scholes / binomial / monte-carlo dispatcher.
* ``compute_greeks``      — analytic Greeks for a European vanilla.
* ``price_bond``          — fixed-rate bond clean / dirty / duration / convexity.
* ``yield_curve_value``   — bootstrap a curve, sample at one tenor.
* ``option_chain``        — the listed chain with exchange-published OI (R15-DATA-079).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import ValidationError

from models.quant import (
    BondPricingRequest,
    GreeksRequest,
    OptionPricingRequest,
    YieldCurveRequest,
)
from services import option_chain
from services.agent_tools import register_tool
from services.quant import bonds, greeks, options, yield_curve
from services.quant.pool import run_quant


def _bad(msg: str) -> dict[str, Any]:
    """Uniform ``{"ok": False, "error": ...}`` shape the LLM can parse."""
    return {"ok": False, "error": msg}


async def _price_option(args: dict[str, Any]) -> dict[str, Any]:
    """Price one option via the requested engine.

    Args must include every field of :class:`OptionPricingRequest`;
    optional fields (``binomial_steps`` / ``monte_carlo_paths`` /
    ``monte_carlo_seed``) get sensible defaults.
    """
    try:
        req = OptionPricingRequest.model_validate(args)
    except ValidationError as exc:
        return _bad(f"invalid OptionPricingRequest: {exc.errors()[0]['msg']}")
    try:
        result = await run_quant(options.price, req)
    except ValueError as exc:
        return _bad(str(exc))
    return {"ok": True, "result": result.model_dump(mode="json")}


async def _compute_greeks(args: dict[str, Any]) -> dict[str, Any]:
    """Compute analytic Greeks (and the BS price) for a European vanilla option."""
    try:
        req = GreeksRequest.model_validate(args)
    except ValidationError as exc:
        return _bad(f"invalid GreeksRequest: {exc.errors()[0]['msg']}")
    try:
        result = await run_quant(greeks.compute_greeks, req)
    except ValueError as exc:
        return _bad(str(exc))
    return {"ok": True, "result": result.model_dump(mode="json")}


async def _price_bond(args: dict[str, Any]) -> dict[str, Any]:
    """Price a fixed-rate bond at a yield-to-maturity."""
    try:
        req = BondPricingRequest.model_validate(args)
    except ValidationError as exc:
        return _bad(f"invalid BondPricingRequest: {exc.errors()[0]['msg']}")
    try:
        result = await run_quant(bonds.price_bond, req)
    except ValueError as exc:
        return _bad(str(exc))
    return {"ok": True, "result": result.model_dump(mode="json")}


async def _yield_curve_value(args: dict[str, Any]) -> dict[str, Any]:
    """Bootstrap a curve and return the full sampled curve.

    Convenience wrapper for the workflow / agent surface. Args are
    :class:`YieldCurveRequest`-shaped; the response carries the entire
    sampled curve so the agent can reason about the term structure.
    """
    try:
        req = YieldCurveRequest.model_validate(args)
    except ValidationError as exc:
        return _bad(f"invalid YieldCurveRequest: {exc.errors()[0]['msg']}")
    try:
        result = await run_quant(yield_curve.bootstrap_curve, req)
    except ValueError as exc:
        return _bad(str(exc))
    return {"ok": True, "result": result.model_dump(mode="json")}


async def _option_chain(args: dict[str, Any]) -> dict[str, Any]:
    """One expiry of a symbol's listed option chain, trimmed to the strikes nearest spot."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        return _bad("missing or non-string symbol")
    try:
        expiry = date.fromisoformat(args["expiry"]) if args.get("expiry") else None
        max_strikes = int(args.get("max_strikes") or 20)
    except (TypeError, ValueError) as exc:
        return _bad(f"invalid argument: {exc}")
    try:
        chain = await option_chain.get_option_chain(symbol.strip(), expiry)
    except ValueError as exc:
        return _bad(str(exc))
    except option_chain.OptionChainUnavailable as exc:
        return _bad(f"provider error: {exc}")
    if chain is None:
        return _bad(f"not_found: {symbol.strip().upper()} has no listed options")
    strikes = sorted({c.strike for c in chain.contracts})
    if chain.underlying_price is not None and len(strikes) > max_strikes:
        spot = chain.underlying_price
        keep = set(sorted(strikes, key=lambda k: abs(k - spot))[:max_strikes])
        chain.contracts = [c for c in chain.contracts if c.strike in keep]
    return {"ok": True, "result": chain.model_dump(mode="json"), "strikes_listed": len(strikes)}


def register() -> None:
    """Register every quant agent tool. Called from the v0.6.0 aggregator."""
    register_tool("price_option", _price_option)
    register_tool("compute_greeks", _compute_greeks)
    register_tool("price_bond", _price_bond)
    register_tool("yield_curve_value", _yield_curve_value)
    register_tool("option_chain", _option_chain)


__all__ = [
    "_compute_greeks",
    "_option_chain",
    "_price_bond",
    "_price_option",
    "_yield_curve_value",
    "register",
]
