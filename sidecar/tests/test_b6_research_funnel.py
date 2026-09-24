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


def _target(symbol: str, region: str, exchange: str) -> Any:
    from services.research.target import ResearchTarget

    return ResearchTarget(
        symbol=symbol,
        name=f"{symbol} Limited",
        exchange=exchange,
        asset_class="equity",
        confidence=1.0,
        region=region,
    )


def _researcher_tools(sub_question: str, target: Any) -> list[str]:
    called: list[str] = []

    async def tool_call(name: str, _args: dict[str, Any]) -> dict[str, Any]:
        called.append(name)
        return {"ok": False, "error": "stub"}

    async def llm(_messages: list[dict[str, Any]]) -> str:
        return "finding"

    asyncio.run(
        deep._run_researcher(
            sub_question, target=target, query="q", region=None, tool_call=tool_call, llm_call=llm
        )
    )
    return called


def test_india_filings_question_never_queries_edgar() -> None:
    """R15-RESEARCH-018: an NSE listing's insider/SEC-shaped sub-question reads the
    exchange announcements feed, never sec_filings_list."""
    called = _researcher_tools(
        "insider activity and sec disclosures", _target("ROUTE", "IN", "NSE")
    )
    assert "sec_filings_list" not in called
    assert "corporate_announcements" in called


def test_sec_is_matched_as_a_whole_word() -> None:
    """R15-RESEARCH-018: 'second'/'sector' no longer land in the filings bucket,
    while a US 'SEC' question still does."""
    us = _target("AAPL", "US", "NASDAQ")
    assert "sec_filings_list" not in _researcher_tools("second-half outlook", us)
    assert "sec_filings_list" not in _researcher_tools("sector outlook", us)
    assert "sec_filings_list" in _researcher_tools("recent SEC activity", us)
