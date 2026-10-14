"""The invented-figure check of the agent-eval grader (``scripts/agent_eval/grounding.py``).

Extractor: what counts as a figure. Matcher: rounding and unit scaling against tool
results. Grader: the check only runs when tool results are supplied.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_EVAL_DIR = Path(__file__).resolve().parents[2] / "scripts" / "agent_eval"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"agent_eval_{name}", _EVAL_DIR / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


grounding = _load("grounding")
grader = _load("grader")

TOOL = json.dumps(
    {"symbol": "AAPL", "market_cap": 3440000000000, "pe": 28.43, "chg": 0.2834, "rev": "1320 m"}
)


def shown(text: str) -> list[str]:
    return [s for s, _ in grounding.figures(text, ignore=True)]


@pytest.mark.parametrize(
    "text",
    [
        "In 2024 it rose.",
        "On 2025-03-04 and 4 March 2025 and Mar 4, 2025 and 03/04/2025.",
        "At 14:30 UTC.",
        "1. First item\n2) Second item\n- 3. third",
        "Step 3 then (2) done.",
        "Filed a 10-K and a 10-Q, the 52-week range, Q3 FY25, DGS10, RSI14.",
        "S&P 500 and Nifty 50 closed.",
        "Over the last 6 months and 3 years, 12 weeks.",
        "5 filings and the 2nd one.",
        "See https://example.com/a/12345678 for details.",
    ],
)
def test_non_figures_are_not_extracted(text: str) -> None:
    assert shown(text) == []


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Price is ₹1,234.50 today", ["₹1,234.50"]),
        ("Revenue of $1.3 bn and 28.3% margin", ["$1.3 bn", "28.3%"]),
        ("Cap 4,186 cr and 3.1 lakh crore", ["4,186 cr", "3.1 lakh crore"]),
        ("Up 25 bps to 7.1", ["25 bps", "7.1"]),
        ("A balance of 1,50,000 and 2,500,000", ["1,50,000", "2,500,000"]),
        ("Volume 150 shares", ["150"]),
        ("Market cap $3.44 T", ["$3.44 T"]),
    ],
)
def test_figures_extracted(text: str, expected: list[str]) -> None:
    assert shown(text) == expected


@pytest.mark.parametrize(
    "num, unit, value",
    [
        ("3.44", " trillion", 3.44e12),
        ("3.44", "T", 3.44e12),
        ("1320", " m", 1.32e9),
        ("4,186", " crore", 4.186e10),
        ("3.1", " lakh crore", 3.1e12),
        ("2", " lakh", 2e5),
        ("5", "k", 5e3),
        ("1.5", " thousand", 1.5e3),
    ],
)
def test_unit_scaling(num: str, unit: str, value: float) -> None:
    assert grounding.candidates(num, unit)[0][0] == pytest.approx(value)


def test_percent_and_bps_read_as_fractions_too() -> None:
    assert grounding.candidates("28.3", "%")[1] == pytest.approx((0.283, 0.0005))
    assert grounding.candidates("25", " bps")[0][0] == pytest.approx(0.0025)


@pytest.mark.parametrize(
    "answer",
    [
        "Market cap is $3.44 T.",
        "Market cap is 3.44 trillion dollars.",
        "P/E is 28.4.",
        "P/E is 28.43.",
        "Margin changed 28.3%.",
        "Revenue is $1.32 bn.",
        "Revenue is $1.3 bn.",  # within the displayed precision of 1.32 bn
        "Cap is 3,44,000 crore.",
        "Cap is 3.44 lakh crore.",
    ],
)
def test_grounded_figures_pass(answer: str) -> None:
    assert grounding.ungrounded(answer, "", [TOOL]) == []


@pytest.mark.parametrize(
    "answer, bad",
    [
        ("Market cap is $3.9 T.", ["$3.9 T"]),
        ("P/E is 31.7.", ["31.7"]),
        ("Revenue is $1.5 bn.", ["$1.5 bn"]),
        ("fundamentals returned: {'price': 2.11}", ["2.11"]),
    ],
)
def test_invented_figures_are_reported(answer: str, bad: list[str]) -> None:
    assert grounding.ungrounded(answer, "", [TOOL]) == bad


def test_user_numbers_and_their_arithmetic_are_given() -> None:
    prompt = "I bought 10 INFY shares at ₹1,500 each."
    assert grounding.ungrounded("You paid ₹1,500 each, ₹15,000 in total.", prompt, []) == []
    assert grounding.ungrounded("That is ₹16,000 in total.", prompt, []) == ["₹16,000"]


def test_no_tool_results_means_every_figure_is_ungrounded() -> None:
    assert grounding.ungrounded("It closed at 2,345.60.", "", []) == ["2,345.60"]


def test_a_figure_is_reported_once() -> None:
    assert grounding.ungrounded("It is 2,345.60, yes 2,345.60.", "", []) == ["2,345.60"]


def _events(text: str) -> list[dict]:
    return [{"kind": "delta", "text": text}, {"kind": "done"}]


def test_grader_checks_figures_only_with_tool_results() -> None:
    scenario = {"id": "x", "prompt": "AAPL market cap?", "expect": {}}
    events = _events("Market cap is $9.9 T.")
    assert grader.grade(scenario, events) == []
    fails = grader.grade(scenario, events, tool_results=[{"name": "t", "ok": True, "result": TOOL}])
    assert len(fails) == 1 and "$9.9 T" in fails[0]


def test_grader_ignores_figures_of_errored_results() -> None:
    scenario = {"id": "x", "prompt": "AAPL market cap?", "expect": {}}
    events = _events("Market cap is $3.44 T.")
    failed = [{"name": "t", "ok": False, "result": TOOL}]
    assert any("ungrounded" in f for f in grader.grade(scenario, events, tool_results=failed))


def test_history_user_turns_are_given_but_assistant_turns_are_not() -> None:
    scenario = {
        "prompt": "Which tool gave that?",
        "options": {
            "history": [
                {"role": "user", "content": "Is it 777?"},
                {"role": "assistant", "content": "It is 3.44 T"},
            ]
        },
    }
    events = _events("It was 777 and 3.44 T.")
    assert grader.ungrounded_figures(scenario, events, []) == ["3.44 T"]
