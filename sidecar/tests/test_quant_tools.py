"""Tests for the Phase 6 quant agent tools.

Each tool wraps a :mod:`services.quant` function — these tests confirm
the registration, the happy-path invocation, and the unhappy-path
``{"ok": False, "error": ...}`` shape.
"""

from __future__ import annotations

import pytest

from services import agent_tools
from services.agent_tools import quant_tools


@pytest.fixture(autouse=True)
def _register_quant_tools() -> None:
    """Re-register quant tools on a clean registry per test."""
    agent_tools.reset_for_tests()
    quant_tools.register()
    yield
    agent_tools.reset_for_tests()


def test_register_lists_all_four_ids() -> None:
    ids = agent_tools.registered_tools()
    assert "price_option" in ids
    assert "compute_greeks" in ids
    assert "price_bond" in ids
    assert "yield_curve_value" in ids


@pytest.mark.asyncio
async def test_price_option_happy_path() -> None:
    out = await agent_tools.invoke_tool(
        "price_option",
        {
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
        },
    )
    assert out["ok"] is True
    assert out["result"]["price"] > 0
    assert out["result"]["greeks"] is not None


@pytest.mark.asyncio
async def test_price_option_invalid_args_returns_error_shape() -> None:
    out = await agent_tools.invoke_tool("price_option", {"spot": "not a number"})
    assert out["ok"] is False
    assert "error" in out


@pytest.mark.asyncio
async def test_compute_greeks_happy_path() -> None:
    out = await agent_tools.invoke_tool(
        "compute_greeks",
        {
            "payoff": "call",
            "spot": 100.0,
            "strike": 100.0,
            "risk_free_rate": 0.05,
            "dividend_yield": 0.02,
            "volatility": 0.20,
            "valuation_date": "2026-05-16",
            "expiry_date": "2027-05-16",
        },
    )
    assert out["ok"] is True
    g = out["result"]["greeks"]
    assert {"delta", "gamma", "vega", "theta", "rho"} <= set(g.keys())


@pytest.mark.asyncio
async def test_price_bond_happy_path() -> None:
    out = await agent_tools.invoke_tool(
        "price_bond",
        {
            "face_value": 1000.0,
            "coupon_rate": 0.05,
            "coupons_per_year": 2,
            "issue_date": "2026-05-16",
            "maturity_date": "2036-05-16",
            "settlement_date": "2026-05-16",
            "yield_to_maturity": 0.05,
        },
    )
    assert out["ok"] is True
    assert out["result"]["clean_price"] == pytest.approx(1000.0, rel=1e-3)


@pytest.mark.asyncio
async def test_yield_curve_value_happy_path() -> None:
    out = await agent_tools.invoke_tool(
        "yield_curve_value",
        {
            "valuation_date": "2026-05-16",
            "instruments": [
                {"type": "deposit", "tenor": 1, "tenor_unit": "months", "rate": 0.041},
                {"type": "swap", "tenor": 5, "tenor_unit": "years", "rate": 0.047},
                {"type": "swap", "tenor": 10, "tenor_unit": "years", "rate": 0.050},
            ],
            "sample_count": 5,
        },
    )
    assert out["ok"] is True
    assert len(out["result"]["curve"]) == 5


# ---------------------------------------------------------------------------
# §6.5 audit defence — placement-style tool ids must not exist
# ---------------------------------------------------------------------------


def test_no_order_placement_tool_ids_registered() -> None:
    """BLUEPRINT §6.5 audit assertion — the agent_tools registry must NEVER
    expose a placement-style tool id even via the Phase 6 quant surface.
    Mirrors the grep done by ``test_safety_end_to_end.py``.
    """
    ids = set(agent_tools.registered_tools())
    forbidden = {"place_order", "submit_order", "execute_order", "auto_approve"}
    assert ids.isdisjoint(forbidden)
