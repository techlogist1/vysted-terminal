"""Tests for ``services.research.iter`` — the IterResearch loop + Heavy panel.

Everything model/tool-facing is injected, so the loops are exercised with fakes:
a ``FakeLLM`` that routes by the prompt's system role (plan / extract / distill /
reflect / synthesize / panel) and a ``fake_tool`` returning cited web + structured
results. The properties under test are the IterResearch invariants:

  - workspace RECONSTRUCTION (a later round's context does NOT carry the full
    findings history — only the distilled report + the latest round's evidence),
  - bounded working report (``render`` is capped),
  - distill resilience (an empty distill keeps the prior report; the brief still
    ships),
  - the shared deep-loop invariants (budget breach → abort→synthesize, never raise),
  - the Heavy panel (N angles → one synthesized brief, sources merged/de-duped,
    survives an angle crash + a dead LLM, emits angle-tagged steps).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.budget_guard import BudgetGuard
from services.research import iter as iter_research
from services.research.iter import _REPORT_CHAR_CAP, run_heavy_research, run_iter_research
from services.research.models import ResearchBrief, ResearchStep


def _run(coro):
    return asyncio.run(coro)


class FakeLLM:
    """Routes a completion by the system prompt; records plan + distill prompts."""

    def __init__(self, *, distill: str = "DISTILLED_REPORT", reflect: str = "gaps remain") -> None:
        self.distill_text = distill
        self.reflect_text = reflect
        self.find_counter = 0
        self.plan_prompts: list[str] = []
        self.distill_prompts: list[str] = []

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        system = messages[0]["content"].lower()
        user = messages[-1]["content"]
        if "expert research panel" in system:
            return "Angle Alpha\nAngle Beta\nAngle Gamma"
        if "planning the next round" in system:
            self.plan_prompts.append(user)
            return "Sub-question A\nSub-question B\nSub-question C"
        if "extract the key finding" in system:
            self.find_counter += 1
            return f"FIND#{self.find_counter}"
        if "evolving research report" in system:
            self.distill_prompts.append(user)
            return self.distill_text
        if "reflect on research coverage" in system:
            return self.reflect_text
        if "lead synthesist" in system:
            return "# Synthesized panel brief\nIntegrated conclusion [1]."
        if "concise research brief" in system:
            return "# Brief\nFinal synthesized brief [1]."
        return ""


async def fake_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "resolve_symbol":
        return {
            "ok": True,
            "resolved": {
                "symbol": "NVDA",
                "name": "NVIDIA Corporation",
                "exchange": "NASDAQ",
                "region": "US",
                "asset_class": "equity",
                "confidence": 0.97,
            },
        }
    if name == "web_search":
        return {
            "ok": True,
            "citations": [
                {
                    "url": "https://ex.com/a",
                    "title": "NVIDIA quarterly results",
                    "excerpt": "NVDA revenue grew",
                    "source": "ex.com",
                }
            ],
        }
    # structured legs (fundamentals / news / price_data / sec_filings_list)
    return {"ok": True, "provider": "test"}


def test_iter_returns_brief_mode_deep() -> None:
    brief = _run(
        run_iter_research(
            "research NVDA",
            tool_call=fake_tool,
            llm_call=FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=2),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.mode == "deep"
    assert brief.markdown.strip()
    assert brief.source_count >= 1


def test_iter_starved_wall_winds_down_cleanly_not_an_abort() -> None:
    """R8 graceful guard (a): with under MIN_ROUND_WALL_SECS of wall budget a
    fresh round never starts — the run closes through the CLEAN synthesis path
    (note=None, never a 'wall-clock guard' banner in the user's face), and the
    dev step trace records why."""

    class SlowLLM:
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            await asyncio.sleep(0.05)
            return "x"

    brief = _run(
        run_iter_research(
            "research NVDA",
            tool_call=fake_tool,
            llm_call=SlowLLM(),
            budget=BudgetGuard(max_wall_seconds=0.5),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()  # the run still ships a brief
    assert brief.note is None  # CLEAN completion — no guard trace as a note
    assert any("stopped before a new round" in s.detail for s in brief.steps)


def test_iter_context_is_reconstructed_not_appended() -> None:
    """The KEY IterResearch property: a later round's plan context carries the
    distilled report + only the latest round's evidence — NOT the full history."""
    llm = FakeLLM(distill="DISTILLED_REPORT", reflect="gaps remain")  # never "complete"
    _run(
        run_iter_research(
            "research NVDA",
            tool_call=fake_tool,
            llm_call=llm,
            budget=BudgetGuard(max_steps=3),  # exactly 3 rounds, then abort→synthesize
        )
    )
    assert len(llm.plan_prompts) == 3
    round3 = llm.plan_prompts[2]
    # Round 3 sees the distilled report …
    assert "DISTILLED_REPORT" in round3
    # … and the LATEST round's findings (round 2 = FIND#4..6) …
    assert "FIND#4" in round3
    # … but NOT round 1's raw findings (FIND#1) — the history was distilled away.
    assert "FIND#1" not in round3


def test_iter_report_render_is_capped() -> None:
    """A chatty distill model can't blow the working context — render() is capped."""
    huge = "X" * (_REPORT_CHAR_CAP * 3)
    llm = FakeLLM(distill=huge, reflect="gaps remain")
    _run(
        run_iter_research(
            "q",
            tool_call=fake_tool,
            llm_call=llm,
            budget=BudgetGuard(max_steps=2),
        )
    )
    # The round-2 plan prompt embeds report.render(); it must be bounded.
    assert len(llm.plan_prompts[1]) < _REPORT_CHAR_CAP * 2


def test_iter_distill_empty_keeps_shipping() -> None:
    """An empty distill (dead/echoing model) keeps the prior report and still ships."""
    brief = _run(
        run_iter_research(
            "q",
            tool_call=fake_tool,
            llm_call=FakeLLM(distill="", reflect="complete"),
            budget=BudgetGuard(max_steps=2),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()


def test_iter_budget_breach_aborts_to_synthesis_never_raises() -> None:
    """A budget that is already breached aborts to a synthesized brief, not a raise.
    The note is the HUMAN budget-stop sentence; the raw ceiling reason lives on
    the dev step trace only (R8)."""
    from services.research.deep import BUDGET_STOP_NOTE

    brief = _run(
        run_iter_research(
            "q",
            tool_call=fake_tool,
            llm_call=FakeLLM(),
            budget=BudgetGuard(max_steps=0),  # breached on the first top-of-round check
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.note == BUDGET_STOP_NOTE
    assert any("step ceiling" in s.detail for s in brief.steps)  # raw reason = dev detail


def test_iter_emits_distill_step() -> None:
    steps: list[ResearchStep] = []
    _run(
        run_iter_research(
            "q",
            tool_call=fake_tool,
            llm_call=FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=2),
            on_step=steps.append,
        )
    )
    kinds = [s.kind for s in steps]
    assert "distill" in kinds
    assert "plan" in kinds and "synthesize" in kinds


# --- Heavy mode (the expert panel) -----------------------------------------


def test_heavy_spawns_angles_and_synthesizes_merged_sources() -> None:
    brief = _run(
        run_heavy_research(
            "investment thesis for NVDA",
            angles=3,
            tool_call=fake_tool,
            llm_call=FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=12),
        )
    )
    assert isinstance(brief, ResearchBrief)
    # R8: the "heavy:N angles" implementation note is GONE — brief.note renders
    # to the user; the angle trace rides structured["panel"] instead.
    assert brief.note is None
    assert [p["angle"] for p in brief.structured["panel"]] == [1, 2, 3]
    # The merged brief carries the ORIGINAL query + the bound symbol — never the
    # focus-augmented explorer task text.
    assert brief.query == "investment thesis for NVDA"
    assert brief.symbol == "NVDA"
    # All angles cited the same web url; the merged source list de-dupes it to one.
    web_urls = [s.url for s in brief.sources if s.url == "https://ex.com/a"]
    assert len(web_urls) == 1
    assert brief.markdown.strip()
    # WS3: the heavy/panel path reconciles web_available with the merged source
    # count (= any(angle.web_available) or bool(merged_sources)). A panel brief
    # that cites N merged sources must report web_available True so it never fires
    # the "web unavailable" banner alongside its sources (symptom #2).
    assert brief.web_available is True


def test_heavy_emits_angle_tagged_steps() -> None:
    steps: list[ResearchStep] = []
    _run(
        run_heavy_research(
            "thesis",
            angles=3,
            tool_call=fake_tool,
            llm_call=FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=12),
            on_step=steps.append,
        )
    )
    # Each explorer's steps are tagged with their angle so the surface shows the
    # parallel exploration.
    tagged = [s for s in steps if s.detail.startswith("[angle ")]
    assert tagged, "expected angle-tagged explorer steps"


def test_heavy_one_angle_crash_still_synthesizes(monkeypatch: pytest.MonkeyPatch) -> None:
    """If one explorer raises, the panel synthesizes from the survivors."""
    calls = {"n": 0}
    real = iter_research.run_iter_research

    async def _flaky(query, **kwargs):  # noqa: ANN001, ANN003
        calls["n"] += 1
        if calls["n"] == 2:  # the second angle blows up
            raise RuntimeError("angle exploded")
        return await real(query, **kwargs)

    monkeypatch.setattr(iter_research, "run_iter_research", _flaky)

    brief = _run(
        run_heavy_research(
            "thesis",
            angles=3,
            tool_call=fake_tool,
            llm_call=FakeLLM(reflect="complete"),
            budget=BudgetGuard(max_steps=12),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()  # synthesized from the 2 survivors


def test_heavy_never_raises_on_dead_llm() -> None:
    """A fully dead LLM (every completion empty) still ships a brief — no raise."""

    async def _dead(_messages: list[dict[str, Any]]) -> str:
        return ""

    brief = _run(
        run_heavy_research(
            "thesis",
            angles=3,
            tool_call=fake_tool,
            llm_call=_dead,
            budget=BudgetGuard(max_steps=12),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()


async def _ambiguous_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
    if name == "resolve_symbol":
        return {
            "ok": True,
            "query": args.get("query"),
            "status": "disambiguate",
            "reason": "marquee family name",
            "resolved": None,
            "needs_disambiguation": True,
            "candidates": [
                {
                    "symbol": "TCS",
                    "name": "Tata Consultancy Services Limited",
                    "exchange": "NSE",
                    "confidence": 0.6,
                    "yahoo_symbol": "TCS.NS",
                }
            ],
            "message": "which did you mean?",
        }
    raise AssertionError(f"no tool but the resolver may run on an ambiguous query: {name}")


def test_iter_disambiguation_returns_chooser_with_zero_spend() -> None:
    # R10 (D37): the iter loop returns the chooser dict before any round runs.
    out = _run(
        run_iter_research(
            "tata results",
            region="IN",
            tool_call=_ambiguous_tool,
            llm_call=FakeLLM(),
            budget=BudgetGuard(max_steps=10),
        )
    )
    assert isinstance(out, dict)
    assert out["ok"] is True and out["needs_disambiguation"] is True
    assert out["candidates"][0]["symbol"] == "TCS"


def test_heavy_disambiguation_returns_chooser_before_fanout() -> None:
    out = _run(
        run_heavy_research(
            "tata results",
            angles=3,
            region="IN",
            tool_call=_ambiguous_tool,
            llm_call=FakeLLM(),
            budget=BudgetGuard(max_steps=12),
        )
    )
    assert isinstance(out, dict)
    assert out["ok"] is True and out["needs_disambiguation"] is True
    assert out["query"] == "tata results"


def test_iter_synthesis_prompt_carries_metric_facts() -> None:
    # R10 (E8): the derived METRIC FACTS block rides the synthesis prompt so
    # the prose states figures under the cards' labels and bases.
    class _RecordingLLM(FakeLLM):
        def __init__(self) -> None:
            super().__init__(reflect="complete")
            self.synthesis_prompts: list[str] = []

        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            system = messages[0]["content"].lower()
            if "concise research brief" in system:
                self.synthesis_prompts.append(messages[-1]["content"])
            return await super().__call__(messages)

    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "resolve_symbol":
            return {
                "ok": True,
                "status": "bound",
                "resolved": {
                    "symbol": "NVDA",
                    "name": "NVIDIA Corporation",
                    "exchange": "NASDAQ",
                    "region": "US",
                    "asset_class": "equity",
                    "confidence": 1.0,
                },
            }
        if name == "price_data":
            return {"ok": True, "provider": "yfinance", "quote": {"price": 80.0}}
        if name == "fundamentals":
            return {
                "ok": True,
                "fundamentals": {"fifty_two_week_high": 100.0, "provider": "yfinance"},
            }
        return await fake_tool(name, args)

    llm = _RecordingLLM()
    brief = _run(
        run_iter_research(
            "NVDA outlook",
            tool_call=tool,
            llm_call=llm,
            budget=BudgetGuard(max_steps=2),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.structured["derived"]["provider"] == "derived"
    assert llm.synthesis_prompts, "synthesis never ran"
    assert any("METRIC FACTS" in p and "Below 52-week high" in p for p in llm.synthesis_prompts)


def test_run_loop_deep_fallback_is_never_silent(monkeypatch):
    """R10 review (E2 — stamp what RAN): if ``run_iter_research`` ever raises,
    ``_run_loop`` drops to the single-pass ``run_deep_research`` fallback. The
    closed EXECUTION_LOOPS enum has no label for that path, so the degradation
    must ride the brief's never-silent ``note`` channel."""
    from services.agent_tools import deep_research as deep_research_tool
    from services.research import deep
    from services.research.depth import profile_for

    async def boom(query: str, **kwargs: Any) -> ResearchBrief:
        raise RuntimeError("iter exploded")

    async def fake_deep(query: str, **kwargs: Any) -> ResearchBrief:
        return ResearchBrief(query=query, symbol="", mode="deep", markdown="fallback brief")

    monkeypatch.setattr(iter_research, "run_iter_research", boom)
    monkeypatch.setattr(deep, "run_deep_research", fake_deep)

    async def llm(messages: list[dict[str, Any]]) -> str:
        return "unused"

    brief = _run(
        deep_research_tool._run_loop(
            profile=profile_for("deep"), query="q", llm_call=llm, rounds=1, wall=120
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.note is not None and "fallback" in brief.note
