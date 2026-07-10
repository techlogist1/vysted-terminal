"""R9 regression suite — pins the live loop-integrity failures (Track B).

Each test mirrors a defect verified on a live build (R9 defect catalogue,
docs/redesign/R9_SAKSOFT_DIAGNOSIS.md):

  V10  the SAKSOFT Q4 FY26 board-outcome filing carries its results tables as
       raster scans; extraction read 27,918 chars of cover-letter text,
       believed it parsed the filing, and the brief said "not parsed" — the
       digital twin (earnings presentation, filed the same evening) was never
       visited;
  V11  off-entity sources leaked at low rates (Coromandel + Tea Post DRHP in
       a SAKSOFT run; a Nestle/Zomato cluster in ROUTE's) via partial-token /
       snippet-passing-mention matches;
  V12  a ROUTE brief transcribed the filing's literal Rs 2 final dividend and
       missed assembling the Rs 11/share FY26 total its own secondary sources
       carried — no cross-source assembly.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.research import disclosures
from services.research.deep import _run_researcher
from services.research.target import target_from_payload
from services.search.extract import scanned_pages_note


def _run(coro):
    return asyncio.run(coro)


def _saksoft_target():
    target = target_from_payload(
        {
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
    )
    assert target is not None
    return target


_OUTCOME_URL = (
    "https://nsearchives.nseindia.com/corporate/"
    "SAKSOFT_25052026134035_OutcomeofBM25052026Signed.pdf"
)
_PRESENTATION_URL = (
    "https://nsearchives.nseindia.com/corporate/"
    "SAKSOFT_25052026215207_Saksoft_LtdQ4-FY26EarningsPresentation.pdf"
)

#: What visit_for_research returns for the REAL outcome filing: cover-letter
#: text plus the scanned-pages honesty note (16 of 27 pages are image-only).
_OUTCOME_VISIT_TEXT = (
    "Saksoft Limited CIN: L72200TN1999PLC054429 — Outcome of the board meeting "
    "held on May 25, 2026: the Board approved the audited standalone and "
    "consolidated financial results for the quarter and year ended March 31, "
    "2026 and recommended a final dividend, subject to shareholder approval. "
    + "The meeting commenced at 12:00 noon and concluded in the afternoon. " * 6
    + "\n\n"
    + scanned_pages_note(16, 27)
)

#: The digital twin: the same-evening earnings presentation, full text layer.
_PRESENTATION_VISIT_TEXT = (
    "Q4 FY26 highlights — Revenue Rs 2,488.45 Mn (Rs 24,884.50 lakh), up 3.7% "
    "YoY; PAT Rs 359.31 Mn (Rs 3,593.09 lakh), up 19.7% YoY, margin 14.44%; "
    "EPS Rs 2.81 basic / Rs 2.76 diluted. FY26 revenue Rs 1,00,719.12 lakh "
    "(+14.1%), PAT Rs 13,326.98 lakh (+22.5%), EPS Rs 10.42. Final dividend "
    "Rs 0.55 per share (55%), record date 2026-07-31, AGM 2026-08-07. "
    "Particulars 24,884.50 23,998.71 3,593.09 3,002.10 2.81 2.35 2.76 2.31."
)


class _SaksoftTool:
    """Serves the SAKSOFT-shaped disclosure feed: scanned outcome at rows[0],
    digital earnings presentation at rows[1] (the band-0.5 row mix)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, dict(args)))
        if name == "corporate_announcements":
            return {
                "ok": True,
                "announcements": [
                    {
                        "exchange": "NSE",
                        "headline": "Outcome of Board Meeting — audited financial results",
                        "category": "Financial Results",
                        "attachment_url": _OUTCOME_URL,
                        "ts": "2026-05-25T13:40:00+05:30",
                    },
                    {
                        "exchange": "NSE",
                        "headline": "Q4 FY26 Earnings Presentation",
                        "category": "Company Update",
                        "attachment_url": _PRESENTATION_URL,
                        "ts": "2026-05-25T21:52:00+05:30",
                    },
                ],
            }
        if name == "web_search":
            return {"ok": True, "citations": [], "results": []}
        return {"ok": True, "provider": "test"}


class _PromptSpyLLM:
    """Records every researcher prompt so evidence reaching the model is
    assertable."""

    def __init__(self) -> None:
        self.user_prompts: list[str] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        self.user_prompts.append(str(messages[-1]["content"]))
        return "FINDING"


def _visit_fake(texts: dict[str, str | None], visited: list[str]):
    async def _visit(url: str) -> str | None:
        visited.append(url)
        return texts.get(url)

    return _visit


# --- V10: the digital-twin fallback visit ------------------------------------------


def test_scanned_outcome_triggers_one_fallback_visit_to_the_digital_twin() -> None:
    """The B1 gate shape: rows[0] is the scanned outcome (visit returns the
    cover letter + scanned-pages note), so the researcher reads rows[1] — the
    digital presentation that carries every Q4 figure."""
    visited: list[str] = []
    llm = _PromptSpyLLM()
    finding, web_res, pairs, visited_pages = _run(
        _run_researcher(
            "What did the Q4 FY26 results announce?",
            target=_saksoft_target(),
            query="Saksoft Limited",
            region="IN",
            tool_call=_SaksoftTool(),
            llm_call=llm,
            visit=_visit_fake(
                {
                    _OUTCOME_URL: _OUTCOME_VISIT_TEXT,
                    _PRESENTATION_URL: _PRESENTATION_VISIT_TEXT,
                },
                visited,
            ),
        )
    )
    assert visited == [_OUTCOME_URL, _PRESENTATION_URL]
    # Both pages ride the run's raw-evidence record.
    assert dict(visited_pages) == {
        _OUTCOME_URL: _OUTCOME_VISIT_TEXT,
        _PRESENTATION_URL: _PRESENTATION_VISIT_TEXT,
    }
    # The extraction prompt saw the honest scanned note AND the real figures.
    prompt = llm.user_prompts[-1]
    assert "16 of 27 pages" in prompt
    assert "24,884.50" in prompt
    assert "3,593.09" in prompt


def test_digit_sparse_cover_letter_triggers_the_fallback() -> None:
    """A multi-attachment outcome whose rows[0] is only the (digital) cover
    letter is digit-sparse — the fallback reads the results annexure row."""
    cover_only = (
        "Dear Sir or Madam, pursuant to Regulation 33 of the SEBI Listing "
        "Obligations we enclose the audited financial results approved by the "
        "Board of Directors at its meeting held today. The results annexure "
        "accompanies this letter as a separate attachment for your records. "
    ) * 4
    visited: list[str] = []
    _run(
        _run_researcher(
            "What did the latest quarterly results announce?",
            target=_saksoft_target(),
            query="Saksoft Limited",
            region="IN",
            tool_call=_SaksoftTool(),
            llm_call=_PromptSpyLLM(),
            visit=_visit_fake(
                {_OUTCOME_URL: cover_only, _PRESENTATION_URL: _PRESENTATION_VISIT_TEXT},
                visited,
            ),
        )
    )
    assert visited == [_OUTCOME_URL, _PRESENTATION_URL]


def test_digit_rich_primary_visit_needs_no_fallback() -> None:
    """A digital results filing at rows[0] already carries the table — the
    fallback must NOT spend a second fetch (bounded cost)."""
    digital_results = (
        "Statement of consolidated financial results for the quarter ended "
        "March 31, 2026 (Rs in lakh): revenue 24,884.50 vs 23,998.71; PAT "
        "3,593.09 vs 3,002.10; EPS 2.81 / 2.76. Year ended: 1,00,719.12 "
        "revenue, 13,326.98 PAT, EPS 10.42. Dividend 0.55 per share. "
        "Segments 12,003.41 8,221.10 4,660.00 totals 24,884.50."
    )
    visited: list[str] = []
    _run(
        _run_researcher(
            "What did the latest quarterly results announce?",
            target=_saksoft_target(),
            query="Saksoft Limited",
            region="IN",
            tool_call=_SaksoftTool(),
            llm_call=_PromptSpyLLM(),
            visit=_visit_fake({_OUTCOME_URL: digital_results}, visited),
        )
    )
    assert visited == [_OUTCOME_URL]


def test_failed_primary_visit_falls_back_to_the_next_row() -> None:
    visited: list[str] = []
    _run(
        _run_researcher(
            "What did the latest quarterly results announce?",
            target=_saksoft_target(),
            query="Saksoft Limited",
            region="IN",
            tool_call=_SaksoftTool(),
            llm_call=_PromptSpyLLM(),
            visit=_visit_fake({_PRESENTATION_URL: _PRESENTATION_VISIT_TEXT}, visited),
        )
    )
    assert visited == [_OUTCOME_URL, _PRESENTATION_URL]


def test_single_disclosure_row_never_double_visits() -> None:
    class _OneRowTool(_SaksoftTool):
        async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
            result = await super().__call__(name, args)
            if name == "corporate_announcements":
                result = dict(result)
                result["announcements"] = result["announcements"][:1]
            return result

    visited: list[str] = []
    _run(
        _run_researcher(
            "What did the latest quarterly results announce?",
            target=_saksoft_target(),
            query="Saksoft Limited",
            region="IN",
            tool_call=_OneRowTool(),
            llm_call=_PromptSpyLLM(),
            visit=_visit_fake({_OUTCOME_URL: _OUTCOME_VISIT_TEXT}, visited),
        )
    )
    assert visited == [_OUTCOME_URL]


# --- V10: the band-0.5 row mix ------------------------------------------------------


def test_presentation_ranks_band_05_behind_the_outcome_filing() -> None:
    """The digital twin must sit at rows[1] for a results question — never a
    fourth scanned outcome or a procedural intimation."""
    feed = {
        "ok": True,
        "announcements": [
            {
                "exchange": "NSE",
                "headline": "Intimation of analyst call audio recording",
                "category": "Company Update",
                "attachment_url": "https://nsearchives.nseindia.com/corporate/AUDIO.pdf",
                "ts": "2026-05-27",
            },
            {
                "exchange": "NSE",
                "headline": "Q4 FY26 Earnings Presentation",
                "category": "Company Update",
                "attachment_url": _PRESENTATION_URL,
                "ts": "2026-05-25T21:52:00+05:30",
            },
            {
                "exchange": "NSE",
                "headline": "Outcome of Board Meeting — audited financial results",
                "category": "Financial Results",
                "attachment_url": _OUTCOME_URL,
                "ts": "2026-05-25T13:40:00+05:30",
            },
        ],
    }
    rows = disclosures.announcement_rows(
        feed, symbol="SAKSOFT", sub_question="What were the Q4 results?"
    )
    assert rows[0]["url"] == _OUTCOME_URL
    assert rows[1]["url"] == _PRESENTATION_URL
    assert rows[2]["url"].endswith("AUDIO.pdf")


# --- V11: zero off-entity sources through the loop ---------------------------------


def test_passing_mention_rows_never_reach_brief_sources() -> None:
    from services.budget_guard import BudgetGuard
    from services.research.iter import run_iter_research

    class _LeakyTool:
        async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
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
                            "url": "https://www.businessdaily.example/coromandel-q4",
                            "title": "Coromandel International Q4 net profit rises 12%",
                            "excerpt": "Other results today: Saksoft, Tea Post and SMEs.",
                        },
                        {
                            "url": "https://www.ipowatch.example/tea-post-drhp",
                            "title": "Tea Post Limited files DRHP for SME IPO",
                            "excerpt": "Peers cited include Saksoft Limited.",
                        },
                        {
                            "url": "https://www.moneycontrol.com/saksoft-q4",
                            "title": "Saksoft Q4 results: PAT up 19.7%",
                            "excerpt": "Saksoft Limited reported",
                        },
                    ],
                }
            return {"ok": True, "provider": "test"}

    class _LLM:
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            system = str(messages[0]["content"]).lower()
            if "reflect on research coverage" in system:
                return "complete"
            if "concise research brief" in system:
                return "# Brief\nPAT up 19.7% [1]."
            return "What did Q4 results say?"

    brief = asyncio.run(
        run_iter_research(
            "Saksoft Limited",
            region="IN",
            tool_call=_LeakyTool(),
            llm_call=_LLM(),
            budget=BudgetGuard(max_steps=10),
        )
    )
    urls = [s.url for s in brief.sources]
    assert "https://www.moneycontrol.com/saksoft-q4" in urls
    for off_entity in ("coromandel", "tea-post"):
        assert not any(off_entity in u for u in urls), f"off-entity source leaked: {off_entity}"


# --- V12: structured progress state + cross-source assembly (B3) -------------------


class _RoutePromptLLM:
    """Routes like the loop fakes but RECORDS every (system, user) pair."""

    def __init__(self) -> None:
        self.prompts: list[tuple[str, str]] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        system = str(messages[0]["content"])
        user = str(messages[-1]["content"])
        self.prompts.append((system, user))
        low = system.lower()
        if "lead synthesist" in low:
            return "# Panel brief\nMerged conclusion [1]."
        if "planning the next round" in low:
            return (
                "What dividends were declared across FY26?\n"
                "What is the price trend?\n"
                "What do the fundamentals and valuation say?"
            )
        if "extract the key finding" in low:
            return (
                "The board declared a final dividend of Rs 2 per share; interim "
                "dividends of Rs 9 per share were paid earlier in FY26."
            )
        if "evolving research report" in low:
            return (
                "## Facts established\n"
                "- Final dividend Rs 2 per share [1]\n"
                "- Interim dividends Rs 9 per share across FY26 [2]\n"
                "- Assembled total: Rs 11 per share for FY26 [1][2]\n"
                "## Open questions\n- none\n"
                "## Dead ends\n- BSE search empty for transcript — do not retry\n"
                "## Planned next\n- close out"
            )
        if "reflect on research coverage" in low:
            return "complete"
        if "concise research brief" in low:
            return "# Brief\nFY26 dividends totalled Rs 11 per share [1][2]."
        return ""


class _RouteTool:
    async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "resolve_symbol":
            return {
                "ok": True,
                "resolved": {
                    "symbol": "ROUTE",
                    "name": "Route Mobile Limited",
                    "exchange": "NSE",
                    "region": "IN",
                    "asset_class": "equity",
                    "confidence": 0.95,
                },
            }
        if name == "web_search":
            rows = [
                {
                    "url": "https://nsearchives.nseindia.com/corporate/ROUTE_outcome.pdf",
                    "title": "Route Mobile — outcome of board meeting (final dividend)",
                    "excerpt": "Final dividend Rs 2 per share",
                    "verified_symbol": "ROUTE",
                },
                {
                    "url": "https://www.moneycontrol.com/route-dividends-fy26",
                    "title": "Route Mobile FY26 dividends: Rs 11 total",
                    "excerpt": "Rs 9 interim plus Rs 2 final",
                },
            ]
            return {"ok": True, "citations": rows, "results": rows}
        return {"ok": True, "provider": "test"}


def _route_iter(llm: _RoutePromptLLM):
    from services.budget_guard import BudgetGuard
    from services.research.iter import run_iter_research

    return asyncio.run(
        run_iter_research(
            "Route Mobile Limited",
            region="IN",
            tool_call=_RouteTool(),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
        )
    )


def test_distill_demands_the_structured_progress_state() -> None:
    """CK-Pro working state: the distill prompt demands the four fixed
    sections, per-fact source markers, dead-end memory, and component facts
    with an assembled-total bullet."""
    llm = _RoutePromptLLM()
    _route_iter(llm)
    distill_systems = [s for s, _ in llm.prompts if "evolving research report" in s.lower()]
    assert distill_systems, "distill prompt never fired"
    system = distill_systems[0]
    for section in (
        "## Facts established",
        "## Open questions",
        "## Dead ends",
        "## Planned next",
    ):
        assert section in system, section
    assert "COMPONENTS of one metric" in system
    assert "assembled" in system.lower()
    assert "do not retry" in system.lower()


def test_planner_is_told_to_respect_dead_ends() -> None:
    # R13: round 1 seeds its fan-out (no planning turn), so drive a MULTI-round
    # run — reflect never completes — to exercise the round-2+ planner and assert
    # its system prompt carries the dead-ends discipline.
    class _NeverCompleteLLM(_RoutePromptLLM):
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            if "reflect on research coverage" in str(messages[0]["content"]).lower():
                self.prompts.append((str(messages[0]["content"]), str(messages[-1]["content"])))
                return "GAP: dividends still unverified"
            return await super().__call__(messages)

    llm = _NeverCompleteLLM()
    _route_iter(llm)
    plan_systems = [s for s, _ in llm.prompts if "planning the next round" in s.lower()]
    assert plan_systems and "dead ends" in plan_systems[0].lower()


def test_synthesis_demands_cross_source_assembly() -> None:
    """The V12 gate shape: synthesis must be prompted to COMPUTE the FY total
    across the interim + final dividend components, never transcribe only the
    filing's literal Rs 2."""
    llm = _RoutePromptLLM()
    brief = _route_iter(llm)
    synth_systems = [s for s, _ in llm.prompts if "concise research brief" in s.lower()]
    assert synth_systems, "synthesis prompt never fired"
    assert "ASSEMBLE ACROSS SOURCES" in synth_systems[0]
    assert "interim" in synth_systems[0].lower()
    # The structured working report (with the component facts) reached the
    # synthesis prompt, so the assembled Rs 11 total is derivable from it.
    synth_users = [u for s, u in llm.prompts if "concise research brief" in s.lower()]
    assert any("Rs 11 per share" in u for u in synth_users)
    assert "Rs 11" in brief.markdown


def test_iter_records_visited_pages_into_the_evidence_store() -> None:
    from services.budget_guard import BudgetGuard
    from services.research.iter import run_iter_research

    store: dict[str, str] = {}

    async def visit(url: str) -> str | None:
        return "Visited full text: final dividend Rs 2, interim Rs 9, total Rs 11."

    asyncio.run(
        run_iter_research(
            "Route Mobile Limited",
            region="IN",
            tool_call=_RouteTool(),
            llm_call=_RoutePromptLLM(),
            budget=BudgetGuard(max_steps=10),
            visit=visit,
            evidence=store,
        )
    )
    assert store, "visited pages never reached the shared evidence store"
    assert any("total Rs 11" in text for text in store.values())


# --- B3: WebWeaver-lite outline-bound synthesis (heavy/ultra only) ------------------


def test_parse_outline_keeps_only_valid_bound_sections() -> None:
    from services.research.iter import _parse_outline

    text = (
        "Financial performance :: [1] [3]\n"
        "- Dividends and capital returns :: [2]\n"
        "Garbled line without markers\n"
        "Out of range :: [9]\n"
        "Valuation :: [1] [1] [2]\n"
    )
    sections = _parse_outline(text, 3)
    assert sections == [
        ("Financial performance", [1, 3]),
        ("Dividends and capital returns", [2]),
        ("Valuation", [1, 2]),
    ]
    # Fewer than two valid sections → the caller falls back to single-call.
    assert len(_parse_outline("only one :: [1]", 3)) == 1
    assert _parse_outline("no structure at all", 3) == []


class _WeaverLLM(_RoutePromptLLM):
    """Answers the WebWeaver outline + section prompts; records everything."""

    def __init__(self) -> None:
        super().__init__()
        self.section_prompts: list[str] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        system = str(messages[0]["content"])
        user = str(messages[-1]["content"])
        low = system.lower()
        if "expert research panel" in low:
            self.prompts.append((system, user))
            return "Dividends and payouts\nGrowth and margins"
        if "plan a research brief as 3-5 sections" in low:
            self.prompts.append((system, user))
            return "Dividends :: [1] [2]\nGrowth :: [1]\nRisks :: [2]"
        if "write one section of a research brief" in low:
            self.prompts.append((system, user))
            self.section_prompts.append(user)
            return "FY26 dividends totalled Rs 11 per share [1][2]."
        return await super().__call__(messages)


def test_heavy_synthesis_weaves_outline_bound_sections() -> None:
    from services.budget_guard import BudgetGuard
    from services.research.iter import run_heavy_research

    llm = _WeaverLLM()
    brief = asyncio.run(
        run_heavy_research(
            "Route Mobile Limited",
            angles=2,
            region="IN",
            tool_call=_RouteTool(),
            llm_call=llm,
            budget=BudgetGuard(max_steps=60),
        )
    )
    # The weave produced section-structured markdown with GLOBAL [n] markers.
    assert "## Dividends" in brief.markdown
    assert "## Growth" in brief.markdown
    assert "[1]" in brief.markdown
    # Each section prompt carried ONLY its bound sources.
    growth_prompts = [p for p in llm.section_prompts if "Section: Growth" in p]
    assert growth_prompts and "[2]" not in growth_prompts[0].split("Sources for THIS section:")[1]
    # The dev trace names the synthesis mode honestly.
    assert any("webweaver outline" in s.detail for s in brief.steps)


def test_garbled_outline_falls_back_to_single_call_synthesis() -> None:
    from services.budget_guard import BudgetGuard
    from services.research.iter import run_heavy_research

    class _GarbledOutlineLLM(_WeaverLLM):
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            system = str(messages[0]["content"]).lower()
            if "plan a research brief as 3-5 sections" in system:
                return "I think the brief should flow naturally without sections."
            if "lead synthesist" in system:
                return "# Panel brief\nMerged conclusion [1]."
            return await super().__call__(messages)

    brief = asyncio.run(
        run_heavy_research(
            "Route Mobile Limited",
            angles=2,
            region="IN",
            tool_call=_RouteTool(),
            llm_call=_GarbledOutlineLLM(),
            budget=BudgetGuard(max_steps=60),
        )
    )
    assert "Merged conclusion" in brief.markdown
    assert any("single-call" in s.detail for s in brief.steps)


def test_heavy_synthesist_fallback_demands_cross_source_assembly() -> None:
    from services.budget_guard import BudgetGuard
    from services.research.iter import run_heavy_research

    captured: list[str] = []

    class _CaptureLLM(_WeaverLLM):
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            system = str(messages[0]["content"])
            if "plan a research brief as 3-5 sections" in system.lower():
                return ""  # force the single-call path
            if "lead synthesist" in system.lower():
                captured.append(system)
                return "# Panel brief\nFY26 dividends totalled Rs 11 [1]."
            return await super().__call__(messages)

    asyncio.run(
        run_heavy_research(
            "Route Mobile Limited",
            angles=2,
            region="IN",
            tool_call=_RouteTool(),
            llm_call=_CaptureLLM(),
            budget=BudgetGuard(max_steps=60),
        )
    )
    assert captured and "ASSEMBLE ACROSS SOURCES" in captured[0]


def test_non_results_question_keeps_feed_order() -> None:
    feed = {
        "ok": True,
        "announcements": [
            {
                "exchange": "NSE",
                "headline": "Q4 FY26 Earnings Presentation",
                "attachment_url": _PRESENTATION_URL,
                "ts": "2026-05-25",
            },
            {
                "exchange": "NSE",
                "headline": "Outcome of Board Meeting — audited financial results",
                "attachment_url": _OUTCOME_URL,
                "ts": "2026-05-24",
            },
        ],
    }
    rows = disclosures.announcement_rows(
        feed, symbol="SAKSOFT", sub_question="Who is on the board of directors?"
    )
    assert [r["url"] for r in rows] == [_PRESENTATION_URL, _OUTCOME_URL]
