"""R8 regression suite — pins the LIVE research-truth failures.

Each test mirrors a defect verified on a live build (regression payloads under
docs/redesign/verification/r8/):

  (i)   a heavy explorer passed its focus-augmented task text into structured
        tools ("Saksoft Limited — focus: Analyze revenue growth…" as a symbol);
  (ii)  every layer re-resolved its own symbol (a Reliance run fuzzy-bound
        CMTL mid-panel);
  (iii) a results-filing PDF in hand extracted nothing → "no quarterly results
        announced";
  (iv)  crypto "Router Protocol" / SEO junk rows became numbered sources;
  (v)   markers like [47] rendered against a 21-source rail;
  (vi)  internal guard traces ("per-round wall-clock guard: round exceeded
        20s", "heavy:3 angles") rendered as the user-facing brief note.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from services.budget_guard import BudgetGuard
from services.research.deep import BUDGET_STOP_NOTE
from services.research.iter import run_heavy_research, run_iter_research
from services.research.models import ResearchBrief
from services.research.target import SYMBOL_SHAPE


def _run(coro):
    return asyncio.run(coro)


#: Substrings that must NEVER appear in a user-facing brief note (vi).
_BANNED_NOTE_FRAGMENTS = ("wall-clock", "guard", "heavy:", "exceeded", "abort")


def _assert_note_humanized(brief: ResearchBrief) -> None:
    if brief.note is None:
        return
    low = brief.note.lower()
    for fragment in _BANNED_NOTE_FRAGMENTS:
        assert fragment not in low, f"note leaked an internal trace: {brief.note!r}"


class _PanelLLM:
    """Routes by system prompt — emits the live run's focus-sentence angles."""

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        system = str(messages[0]["content"]).lower()
        if "expert research panel" in system:
            return (
                "Analyze revenue growth trajectory, margin trends, and valuation "
                "multiples relative to historical and peer ranges\n"
                "Map competitive positioning and client concentration\n"
                "Assess risks, catalysts, and recent exchange disclosures"
            )
        if "planning the next round" in system:
            return "What did the latest quarterly results say?\nWhat is the price trend?"
        if "extract the key finding" in system:
            return "FINDING"
        if "evolving research report" in system:
            return "DISTILLED"
        if "reflect on research coverage" in system:
            return "complete"
        if "lead synthesist" in system:
            return "# Panel brief\nMerged conclusion [1]."
        if "concise research brief" in system:
            return "# Brief\nConclusion [1]."
        return ""


class _SpyTool:
    """Records every (name, args) and serves Saksoft-shaped fixtures."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, dict(args)))
        if name == "resolve_symbol":
            return {
                "ok": True,
                "resolved": {
                    "symbol": "SAKSOFT",
                    "name": "Saksoft Limited",
                    "exchange": "NSE",
                    "region": "IN",
                    "asset_class": "equity",
                    "confidence": 0.96,
                },
            }
        if name == "web_search":
            return {
                "ok": True,
                "citations": [
                    {
                        "url": "https://www.moneycontrol.com/saksoft-q4",
                        "title": "Saksoft Q4 results: revenue up",
                        "excerpt": "Saksoft Limited reported",
                    }
                ],
            }
        if name == "corporate_announcements":
            return {"ok": True, "announcements": [], "count": 0}
        return {"ok": True, "provider": "test"}

    def symbol_args(self) -> list[str]:
        out: list[str] = []
        for name, args in self.calls:
            if name in ("resolve_symbol", "web_search"):
                continue
            if isinstance(args.get("symbol"), str):
                out.append(args["symbol"])
            for sym in args.get("symbols") or []:
                if isinstance(sym, str):
                    out.append(sym)
        return out


def _heavy(tool: _SpyTool) -> ResearchBrief:
    return _run(
        run_heavy_research(
            "Saksoft Limited",
            angles=3,
            region="IN",
            tool_call=tool,
            llm_call=_PanelLLM(),
            budget=BudgetGuard(max_steps=40),
        )
    )


# --- (i) + (ii): symbol truth through the heavy panel ---------------------------


def test_heavy_structured_calls_never_carry_focus_text() -> None:
    tool = _SpyTool()
    brief = _heavy(tool)
    symbols = tool.symbol_args()
    assert symbols, "expected structured tool calls"
    for value in symbols:
        assert "focus:" not in value, value
        assert SYMBOL_SHAPE.match(value), f"non-ticker symbol arg: {value!r}"
        assert value == "SAKSOFT"
    # The published identity is the ORIGINAL query + the bound ticker — never
    # the focus sentence the live ULTRA run published as brief.symbol.
    assert brief.symbol == "SAKSOFT"
    assert brief.query == "Saksoft Limited"
    for entry in brief.structured["panel"]:
        assert "focus:" not in str(entry.get("symbol") or "")


def test_heavy_resolves_exactly_once() -> None:
    tool = _SpyTool()
    _heavy(tool)
    resolves = [name for name, _ in tool.calls if name == "resolve_symbol"]
    assert len(resolves) == 1


def test_heavy_snapshot_is_shared_not_repulled_per_angle() -> None:
    tool = _SpyTool()
    _heavy(tool)
    names = [n for n, _ in tool.calls]
    # The panel snapshot ran up front (price_data before the first web round).
    first_web = next(i for i, n in enumerate(names) if n == "web_search")
    assert "price_data" in names[:first_web]
    # It is pulled ONCE for the panel, not once per explorer. R13: round-1
    # researchers may add their OWN price leg (a "price action" sub-question),
    # so counting price_data before the first web is no longer a clean signal —
    # instead count the SNAPSHOT's signature: price_data immediately followed by
    # fundamentals (snapshot_structured gathers the pair together up front). A
    # researcher pulls a SINGLE structured tool gathered with web, never the
    # pair — so the adjacent pair occurs exactly once (a per-explorer re-pull
    # would show one pair per angle).
    snapshot_pairs = sum(
        1
        for i in range(len(names) - 1)
        if names[i] == "price_data" and names[i + 1] == "fundamentals"
    )
    assert snapshot_pairs == 1


# --- (iii): a results PDF in hand yields its numbers ------------------------------


def test_results_pdf_extracts_seeded_numbers() -> None:
    from services.search.extract import fetch_page
    from tests.test_search_extract import _pdf_bytes, _resolver_public

    pages = ["Quarterly results: revenue Rs 1,234 crore, PAT Rs 210 crore, dividend Rs 5."]

    async def fetch_bytes(url: str) -> tuple[int, bytes]:
        return 200, _pdf_bytes(pages)

    out = _run(
        fetch_page(
            "https://nsearchives.nseindia.com/corporate/ROUTE_results.pdf",
            pdf_fetch=fetch_bytes,
            resolver=_resolver_public,
        )
    )
    assert out["ok"] is True
    assert "Rs 1,234 crore" in out["content"]
    assert "PAT Rs 210 crore" in out["content"]


# --- (iv): junk rows never become sources -----------------------------------------


def test_junk_rows_never_reach_sources_or_coverage() -> None:
    class _JunkyTool(_SpyTool):
        async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
            if name == "web_search":
                self.calls.append((name, dict(args)))
                return {
                    "ok": True,
                    "citations": [
                        {
                            "url": "https://coinmarketcap.com/currencies/router-protocol/",
                            "title": "Router Protocol (ROUTE) price today",
                            "excerpt": "live token price",
                        },
                        {
                            "url": "https://www.scribd.com/doc/1",
                            "title": "Saksoft Limited results discussion",
                        },
                        {
                            "url": "https://blog.example/sr",
                            "title": "What is support and resistance in trading?",
                        },
                        {
                            "url": "https://www.moneycontrol.com/saksoft-q4",
                            "title": "Saksoft Q4 results: revenue up",
                            "excerpt": "Saksoft Limited reported",
                        },
                    ],
                }
            return await super().__call__(name, args)

    tool = _JunkyTool()
    brief = _run(
        run_iter_research(
            "Saksoft Limited",
            region="IN",
            tool_call=tool,
            llm_call=_PanelLLM(),
            budget=BudgetGuard(max_steps=10),
        )
    )
    urls = [s.url for s in brief.sources]
    assert "https://www.moneycontrol.com/saksoft-q4" in urls
    for junk in ("coinmarketcap.com", "scribd.com", "blog.example/sr"):
        assert not any(junk in u for u in urls), f"junk row reached sources: {junk}"


# --- (v): markers never exceed the source rail ------------------------------------


def test_markers_never_exceed_source_count() -> None:
    class _FabricatingLLM(_PanelLLM):
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            system = str(messages[0]["content"]).lower()
            if "concise research brief" in system:
                return "# Brief\nRevenue grew [1]. Margin claim [47]. Cash flow [99]."
            return await super().__call__(messages)

    tool = _SpyTool()
    brief = _run(
        run_iter_research(
            "Saksoft Limited",
            region="IN",
            tool_call=tool,
            llm_call=_FabricatingLLM(),
            budget=BudgetGuard(max_steps=10),
        )
    )
    n = len(brief.sources)
    markers = [int(m) for m in re.findall(r"\[(\d{1,3})\](?!\()", brief.markdown)]
    assert markers, "expected at least one surviving in-range marker"
    assert all(1 <= m <= n for m in markers), f"dangling markers {markers} vs {n} sources"


# --- (vi): notes are human, never internal traces ---------------------------------


def test_budget_stop_note_is_the_human_sentence() -> None:
    tool = _SpyTool()
    brief = _run(
        run_iter_research(
            "Saksoft Limited",
            region="IN",
            tool_call=tool,
            llm_call=_PanelLLM(),
            budget=BudgetGuard(max_steps=0),  # breached immediately
        )
    )
    assert brief.note == BUDGET_STOP_NOTE
    _assert_note_humanized(brief)


def test_starved_wall_run_ships_with_no_note() -> None:
    class _SlowLLM(_PanelLLM):
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            await asyncio.sleep(0.02)
            return await super().__call__(messages)

    tool = _SpyTool()
    brief = _run(
        run_iter_research(
            "Saksoft Limited",
            region="IN",
            tool_call=tool,
            llm_call=_SlowLLM(),
            budget=BudgetGuard(max_wall_seconds=0.5),
        )
    )
    # The live failure rendered "per-round wall-clock guard: round exceeded
    # 20s" as the brief note; a starved wall now closes CLEANLY.
    assert brief.note is None
    _assert_note_humanized(brief)


def test_heavy_note_carries_no_angle_banner() -> None:
    tool = _SpyTool()
    brief = _heavy(tool)
    # "heavy:3 angles" rendered as a live banner; the angle trace belongs to
    # structured.panel, the note to humans.
    assert brief.note is None or "heavy" not in brief.note.lower()
    _assert_note_humanized(brief)
    assert len(brief.structured["panel"]) == 3


def test_every_breach_reason_humanizes() -> None:
    for budget in (
        BudgetGuard(max_steps=0),
        BudgetGuard(max_tokens=0),
        BudgetGuard(max_spend_usd=0.0),
    ):
        tool = _SpyTool()
        brief = _run(
            run_iter_research(
                "Saksoft Limited",
                region="IN",
                tool_call=tool,
                llm_call=_PanelLLM(),
                budget=budget,
            )
        )
        assert brief.note == BUDGET_STOP_NOTE
        _assert_note_humanized(brief)
