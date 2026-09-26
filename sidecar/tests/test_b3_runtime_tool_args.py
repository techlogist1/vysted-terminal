"""The runtime-level tool-argument check (D-B3-4), one test per pinned behaviour.

Validation lived only in the OpenAI adapter, and the runtime yielded every
``tool_use`` to the UI before any check.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent, LLMUsage
from services import agent_runtime


class _OneCallProvider:
    """Round 1 emits one tool call exactly as an adapter handed it over."""

    def __init__(self, name: str, args: dict[str, Any]) -> None:
        self._name = name
        self._args = args
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **_: Any
    ) -> AsyncIterator[Any]:
        self.round_messages.append(list(messages))
        if len(self.round_messages) == 1:
            yield LLMToolUseEvent(tool_call_id="c-1", name=self._name, input=dict(self._args))
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))
            return
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))


async def _invoke(
    monkeypatch: pytest.MonkeyPatch, name: str, args: dict[str, Any], provider_id: str = "ollama"
) -> tuple[list[Any], dict[str, Any]]:
    """Run one call through the real dispatch; return (events, the model's tool result)."""
    agent_runtime.reload()
    provider = _OneCallProvider(name, args)
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="x",
            api_key="k",
            provider=provider_id,
            mode="edit",
            autonomy="auto",
        )
    ]
    msg = next(m for m in provider.round_messages[1] if m.role == "tool")
    return events, json.loads(msg.content)


def _yielded(events: list[Any], name: str) -> list[LLMToolUseEvent]:
    return [e for e in events if isinstance(e, LLMToolUseEvent) and e.name == name]


@pytest.mark.asyncio
async def test_add_position_without_cost_basis_is_never_yielded_and_asks_the_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The captured llama3.1:8b run1 shape (R15-AGENT-022): cost_basis null.
    args = {"symbol": "SUMAX.NS", "quantity": 40, "cost_basis": None, "purchased_at": "2026-08-23"}
    events, result = await _invoke(monkeypatch, "portfolio_add_position", args)
    assert _yielded(events, "portfolio_add_position") == []
    assert result["ok"] is False
    assert "host_action" not in result  # the host-action handler never ran
    assert "missing cost_basis" in result["error"]
    assert "ask the user" in result["error"]


#: Captured verbatim from llama3.1:8b (surface/screener/20-agent-screen-llama.jsonl).
_STRINGIFIED_CRITERIA = (
    '[{"field":"pe_ratio","operator":"lt","value":20},'
    '{"field":"roe","operator":"gt","value":{"min":15,"max":15}}, '
    '{"field":"debt_to_equity","operator":"lt","value":0.5}]'
)


@pytest.mark.asyncio
async def test_stringified_screener_criteria_is_yielded_as_a_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args = {"criteria": _STRINGIFIED_CRITERIA, "universe": "nse-all"}
    events, _ = await _invoke(monkeypatch, "write_screener_filters", args)
    [call] = _yielded(events, "write_screener_filters")
    criteria = call.input["criteria"]
    assert isinstance(criteria, list) and len(criteria) == 3
    assert criteria[0] == {"field": "pe_ratio", "operator": "lt", "value": 20}
    assert call.input["universe"] == "nse-all"


@pytest.mark.asyncio
async def test_unknown_indicator_key_fails_validation_naming_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R15-AGENT-054: one unknown key made the chart's fetch reject the whole set.
    args = {"indicators": ["rsi", "bollinger_bands"]}
    events, result = await _invoke(monkeypatch, "set_chart_indicators", args)
    assert _yielded(events, "set_chart_indicators") == []
    assert result["ok"] is False
    assert "bollinger_bands" in result["error"]


@pytest.mark.asyncio
async def test_groq_shaped_invalid_args_never_reach_the_handler(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # R15-AGENT-047: the Groq adapter passes args through unvalidated (no
    # sentinel), so only the runtime check stands between them and the handler.
    args = {"symbol": "INFY.NS", "quantity": "ten", "cost_basis": 1500}
    events, result = await _invoke(monkeypatch, "portfolio_add_position", args, "groq")
    assert _yielded(events, "portfolio_add_position") == []
    assert result["ok"] is False
    assert "host_action" not in result
    assert "'ten' is not of type 'number'" in result["error"]


@pytest.mark.parametrize(
    ("tool", "args", "key", "expected"),
    [
        ("option_chain", {"symbol": "NIFTY", "max_strikes": "10"}, "max_strikes", 10),
        # Class pin: a tool the coercion was not written against.
        (
            "screener_run",
            {"universe": "nse-all", "criteria": [], "limit": "25"},
            "limit",
            25,
        ),
    ],
)
def test_integer_sent_as_a_string_is_coerced(
    tool: str, args: dict[str, Any], key: str, expected: int
) -> None:
    # R15-AGENT-093: llama3.1:8b sends integers as strings ("10", "25").
    event = LLMToolUseEvent(tool_call_id="c-1", name=tool, input=dict(args))
    agent_runtime._normalise_tool_args(event)
    assert agent_runtime.INVALID_ARGS_SENTINEL not in event.input
    assert event.input[key] == expected and type(event.input[key]) is int


def test_a_non_numeric_integer_string_stays_invalid() -> None:
    args = {"symbol": "NIFTY", "max_strikes": "ten"}
    event = LLMToolUseEvent(tool_call_id="c-1", name="option_chain", input=args)
    agent_runtime._normalise_tool_args(event)
    assert "'ten' is not of type 'integer'" in event.input[agent_runtime.INVALID_ARGS_SENTINEL]


def test_nested_numeric_string_is_coerced() -> None:
    # R15-AGENT-093 round 2: coercion only worked at the top level and refused
    # an integral float ("5.0") for an integer. Now it descends into
    # properties/items, including after a stringified array is parsed.
    event = LLMToolUseEvent(
        tool_call_id="c-1",
        name="add_chart_drawing",
        input={"kind": "trendline", "points": [{"price": "185.5"}]},
    )
    agent_runtime._normalise_tool_args(event)
    assert agent_runtime.INVALID_ARGS_SENTINEL not in event.input
    assert event.input["points"][0]["price"] == 185.5

    # The stringified array itself, sent whole.
    event = LLMToolUseEvent(
        tool_call_id="c-2",
        name="add_chart_drawing",
        input={"kind": "trendline", "points": '[{"price": "185.5"}]'},
    )
    agent_runtime._normalise_tool_args(event)
    assert agent_runtime.INVALID_ARGS_SENTINEL not in event.input
    assert event.input["points"] == [{"price": 185.5}]

    # An integral float string ("5.0") is coerced to int, not rejected.
    event = LLMToolUseEvent(
        tool_call_id="c-3", name="option_chain", input={"symbol": "NIFTY", "max_strikes": "5.0"}
    )
    agent_runtime._normalise_tool_args(event)
    assert agent_runtime.INVALID_ARGS_SENTINEL not in event.input
    assert event.input["max_strikes"] == 5 and type(event.input["max_strikes"]) is int

    # A non-coercible nested value still fails validation (the sentinel), not
    # a silent pass-through.
    event = LLMToolUseEvent(
        tool_call_id="c-4",
        name="add_chart_drawing",
        input={"kind": "trendline", "points": [{"price": "ten"}]},
    )
    agent_runtime._normalise_tool_args(event)
    assert agent_runtime.INVALID_ARGS_SENTINEL in event.input

    # Fresh case: a tool the fix was not written against, with a nested
    # numeric items schema (yield_curve_value.instruments[].tenor/rate).
    event = LLMToolUseEvent(
        tool_call_id="c-5",
        name="yield_curve_value",
        input={
            "valuation_date": "2026-09-26",
            "sample_count": 5,
            "instruments": [
                {"type": "deposit", "tenor": "3", "tenor_unit": "months", "rate": "0.05"}
            ],
        },
    )
    agent_runtime._normalise_tool_args(event)
    assert agent_runtime.INVALID_ARGS_SENTINEL not in event.input
    row = event.input["instruments"][0]
    assert row["tenor"] == 3 and type(row["tenor"]) is int
    assert row["rate"] == 0.05 and type(row["rate"]) is float
