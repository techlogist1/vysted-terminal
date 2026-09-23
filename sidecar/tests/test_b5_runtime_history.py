"""Batch 5 (W3): long threads fold, they do not fall off a window.

R15-AGENT-040: the client sent the last ten messages as prose only and
``_coerce_history`` capped at ten again, so a constraint the user set on turn 1
(and every tool failure) silently vanished a few turns later.
"""

from __future__ import annotations

from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent
from services import agent_runtime

_SCOPE = "I only care about FY26 guidance vs delivery for BDL"


class _Records:
    def __init__(self) -> None:
        self.messages: list[Any] = []

    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        self.messages = list(messages)
        yield LLMDeltaEvent(text="Guidance was Rs 4,000 cr; delivery tracked 92%.")
        yield LLMDoneEvent(finish_reason="stop")


def _thread(turns: int) -> list[dict[str, str]]:
    history: list[dict[str, str]] = []
    for n in range(1, turns + 1):
        ask = f"{_SCOPE}. Start with the order book." if n == 1 else f"Follow-up {n} on BDL."
        answer = f"Answer {n}."
        if n == 2:
            answer += "\n\n[failed: corporate_announcements: BSE lane failed]"
        history += [{"role": "user", "content": ask}, {"role": "assistant", "content": answer}]
    return history


async def _drive(monkeypatch: pytest.MonkeyPatch, prior_turns: int) -> tuple[str, list[Any]]:
    agent_runtime.reload()
    provider = _Records()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    events = [
        e
        async for e in agent_runtime.invoke_agent(
            agent_id="copilot",
            prompt="And the latest quarter?",
            provider="openai",
            api_key="k",
            mode="ask",
            options={"history": _thread(prior_turns)},
        )
    ]
    summaries = [
        m.content
        for m in provider.messages
        if m.content.startswith("Earlier in this conversation (older turns, summarised):")
    ]
    assert len(summaries) == 1
    return summaries[0], events


@pytest.mark.asyncio
async def test_turn_one_scope_survives_into_the_summary_on_turn_seven(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, events = await _drive(monkeypatch, prior_turns=6)
    assert _SCOPE in summary
    notices = [e for e in events if e.kind == "research_step" and e.step_kind == "notice"]
    assert [n.tool for n in notices] == ["history"]


@pytest.mark.asyncio
async def test_a_turn_two_tool_failure_survives_into_the_summary_on_turn_eight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, _events = await _drive(monkeypatch, prior_turns=7)
    assert "- [failed: corporate_announcements: BSE lane failed]" in summary
