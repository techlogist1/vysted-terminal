"""Tests for the R7 depth router + the finance tuning threaded into the loops.

Two layers:

  - ``services.research.depth`` — the ONE knob table: naming (normal / deep /
    ultra + legacy aliases), the per-depth profile scaling (rounds, researchers,
    angles, report cap, wall, coverage strictness, cross-check, site bias).
  - The REAL iter loop with fakes (same pattern as ``test_research_iter``),
    proving the knobs change behaviour: the no-price-feed coverage-floor
    loosening (web-only coverage finishes cleanly AND the brief says so), the
    ULTRA >=2-independent-domains strictness, the ``report_char_cap`` knob, the
    server-date directive on every research prompt, the finance ``site:`` query
    bias, and tier-ranked citation ordering.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.budget_guard import BudgetGuard
from services.research import depth as depth_mod
from services.research.deep import (
    _Findings,
    coverage_floor_met,
    structured_feeds_available,
)
from services.research.iter import run_iter_research
from services.research.models import ResearchBrief, ResearchSource


def _run(coro):
    return asyncio.run(coro)


# --- the depth table (the ONE source of truth) --------------------------------


def test_normalize_depth_canonical_and_legacy_aliases() -> None:
    assert depth_mod.normalize_depth("normal") == "normal"
    assert depth_mod.normalize_depth("deep") == "deep"
    assert depth_mod.normalize_depth("ultra") == "ultra"
    # Legacy spellings (the current catalog enum) map forever.
    assert depth_mod.normalize_depth("quick") == "normal"
    assert depth_mod.normalize_depth("fast") == "normal"
    assert depth_mod.normalize_depth("heavy") == "ultra"
    assert depth_mod.normalize_depth("panel") == "ultra"
    assert depth_mod.normalize_depth("iter") == "deep"
    # Garbage floors to the cheap pass, never an escalation.
    assert depth_mod.normalize_depth(None) == "normal"
    assert depth_mod.normalize_depth("bananas") == "normal"
    assert depth_mod.normalize_depth(True) == "ultra"  # the old "all out" toggle


def test_profiles_scale_monotonically_with_depth() -> None:
    normal = depth_mod.profile_for("normal")
    deep = depth_mod.profile_for("deep")
    ultra = depth_mod.profile_for("ultra")
    assert (normal.loop, deep.loop, ultra.loop) == ("fast", "iter", "heavy")
    # The brief's contract: DEEP ~3 rounds x 3 researchers; ULTRA = 3 angles.
    assert deep.rounds == 3 and deep.researchers == 3 and deep.angles == 1
    assert ultra.angles == 3
    # Every knob scales upward, never down.
    assert ultra.rounds >= deep.rounds
    assert ultra.report_char_cap > deep.report_char_cap > normal.report_char_cap
    assert ultra.wall_seconds > deep.wall_seconds
    assert ultra.min_web_domains > deep.min_web_domains
    # Cross-check is ULTRA-only; the finance site bias rides DEEP and ULTRA.
    assert (normal.cross_check, deep.cross_check, ultra.cross_check) == (False, False, True)
    assert (normal.site_bias, deep.site_bias, ultra.site_bias) == (False, True, True)


def test_profile_for_tolerates_any_spelling() -> None:
    assert depth_mod.profile_for("HEAVY ").depth == "ultra"
    assert depth_mod.profile_for(42).depth == "normal"


# --- coverage floor unit behaviour --------------------------------------------


def _findings_with_web(urls: list[str]) -> _Findings:
    f = _Findings()
    for url in urls:
        f.web_sources.append(ResearchSource(url=url, title=url, excerpt="x"))
    if urls:
        f.coverage["web"] = True
    return f


_FEEDS_OK = {"price": {"ok": True}, "fundamentals": {"ok": True}}
_FEEDS_NONE = {"price": {"ok": False}, "fundamentals": {"ok": False}}


def test_floor_loosens_to_web_only_when_no_structured_feed() -> None:
    findings = _findings_with_web(["https://a.example/1"])
    # Structured feeds returned provider:none -> web alone satisfies the floor.
    assert structured_feeds_available(_FEEDS_NONE) is False
    assert coverage_floor_met(findings, structured=_FEEDS_NONE, min_web_domains=1) is True
    # With feeds AVAILABLE the full dimension floor still applies (price /
    # fundamentals / news coverage was never gathered here).
    assert coverage_floor_met(findings, structured=_FEEDS_OK, min_web_domains=1) is False


def test_floor_strictness_counts_distinct_domains_not_rows() -> None:
    same_domain = _findings_with_web(["https://a.example/1", "https://a.example/2"])
    two_domains = _findings_with_web(["https://a.example/1", "https://b.example/1"])
    assert coverage_floor_met(same_domain, structured=_FEEDS_NONE, min_web_domains=2) is False
    assert coverage_floor_met(two_domains, structured=_FEEDS_NONE, min_web_domains=2) is True


def test_floor_with_no_web_is_never_met_even_loosened() -> None:
    assert coverage_floor_met(_Findings(), structured=_FEEDS_NONE, min_web_domains=1) is False


# --- the REAL iter loop with the depth knobs -----------------------------------


class _FakeLLM:
    """Routes by system prompt; records every system prompt + plan contexts."""

    def __init__(self, *, distill: str = "DISTILLED", reflect: str = "complete") -> None:
        self.distill_text = distill
        self.reflect_text = reflect
        self.system_prompts: list[str] = []
        self.plan_prompts: list[str] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        system = messages[0]["content"]
        self.system_prompts.append(system)
        low = system.lower()
        user = messages[-1]["content"]
        if "planning the next round" in low:
            self.plan_prompts.append(user)
            return (
                "What do the latest SEC filings say?\n"
                "What is the price trend?\n"
                "What recent news affects the company?"
            )
        if "extract the key finding" in low:
            return "FINDING"
        if "evolving research report" in low:
            return self.distill_text
        if "reflect on research coverage" in low:
            return self.reflect_text
        if "concise research brief" in low:
            return "# Brief\nWeb-grounded conclusion [1]."
        return ""


def _micro_cap_tool(web_urls: list[str]):
    """A micro-cap world: resolve works, ALL structured providers return none,
    the web answers. Records every web_search query."""
    web_queries: list[str] = []

    async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "resolve_symbol":
            return {"ok": True, "resolved": {"symbol": "TINYCO"}}
        if name == "web_search":
            web_queries.append(args["query"])
            return {
                "ok": True,
                "citations": [
                    {"url": u, "title": u, "excerpt": "e", "source": u} for u in web_urls
                ],
            }
        # price_data / fundamentals / news / sec_filings_list: provider none.
        return {"ok": False, "error": f"no provider covers TINYCO ({name})"}

    _tool.web_queries = web_queries  # type: ignore[attr-defined]
    return _tool


def test_no_price_feed_run_finishes_cleanly_and_brief_says_so() -> None:
    """The no-price-feed resilience: web-only coverage satisfies the loosened
    floor (clean finish, no budget-abort note) and the brief states it."""
    tool = _micro_cap_tool(["https://localnews.example/tinyco"])
    brief = _run(
        run_iter_research(
            "research TINYCO",
            tool_call=tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=6),
            min_web_domains=1,
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.note is None  # clean break — NOT a budget abort
    assert "Coverage note" in brief.markdown
    assert "web sources alone" in brief.markdown


def test_structured_backed_run_carries_no_web_only_note() -> None:
    async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG001
        if name == "resolve_symbol":
            return {"ok": True, "resolved": {"symbol": "NVDA"}}
        if name == "web_search":
            return {
                "ok": True,
                "citations": [{"url": "https://ex.com/a", "title": "A", "excerpt": "x"}],
            }
        return {"ok": True, "provider": "test"}

    brief = _run(
        run_iter_research(
            "research NVDA",
            tool_call=_tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=6),
        )
    )
    assert brief.note is None
    assert "Coverage note" not in brief.markdown


def test_ultra_strictness_blocks_single_domain_completion() -> None:
    """min_web_domains=2 (the ULTRA floor): one domain can never complete cleanly
    — the run is cut by the budget instead, and the brief still ships."""
    tool = _micro_cap_tool(["https://onlyblog.example/a", "https://onlyblog.example/b"])
    brief = _run(
        run_iter_research(
            "research TINYCO",
            tool_call=tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=2),
            min_web_domains=2,
        )
    )
    assert brief.note is not None and "step ceiling" in brief.note


def test_ultra_strictness_met_by_two_independent_domains() -> None:
    tool = _micro_cap_tool(["https://a.example/1", "https://b.example/1"])
    brief = _run(
        run_iter_research(
            "research TINYCO",
            tool_call=tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=6),
            min_web_domains=2,
        )
    )
    assert brief.note is None  # the stricter floor was genuinely met


def test_report_char_cap_knob_bounds_the_working_report() -> None:
    cap = 1000
    llm = _FakeLLM(distill="X" * (cap * 5), reflect="gaps remain")
    _run(
        run_iter_research(
            "q",
            tool_call=_micro_cap_tool(["https://a.example/1"]),
            llm_call=llm,
            budget=BudgetGuard(max_steps=2),
            report_char_cap=cap,
        )
    )
    # The round-2 plan prompt embeds report.render(); the ULTRA/DEEP cap knob
    # (not the module default) must bound it.
    assert len(llm.plan_prompts[1]) < cap * 3


def test_every_research_prompt_carries_the_server_date() -> None:
    llm = _FakeLLM(reflect="complete")
    _run(
        run_iter_research(
            "research TINYCO",
            tool_call=_micro_cap_tool(["https://a.example/1"]),
            llm_call=llm,
            budget=BudgetGuard(max_steps=6),
        )
    )
    assert llm.system_prompts  # plan, extract, distill, reflect, synthesize
    for prompt in llm.system_prompts:
        assert "Server date:" in prompt


def test_site_bias_filters_filings_questions_toward_regulators() -> None:
    tool = _micro_cap_tool(["https://a.example/1"])
    _run(
        run_iter_research(
            "research TINYCO",
            tool_call=tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=6),
            site_bias=True,
        )
    )
    # The plan emits a filings-shaped sub-question; its web query carries the
    # regulator site: hint. The price-trend question stays unfiltered.
    assert any("site:sec.gov" in q for q in tool.web_queries)
    assert any("site:" not in q for q in tool.web_queries)


def test_site_bias_off_leaves_queries_untouched() -> None:
    tool = _micro_cap_tool(["https://a.example/1"])
    _run(
        run_iter_research(
            "research TINYCO",
            tool_call=tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=6),
            site_bias=False,
        )
    )
    assert all("site:" not in q for q in tool.web_queries)


def test_heavy_panel_carries_the_web_only_note() -> None:
    """ULTRA on a no-feed instrument: the MERGED panel brief states the
    web-only coverage even though the synthesist rewrites the prose."""
    from services.research.iter import run_heavy_research

    tool = _micro_cap_tool(["https://a.example/1", "https://b.example/1"])

    class _PanelLLM(_FakeLLM):
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            low = messages[0]["content"].lower()
            if "expert research panel" in low:
                return "Angle A\nAngle B"
            if "lead synthesist" in low:
                return "# Panel brief\nMerged conclusion [1]."  # note dropped
            return await super().__call__(messages)

    brief = _run(
        run_heavy_research(
            "research TINYCO",
            angles=2,
            tool_call=tool,
            llm_call=_PanelLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=20),
            min_web_domains=2,
        )
    )
    assert "Coverage note" in brief.markdown
    assert brief.markdown.count("Coverage note") == 1  # stated once, not per angle


def test_citations_are_tier_ranked_for_synthesis() -> None:
    """A primary-record source gathered AFTER a blog still takes the low [n]."""
    tool = _micro_cap_tool(
        ["https://randomblog.example/post", "https://www.sec.gov/filing/tinyco-10k"]
    )
    brief = _run(
        run_iter_research(
            "research TINYCO",
            tool_call=tool,
            llm_call=_FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=6),
        )
    )
    web_urls = [s.url for s in brief.sources if s.url.startswith("https://")]
    assert web_urls[0] == "https://www.sec.gov/filing/tinyco-10k"


def test_composer_slider_depth_is_the_request_default() -> None:
    """options.research_depth (the slider) routes a depth-less research call.

    The model passing an explicit depth still wins; clearing the ContextVar
    restores the NORMAL floor. Wired via config.set_request_research_depth in
    agent_runtime → services/agent_tools/research.py.
    """
    import config as app_config
    from services.research import depth as depth_mod

    token = app_config.set_request_research_depth("ultra")
    try:
        assert depth_mod.normalize_depth(None or app_config.get_request_research_depth()) == "ultra"
        # explicit model arg wins over the slider default
        assert (
            depth_mod.normalize_depth("deep" or app_config.get_request_research_depth()) == "deep"
        )
    finally:
        app_config._research_depth_ctx.reset(token)
    assert depth_mod.normalize_depth(None or app_config.get_request_research_depth()) == "normal"
