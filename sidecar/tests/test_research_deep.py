"""Tests for ``services.research.deep.run_deep_research`` — the bounded loop.

No network, no real LLM: ``tool_call`` and ``llm_call`` are fakes returning
canned dicts / strings. The tests assert (a) a normal run produces a
``ResearchBrief`` with markdown + sources + steps; (b) a TINY budget forces
abort→synthesize on the FIRST breach and STILL returns a brief (never raises),
with ``note`` set to the breach reason; (c) the coverage floor gates "complete";
and (d) steps are recorded via ``on_step``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.budget_guard import BudgetGuard
from services.research import deep
from services.research.deep import run_deep_research
from services.research.models import ResearchBrief, ResearchStep


class _FakeLLM:
    """Canned one-shot completions, keyed by the role-marker in the prompt.

    ``reflect_complete`` toggles whether the reflect turn declares coverage
    complete (lets a test drive a one-round clean finish vs. keep-going).
    """

    def __init__(self, *, reflect_complete: bool = True) -> None:
        self.reflect_complete = reflect_complete
        self.calls = 0

    async def __call__(self, messages: list[dict[str, Any]]) -> str:
        self.calls += 1
        system = ""
        for m in messages:
            if m.get("role") == "system":
                system = str(m.get("content", "")).lower()
                break
        if "planning a research run" in system:
            return "- What is the price trend?\n- What do fundamentals say?\n- What is the news?"
        if "reflect on research coverage" in system:
            return "Coverage is COMPLETE." if self.reflect_complete else "GAP: more news needed."
        if "research analyst" in system:
            return "Finding: the data supports a stable outlook."
        if "write a concise research brief" in system:
            return "# Brief\n\nApple looks stable [1]. Fundamentals are solid [2]."
        return "ok"


def _web_result() -> dict[str, Any]:
    return {
        "ok": True,
        "backend": "exa",
        "results": [{"url": "https://news.example/a", "title": "A", "snippet": "s"}],
        "citations": [{"url": "https://news.example/a", "title": "A", "excerpt": "e"}],
    }


class _FakeToolCall:
    """Canned ``tool_call`` covering resolve + the structured legs + web."""

    def __init__(self, *, web_ok: bool = True) -> None:
        self.web_ok = web_ok
        self.calls: list[str] = []

    async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(name)
        await asyncio.sleep(0)
        if name == "resolve_symbol":
            return {
                "ok": True,
                "resolved": {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "asset_class": "equity",
                },
            }
        if name == "price_data":
            return {"ok": True, "symbol": "AAPL", "provider": "yfinance", "quote": {"price": 1.0}}
        if name == "fundamentals":
            return {"ok": True, "fundamentals": {"pe_ratio": 30.0}, "provider": "openbb"}
        if name == "news":
            return {"ok": True, "count": 1, "news": [{"headline": "x"}], "provider": "news"}
        if name == "sec_filings_list":
            return {"ok": True, "filings": {"items": []}, "provider": "sec-edgar"}
        if name == "web_search":
            return _web_result() if self.web_ok else {"ok": False, "message": "no backend"}
        return {"ok": False, "error": f"unexpected {name}"}


def _collect_steps() -> tuple[list[ResearchStep], Any]:
    captured: list[ResearchStep] = []

    def sink(step: ResearchStep) -> None:
        captured.append(step)

    return captured, sink


def test_deep_normal_run_produces_brief() -> None:
    llm = _FakeLLM(reflect_complete=True)
    tools = _FakeToolCall(web_ok=True)
    captured, sink = _collect_steps()
    budget = BudgetGuard(max_steps=10)

    brief = asyncio.run(
        run_deep_research(
            "Apple outlook",
            region="US",
            tool_call=tools,
            llm_call=llm,
            budget=budget,
            on_step=sink,
        )
    )

    assert isinstance(brief, ResearchBrief)
    assert brief.mode == "deep"
    assert brief.symbol == "AAPL"
    assert brief.markdown.strip()
    assert brief.note is None  # clean finish, no breach
    assert brief.source_count == len(brief.sources)
    assert brief.sources  # web + structured provenance gathered
    assert brief.web_available is True
    assert brief.cost["steps"] >= 1

    # Steps recorded via on_step across the stages.
    kinds = {s.kind for s in captured}
    assert {"plan", "tool", "compress", "reflect", "synthesize"} <= kinds
    assert captured == brief.steps  # the sink saw exactly what's on the brief

    # to_dict round-trips cleanly (serialisable).
    d = brief.to_dict()
    assert d["mode"] == "deep"
    assert isinstance(d["sources"], list)
    assert isinstance(d["steps"], list)


def test_deep_tiny_step_budget_aborts_to_synthesize() -> None:
    """max_steps=1: the top-of-round gate trips on the SECOND round's check.

    Round 1 records one step (steps=1). Round 2's top-of-round ``breach()`` sees
    steps>=1 and forces abort→synthesize. The run STILL returns a brief and never
    raises; ``note`` carries the breach reason.
    """
    llm = _FakeLLM(reflect_complete=False)  # never "complete" -> would loop forever
    tools = _FakeToolCall(web_ok=True)
    captured, sink = _collect_steps()
    budget = BudgetGuard(max_steps=1)

    brief = asyncio.run(
        run_deep_research(
            "Apple",
            region="US",
            tool_call=tools,
            llm_call=llm,
            budget=budget,
            on_step=sink,
        )
    )

    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()  # a brief, never empty
    assert brief.note is not None
    assert "step ceiling" in brief.note
    # The final step is the abort→synthesize.
    assert brief.steps[-1].kind == "synthesize"
    assert "abort" in brief.steps[-1].detail


def test_deep_zero_wall_budget_aborts_on_first_breach() -> None:
    """max_wall_seconds=0: breached on the very FIRST top-of-round check, before
    any round runs — still returns a brief, note set, zero researcher steps."""
    llm = _FakeLLM(reflect_complete=True)
    tools = _FakeToolCall(web_ok=True)
    budget = BudgetGuard(max_wall_seconds=0)

    brief = asyncio.run(
        run_deep_research(
            "Apple",
            region="US",
            tool_call=tools,
            llm_call=llm,
            budget=budget,
        )
    )

    assert isinstance(brief, ResearchBrief)
    assert brief.note is not None
    assert "wall-clock ceiling" in brief.note
    # Only the synthesize step ran (immediate abort before the first plan).
    assert [s.kind for s in brief.steps] == ["synthesize"]
    assert brief.markdown.strip()


def test_deep_coverage_floor_blocks_premature_complete() -> None:
    """Even when reflect SAYS complete, a missing web source blocks the break.

    With ``web_ok=False`` the web COVERAGE dimension never gets a web source, so
    the coverage floor is never met. The loop therefore can't finish cleanly — it
    runs until the step budget aborts it. The brief still ships (abort→synthesize)
    and the web coverage dimension was indeed never covered.
    """
    llm = _FakeLLM(reflect_complete=True)  # model claims done every round
    tools = _FakeToolCall(web_ok=False)  # but web never yields a source
    budget = BudgetGuard(max_steps=3)

    brief = asyncio.run(
        run_deep_research(
            "Apple",
            region="US",
            tool_call=tools,
            llm_call=llm,
            budget=budget,
        )
    )

    assert isinstance(brief, ResearchBrief)
    # The floor was never met -> the run was cut by the budget, not a clean break.
    assert brief.note is not None
    assert "ceiling" in brief.note
    # WS3: web COVERAGE was never met, but the structured legs still produced
    # cited sources — so web_available is reconciled to True (a brief that cites N
    # sources must NOT also claim the web was unavailable / symptom #2). The honest
    # "structured data only" banner is reserved for a brief with ZERO sources.
    assert brief.source_count > 0
    assert brief.web_available is True


def test_deep_zero_sources_keeps_honest_structured_only_flag() -> None:
    """WS3: the honest structured-only flag is PRESERVED when truly zero sources.

    Every leg (structured + web) misses, so ``all_sources()`` is empty and
    ``source_count == 0``. Then — and only then — ``web_available`` stays False so
    the panel can fire the honest "no web sources found" banner. This is the
    legitimate affordance the WS3 reconciliation must NOT delete.
    """

    class _AllLegsMiss(_FakeToolCall):
        async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
            self.calls.append(name)
            await asyncio.sleep(0)
            if name == "resolve_symbol":
                return await super().__call__(name, args)
            # Every gather leg (structured + web) is a clean miss → no source.
            return {"ok": False, "error": f"{name} unavailable"}

    llm = _FakeLLM(reflect_complete=True)
    tools = _AllLegsMiss(web_ok=False)
    budget = BudgetGuard(max_steps=3)

    brief = asyncio.run(
        run_deep_research(
            "Apple",
            region="US",
            tool_call=tools,
            llm_call=llm,
            budget=budget,
        )
    )

    assert isinstance(brief, ResearchBrief)
    assert brief.source_count == 0
    assert not brief.sources
    # Honest structured-only state survives: zero sources => web_available False.
    assert brief.web_available is False


def test_deep_clean_finish_when_floor_and_reflect_agree() -> None:
    """web_ok + reflect_complete + room in the budget => clean finish, no note."""
    llm = _FakeLLM(reflect_complete=True)
    tools = _FakeToolCall(web_ok=True)
    budget = BudgetGuard(max_steps=20)

    brief = asyncio.run(
        run_deep_research(
            "Apple",
            region="US",
            tool_call=tools,
            llm_call=llm,
            budget=budget,
        )
    )

    assert brief.note is None
    assert brief.steps[-1].kind == "synthesize"
    assert "abort" not in brief.steps[-1].detail


def test_deep_never_raises_on_dead_llm() -> None:
    """A totally dead llm_call still yields a brief (deterministic fallback)."""

    async def dead_llm(messages: list[dict[str, Any]]) -> str:
        raise RuntimeError("provider down")

    tools = _FakeToolCall(web_ok=True)
    budget = BudgetGuard(max_steps=2)

    brief = asyncio.run(
        run_deep_research(
            "Apple",
            region="US",
            tool_call=tools,
            llm_call=dead_llm,
            budget=budget,
        )
    )

    assert isinstance(brief, ResearchBrief)
    assert brief.markdown.strip()  # the deterministic fallback fired


def test_safe_llm_per_call_guard_returns_empty_on_overrun(monkeypatch: pytest.MonkeyPatch) -> None:
    """The universal mid-call wall guard: a single inner LLM call that outlives the
    per-call cap yields '' (so the loop degrades to abort→synthesize) instead of
    hanging the round — the hang-prevention backstop for any swapped-in model,
    including a 'thinking' one whose injected call path carries no timeout."""
    monkeypatch.setattr(deep, "_LLM_CALL_TIMEOUT_SECS", 0.05)

    async def slow(_messages: list[dict[str, Any]]) -> str:
        await asyncio.sleep(5)  # far past the tiny cap — would hang the round without the guard
        return "should never arrive"

    out = asyncio.run(deep._safe_llm(slow, [{"role": "user", "content": "x"}]))
    assert out == ""
