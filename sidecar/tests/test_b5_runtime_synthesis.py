"""Batch 5 (W3): a research synthesis cut at the model's output limit says so.

R15-RESEARCH-014: ``oneshot`` returned the partial text of a ``max_tokens``
finish, so a truncated deep synthesis rendered as a complete brief. The finish
reason now reaches the synthesis, which puts a note on the brief.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent
from services.budget_guard import BudgetGuard
from services.llm import oneshot
from services.research.deep import SYNTHESIS_TRUNCATED_NOTE, run_deep_research
from services.research.iter import run_iter_research


class _SynthesisProvider:
    """The model the synthesis runs on, finishing with ``finish_reason``."""

    def __init__(self, finish_reason: str) -> None:
        self.finish_reason = finish_reason

    async def stream_chat(self, messages: Any, model: str, api_key: Any = None, **kwargs: Any):
        yield LLMDeltaEvent(text="# Brief\n| FY24 revenue | 1,2")
        yield LLMDoneEvent(finish_reason=self.finish_reason)


async def _llm_call(messages: list[dict[str, Any]]) -> str:
    """Every research call; the synthesis goes through the real oneshot seam."""
    system = messages[0]["content"].lower()
    if "concise research brief" in system:
        return await oneshot.complete("anthropic", "claude-opus-4-8", None, messages)
    if "reflect on research coverage" in system:
        return "complete"
    if "planning the next round" in system:
        return "Sub-question A"
    return "FINDING"


async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "web_search":
        return {
            "ok": True,
            "citations": [{"url": "https://ex.com/a", "title": "Results", "source": "ex.com"}],
        }
    return {"ok": True}


def _brief(monkeypatch: pytest.MonkeyPatch, loop: Any, finish_reason: str) -> Any:
    monkeypatch.setattr(oneshot, "get_provider", lambda *_a: _SynthesisProvider(finish_reason))
    return asyncio.run(
        loop("research NVDA", tool_call=_tool, llm_call=_llm_call, budget=BudgetGuard(max_steps=2))
    )


@pytest.mark.parametrize("loop", [run_iter_research, run_deep_research], ids=["iter", "deep"])
def test_synthesis_cut_at_max_tokens_notes_the_brief(
    monkeypatch: pytest.MonkeyPatch, loop: Any
) -> None:
    brief = _brief(monkeypatch, loop, "max_tokens")
    assert SYNTHESIS_TRUNCATED_NOTE in (brief.note or "")


def test_a_finished_synthesis_carries_no_truncation_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    brief = _brief(monkeypatch, run_iter_research, "end_turn")
    assert SYNTHESIS_TRUNCATED_NOTE not in (brief.note or "")
