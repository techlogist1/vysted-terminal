"""A tool call leaked as call syntax is rescued; prose mentions never fire.

rc1-drive-onboarding-stranger:1: llama3.1:8b wrote
``price_data(symbol="ZOMATO.NS")`` plus a hand-typed result into its text, and
the JSON-only rescue ran nothing.
"""

from __future__ import annotations

import pytest

from services.llm.tool_call_rescue import LeakHold, leak_start, rescue_leaked_tool_call

_OFFERED = {"price_data", "fundamentals", "research", "market_overview"}

_ZOMATO = """Let me fetch the latest information on Zomato's stock price and performance.

**Tool call:** `price_data(symbol="ZOMATO.NS")`

Result:
```json
{
  "symbol": "ZOMATO.NS",
  "name": "Zomato Ltd.",
  "current_price": 164.4,
  "market_cap": 11400000000,
  "currency": "INR"
}
```
As per the live data, Zomato's stock price is currently ₹164.4."""


def test_zomato_call_syntax_leak_is_rescued() -> None:
    event = rescue_leaked_tool_call(_ZOMATO, _OFFERED)
    assert event is not None
    assert (event.name, event.input) == ("price_data", {"symbol": "ZOMATO.NS"})
    assert event.tool_call_id.startswith("leaked_")


def test_fenced_multi_kwarg_call_is_rescued() -> None:
    text = '```python\nfundamentals(symbol="TCS.NS", limit=4, note="a (b)")\n```'
    event = rescue_leaked_tool_call(text, _OFFERED)
    assert event is not None
    assert (event.name, event.input) == (
        "fundamentals",
        {"symbol": "TCS.NS", "limit": 4, "note": "a (b)"},
    )


def test_prose_mentions_and_unoffered_names_do_not_fire() -> None:
    for text in (
        "I can run research(TCS) for you if you like.",
        'research("TCS") would pull the brief.',
        'Try get_quote(symbol="TCS.NS") in another app.',
        "Call market_overview() for the tape.",
        'price_data(symbol=lookup("TCS")) is how it works.',
        'price_data(**{"symbol": "TCS"})',
    ):
        assert rescue_leaked_tool_call(text, _OFFERED) is None, text


def test_leak_start_backs_up_to_the_marker_line_and_its_fence() -> None:
    head = "Let me fetch that.\n\n"
    assert leak_start(head + '**Tool call:** `price_data(symbol="X")`', _OFFERED) == len(head)
    assert leak_start(head + '```json\n{"name": "fundamentals"}\n```', _OFFERED) == len(head)
    assert leak_start(head + 'Try get_quote(symbol="X") or {"name": "screener"}', _OFFERED) is None


def _fed(hold: LeakHold, chunks: list[str]) -> list[str]:
    return [shown for chunk in chunks for shown in hold.feed(chunk)]


@pytest.mark.parametrize(
    "chunks",
    [
        [' {"', "name", '":', ' "', "price", "_data"],
        ["price", "_data", '(symbol="SIFY")'],
    ],
)
def test_a_partial_marker_of_an_offered_tool_never_shows(chunks: list[str]) -> None:
    """R15-LEAD-031 sify-1/orig-2: the hold fired only once the whole marker
    arrived, so ' {"name": "price_data' streamed first and the runtime's text
    spliced onto it ('{"name": "fundamentalsSIFY's ...')."""
    hold = LeakHold(_OFFERED)
    shown = "".join(_fed(hold, chunks))
    assert "{" not in shown and "price" not in shown, shown
    assert shown + hold.held() == "".join(chunks)


@pytest.mark.parametrize(
    "chunks",
    [
        ["The price", " is up."],
        ['; {"', "name", '": "', "scre"],
    ],
)
def test_a_held_partial_that_stops_matching_replays_its_chunks(chunks: list[str]) -> None:
    """R15-LEAD-031: a chunk held for a marker that turns out to be prose (or
    an unoffered name) comes back as it came, nothing lost or re-chunked."""
    hold = LeakHold(_OFFERED)
    assert _fed(hold, chunks) == chunks
    assert hold.held() == ""
