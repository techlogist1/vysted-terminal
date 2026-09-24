"""The agent-eval grader (``scripts/agent_eval/grader.py``, R15-AGENT-007).

Grades recorded ``vy.py invoke --out`` event streams: one clean pass, one test
per failure mode (the {}-args call of COD-llm-adapters-2-1 first), the pass^k
arithmetic, and the scenario set's tool names against its agent's allow-list.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path
from typing import Any

import pytest

from services.agent_tools.catalog import CAPABILITY_CATALOG

_EVAL_DIR = Path(__file__).resolve().parents[2] / "scripts" / "agent_eval"
_spec = importlib.util.spec_from_file_location("agent_eval_grader", _EVAL_DIR / "grader.py")
assert _spec and _spec.loader
grader = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grader)

_PRICE = {
    "id": "price-reliance",
    "prompt": "How has RELIANCE performed over the past year?",
    "expect": {"tools": [{"tool": "price_data|compare_symbols", "input": "(?i)RELIANCE"}]},
}
_RESEARCH = {
    "id": "research-brief-reliance",
    "expect": {
        "tools": [{"tool": "research", "input": "RELIANCE"}, {"tool": "publish_brief"}],
        "research_step": True,
    },
}
_ASK_BACK = {
    "id": "missing-param-portfolio",
    "state_probe": "/portfolio/positions",
    "expect": {"forbid_tools": ["portfolio_add_position"], "answer_matches": [r"\?"]},
}


def _call(name: str, args: dict[str, Any], call_id: str = "call-1") -> dict[str, Any]:
    return {"kind": "tool_use", "tool_call_id": call_id, "name": name, "input": args}


def _text(text: str) -> dict[str, Any]:
    return {"kind": "delta", "text": text}


_DONE = {
    "kind": "done",
    "usage": {"input_tokens": 2738, "output_tokens": 35},
    "finish_reason": "stop",
}


def _price_stream(*, args: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    return [
        _call("price_data", {"symbol": "RELIANCE.NS", "range": "1y"} if args is None else args),
        {"kind": "heartbeat"},
        _text("RELIANCE is up 8% over the year"),
        _text(", with a 14% drawdown in March."),
        _DONE,
    ]


def test_a_clean_trial_passes() -> None:
    assert grader.grade(_PRICE, _price_stream()) == []


def test_a_tool_call_with_empty_args_fails() -> None:
    # COD-llm-adapters-2-1: every Anthropic tool call dispatched with input={}.
    failures = grader.grade(_PRICE, _price_stream(args={}))
    assert any("price_data called without required ['symbol']" in f for f in failures)
    assert any("no price_data|compare_symbols call" in f for f in failures)


def test_a_call_the_runtime_marked_invalid_fails() -> None:
    reason = "invalid arguments for price_data: 'symbol' is a required property"
    failures = grader.grade(_PRICE, _price_stream(args={grader.INVALID_ARGS: reason}))
    assert f"price_data called with invalid args: {reason}" in failures


@pytest.mark.parametrize(
    ("scenario", "events", "expected"),
    [
        (
            _PRICE,
            [_call("fundamentals", {"symbol": "RELIANCE"}), _text("ok"), _DONE],
            "no price_data",
        ),
        (_PRICE, [_call("price_data", {"symbol": "RELIANCE"}), _DONE], "empty answer"),
        (_PRICE, [_call("price_data", {"symbol": "RELIANCE"}), _text("ok")], "without a done"),
        (
            _PRICE,
            [_call("price_data", {"symbol": "RELIANCE"}), {"kind": "error", "code": "auth"}, _DONE],
            "error event: auth",
        ),
        (
            _PRICE,
            [_text('<|python_tag|>{"name": "price_data"}'), _DONE],
            "answer matches forbidden",
        ),
        (
            _RESEARCH,
            [_call("research", {"query": "RELIANCE"}), _text("brief"), _DONE],
            "no publish_brief",
        ),
        (
            _RESEARCH,
            [
                _call("research", {"query": "RELIANCE"}),
                _call("publish_brief", {"structured": {}}, "call-1__autobrief"),
                _text("brief"),
                _DONE,
            ],
            "no research_step",
        ),
        (
            _ASK_BACK,
            [
                _call("portfolio_add_position", {"symbol": "INFY", "quantity": 1, "cost_basis": 1}),
                _text("Done?"),
                _DONE,
            ],
            "forbidden tool called: portfolio_add_position",
        ),
        (_ASK_BACK, [_text("Added the shares."), _DONE], "answer does not match"),
        (
            _ASK_BACK,
            # llama3.1:8b, live: the call printed as text instead of made (a question
            # mark in the text must not rescue it).
            [_text('{"name": "portfolio_add_position", "parameters": {"symbol": null}}?'), _DONE],
            "answer matches forbidden",
        ),
    ],
)
def test_each_failure_mode_fails_the_trial(
    scenario: dict[str, Any], events: list[dict[str, Any]], expected: str
) -> None:
    failures = grader.grade(scenario, events)
    assert any(expected in f for f in failures), failures


def test_a_write_under_ask_fails_on_the_end_state() -> None:
    events = [_text("Which symbol, how many shares and at what price?"), _DONE]
    assert grader.grade(_ASK_BACK, events, [], []) == []
    changed = grader.grade(_ASK_BACK, events, [], [{"symbol": "INFY.NS", "quantity": 10}])
    assert changed == ["end state changed under ASK: /portfolio/positions"]


def test_the_runtime_autobrief_is_not_graded_as_a_model_call() -> None:
    events = [
        _call("research", {"query": "RELIANCE"}),
        {
            "kind": "research_step",
            "tool_call_id": "call-1",
            "tool": "research",
            "step_kind": "engine",
        },
        _call("publish_brief", {"structured": {"symbol": "RELIANCE.NS"}}, "call-1__autobrief"),
        _text("Brief published."),
        _DONE,
    ]
    assert grader.grade(_RESEARCH, events) == []


def test_pass_hat_k_counts_a_scenario_only_when_all_k_trials_pass() -> None:
    report = grader.pass_hat_k(
        {
            "a": [True, True, True],
            "b": [True, False, True],
            "c": [True, True, True, False],
            "d": [True],
        },
        3,
    )
    assert report["per_scenario"] == {"a": 1.0, "b": 0.0, "c": 0.25}  # C(3,3)/C(4,3)
    assert report["pass_hat_k"] == pytest.approx(1.25 / 3)
    assert report["pass_hat_1"] == pytest.approx(8 / 10)
    assert report["incomplete"] == ["d"]


def test_the_scenario_set_names_only_tools_its_agent_can_call() -> None:
    agents = Path(__file__).resolve().parents[1] / "agents"
    scenarios = json.loads((_EVAL_DIR / "scenarios.json").read_text(encoding="utf-8"))
    assert 12 <= len(scenarios) <= 20
    assert len({s["id"] for s in scenarios}) == len(scenarios)
    for scenario in scenarios:
        expect = scenario["expect"]
        names = [n for w in expect.get("tools", []) for n in w["tool"].split("|")]
        names += expect.get("forbid_tools", [])
        allowed = json.loads(
            (agents / f"{scenario.get('agent', 'copilot')}.json").read_text(encoding="utf-8")
        )
        unknown = [n for n in names if n not in allowed["tools"] or n not in CAPABILITY_CATALOG]
        assert not unknown, f"{scenario['id']} names tools its agent cannot call: {unknown}"
        for pattern in [w.get("input") or "" for w in expect.get("tools", [])] + expect.get(
            "answer_matches", []
        ):
            re.compile(pattern)
