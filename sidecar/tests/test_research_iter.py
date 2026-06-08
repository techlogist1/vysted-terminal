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
        return {"ok": True, "resolved": {"symbol": "NVDA"}}
    if name == "web_search":
        return {
            "ok": True,
            "citations": [
                {"url": "https://ex.com/a", "title": "A", "excerpt": "x", "source": "ex.com"}
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


def test_iter_per_round_wall_guard_aborts_not_hangs() -> None:
    """The slow-fallback fix: a round whose LLM calls outlive the wall slice is
    cut by the per-round ``asyncio.timeout`` guard and aborts→synthesizes — the
    run STILL returns a brief (never the 8-minutes-unfinished hang)."""

    class SlowLLM:
        async def __call__(self, messages: list[dict[str, Any]]) -> str:
            # Much longer than the tiny per-round wall slice below (a stand-in for
            # a heavy "thinking" model streaming for minutes).
            await asyncio.sleep(0.3)
            return "x"

    # A small-but-nonzero wall budget: the round-1 top-of-round breach passes
    # (~0s elapsed), then the per-round guard fires inside the first LLM call.
    brief = _run(
        run_iter_research(
            "research NVDA",
            tool_call=fake_tool,
            llm_call=SlowLLM(),
            budget=BudgetGuard(max_wall_seconds=0.05),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()  # abort→synthesize still ships a brief
    assert brief.note is not None and "wall-clock guard" in brief.note


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
    """A budget that is already breached aborts to a synthesized brief, not a raise."""
    brief = _run(
        run_iter_research(
            "q",
            tool_call=fake_tool,
            llm_call=FakeLLM(),
            budget=BudgetGuard(max_steps=0),  # breached on the first top-of-round check
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.note is not None  # the abort reason is stamped
    assert "step ceiling" in brief.note


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
    assert brief.note is not None and brief.note.startswith("heavy:")
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
