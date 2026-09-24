"""Batch-7 research-funnel pins: failed visits and crashed explorers leave steps."""

from __future__ import annotations

import asyncio
from typing import Any

from services.budget_guard import BudgetGuard
from services.research import iter as iter_research
from services.research.models import ResearchBrief
from services.research.target import ResearchTarget


def _target(symbol: str, region: str, exchange: str) -> ResearchTarget:
    return ResearchTarget(
        symbol=symbol,
        name=f"{symbol} Limited",
        exchange=exchange,
        asset_class="equity",
        confidence=1.0,
        region=region,
    )


async def _llm(_messages: list[dict[str, Any]]) -> str:
    return "COMPLETE"


def test_a_403_visit_is_recorded_as_an_error_step(monkeypatch) -> None:
    """R15-RESEARCH-019: a primary page behind an anti-bot 403 leaves an error
    step naming the reason instead of silently vanishing from the run."""
    from services.search import extract

    async def forbidden(url: str, *, max_chars: int) -> dict[str, Any]:
        return {"ok": False, "url": url, "error": "HTTP 403"}

    monkeypatch.setattr(extract, "fetch_page", forbidden)

    async def tool_call(name: str, _args: dict[str, Any]) -> dict[str, Any]:
        if name == "web_search":
            return {
                "ok": True,
                "results": [{"url": "https://ir.example.com/q4", "title": "AAPL Q4 results"}],
            }
        return {"ok": False, "error": "stub"}

    brief = asyncio.run(
        iter_research.run_iter_research(
            "AAPL results",
            tool_call=tool_call,
            llm_call=_llm,
            budget=BudgetGuard(max_steps=6),
            visit=extract.visit_for_research,
            target=_target("AAPL", "US", "NASDAQ"),
            bound=True,
        )
    )
    failed = [s for s in brief.steps if s.status == "error" and "visit failed" in s.detail]
    assert failed
    assert "https://ir.example.com/q4" in failed[0].detail
    assert "HTTP 403" in failed[0].detail


def test_a_crashed_ultra_explorer_leaves_an_error_step(monkeypatch) -> None:
    """R15-RESEARCH-033: a raising explorer is named in an error step, not dropped."""
    calls: list[str] = []

    async def explorer(task: str, **_kw: Any) -> ResearchBrief:
        calls.append(task)
        if len(calls) == 2:
            raise ValueError("angle two exploded")
        return ResearchBrief(query=task, symbol="AAPL", mode="deep", markdown="## angle")

    monkeypatch.setattr(iter_research, "run_iter_research", explorer)

    async def tool_call(_name: str, _args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": False, "error": "stub"}

    async def silent(_messages: list[dict[str, Any]]) -> str:
        return ""

    emitted: list[Any] = []
    brief = asyncio.run(
        iter_research.run_heavy_research(
            "AAPL thesis",
            angles=2,
            tool_call=tool_call,
            llm_call=silent,
            budget=BudgetGuard(max_steps=20),
            on_step=emitted.append,
            target=_target("AAPL", "US", "NASDAQ"),
            bound=True,
        )
    )
    assert isinstance(brief, ResearchBrief)
    crashed = [s for s in brief.steps if s.status == "error" and "angle 2" in s.detail]
    assert len(crashed) == 1
    assert "ValueError: angle two exploded" in crashed[0].detail
    assert crashed[0] in emitted
