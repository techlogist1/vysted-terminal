"""Tests for ``services.research.verify`` — the ULTRA cross-check round.

Everything model/tool-facing is injected, mirroring the loop suites: a routing
FakeLLM (claim extraction vs per-claim verdict) and a canned ``web_search``
tool. Properties under test: disagreements are FLAGGED in the brief (markdown
section + note + structured), independence is enforced (fewer than
``min_domains`` distinct domains → honest UNVERIFIED, never a silent pass), a
breached budget skips the round honestly, ambiguity degrades to UNVERIFIED,
and the existing ``[n]`` source rail is never renumbered.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.budget_guard import BudgetGuard
from services.research.models import ResearchBrief, ResearchSource
from services.research.verify import _parse_verdict, cross_check


def _run(coro):
    return asyncio.run(coro)


def _brief(markdown: str = "# Brief\nNVDA revenue grew 94% in FY2024 [1].") -> ResearchBrief:
    return ResearchBrief(
        query="NVDA thesis",
        symbol="NVDA",
        mode="deep",
        markdown=markdown,
        sources=[ResearchSource(url="https://ex.com/a", title="A", excerpt="x")],
        source_count=1,
    )


class _FakeLLM:
    """Routes by system prompt: claim extraction vs per-claim verdict."""

    def __init__(self, *, claims: str, verdict: str) -> None:
        self.claims_text = claims
        self.verdict_text = verdict
        self.verdict_prompts: list[str] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        system = messages[0]["content"].lower()
        if "numeric claims" in system:
            return self.claims_text
        if "verify one numeric claim" in system:
            self.verdict_prompts.append(messages[-1]["content"])
            return self.verdict_text
        return ""


def _web_tool(urls: list[str]):
    """A web_search fake returning one citation per url; records queries."""
    queries: list[str] = []

    async def _tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        assert name == "web_search"
        queries.append(args["query"])
        return {
            "ok": True,
            "citations": [{"url": u, "title": u, "excerpt": "evidence"} for u in urls],
        }

    _tool.queries = queries  # type: ignore[attr-defined]
    return _tool


TWO_DOMAINS = ["https://www.reuters.com/a", "https://www.bloomberg.com/b"]


def test_disagreement_is_flagged_in_markdown_note_and_structured() -> None:
    llm = _FakeLLM(
        claims="NVDA revenue grew 94% in FY2024",
        verdict="DISAGREE — Reuters reports 78%, not 94%",
    )
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
        )
    )
    assert "## Cross-check" in brief.markdown
    assert "DISAGREEMENT" in brief.markdown
    assert brief.note is not None and "1 numeric disagreement" in brief.note
    payload = brief.structured["cross_check"]
    assert payload["disagreements"] == 1
    assert payload["claims"][0]["verdict"] == "disagree"
    assert payload["claims"][0]["domains"] == ["bloomberg.com", "reuters.com"]


def test_agreement_keeps_note_clean_and_records_section() -> None:
    llm = _FakeLLM(
        claims="NVDA revenue grew 94% in FY2024",
        verdict="AGREE — both sources state 94%",
    )
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
        )
    )
    assert "AGREE" in brief.markdown
    assert brief.note is None  # nothing to flag
    assert brief.structured["cross_check"]["disagreements"] == 0
    # The verdict prompt carried BOTH independent domains as fenced evidence.
    assert "reuters.com" in llm.verdict_prompts[0]
    assert "bloomberg.com" in llm.verdict_prompts[0]


def test_single_domain_is_unverified_never_silently_passed() -> None:
    """Independence floor: one domain (however many rows) cannot verify a claim."""
    llm = _FakeLLM(claims="EPS was $12.96", verdict="AGREE — looks right")
    one_domain = ["https://blog.example/a", "https://blog.example/b"]
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(one_domain),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            min_domains=2,
        )
    )
    payload = brief.structured["cross_check"]
    assert payload["claims"][0]["verdict"] == "unverified"
    assert "1 independent source" in payload["claims"][0]["detail"]
    # The verdict LLM was never consulted — there was nothing independent to compare.
    assert llm.verdict_prompts == []
    assert "UNVERIFIED" in brief.markdown


def test_breached_budget_skips_honestly() -> None:
    llm = _FakeLLM(claims="x 1", verdict="AGREE")
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=0),  # already breached
        )
    )
    assert brief.structured["cross_check"]["skipped"] is True
    assert "step ceiling" in brief.structured["cross_check"]["reason"]
    assert "## Cross-check" not in brief.markdown  # no fake section
    assert any("cross-check skipped" in s.detail for s in brief.steps)


def test_no_numeric_claims_is_an_honest_noop() -> None:
    llm = _FakeLLM(claims="the outlook is positive", verdict="AGREE")  # no digits
    brief = _run(
        cross_check(
            _brief("# Brief\nQualitative outlook only."),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
        )
    )
    assert brief.structured["cross_check"] == {"claims": [], "disagreements": 0}
    assert "## Cross-check" not in brief.markdown
    assert any("no numeric claims" in s.detail for s in brief.steps)


def test_sources_rail_is_never_renumbered() -> None:
    """Re-check evidence is named by domain in the section text — the gathered
    ``[n]`` source list must stay byte-identical."""
    llm = _FakeLLM(claims="grew 94% in FY2024", verdict="AGREE — confirmed")
    brief = _brief()
    before = [s.url for s in brief.sources]
    out = _run(
        cross_check(
            brief,
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
        )
    )
    assert [s.url for s in out.sources] == before


def test_parse_verdict_is_conservative() -> None:
    assert _parse_verdict("DISAGREE — sources differ")[0] == "disagree"
    # "the sources disagree" contains "agree" as a substring — disagreement wins.
    assert _parse_verdict("the sources disagree on the figure")[0] == "disagree"
    assert _parse_verdict("AGREE — consistent across both")[0] == "agree"
    assert _parse_verdict("")[0] == "unverified"
    assert _parse_verdict("cannot tell from the evidence")[0] == "unverified"


def test_dead_llm_degrades_to_unverified_never_raises() -> None:
    async def _dead(_messages: list[dict[str, Any]]) -> str:
        return ""

    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=_dead,
            budget=BudgetGuard(max_steps=10),
        )
    )
    # No claims could be extracted — honest no-op, brief intact.
    assert brief.markdown.startswith("# Brief")
    assert brief.structured["cross_check"]["claims"] == []
