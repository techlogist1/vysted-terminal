"""Batch-6 research-funnel pins (R15 register entries named per test)."""

from __future__ import annotations

import asyncio
from typing import Any

from services.agent_tools import deep_research
from services.budget_guard import BudgetGuard
from services.research import deep
from services.research import iter as iter_research
from services.research.depth import PROFILES
from services.research.models import ResearchBrief


def test_ultra_heavy_raise_falls_back_to_single_pass_with_note(monkeypatch) -> None:
    """R15-RESEARCH-017: a raising run_heavy_research degrades like DEEP does."""

    async def boom(*_a: Any, **_k: Any) -> Any:
        raise RuntimeError("panel synthesis exploded")

    async def single_pass(query: str, **_k: Any) -> ResearchBrief:
        return ResearchBrief(query=query, symbol="X", mode="deep", markdown="## brief")

    monkeypatch.setattr(iter_research, "run_heavy_research", boom)
    monkeypatch.setattr(deep, "run_deep_research", single_pass)

    async def llm(_messages: list[dict[str, Any]]) -> str:
        return ""

    brief = asyncio.run(
        deep_research._run_loop(
            profile=PROFILES["ultra"],
            query="research X",
            llm_call=llm,
            budget=BudgetGuard(max_steps=4),
        )
    )
    assert isinstance(brief, ResearchBrief)
    assert brief.markdown == "## brief"
    assert brief.note == "heavy loop raised; the single-pass deep fallback ran"
