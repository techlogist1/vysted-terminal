"""R15-AGENT-019: the agent-mode intent gate keeps the write tool a request needs.

``classify_intent`` defaulted every cue-less prompt to ``read`` and its edit cues
had no note/save/screen/delete/update/bought, so "Write a note on …", the
composer's own ``/screener`` expansion and "Delete TCS from my portfolio" lost
exactly the write tool they asked for.
"""

from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

import pytest

from models.llm import LLMDeltaEvent, LLMDoneEvent, LLMMessage, LLMUsage
from services import agent_runtime, planner

#: The pre-batch-24 shipping `_NO_TOOL_CUE` (planner.py at 1db862d0), kept verbatim as the
#: reference for the batch-24 subset invariant: the narrowed cue may only turn a strip into
#: a keep, never add a new strip.
_SHIP_NO_TOOL_CUE = re.compile(
    r"\bwithout (?:calling|using|running|invoking)(?: any)? tools?\b"
    r"|\b(?:don'?t|do not|never) (?:call|use)(?: any)? tools?\b"
    r"|\bno tool(?:s\b|\s*calls?\b)"
    r"|\b(?:just|only) answer from what (?:i )?(?:gave|told) you\b"
)

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


@pytest.mark.asyncio
async def test_named_tool_exclusion_keeps_the_rest_of_the_surface(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Excluding one NAMED tool is not a no-tool instruction: price_data stays.
    assert "price_data" in await _agent_tool_ids(
        monkeypatch, "Without calling the news tool, get TCS.NS price"
    )


@pytest.mark.asyncio
async def test_normal_portfolio_add_is_unaffected_by_no_tool_cue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert "portfolio_add_position" in await _agent_tool_ids(
        monkeypatch, "Add 10 TCS at 3,200 to my portfolio"
    )


# R15-LEAD-035 batch-24: the narrowing-only closed-tail + reported-speech guard on
# _NO_TOOL_CUE. dv_fix_regex.CASES / fix-regex.out is the batch-23 disposition
# verifier's classification of every phrasing seen across batches 21-23; the fix
# regex is pinned against it here so a future edit to the cue can't regress either
# direction (a new over-strip, or a previously-correct strip going missing).

_FIX_REGEX_CASES: list[tuple[bool, bool, str]] = [
    # (want_strip, expect_empty, prompt) -- all 67 rows of batch-23
    # verifier-evidence/disposition/fix-regex.out, in file order (duplicates kept).
    (
        True,
        True,
        "Without calling any tool, add 10 SBIN at ₹800 to my portfolio and tell me the total.",
    ),
    (True, True, "Don't use any tools, add 7 INFY to my holdings"),
    (True, True, "Never use tools for this: add 5 TCS at ₹3,000 to my holdings."),
    (True, True, "DON'T USE TOOLS. Sell 5 ITC at ₹420 from my portfolio."),
    (
        True,
        True,
        "no tool calls — I sold 4 TCS at ₹3,200, update my position and tell me what I got.",
    ),
    (True, True, "No tools please. I bought 25 WIPRO at ₹165 today — put them in my portfolio."),
    (True, True, "Do not call tools. Remove my HDFCBANK holding."),
    (
        True,
        False,
        "Answer without any tools: I sold 5 TCS shares at ₹3,100 each. Restate my total proceeds.",
    ),
    (True, False, "Do not call a tool. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
    (True, False, "Don’t use any tools. I sold 5 TCS shares at ₹3,100 each; restate my proceeds."),
    (
        True,
        False,
        "Avoid calling any functions. I bought 40 ITC shares at ₹415, add them to my holdings and "
        "tell me what I spent.",
    ),
    (
        True,
        False,
        "Skip the tools for this one — I hold 12 HDFCBANK at ₹1,600; add 3 more at ₹1,650, what is "
        "my average?",
    ),
    (
        True,
        False,
        "Zero tool calls please: I want to add 7 INFY at ₹1,500 to my portfolio — just tell me the "
        "total cost.",
    ),
    (
        True,
        False,
        "I hold 40 HDFCBANK at ₹1,640; answer only from what I gave you: what is my cost basis?",
    ),
    (True, False, "Refrain from calling any tools and restate my 5 TCS at ₹3,100."),
    (
        True,
        False,
        "Without using functions, add 3 HDFCBANK at ₹1,650 to my holdings and tell me the total.",
    ),
    (True, False, "No function calls. I bought 15 WIPRO at ₹250; total cost?"),
    (True, False, "Please don’t invoke any tool — record nothing, just tell me 5 × ₹3,100."),
    (True, False, "Hands off the tools: add 20 SBIN at ₹800 to my portfolio."),
    (True, False, "No external calls. Record a buy of 5 RELIANCE at ₹1,200 in my portfolio."),
    (True, False, "Don't look anything up; I sold 3 INFY at ₹1,010 — update my holdings."),
    (True, False, "Without any function calls, delete my TCS position."),
    (True, False, "Tools off for this one: what is TCS.NS trading at right now?"),
    (True, False, "Please don't touch any tools, just tell me INFY.NS's current price."),
    (
        False,
        False,
        "Don't just use the tools blindly — check the TCS.NS price and explain the move.",
    ),
    (False, False, "Never call the tools twice for one symbol; get the INFY.NS price."),
    (False, False, "Don't call functions you don't need, just get me SBIN.NS's latest price."),
    (False, False, "No lookups needed for TCS, I know it; what is ITC.NS trading at?"),
    (False, False, "Never use the search tools, only the quote: INFY.NS price?"),
    (False, False, "Don't use the tools for arithmetic; get the TCS.NS price."),
    (False, False, "Do not call the tools again for TCS, just get INFY.NS price."),
    (False, False, "I never said don't use tools — get RELIANCE.NS price."),
    (False, False, "Don't use any tools other than price data: TCS.NS close?"),
    (False, False, "Don't use tools for the math, but do fetch the TCS.NS price."),
    (False, False, "No tools except price_data for TCS.NS"),
    (False, False, "Don't use tools you don't need; get the ITC.NS price."),
    (False, False, "Don't call tools twice — what is HDFCBANK.NS at?"),
    (False, False, "Do not use tools from the web, only the quote: WIPRO.NS price?"),
    (
        False,
        False,
        "Get the latest price of SBIN.NS and state it in one sentence that calls the company SBI.",
    ),
    (False, False, "Get the latest price of TCS.NS and state it in one sentence."),
    (False, False, "What is INFY.NS trading at right now? One line."),
    (False, False, "Fetch ITC.NS with price_data and tell me its current price."),
    (False, False, "Latest HDFCBANK.NS price please, just the number and the date."),
    (False, False, "Use price_data for WIPRO.NS and give me the current price and today's change."),
    (
        True,
        True,
        "I sold 5 TCS shares at ₹3,100 each. Without calling any tool, restate my sale price and "
        "my total proceeds.",
    ),
    (
        True,
        True,
        "Please answer without using any tools: I own 30 ITC shares at ₹410 and will add 10 more "
        "at ₹420. What's my new average cost?",
    ),
    (
        True,
        True,
        "No tools please. I bought 15 WIPRO shares at ₹250 and sold them at ₹262. What was my "
        "profit?",
    ),
    (True, True, "Don't use any tools, add 7 INFY to my holdings"),
    (True, True, "no tool calls — I sold 4 TCS at ₹3,200, what did I get?"),
    (True, True, "DON'T USE TOOLS. Sell 5 ITC at ₹420 from my portfolio."),
    (True, True, "Never use tools for this: add 5 TCS at ₹3,000 to my holdings."),
    (
        True,
        True,
        "I hold 40 HDFCBANK at ₹1,640; just answer from what I gave you: what is my cost basis?",
    ),
    (
        False,
        False,
        "Just get the latest price from the market for the stocks in this message: TCS.NS, INFY.NS",
    ),
    (False, False, "Only use data from price_data for the above symbols: TCS.NS"),
    (False, False, "Why did you not use the tools? Get the TCS.NS price now."),
    (False, False, "Don't forget to use the tools to get the latest TCS.NS price."),
    (False, False, "Do not answer without using the tools: what is TCS.NS trading at?"),
    (False, False, "Never guess, always call the tools: what is INFY.NS trading at"),
    (False, False, "Don't use web search, get TCS.NS price"),
    (False, False, "Add 10 TCS at 3,200 to my portfolio"),
    (False, False, "What tools do you have?"),
    (False, False, "I don't trust your memory, use the tools to fetch INFY.NS fundamentals"),
    (False, False, "Could you use the tools to get HDFCBANK.NS price?"),
    (False, False, "Don't rely on memory; get TCS.NS price with the tools."),
    (False, False, "No need to avoid the tools this time: what is SBIN.NS at?"),
    (False, False, "What is TCS.NS at? Don't call the news tool."),
    (False, False, "Without calling the fundamentals tool, use price_data for TCS.NS."),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(("want_strip", "expect_empty", "prompt"), _FIX_REGEX_CASES)
async def test_fix_regex_cases_against_the_gate_off_surface(
    monkeypatch: pytest.MonkeyPatch, want_strip: bool, expect_empty: bool, prompt: str
) -> None:
    tool_ids = await _agent_tool_ids(monkeypatch, prompt)
    assert (tool_ids == set()) == expect_empty
    if expect_empty:
        # Subset invariant: the fix may only strip what the shipping cue also stripped.
        assert _SHIP_NO_TOOL_CUE.search(prompt.lower())
    if not want_strip:
        # 0 over-strips: a prompt that must keep the surface never gets emptied.
        assert tool_ids


# Held-out class cases (planner-chosen, not in fix-regex.out) added to the Test B
# subset-invariant parametrisation below.
_HELD_OUT_SUBSET_CASES = [
    "Don't use tools unless you must; get the TCS.NS price.",
    "Never call tools on my behalf, get INFY.NS price",
    "you say don't use tools, but get TCS.NS price",
    "No tools at all: I bought 5 ITC at ₹420, what's the total?",
    "Do not use any tools here. I hold 10 SBIN at ₹800; what's my cost?",
]


@pytest.mark.parametrize("prompt", [p for _, _, p in _FIX_REGEX_CASES] + _HELD_OUT_SUBSET_CASES)
def test_fix_regex_is_a_subset_of_the_shipping_regex(prompt: str) -> None:
    lowered = prompt.lower()
    if planner._NO_TOOL_CUE.search(lowered):
        assert _SHIP_NO_TOOL_CUE.search(lowered)


# The 7 explicit data requests the shipping cue over-matched (batch-23
# verifier-evidence/disposition/dv_prompts.OVER); the fix must keep price_data.
_OVER_PROMPTS = [
    "I never said don't use tools — get RELIANCE.NS price.",
    "Don't use any tools other than price data: TCS.NS close?",
    "Don't use tools for the math, but do fetch the TCS.NS price.",
    "No tools except price_data for TCS.NS",
    "Don't use tools you don't need; get the ITC.NS price.",
    "Don't call tools twice — what is HDFCBANK.NS at?",
    "Do not use tools from the web, only the quote: WIPRO.NS price?",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("prompt", _OVER_PROMPTS)
async def test_over_prompts_keep_price_data(monkeypatch: pytest.MonkeyPatch, prompt: str) -> None:
    assert "price_data" in await _agent_tool_ids(monkeypatch, prompt)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("prompt", "expect_price_data"),
    [
        # Class pin: cases the fix was not written against (planner-chosen), verified
        # offline against both the shipping and the fix regex (batch-24 PLAN.md).
        ("Don't use tools unless you must; get the TCS.NS price.", True),
        ("Never call tools on my behalf, get INFY.NS price", True),
        ("you say don't use tools, but get TCS.NS price", True),
        ("No tools at all: I bought 5 ITC at ₹420, what's the total?", False),
        (
            "Do not use any tools here. I hold 10 SBIN at ₹800; what's my cost?",
            False,
        ),
    ],
)
async def test_held_out_class_cases_batch24(
    monkeypatch: pytest.MonkeyPatch, prompt: str, expect_price_data: bool
) -> None:
    tool_ids = await _agent_tool_ids(monkeypatch, prompt)
    if expect_price_data:
        assert "price_data" in tool_ids
    else:
        assert tool_ids == set()
