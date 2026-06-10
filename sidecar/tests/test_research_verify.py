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
    # R8: the published reason is the HUMAN sentence; the raw breach telemetry
    # ("step ceiling…") rides only the dev step below.
    assert brief.structured["cross_check"]["reason"] == (
        "Skipped to stay within the run's time budget."
    )
    assert any("step ceiling" in s.detail for s in brief.steps)
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


# --- R9 B4: the dual-channel cross-verification rule --------------------------------


def _native_channel(reply: dict[str, Any]):
    """A native-search channel fake recording every prompt."""
    prompts: list[str] = []

    async def _channel(prompt: str) -> dict[str, Any]:
        prompts.append(prompt)
        return reply

    _channel.prompts = prompts  # type: ignore[attr-defined]
    return _channel


_NATIVE_OK = {
    "ok": True,
    "text": "NVDA's FY2024 data-center revenue grew 94%, per the company's 10-K.",
    "citations": [],
}
_NATIVE_DARK = {"ok": False, "reason": "empty", "text": "", "citations": []}


def test_dual_channel_agreement_is_corroborated() -> None:
    llm = _FakeLLM(
        claims="NVDA revenue grew 94% in FY2024",
        verdict="AGREE — both channels state 94%",
    )
    channel = _native_channel(_NATIVE_OK)
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            native_search=channel,
        )
    )
    check = brief.structured["cross_check"]["claims"][0]
    assert check["channels"] == ["searxng", "native"]
    assert check["corroborated"] is True
    assert brief.structured["cross_check"]["channels"] == ["searxng", "native"]
    assert "corroborated across channels" in brief.markdown
    # The native channel saw the claim, and the verdict prompt saw BOTH
    # labeled evidence blocks.
    assert channel.prompts and "94%" in channel.prompts[0]
    user = llm.verdict_prompts[0]
    assert "SearXNG lane" in user
    assert "native model web search" in user


def test_channel_disagreement_is_flagged_honestly() -> None:
    llm = _FakeLLM(
        claims="NVDA revenue grew 94% in FY2024",
        verdict="DISAGREE — the native channel reports 78%, the web rows 94%",
    )
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            native_search=_native_channel(_NATIVE_OK),
        )
    )
    check = brief.structured["cross_check"]["claims"][0]
    assert check["verdict"] == "disagree"
    assert check["corroborated"] is False
    assert "DISAGREEMENT" in brief.markdown
    assert brief.note is not None and "disagreement" in brief.note
    # The verdict system prompt carried the channel-conflict rule.
    # (Prompt content rides the recorded user message; the rule is system-side
    # and exercised by the dual evidence blocks being present.)
    assert "native model web search" in llm.verdict_prompts[0]


def test_single_channel_claim_is_flagged_not_corroborated() -> None:
    """The native channel comes back dark — the claim is still cross-checked
    on the SearXNG lane but FLAGGED single-channel, never corroborated."""
    llm = _FakeLLM(
        claims="NVDA revenue grew 94% in FY2024",
        verdict="AGREE — both web sources state 94%",
    )
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            native_search=_native_channel(_NATIVE_DARK),
        )
    )
    check = brief.structured["cross_check"]["claims"][0]
    assert check["channels"] == ["searxng"]
    assert check["corroborated"] is False
    assert "single-channel (searxng)" in brief.markdown
    assert "not corroborated by the other channel" in brief.markdown


def test_native_channel_compensates_a_thin_searx_lane() -> None:
    """One SearXNG domain + the native grounded completion = two independent
    retrieval paths — the verdict runs instead of an automatic UNVERIFIED."""
    llm = _FakeLLM(
        claims="EPS was $12.96",
        verdict="AGREE — the grounded search confirms $12.96",
    )
    one_domain = ["https://blog.example/a"]
    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(one_domain),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            min_domains=2,
            native_search=_native_channel(_NATIVE_OK),
        )
    )
    check = brief.structured["cross_check"]["claims"][0]
    assert check["verdict"] == "agree"
    assert check["channels"] == ["searxng", "native"]
    assert llm.verdict_prompts, "the verdict LLM should have been consulted"


def test_both_channels_dark_is_unverified() -> None:
    llm = _FakeLLM(claims="EPS was $12.96", verdict="AGREE")

    async def _dark_web(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": "backend dark"}

    brief = _run(
        cross_check(
            _brief(),
            tool_call=_dark_web,
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            native_search=_native_channel(_NATIVE_DARK),
        )
    )
    check = brief.structured["cross_check"]["claims"][0]
    assert check["verdict"] == "unverified"
    assert check["channels"] == []
    assert llm.verdict_prompts == []


def test_native_channel_crash_degrades_to_single_lane() -> None:
    llm = _FakeLLM(
        claims="NVDA revenue grew 94% in FY2024",
        verdict="AGREE — both web sources state 94%",
    )

    async def _boom(prompt: str) -> dict[str, Any]:
        raise RuntimeError("provider down")

    brief = _run(
        cross_check(
            _brief(),
            tool_call=_web_tool(TWO_DOMAINS),
            llm_call=llm,
            budget=BudgetGuard(max_steps=10),
            native_search=_boom,
        )
    )
    check = brief.structured["cross_check"]["claims"][0]
    assert check["verdict"] == "agree"
    assert check["channels"] == ["searxng"]


def test_no_native_channel_keeps_single_lane_shape() -> None:
    """native_search=None (tier_b, or a native-less chat model) must keep the
    pre-R9 wire shape byte-compatible: no channels keys anywhere."""
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
    payload = brief.structured["cross_check"]
    assert "channels" not in payload
    assert set(payload["claims"][0].keys()) == {"claim", "verdict", "detail", "domains"}
    assert "single-channel" not in brief.markdown
    assert "corroborated across channels" not in brief.markdown
