"""Phase 6 workflow nodes — QuantLib pricing surface (Teammate Q).

Four node types register here:

* ``quant.price_option``      — dispatch into BS / Binomial / MC.
* ``quant.compute_greeks``    — analytic Greeks helper.
* ``quant.price_bond``        — fixed-rate bond pricing.
* ``quant.yield_curve``       — depo+swap bootstrap of a zero curve.

Each handler accepts inputs via the standard inputs/config split — the
``config`` dict is the node-level static spec from the saved workflow,
and ``inputs`` are the dynamic outputs from upstream nodes. The node
merges them with ``inputs`` taking precedence so an upstream node's
emitted spot/strike/etc. wins over the static config.
"""

from __future__ import annotations

from typing import Any

from models.quant import (
    BondPricingRequest,
    GreeksRequest,
    OptionPricingRequest,
    YieldCurveRequest,
)
from services import workflow_engine
from services.quant import bonds, greeks, options, yield_curve


def _merge(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Static config + dynamic inputs — inputs win on a key collision."""
    merged: dict[str, Any] = {}
    merged.update(config)
    merged.update({k: v for k, v in inputs.items() if v is not None})
    return merged


async def price_option(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Price one option via the requested engine.

    Returns ``{"result": <OptionPricingResult model_dump>}``. Workflow
    edges typically pluck ``result.price`` / ``result.greeks.delta``
    / etc. via the ``transform.json_path`` built-in.
    """
    args = _merge(inputs, config)
    try:
        req = OptionPricingRequest.model_validate(args)
    except Exception as exc:
        raise ValueError(f"quant.price_option: invalid request: {exc}") from exc
    result = options.price(req)
    return {"result": result.model_dump(mode="json")}


async def compute_greeks(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Compute analytic Greeks for a European vanilla option."""
    args = _merge(inputs, config)
    try:
        req = GreeksRequest.model_validate(args)
    except Exception as exc:
        raise ValueError(f"quant.compute_greeks: invalid request: {exc}") from exc
    result = greeks.compute_greeks(req)
    return {"result": result.model_dump(mode="json")}


async def price_bond(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Price a fixed-rate bond at the given YTM."""
    args = _merge(inputs, config)
    try:
        req = BondPricingRequest.model_validate(args)
    except Exception as exc:
        raise ValueError(f"quant.price_bond: invalid request: {exc}") from exc
    result = bonds.price_bond(req)
    return {"result": result.model_dump(mode="json")}


async def bootstrap_yield_curve(inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Bootstrap and sample a zero curve from depo + swap instruments."""
    args = _merge(inputs, config)
    try:
        req = YieldCurveRequest.model_validate(args)
    except Exception as exc:
        raise ValueError(f"quant.yield_curve: invalid request: {exc}") from exc
    result = yield_curve.bootstrap_curve(req)
    return {"result": result.model_dump(mode="json")}


def register() -> None:
    """Register every quant workflow-node type. Called from the v0.6.0 aggregator."""
    workflow_engine.register_node_type("quant.price_option", price_option)
    workflow_engine.register_node_type("quant.compute_greeks", compute_greeks)
    workflow_engine.register_node_type("quant.price_bond", price_bond)
    workflow_engine.register_node_type("quant.yield_curve", bootstrap_yield_curve)


__all__ = [
    "bootstrap_yield_curve",
    "compute_greeks",
    "price_bond",
    "price_option",
    "register",
]
