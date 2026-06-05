"""Safety + behaviour tests for the copilot's per-invocation action tools.

The copilot can DRIVE the terminal (open panels, set the chart symbol, add to
the watchlist) and can PREPARE — never place — broker orders. These tests pin
the §6.5 invariant: no tool the AI can call places/submits/executes an order;
``propose_order`` only ever returns an ``awaiting_user_review`` directive.
"""

from __future__ import annotations

import asyncio
import re

from models.agent import AgentContextSnapshot
from services import agent_runtime, agent_tools
from services.agent_tools.schemas import TOOL_SCHEMAS

_FORBIDDEN = re.compile(r"place_order|submit_order|execute_order")


def test_no_order_placement_tool_anywhere() -> None:
    # §6.5: neither the model-facing schema catalog nor the live handler
    # registry may expose an order-placement tool id.
    for tid in TOOL_SCHEMAS:
        assert not _FORBIDDEN.search(tid), f"forbidden placement tool id in schemas: {tid}"
    for tid in agent_tools.registered_tools():
        assert not _FORBIDDEN.search(tid), f"forbidden placement tool id registered: {tid}"


def test_propose_order_only_prepares_never_places() -> None:
    local = agent_runtime._build_local_tools(None)
    assert "propose_order" in local
    result = asyncio.run(local["propose_order"]({"symbol": "AAPL", "side": "buy", "quantity": 10}))
    assert result["ok"] is True
    assert result["proposal_created"] is True
    assert result["status"] == "awaiting_user_review"
    assert result["host_action"]["type"] == "propose_order"
    # It must NOT report the order as applied/placed.
    assert "applied" not in result
    assert "placed" not in result


def test_ui_action_tools_return_host_directives() -> None:
    local = agent_runtime._build_local_tools(None)
    for tid in ("set_chart_symbol", "open_panel", "add_to_watchlist"):
        assert tid in local
        result = asyncio.run(local[tid]({"symbol": "AAPL", "panel": "chart"}))
        assert result["ok"] is True
        assert result["host_action"]["type"] == tid
        # FR-010 diff gate: host actions are STAGED for review, never applied
        # immediately — the model must not be told the change already happened.
        assert "applied" not in result
        assert result["status"] == "awaiting_user_review"


def test_write_screener_filters_stages_for_review() -> None:
    # FR-114: the agent CONFIGURES the screener panel; it never runs it. Like
    # every host action it is STAGED for the user's review (the §6.5 gate), so it
    # returns awaiting_user_review with the host_action directive and no "applied".
    local = agent_runtime._build_local_tools(None)
    assert "write_screener_filters" in local
    args = {
        "criteria": [{"field": "pe_ratio", "operator": "lt", "value": 15}],
        "group": {
            "combinator": "or",
            "criteria": [
                {"field": "roe", "operator": "gt", "value": 0.2},
                {
                    "combinator": "and",
                    "criteria": [
                        {"field": "dividend_yield", "operator": "gt", "value": 0.03},
                        {"field": "debt_to_equity", "operator": "lt", "value": 1},
                    ],
                },
            ],
        },
        "universe": "sp500",
    }
    result = asyncio.run(local["write_screener_filters"](args))
    assert result["ok"] is True
    assert result["status"] == "awaiting_user_review"
    assert result["host_action"]["type"] == "write_screener_filters"
    # The full criteria + nested group tree round-trips to the host directive.
    assert result["host_action"]["args"] == args
    # It must NOT report the filters as applied/run.
    assert "applied" not in result


def test_get_terminal_state_returns_inbound_snapshot() -> None:
    snap = AgentContextSnapshot(by_source={"__terminal__": {"focusedSymbol": "NVDA"}})
    local = agent_runtime._build_local_tools(snap)
    result = asyncio.run(local["get_terminal_state"]({}))
    assert result["ok"] is True
    assert result["state"]["focusedSymbol"] == "NVDA"


def test_get_terminal_state_handles_missing_snapshot() -> None:
    local = agent_runtime._build_local_tools(None)
    result = asyncio.run(local["get_terminal_state"]({}))
    assert result["ok"] is True
    assert result["state"] == {}
