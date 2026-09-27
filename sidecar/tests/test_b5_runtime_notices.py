"""Batch 5 (W3): every runtime notice is a typed ``notice`` step (C9).

The chat used to recognise a notice by matching its English copy, and the copy
drifted (R15-AGENT-031 / R15-UI-054). Each notice now carries
``step_kind="notice"``, so the frontend branches on the kind alone.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMToolUseEvent, LLMUsage
from services import action_ledger, agent_runtime


@pytest.fixture(autouse=True)
def _clean_ledger(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    action_ledger.reset_for_tests()
    monkeypatch.setattr(agent_runtime, "_ACK_GRACE_SECONDS", 0.0)
    yield
    action_ledger.reset_for_tests()


@pytest.mark.asyncio
async def test_all_three_divergence_branches_emit_notice_kind() -> None:
    # No ack, kept_previous and failed: the three divergence branches.
    action_ledger.record("kept", "kept_previous", {"symbol": "AAPL"})
    action_ledger.record("failed", "failed", {"symbol": "MSFT"})
    notices = await agent_runtime._publish_divergence_notices(["unacked", "kept", "failed"])
    assert len(notices) == 3
    assert {n.step_kind for n in notices} == {"notice"}


class _SetChartThenClaimProvider:
    """Round 1 calls set_chart_symbol; round 2 claims it is done."""

    def __init__(self) -> None:
        self._round = 0

    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        if self._round == 0:
            self._round += 1
            yield LLMToolUseEvent(
                tool_call_id="c-1", name="set_chart_symbol", input={"symbol": "BDL"}
            )
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="I've set BDL on your chart.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2), finish_reason="stop")


async def _drive(monkeypatch: pytest.MonkeyPatch, autonomy: str) -> list[Any]:
    agent_runtime.reload()
    provider = _SetChartThenClaimProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    return [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="put BDL on the chart",
            api_key="k",
            mode="edit",
            autonomy=autonomy,
        )
    ]


def _notices(events: list[Any]) -> list[str]:
    return [e.detail for e in events if e.kind == "research_step" and e.step_kind == "notice"]


@pytest.mark.asyncio
async def test_ask_drive_names_the_staged_action_before_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events = await _drive(monkeypatch, "ask")
    assert _notices(events) == [
        "Staged for your review, not applied yet: set_chart_symbol BDL. Accept it below to apply."
    ]
    assert events[-1].kind == "done"


@pytest.mark.asyncio
async def test_auto_drive_has_no_staged_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    action_ledger.record("c-1", "applied")
    assert _notices(await _drive(monkeypatch, "auto")) == []


class _ResearchThenClaimProvider:
    """Round 1 calls research on MSFT; round 2 claims the brief is up. Records
    each round's messages."""

    def __init__(self) -> None:
        self.round_messages: list[list[Any]] = []

    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        self.round_messages.append(list(messages))
        if messages[-1].role != "tool":
            yield LLMToolUseEvent(tool_call_id="r-1", name="research", input={"query": "MSFT"})
            yield LLMDoneEvent(usage=LLMUsage(input_tokens=5, output_tokens=1))
            return
        yield LLMDeltaEvent(text="Built you a brief.")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=3, output_tokens=2), finish_reason="stop")


async def _drive_research(
    monkeypatch: pytest.MonkeyPatch, autonomy: str | None
) -> tuple[list[Any], str]:
    agent_runtime.reload()
    brief = {"symbol": "MSFT", "query": "MSFT", "markdown": "## MSFT"}

    async def _research(_call: Any, _local: Any = None) -> AsyncIterator[Any]:
        yield agent_runtime._ToolDone(json.dumps({"ok": True, "brief": brief}))

    monkeypatch.setattr(agent_runtime, "_dispatch_tool_with_progress", _research)
    provider = _ResearchThenClaimProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="Publish a research brief for MSFT.",
            api_key="k",
            mode="edit",
            autonomy=autonomy,
        )
    ]
    [tool_msg] = [m for m in provider.round_messages[1] if m.role == "tool"]
    return events, tool_msg.content


@pytest.mark.asyncio
@pytest.mark.parametrize("autonomy", [None, "ask"])
async def test_review_autobrief_is_named_staged_and_the_model_is_told(
    monkeypatch: pytest.MonkeyPatch, autonomy: str | None
) -> None:
    # rc1-scenarios:1: the synthetic publish_brief was queued for review with
    # no staged notice, and the model narrated it as published.
    events, tool_content = await _drive_research(monkeypatch, autonomy)
    assert (
        "Staged for your review, not applied yet: publish_brief MSFT. Accept it below to apply."
        in _notices(events)
    )
    assert "awaiting_user_review" in tool_content


@pytest.mark.asyncio
async def test_auto_autobrief_is_not_named_staged(monkeypatch: pytest.MonkeyPatch) -> None:
    events, tool_content = await _drive_research(monkeypatch, "auto")
    assert not any(n.startswith("Staged for your review") for n in _notices(events))
    assert "awaiting_user_review" not in tool_content
