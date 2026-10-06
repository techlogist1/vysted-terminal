"""R15-CODE-AGENT-009: invoke_agent's pre-loop resolution, tested directly.

The tool-surface gate, the native-search tier choice and the planner pre-pass
were inline in ``invoke_agent`` and reachable only through a fake provider.
"""

from __future__ import annotations

import pytest

import config
from services import agent_runtime
from services.agent_tools import catalog

_DATA_WRITES = {
    "write_note",
    "write_screener_filters",
    "save_screen",
    "save_layout",
    "portfolio_add_position",
    "portfolio_update_position",
    "portfolio_delete_position",
    "remove_from_watchlist",
}


def _copilot() -> agent_runtime.AgentSpec:
    agent_runtime.reload()
    spec = agent_runtime.get_agent("copilot")
    assert spec is not None
    return spec


def test_read_intent_strips_every_data_write() -> None:
    spec = _copilot()
    assert _DATA_WRITES <= set(catalog.resolve_tool_ids(spec.tools)[0])

    tool_ids, read_only, _ = agent_runtime._resolve_tool_surface(
        spec, "agent", "What is the current P/E of AAPL?"
    )

    assert read_only is True
    assert not _DATA_WRITES & set(tool_ids)
    assert all(
        catalog.is_read_only(t) is True or t in agent_runtime._READ_SAFE_PANEL_ACTIONS
        for t in tool_ids
    )
    assert "set_chart_symbol" in tool_ids  # a read turn may still ground on a chart


def test_legacy_ask_mode_strips_panel_actions_too() -> None:
    tool_ids, read_only, _ = agent_runtime._resolve_tool_surface(_copilot(), "ask", "hi")

    assert read_only is True
    assert all(catalog.is_read_only(t) is True for t in tool_ids)


def test_write_intent_keeps_the_full_surface() -> None:
    spec = _copilot()
    tool_ids, read_only, retired = agent_runtime._resolve_tool_surface(
        spec, "agent", "Write a note on RELIANCE: capex guidance raised"
    )

    assert read_only is False
    assert tool_ids == catalog.resolve_tool_ids(spec.tools)[0]
    assert retired == []


def test_unsupported_model_gets_no_native_search() -> None:
    assert agent_runtime._select_native_search("openai", "gpt-4.1-mini", None) is False
    assert agent_runtime._select_native_search("openrouter", "some/model", "plugin") is False
    assert agent_runtime._select_native_search("ollama", "qwen2.5:7b", None) is False
    assert agent_runtime._select_native_search("anthropic", "claude-sonnet-4-6", None) is True


def test_tier_b_never_rides_chat_model_native_search() -> None:
    token = config.set_request_research_search_tier(config.SEARCH_TIER_B)
    try:
        assert agent_runtime._select_native_search("anthropic", "claude-sonnet-4-6", None) is False
    finally:
        config._research_search_tier_ctx.reset(token)


async def _must_not_plan(*_a: object, **_k: object) -> str:
    raise AssertionError("the planner LLM must not be called")


@pytest.mark.asyncio
async def test_prepass_on_a_non_planner_provider_yields_no_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_runtime.oneshot, "complete", _must_not_plan)

    plan = await agent_runtime._plan_prepass(
        "ollama",
        "agent",
        False,
        "qwen2.5:7b",
        None,
        "open a chart of AAPL and add NVDA to my watchlist",
        None,
    )

    assert plan is None


@pytest.mark.asyncio
async def test_prepass_skips_a_read_only_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_runtime.oneshot, "complete", _must_not_plan)

    plan = await agent_runtime._plan_prepass(
        "openai", "agent", True, "gpt-4.1-mini", "k", "compare AAPL and then MSFT", None
    )

    assert plan is None


@pytest.mark.asyncio
async def test_prepass_stages_host_action_steps(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _plan(*_a: object, **_k: object) -> str:
        return (
            '[{"action":"set_chart_symbol","args":{"symbol":"AAPL"},"rationale":"chart"},'
            '{"action":"research","args":{"query":"AAPL"},"rationale":"read"}]'
        )

    monkeypatch.setattr(agent_runtime.oneshot, "complete", _plan)

    plan = await agent_runtime._plan_prepass(
        "openai",
        "agent",
        False,
        "gpt-4.1-mini",
        "k",
        "open a chart of AAPL and add NVDA to my watchlist",
        None,
    )

    assert plan is not None
    assert [s["staged"] for s in plan.steps] == [True, False]
