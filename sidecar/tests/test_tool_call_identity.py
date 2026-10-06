"""Tool-call identity is runtime-owned (R15-AGENT-046, D-B9-5).

Gemini mints ``f"{name}_{index}"`` per stream, so the same id recurs in every
turn. The ack ledger is process-global, so a late ack for turn 1 must never
ground turn 2's action (or brief) as applied.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMToolUseEvent, LLMUsage
from services import action_ledger, agent_runtime


class _GeminiStyleProvider:
    """Every turn: round 1 calls ``name`` with the per-stream id ``{name}_0``,
    round 2 answers. Records each round's messages."""

    def __init__(self, name: str, args: dict[str, Any]) -> None:
        self._name = name
        self._args = args
        self.round_messages: list[list[LLMMessage]] = []

    async def stream_chat(self, messages: list[LLMMessage], **_: Any) -> AsyncIterator[Any]:
        self.round_messages.append(list(messages))
        if messages[-1].role != "tool":
            yield LLMToolUseEvent(
                tool_call_id=f"{self._name}_0", name=self._name, input=dict(self._args)
            )
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="Done.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2))


async def _turn(monkeypatch: pytest.MonkeyPatch, provider: _GeminiStyleProvider) -> list[Any]:
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    return [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot", prompt="load SPY", api_key="k", mode="edit", autonomy="auto"
        )
    ]


@pytest.fixture(autouse=True)
def _clean(monkeypatch: pytest.MonkeyPatch) -> Any:
    action_ledger.reset_for_tests()
    agent_runtime.reload()
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    yield
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_a_late_turn_one_ack_does_not_ground_turn_two(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _GeminiStyleProvider("set_chart_symbol", {"symbol": "SPY"})
    first = await _turn(monkeypatch, provider)
    first_id = next(e.tool_call_id for e in first if isinstance(e, LLMToolUseEvent))
    # The panel's ack for turn 1 lands after turn 1 ended (under either id the
    # panel could have seen).
    action_ledger.record(first_id, "applied")
    action_ledger.record("set_chart_symbol_0", "applied")

    second = await _turn(monkeypatch, provider)
    second_id = next(e.tool_call_id for e in second if isinstance(e, LLMToolUseEvent))
    assert second_id not in {first_id, "set_chart_symbol_0"}
    assert second_id.startswith("call_")
    result = next(
        m for m in provider.round_messages[-1] if m.role == "tool" and m.tool_call_id == second_id
    )
    assert json.loads(result.content)["status"] == "dispatched_unconfirmed"


@pytest.mark.asyncio
async def test_a_prior_brief_ack_does_not_confirm_a_new_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = _GeminiStyleProvider("publish_brief", {"markdown": "## x"})
    first = await _turn(monkeypatch, provider)
    first_id = next(e.tool_call_id for e in first if isinstance(e, LLMToolUseEvent))
    action_ledger.record(first_id, "applied")
    action_ledger.record("publish_brief_0", "applied")

    second = await _turn(monkeypatch, provider)
    assert any("did not confirm" in d for d in _publish_notices(second))


def _publish_notices(events: list[Any]) -> list[str]:
    return [
        e.detail
        for e in events
        if getattr(e, "kind", None) == "research_step"
        and getattr(e, "tool", None) == "publish_brief"
    ]


@pytest.mark.asyncio
async def test_a_prior_autobrief_ack_does_not_confirm_a_new_auto_brief(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = {"query": "NVDA", "markdown": "## x", "execution": {"run_id": "r"}}

    async def _research_result(_call: Any, _local: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone(json.dumps({"ok": True, "brief": brief}))

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _research_result)
    provider = _GeminiStyleProvider("research", {"query": "NVDA"})
    first = await _turn(monkeypatch, provider)
    [first_brief] = [e for e in first if getattr(e, "name", None) == "publish_brief"]
    action_ledger.record(first_brief.tool_call_id, "applied")
    action_ledger.record("research_0__autobrief", "applied")

    second = await _turn(monkeypatch, provider)
    [second_brief] = [e for e in second if getattr(e, "name", None) == "publish_brief"]
    assert second_brief.input == brief
    assert second_brief.tool_call_id not in {first_brief.tool_call_id, "research_0__autobrief"}
    assert any("did not confirm" in d for d in _publish_notices(second))
