"""Tests for the R8 disclosures dimension — exchange feeds inside research.

The live failure: research never consulted the in-house disclosure tools, so a
ROUTE earnings question concluded "no quarterly results announced" while the
2026-05-07 "Financial Results/Dividend" board meeting sat in the calendar feed
and the results PDF sat in the announcements feed.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.research import disclosures
from services.research.deep import _run_researcher
from services.research.target import target_from_payload


def _run(coro):
    return asyncio.run(coro)


def _india_target(symbol: str = "ROUTE", name: str = "Route Mobile Limited"):
    target = target_from_payload(
        {
            "ok": True,
            "resolved": {
                "symbol": symbol,
                "name": name,
                "exchange": "NSE",
                "region": "IN",
                "asset_class": "equity",
                "confidence": 0.95,
            },
        }
    )
    assert target is not None
    return target


def _us_target():
    target = target_from_payload(
        {
            "ok": True,
            "resolved": {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "exchange": "NASDAQ",
                "region": "US",
                "asset_class": "equity",
                "confidence": 0.98,
            },
        }
    )
    assert target is not None
    return target


_ANNOUNCEMENTS_OK: dict[str, Any] = {
    "ok": True,
    "symbol": "ROUTE",
    "exchange": None,
    "sources": ["NSE", "BSE"],
    "errors": {},
    "count": 2,
    "announcements": [
        {
            "symbol": "ROUTE",
            "exchange": "NSE",
            "headline": "Outcome of board meeting — financial results Q4 FY26",
            "category": "Financial Results",
            "attachment_url": "https://nsearchives.nseindia.com/corporate/ROUTE_results.pdf",
            "ts": "2026-05-07T18:02:00+05:30",
        },
        {
            "symbol": "ROUTE",
            "exchange": "BSE",
            "headline": "Earnings call transcript",
            "category": "Company Update",
            "attachment_url": None,
            "ts": "2026-05-08T10:00:00+05:30",
        },
    ],
}


# --- classification ------------------------------------------------------------


def test_question_shapes() -> None:
    assert disclosures.is_disclosure_question("What did the Q4 results say?")
    assert disclosures.is_disclosure_question("Any dividend announced?")
    assert disclosures.is_disclosure_question("Summarise the earnings call transcript")
    assert not disclosures.is_disclosure_question("What is the price trend?")

    assert disclosures.is_earnings_date_question("When are the next quarterly results?")
    assert disclosures.is_earnings_date_question("What is the date of the earnings call?")
    assert not disclosures.is_earnings_date_question("How did margins trend this quarter?")


def test_wants_disclosures_is_india_gated() -> None:
    q = "What were the latest quarterly results?"
    assert disclosures.wants_disclosures(_india_target(), q) is True
    assert disclosures.wants_disclosures(_us_target(), q) is False
    assert disclosures.wants_disclosures(None, q) is False
    assert disclosures.wants_disclosures(_india_target(), "price trend?") is False


def test_plan_hint_only_for_india() -> None:
    assert "Exchange disclosures" in disclosures.plan_hint(_india_target())
    assert disclosures.plan_hint(_us_target()) == ""
    assert disclosures.plan_hint(None) == ""


# --- row mapping ---------------------------------------------------------------


def test_announcement_rows_become_verified_filing_sources() -> None:
    rows = disclosures.announcement_rows(_ANNOUNCEMENTS_OK, symbol="ROUTE")
    # Only the attachment-bearing item is citable/visitable.
    assert len(rows) == 1
    row = rows[0]
    assert row["url"] == "https://nsearchives.nseindia.com/corporate/ROUTE_results.pdf"
    assert row["title"].startswith("Outcome of board meeting")
    assert row["verified_symbol"] == "ROUTE"
    assert row["source_type"] == "filing"


def test_announcement_rows_rank_on_the_exchange_tier() -> None:
    from services.research import finance

    [row] = disclosures.announcement_rows(_ANNOUNCEMENTS_OK, symbol="ROUTE")
    assert finance.domain_tier(row["url"]) == finance.TIER_PRIMARY


def test_announcement_rows_on_a_miss_are_empty() -> None:
    assert disclosures.announcement_rows({"ok": False, "error": "down"}, symbol="ROUTE") == []
    assert disclosures.announcement_rows({}, symbol="ROUTE") == []


# --- gather ----------------------------------------------------------------------


def test_gather_pulls_announcements_and_calendar(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        calls.append((name, args))
        return _ANNOUNCEMENTS_OK

    async def fake_calendar(symbol: str) -> dict[str, Any]:
        assert symbol == "ROUTE"
        return {
            "ok": True,
            "symbol": "ROUTE",
            "count": 1,
            "events": [
                {
                    "symbol": "ROUTE",
                    "purpose": "Financial Results/Dividend",
                    "description": "Board meeting",
                    "date": "2026-05-07",
                }
            ],
        }

    monkeypatch.setattr(disclosures, "fetch_results_calendar", fake_calendar)
    bundle = _run(
        disclosures.gather(
            tool, target=_india_target(), sub_question="When are the next quarterly results?"
        )
    )
    assert calls[0][0] == "corporate_announcements"
    assert calls[0][1]["symbol"] == "ROUTE"
    assert bundle["announcements"] is not None
    assert len(bundle["rows"]) == 1
    # The calendar's meeting rides the prompt context for date questions.
    assert "2026-05-07" in bundle["context"]
    assert "Financial Results/Dividend" in bundle["context"]
    assert "Outcome of board meeting" in bundle["context"]


def test_gather_skips_calendar_for_non_date_questions(monkeypatch: pytest.MonkeyPatch) -> None:
    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        return _ANNOUNCEMENTS_OK

    async def explode(symbol: str) -> dict[str, Any]:
        raise AssertionError("calendar must not be consulted for a non-date question")

    monkeypatch.setattr(disclosures, "fetch_results_calendar", explode)
    bundle = _run(
        disclosures.gather(tool, target=_india_target(), sub_question="Summarise the results")
    )
    assert bundle["calendar"] is None


def test_gather_survives_a_dead_tool() -> None:
    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        raise RuntimeError("registry down")

    bundle = _run(disclosures.gather(tool, target=_india_target(), sub_question="latest results?"))
    assert bundle["rows"] == []
    assert bundle["announcements"] is None


# --- researcher integration ------------------------------------------------------


class _Tool:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(name)
        if name == "corporate_announcements":
            return _ANNOUNCEMENTS_OK
        if name == "web_search":
            return {
                "ok": True,
                "citations": [
                    {
                        "url": "https://moneycontrol.com/route-q4",
                        "title": "Route Mobile Q4 results",
                        "excerpt": "x",
                    }
                ],
            }
        return {"ok": True, "provider": "test"}


async def _llm(messages: list[dict[str, Any]]) -> str:
    return "Finding."


def test_researcher_consults_disclosures_for_india_results_question() -> None:
    tool = _Tool()
    visited: list[str] = []

    async def visit(url: str) -> str:
        visited.append(url)
        return "Revenue Rs 1,234 crore for the quarter."

    finding, web_res, pairs, visited_pages = _run(
        _run_researcher(
            "What did the latest quarterly results announce?",
            target=_india_target(),
            query="Route Mobile",
            region="IN",
            tool_call=tool,
            llm_call=_llm,
            visit=visit,
        )
    )
    assert "corporate_announcements" in tool.calls
    # The attachment PDF is a first-class citation row AND the visited page.
    urls = [row["url"] for row in web_res["citations"]]
    assert "https://nsearchives.nseindia.com/corporate/ROUTE_results.pdf" in urls
    assert visited == ["https://nsearchives.nseindia.com/corporate/ROUTE_results.pdf"]
    # The announcements pull records news-dimension coverage.
    assert any(p["dim"] == "news" and p["result"].get("announcements") for p in pairs)


def test_researcher_skips_disclosures_for_us_target() -> None:
    tool = _Tool()
    _run(
        _run_researcher(
            "What did the latest quarterly results announce?",
            target=_us_target(),
            query="Apple",
            region="US",
            tool_call=tool,
            llm_call=_llm,
        )
    )
    assert "corporate_announcements" not in tool.calls


def test_results_filing_outranks_newer_procedural_intimations() -> None:
    # The live R8 gate-1 failure: the Q4 results outcome sat at feed index 14
    # behind a stack of newer intimations, so the researcher's one visit read a
    # procedural PDF and the brief said "content remains unextracted". For a
    # results-shaped question the results-payload headline must rank FIRST.
    feed = {
        "ok": True,
        "announcements": [
            {
                "exchange": "NSE",
                "headline": "Intimation of analyst call audio recording",
                "category": "Company Update",
                "attachment_url": "https://nsearchives.nseindia.com/corporate/AUDIO.pdf",
                "ts": "2026-05-22",
            },
            {
                "exchange": "NSE",
                "headline": "Copy of newspaper publication",
                "category": "Company Update",
                "attachment_url": "https://nsearchives.nseindia.com/corporate/NEWSPAPER.pdf",
                "ts": "2026-05-09",
            },
            {
                "exchange": "NSE",
                "headline": (
                    "ROUTE MOBILE LIMITED has submitted to the Exchange, "
                    "the financial results for the period ended March 31, 2026"
                ),
                "category": "Financial Results",
                "attachment_url": "https://nsearchives.nseindia.com/corporate/OUTCOME.pdf",
                "ts": "2026-05-07",
            },
        ],
    }
    rows = disclosures.announcement_rows(
        feed, symbol="ROUTE", sub_question="What were the latest quarterly results?"
    )
    assert rows[0]["url"].endswith("OUTCOME.pdf")
    # A non-results question keeps the feed order (newest first).
    rows_plain = disclosures.announcement_rows(
        feed, symbol="ROUTE", sub_question="Any recent announcements?"
    )
    assert rows_plain[0]["url"].endswith("AUDIO.pdf")
