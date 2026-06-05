"""In-house planner tests (Track E — the OpenCode fallback).

``classify_intent`` is deterministic (no LLM); ``decompose`` is exercised with a
scripted fake ``llm_call`` so the JSON parsing + the never-dead-end fallback are
proven without a network round-trip.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.planner import (
    PLAN_ACTIONS,
    IntentResult,
    classify_intent,
    decompose,
)


def _run(coro: Any) -> Any:
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# classify_intent
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("research NVDA", "research"),
        ("do a deep dive on Tesla's outlook", "research"),
        ("what's the bull case for AAPL?", "research"),
        ("set up a cockpit for NVDA", "build"),
        ("open a chart and the watchlist and news", "build"),
        ("compare NVDA and AMD side by side", "build"),
        ("add RSI to the chart", "edit"),
        ("switch the chart to MSFT", "edit"),
        ("add BTC to my watchlist", "edit"),
        ("what is a P/E ratio?", "read"),
        ("explain how options pricing works", "read"),
        ("", "read"),
        ("hmm", "read"),
    ],
)
def test_classify_intent_maps_language_to_intent(text: str, expected: str) -> None:
    result = classify_intent(text)
    assert isinstance(result, IntentResult)
    assert result.intent == expected, f"{text!r} -> {result.to_dict()}"


def test_read_is_the_only_non_mutating_intent() -> None:
    assert classify_intent("what is AAPL?").mutates is False
    assert classify_intent("set up a research cockpit for AAPL").mutates is True


def test_compound_request_is_flagged_and_biased_to_build() -> None:
    res = classify_intent("open the chart, then add news, and also pull up the screener")
    assert res.compound is True
    assert res.intent == "build"


def test_single_panel_edit_is_not_compound() -> None:
    res = classify_intent("add RSI to the chart")
    assert res.compound is False
    assert res.intent == "edit"


# ---------------------------------------------------------------------------
# decompose
# ---------------------------------------------------------------------------


def test_decompose_parses_a_valid_plan() -> None:
    # FR-115: there is ONE research action — `research` with an internal `depth`
    # arg ('deep' here). The removed `deep_research` verb is no longer a plan action.
    plan_json = """[
      {"action": "arrange_layout", "args": {"pattern": "research-cockpit"}, "rationale": "stage"},
      {"action": "set_chart_symbol", "args": {"symbol": "NVDA"}, "rationale": "focus NVDA"},
      {"action": "research", "args": {"query": "NVDA outlook", "depth": "deep"}, "rationale": "ask"}
    ]"""

    async def fake_llm(_prompt: str) -> str:
        return plan_json

    plan = _run(decompose("set up NVDA and research it deeply", llm_call=fake_llm))
    assert plan.ok
    assert [s.action for s in plan.steps] == ["arrange_layout", "set_chart_symbol", "research"]
    assert plan.steps[1].args == {"symbol": "NVDA"}
    assert plan.steps[2].args == {"query": "NVDA outlook", "depth": "deep"}
    assert all(s.action in PLAN_ACTIONS for s in plan.steps)


def test_decompose_tolerates_code_fences_and_prose() -> None:
    async def fake_llm(_prompt: str) -> str:
        return (
            'Sure! Here is the plan:\n```json\n[{"action":"research","args":{"query":"AAPL"}}]\n```'
        )

    plan = _run(decompose("look into AAPL", llm_call=fake_llm))
    assert [s.action for s in plan.steps] == ["research"]


def test_decompose_drops_unknown_actions() -> None:
    async def fake_llm(_prompt: str) -> str:
        return '[{"action":"hack_the_planet","args":{}},{"action":"answer","args":{}}]'

    plan = _run(decompose("hi", llm_call=fake_llm))
    assert [s.action for s in plan.steps] == ["answer"]


def test_decompose_falls_back_when_model_returns_garbage() -> None:
    async def fake_llm(_prompt: str) -> str:
        return "I cannot help with that."

    plan = _run(decompose("research the outlook for NVDA", llm_call=fake_llm))
    # never dead-ends — a research-leaning ask falls back to a single research step
    assert plan.ok
    assert plan.steps[0].action == "research"
    assert plan.note


def test_decompose_falls_back_when_llm_raises() -> None:
    async def fake_llm(_prompt: str) -> str:
        raise RuntimeError("no key configured")

    plan = _run(decompose("what is a call option", llm_call=fake_llm))
    assert plan.ok
    assert plan.steps[0].action == "answer"
    assert "planner unavailable" in (plan.note or "")


def test_decompose_empty_request_is_not_ok() -> None:
    async def fake_llm(_prompt: str) -> str:
        return "[]"

    plan = _run(decompose("   ", llm_call=fake_llm))
    assert not plan.ok
