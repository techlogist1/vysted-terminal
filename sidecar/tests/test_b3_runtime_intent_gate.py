"""R15-AGENT-019: the agent-mode intent gate keeps the write tool a request needs.

``classify_intent`` defaulted every cue-less prompt to ``read`` and its edit cues
had no note/save/screen/delete/update/bought, so "Write a note on …", the
composer's own ``/screener`` expansion and "Delete TCS from my portfolio" lost
exactly the write tool they asked for.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMUsage
from services import agent_runtime

#: Captured phrasings (composer-chat/52-intent-gate-probe.txt and
#: portfolio-notes/30-intent-gate-portfolio-notes.txt) -> the write tool each needs.
_PHRASINGS = [
    (
        "Write a note on Cochin Shipyard: valuation looks stretched at ~54x trailing "
        "P/E; revisit after Q2 results.",
        "write_note",
    ),
    (
        "screen for Indian defence and shipbuilding stocks with P/E below 60 and "
        "market cap above 10000 crore",
        "write_screener_filters",
    ),
    # The /screener slash expansion, verbatim: `screen for ${args}` (slash-commands.ts).
    ("screen for defence stocks P/E < 40", "write_screener_filters"),
    ("Screen for cheap profitable tech", "write_screener_filters"),
    ("find me low-P/E high-ROE names", "write_screener_filters"),
    ("Save this screen as Defence value", "save_screen"),
    ("Save my layout as research desk", "save_layout"),
    ("Note: BDL order inflow looks lumpy", "write_note"),
    ("Jot down that HAL results are on 12 Nov", "write_note"),
    ("Add a note to COCHINSHIP", "write_note"),
    ("I bought 10 shares of INFY at 1500, track it in my portfolio", "portfolio_add_position"),
    ("Add 10 INFY.NS at 1500 to my portfolio", "portfolio_add_position"),
    ("Put 25 HDFC Bank at 1600 in my paper portfolio", "portfolio_add_position"),
    ("Log a buy: 5 TCS @ 2500", "portfolio_add_position"),
    ("I sold my TCS, remove it from my portfolio", "portfolio_delete_position"),
    ("Delete TCS from my portfolio", "portfolio_delete_position"),
    ("Change my TCS position to 25 shares", "portfolio_update_position"),
    ("Update my RELIANCE cost basis to 1180", "portfolio_update_position"),
    ("My RELIANCE lot is actually 12 shares not 10", "portfolio_update_position"),
    ("Save a note on RELIANCE: capex guidance raised", "write_note"),
    ("Append to my RELIANCE note that Jio IPO is H1", "write_note"),
    ("Remember that HAL results are on 12 Nov", "write_note"),
    ("Write this to my general notes: rates on hold", "write_note"),
    ("Replace my TCS note with: exit below 2000", "write_note"),
]

_DATA_WRITES = {
    "write_note",
    "write_screener_filters",
    "save_screen",
    "save_layout",
    "portfolio_add_position",
    "portfolio_update_position",
    "portfolio_delete_position",
}


class _CaptureProvider:
    def __init__(self) -> None:
        self.tool_ids: list[str] | None = None

    async def stream_chat(
        self, messages: list[LLMMessage], model: str, api_key: str | None = None, **kw: Any
    ) -> AsyncIterator[Any]:
        self.tool_ids = list(kw["tool_ids"])
        yield LLMDeltaEvent(text="ok")
        yield LLMDoneEvent(usage=LLMUsage(input_tokens=1, output_tokens=1))


async def _agent_tool_ids(monkeypatch: pytest.MonkeyPatch, prompt: str) -> set[str]:
    agent_runtime.reload()
    provider = _CaptureProvider()
    monkeypatch.setattr(agent_runtime, "get_provider", lambda *_a, **_k: provider)
    async for _ in agent_runtime.invoke_agent(
        agent_id="copilot", prompt=prompt, api_key="k", provider="ollama", mode="agent"
    ):
        pass
    assert provider.tool_ids is not None
    return set(provider.tool_ids)


@pytest.mark.asyncio
@pytest.mark.parametrize(("prompt", "needed"), _PHRASINGS)
async def test_captured_phrasing_keeps_its_write_tool(
    monkeypatch: pytest.MonkeyPatch, prompt: str, needed: str
) -> None:
    assert needed in await _agent_tool_ids(monkeypatch, prompt)


@pytest.mark.asyncio
async def test_held_out_jot_question_keeps_write_note(monkeypatch: pytest.MonkeyPatch) -> None:
    # A read cue ("?") and an edit cue together: the edit cue must win.
    assert "write_note" in await _agent_tool_ids(
        monkeypatch, "Could you jot down that HDFC looks cheap?"
    )


@pytest.mark.asyncio
async def test_positive_read_cue_still_strips_data_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    tool_ids = await _agent_tool_ids(monkeypatch, "what is P/E?")
    assert tool_ids.isdisjoint(_DATA_WRITES)
    assert "price_data" in tool_ids
