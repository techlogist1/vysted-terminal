"""Capability-completeness audit (FR-090 / SC-022).

Every "obvious finance action" a user can reasonably ask the copilot to take
must be reachable by the agent — i.e. declared in :data:`CAPABILITY_CATALOG`
as an ``internal`` capability. This test pins the enumerated set so a future
edit that drops one (or flips its read-only/kind flags incoherently) fails CI
instead of silently dead-ending the agent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.agent_tools.catalog import CAPABILITY_CATALOG

# The enumerated set of obvious finance actions (FR-090 / SC-022). Each maps to
# a concrete capability id the agent must be able to reach.
OBVIOUS_ACTIONS: tuple[str, ...] = (
    "resolve_symbol",
    "price_data",
    "fundamentals",
    "news",
    "market_overview",
    "sec_filings_list",
    "compare_symbols",
    "set_chart_indicators",
    "arrange_layout",
    "open_panel",
    "close_panel",
    "focus_panel",
    "set_chart_symbol",
    "add_to_watchlist",
    "get_portfolio",
    "get_terminal_state",
)

_COPILOT_JSON = Path(__file__).resolve().parents[1] / "agents" / "copilot.json"


def _copilot_tools() -> list[str]:
    return json.loads(_COPILOT_JSON.read_text(encoding="utf-8"))["tools"]


@pytest.mark.parametrize("action_id", OBVIOUS_ACTIONS)
def test_every_obvious_action_is_in_the_catalog(action_id: str) -> None:
    """Each enumerated obvious action is an internal catalog capability."""
    assert action_id in CAPABILITY_CATALOG, (
        f"obvious action {action_id!r} is missing from CAPABILITY_CATALOG — "
        "the agent cannot reach it"
    )
    assert CAPABILITY_CATALOG[action_id].internal is True, (
        f"obvious action {action_id!r} is not projected to the internal copilot "
        "surface (internal must be True)"
    )


def test_new_b2_capabilities_present() -> None:
    """The B2 additions exist with the right kind/flags."""
    compare = CAPABILITY_CATALOG["compare_symbols"]
    assert compare.kind == "read_handler"
    assert compare.read_only is True
    assert compare.domain == "quotes"

    indicators = CAPABILITY_CATALOG["set_chart_indicators"]
    assert indicators.kind == "host_action"
    assert indicators.read_only is False
    assert indicators.domain == "indicators"


def test_arrange_layout_has_named_templates() -> None:
    """arrange_layout exposes the named cockpit templates in its pattern enum."""
    pattern_enum = CAPABILITY_CATALOG["arrange_layout"].input_schema["properties"]["pattern"][
        "enum"
    ]
    for template in ("research-cockpit", "compare", "single-focus", "macro-scan"):
        assert template in pattern_enum, (
            f"arrange_layout is missing the named template {template!r}"
        )


def test_host_actions_are_not_read_only() -> None:
    """Safety coherence: every host_action capability mutates (read_only=False)."""
    for cap in CAPABILITY_CATALOG.values():
        if cap.kind == "host_action":
            assert cap.read_only is False, (
                f"host_action {cap.id!r} is marked read_only=True — a terminal-"
                "driving action must declare read_only=False so the mutation gate fires"
            )


def test_copilot_can_reach_core_actions() -> None:
    """copilot.json grants the already-wired core obvious actions."""
    tools = _copilot_tools()
    for tool_id in (
        "resolve_symbol",
        "price_data",
        "fundamentals",
        "news",
        "arrange_layout",
        "set_chart_symbol",
    ):
        assert tool_id in tools, (
            f"copilot.json 'tools' is missing {tool_id!r} — the copilot cannot reach it"
        )


def test_copilot_grants_b2_actions() -> None:
    """The copilot can reach the B2 capabilities (wired into copilot.json's tools)."""
    tools = _copilot_tools()
    assert "set_chart_indicators" in tools
    assert "compare_symbols" in tools


def test_copilot_grants_market_overview_and_roster_count() -> None:
    """WS1: market_overview is wired into the copilot's tool roster, which now
    totals 36 tools (34 + the R7 corporate_announcements/shareholding_pattern)."""
    tools = _copilot_tools()
    assert "market_overview" in tools, (
        "copilot.json 'tools' is missing 'market_overview' — the copilot cannot reach it"
    )
    assert len(tools) == 36, f"copilot tool roster expected 36, got {len(tools)}"


def test_copilot_and_researcher_grant_disclosure_tools() -> None:
    """R7 Component 3: the copilot + AI Researcher can pull Indian filings."""
    copilot_tools = _copilot_tools()
    researcher_tools = json.loads(
        (_COPILOT_JSON.parent / "researcher.json").read_text(encoding="utf-8")
    )["tools"]
    for tool_id in ("corporate_announcements", "shareholding_pattern"):
        assert tool_id in copilot_tools, f"copilot.json 'tools' is missing {tool_id!r}"
        assert tool_id in researcher_tools, f"researcher.json 'tools' is missing {tool_id!r}"
        cap = CAPABILITY_CATALOG[tool_id]
        assert cap.kind == "read_handler"
        assert cap.read_only is True
        assert cap.internal is True
        assert cap.mcp is True  # read_handler (not internal-only) → projected to MCP


def test_market_overview_is_a_read_handler() -> None:
    """market_overview is a SAFE-auto read_handler (read_only=True), auto-projected
    to the model schema + allow-list + MCP surface by the catalog."""
    cap = CAPABILITY_CATALOG["market_overview"]
    assert cap.kind == "read_handler"
    assert cap.read_only is True
    assert cap.internal is True
    assert cap.mcp is True  # read_handler (not in _MCP_INTERNAL_ONLY) → exposed on MCP
