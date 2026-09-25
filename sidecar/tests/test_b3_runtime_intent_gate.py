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
from services import agent_runtime, planner

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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt",
    [
        "Can you log 10 TCS at 3400 in my portfolio?",
        "Can you record that I hold 20 ITC at 410?",
        # Class pin: neither log nor record, only the "<qty> <symbol> at <price>" shape.
        "Could you enter 5 HDFCBANK at 1600 into my portfolio?",
    ],
)
async def test_question_shaped_holding_ask_keeps_portfolio_add_position(
    monkeypatch: pytest.MonkeyPatch, prompt: str
) -> None:
    # The trailing "?" is a positive read cue; the bookkeeping cue must still win.
    assert "portfolio_add_position" in await _agent_tool_ids(monkeypatch, prompt)


@pytest.mark.asyncio
async def test_portfolio_question_still_strips_data_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    tool_ids = await _agent_tool_ids(monkeypatch, "How is my portfolio doing?")
    assert tool_ids.isdisjoint(_DATA_WRITES)


# R15-LEAD-035: an explicit in-turn "without calling any tool" instruction
# empties the whole tool surface server-side, rather than relying on the model
# to self-restrain. Tests 1-2 need agent_runtime._resolve_tool_surface's
# companion hunk (batch-21 W1) and pass only on the merged tree — see
# docs/redesign/verification/r15/stage-c/batch-21/PLAN.md "W1 applies for W2".


@pytest.mark.asyncio
async def test_explicit_no_tool_instruction_empties_tool_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Verbatim t-user-sale (batch-19 verifier-evidence/b19v_live.py:29).
    prompt = (
        "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate "
        "my sale price and my total proceeds."
    )
    assert await _agent_tool_ids(monkeypatch, prompt) == set()


@pytest.mark.asyncio
async def test_fresh_no_tool_phrasing_empties_tool_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompt = "Don't use any tools — I hold 40 HDFCBANK at ₹1,640; just tell me my cost basis."
    assert await _agent_tool_ids(monkeypatch, prompt) == set()


async def _gate_off_tool_ids(monkeypatch: pytest.MonkeyPatch, prompt: str) -> set[str]:
    """The surface the same prompt gets with the no-tool cue switched off."""
    with monkeypatch.context() as m:
        m.setattr(planner, "_no_tool_cue", lambda _text: False)
        return await _agent_tool_ids(m, prompt)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "prompt",
    ["Without calling the news tool, get TCS.NS price", "Don't use web search, get TCS.NS price"],
)
async def test_named_tool_exclusion_keeps_the_rest_of_the_surface(
    monkeypatch: pytest.MonkeyPatch, prompt: str
) -> None:
    # Excluding one NAMED tool is not a no-tool instruction: price_data stays.
    tool_ids = await _agent_tool_ids(monkeypatch, prompt)
    assert "price_data" in tool_ids
    assert tool_ids == await _gate_off_tool_ids(monkeypatch, prompt)


@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", ["Add 10 TCS at 3,200 to my portfolio", "Add 10 TCS at 3,200"])
async def test_normal_portfolio_add_is_unaffected_by_no_tool_cue(
    monkeypatch: pytest.MonkeyPatch, prompt: str
) -> None:
    tool_ids = await _agent_tool_ids(monkeypatch, prompt)
    assert "portfolio_add_position" in tool_ids
    assert tool_ids == await _gate_off_tool_ids(monkeypatch, prompt)


# batch-22's over-match (verifier l035-surface.out) stripped these data requests
# to zero tools and the model fabricated prices; the first six are verbatim.
_KEEP_SURFACE = [
    "Don't forget to use the tools to get the latest TCS.NS price.",
    "Do not answer without using the tools: what is TCS.NS trading at?",
    "Why did you not use the tools? Get the TCS.NS price now.",
    "Why did you not use the tools",
    "Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS",
    "Only use data from price_data for the above symbols: TCS.NS",
    "No tools except price_data for TCS.NS",
    "No tools other than a price lookup for TCS.NS.",
    "Answer using the latest data, not just from memory: TCS.NS price",
    "Don't reply if you do not call the tools: what is INFY.NS at?",
    "Did you not call any tools? Get INFY.NS price.",
    "No tools for the arithmetic; use the tools to get the TCS.NS price.",
    "Take the tickers from this message and fetch prices: TCS.NS",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", _KEEP_SURFACE)
async def test_data_request_mentioning_tools_keeps_its_surface(
    monkeypatch: pytest.MonkeyPatch, prompt: str
) -> None:
    tool_ids = await _agent_tool_ids(monkeypatch, prompt)
    assert "price_data" in tool_ids
    assert tool_ids == await _gate_off_tool_ids(monkeypatch, prompt)


# Every true no-tool phrasing batch-21 and batch-22 found kept the surface.
_NO_TOOL = [
    "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds.",
    "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds.",
    "Don\u2019t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds.",
    "Avoid calling any functions. I bought 40 ITC shares at ₹415, add them to my holdings "
    "and tell me what I spent.",
    "Zero tool calls please: I want to add 7 INFY at ₹1,500 to my portfolio — just tell me "
    "the total cost.",
    "Skip the tools for this one — I hold 12 HDFCBANK at ₹1,600; add 3 more at ₹1,650, what "
    "is my average?",
    "I hold 40 HDFCBANK at ₹1,640; answer only from what I gave you: what is my cost basis?",
    "From memory only: what did TCS close at last year?",
    "No tools: what is 5 × 3,100?",
    "Please refrain from using tools, just compute it.",
    "Don't make any tool calls, restate my 5 TCS at ₹3,100.",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", _NO_TOOL)
async def test_no_tool_phrasing_empties_tool_surface(
    monkeypatch: pytest.MonkeyPatch, prompt: str
) -> None:
    assert await _agent_tool_ids(monkeypatch, prompt) == set()
