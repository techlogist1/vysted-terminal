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
    msg = next(
        m for m in provider.round_messages[1] if m.role == "tool" and m.tool_call_id == "c-1"
    )
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
