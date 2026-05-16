"""Tests for the Phase 6 quant workflow nodes."""

from __future__ import annotations

import pytest

from services import workflow_engine
from services.workflow_nodes import quant_nodes


@pytest.fixture(autouse=True)
def _register_quant_nodes() -> None:
    workflow_engine.reset_registry_for_tests()
    quant_nodes.register()
    yield
    workflow_engine.reset_registry_for_tests()


def test_register_all_four_node_types() -> None:
    types = set(workflow_engine.registered_node_types())
    assert {
        "quant.price_option",
        "quant.compute_greeks",
        "quant.price_bond",
        "quant.yield_curve",
    } <= types


@pytest.mark.asyncio
async def test_price_option_node() -> None:
    config = {
        "exercise": "european",
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.02,
        "volatility": 0.20,
        "valuation_date": "2026-05-16",
        "expiry_date": "2027-05-16",
        "method": "black-scholes",
    }
    out = await quant_nodes.price_option({}, config)
    assert out["result"]["price"] > 0


@pytest.mark.asyncio
async def test_price_option_node_inputs_override_config() -> None:
    """Inputs override config — supports upstream-emitted spot values."""
    config = {
        "exercise": "european",
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.02,
        "volatility": 0.20,
        "valuation_date": "2026-05-16",
        "expiry_date": "2027-05-16",
        "method": "black-scholes",
    }
    out_base = await quant_nodes.price_option({}, config)
    out_override = await quant_nodes.price_option({"spot": 110.0}, config)
    assert out_override["result"]["price"] > out_base["result"]["price"]


@pytest.mark.asyncio
async def test_compute_greeks_node() -> None:
    config = {
        "payoff": "call",
        "spot": 100.0,
        "strike": 100.0,
        "risk_free_rate": 0.05,
        "dividend_yield": 0.02,
        "volatility": 0.20,
        "valuation_date": "2026-05-16",
        "expiry_date": "2027-05-16",
    }
    out = await quant_nodes.compute_greeks({}, config)
    assert out["result"]["greeks"]["delta"] > 0


@pytest.mark.asyncio
async def test_price_bond_node() -> None:
    config = {
        "face_value": 1000.0,
        "coupon_rate": 0.05,
        "coupons_per_year": 2,
        "issue_date": "2026-05-16",
        "maturity_date": "2036-05-16",
        "settlement_date": "2026-05-16",
        "yield_to_maturity": 0.05,
    }
    out = await quant_nodes.price_bond({}, config)
    assert out["result"]["clean_price"] == pytest.approx(1000.0, rel=1e-3)


@pytest.mark.asyncio
async def test_yield_curve_node() -> None:
    config = {
        "valuation_date": "2026-05-16",
        "instruments": [
            {"type": "deposit", "tenor": 1, "tenor_unit": "months", "rate": 0.041},
            {"type": "swap", "tenor": 10, "tenor_unit": "years", "rate": 0.050},
        ],
        "sample_count": 5,
    }
    out = await quant_nodes.bootstrap_yield_curve({}, config)
    assert len(out["result"]["curve"]) == 5


@pytest.mark.asyncio
async def test_price_option_node_invalid_raises() -> None:
    with pytest.raises(ValueError, match="quant.price_option"):
        await quant_nodes.price_option({}, {"spot": "not a number"})
