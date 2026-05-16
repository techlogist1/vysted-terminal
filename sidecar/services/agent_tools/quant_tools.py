"""Phase 6 agent tools — QuantLib pricing surface (Teammate Q).

Each tool is a thin wrapper over the :mod:`services.quant` service
module. The wrappers parse the agent's JSON-shaped args into the
Pydantic request, dispatch, and return ``model_dump(mode="json")`` so
the LLM sees plain-JSON.

These are read-only / math-only tools — no broker or order-placement
side effects. The §6.5 audit suite's tool-id grep
(``test_safety_end_to_end.py::test_audit_6``) confirms none of the ids
below collide with ``place_order`` / ``submit_order`` / ``execute_order``.

Registered tool ids:

* ``price_option``        — black-scholes / binomial / monte-carlo dispatcher.
* ``compute_greeks``      — analytic Greeks for a European vanilla.
* ``price_bond``          — fixed-rate bond clean / dirty / duration / convexity.
* ``yield_curve_value``   — bootstrap a curve, sample at one tenor.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from models.quant import (
    BondPricingRequest,
    GreeksRequest,
    OptionPricingRequest,
    YieldCurveRequest,
)
from services.agent_tools import register_tool
from services.quant import bonds, greeks, options, yield_curve


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
        result = options.price(req)
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
        result = greeks.compute_greeks(req)
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
        result = bonds.price_bond(req)
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
        result = yield_curve.bootstrap_curve(req)
    except ValueError as exc:
        return _bad(str(exc))
    return {"ok": True, "result": result.model_dump(mode="json")}


def register() -> None:
    """Register every quant agent tool. Called from the v0.6.0 aggregator."""
    register_tool("price_option", _price_option)
    register_tool("compute_greeks", _compute_greeks)
    register_tool("price_bond", _price_bond)
    register_tool("yield_curve_value", _yield_curve_value)


__all__ = [
    "_compute_greeks",
    "_price_bond",
    "_price_option",
    "_yield_curve_value",
    "register",
]
