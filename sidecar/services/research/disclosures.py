"""Exchange disclosures inside the research loop (R8).

The in-house disclosure tools exist and work — ``corporate_announcements``
(merged BSE+NSE feed with results PDFs and earnings-call transcripts as
``attachment_url``) and the NSE results calendar — but research never consulted
them: a ROUTE earnings question searched the open web while the 2026-05-07
"Financial Results/Dividend" board meeting sat in the calendar feed. This
module gives :func:`~services.research.deep._run_researcher` a disclosures
dimension:

  - :func:`wants_disclosures` — fires when the bound target trades in India
    and the sub-question is results/earnings/announcement/dividend/transcript
    shaped.
  - :func:`gather` — pulls the announcements via the REGISTERED
    ``corporate_announcements`` agent tool (the injected ``tool_call`` seam,
    same as every other leg) and, for earnings-DATE questions, the results
    calendar via :func:`fetch_results_calendar` (a thin injectable wrapper —
    the calendar has no registered tool, and the catalog is owned elsewhere).
  - Announcement ``attachment_url`` rows come back as web-row-shaped citations
    stamped ``verified_symbol`` (they are keyed to the bound symbol by the
    exchange feed itself), so they pass the relevance gate, rank on the
    exchange tier of the finance ladder, and are VISITABLE — the PDF lane in
    :mod:`services.search.extract` reads them.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from services.research.target import ResearchTarget

#: How many announcements one researcher FETCHES. Deep enough that a quarter-old
#: results filing is still in the window — the live ROUTE feed had the Q4 FY26
#: outcome PDF at index 14, past the old 12-item fetch, so research listed
#: intimations but never saw the filing that actually carries the numbers.
_ANNOUNCEMENT_LIMIT = 50

#: How many announcement lines the prompt context shows (compact).
_CONTEXT_LIMIT = 12

#: How many announcement rows become citable sources per researcher.
_MAX_SOURCE_ROWS = 5

#: Headline shapes that carry the actual RESULTS payload (the outcome/financial
#: results filing and its press release) — ranked FIRST for results-shaped
#: questions so the researcher's one visit reads the filing with the numbers,
#: not the newest procedural intimation.
_RESULTS_HEADLINE_RX = re.compile(
    r"(?i)\b(financial\s+results?|outcome\s+of\s+(the\s+)?board|un-?audited|audited"
    r"|press\s+release.{0,40}(result|quarter)|results?\s+for\s+the)\b"
)

#: Headline shapes of the DIGITAL TWIN of a results filing — the investor /
#: earnings presentation or press release the company files the same evening.
#: Band 0.5 (R9 B1): right behind the outcome filing, ahead of everything
#: else, so when the outcome's tables turn out to be raster scans the
#: researcher's ONE fallback visit (``rows[1]``) reads the document that
#: carries every figure with a real text layer — not a fourth scanned outcome.
_PRESENTATION_HEADLINE_RX = re.compile(
    r"(?i)\b(investor\s+presentation|earnings\s+presentation|press\s+release"
    r"|analyst\s+presentation|results?\s+presentation)\b"
)


def _results_band(title: str) -> float:
    """Rank band for a results-shaped question: 0 = the results filing itself,
    0.5 = its digital twin (presentation / press release), 1 = the rest."""
    if _RESULTS_HEADLINE_RX.search(title):
        return 0.0
    if _PRESENTATION_HEADLINE_RX.search(title):
        return 0.5
    return 1.0


#: Sub-question shapes that should consult the disclosure feeds.
_DISCLOSURE_KEYWORDS = (
    "result",
    "earnings",
    "quarterly",
    "quarter",
    "announce",
    "dividend",
    "transcript",
    "concall",
    "conference call",
    "board meeting",
    "agm",
    "filing",
    "disclosure",
    "shareholding",
)

#: Earnings-DATE shapes — these additionally consult the results calendar.
_DATE_KEYWORDS = ("when", "date", "next", "upcoming", "schedule", "calendar", "announced")

_INDIA_EXCHANGES = ("NSE", "BSE")


def is_india_target(target: ResearchTarget | None) -> bool:
    """Does the bound instrument trade on an Indian exchange?"""
    if target is None:
        return False
    if (target.region or "").strip().upper() == "IN":
        return True
    return (target.exchange or "").strip().upper() in _INDIA_EXCHANGES


def is_disclosure_question(text: str) -> bool:
    """Is this sub-question results/earnings/announcement/transcript shaped?"""
    low = (text or "").lower()
    return any(k in low for k in _DISCLOSURE_KEYWORDS)


def is_earnings_date_question(text: str) -> bool:
    """Does the sub-question ask WHEN results/earnings happen(ed)?"""
    low = (text or "").lower()
    return is_disclosure_question(low) and any(k in low for k in _DATE_KEYWORDS)


def wants_disclosures(target: ResearchTarget | None, sub_question: str) -> bool:
    """Should this researcher consult the exchange disclosure feeds?"""
    return is_india_target(target) and is_disclosure_question(sub_question)


def wants_disclosures_floor(target: ResearchTarget | None) -> bool:
    """The RUN-LEVEL floor trigger (R13): pull the exchange feeds for ANY
    India-listed target at DEEP/ULTRA, regardless of sub-question shape.

    The per-researcher :func:`wants_disclosures` gate stays sub-question-shaped
    (a results question consults the feeds; a price question does not). But when
    web coverage is starving — a thin micro-cap (KSE) whose open-web results are
    all its foreign namesake, or a run whose planning ate the wall before any
    researcher fired — the run STILL owes the user the dated exchange filings it
    can pull deterministically. So the loop pulls announcements ONCE up front for
    every Indian listing and feeds them to the structured floor
    (:func:`services.research.deep.build_structured_floor`). Design note: this is
    a coarse always-on trigger by DESIGN — the feed call is cheap, the data is
    always relevant for an Indian listing, and it is the difference between a
    "No findings" brief and one grounded in real filings."""
    return is_india_target(target)


async def gather_floor(
    tool_call: Any, *, target: ResearchTarget, limit: int = _ANNOUNCEMENT_LIMIT
) -> dict[str, Any]:
    """Up-front exchange-announcements pull for the structured floor (R13).

    Returns ``{"ok", "announcements", "rows"}``: ``announcements`` is the raw
    dated feed (for the floor's brief body), ``rows`` are citable/visitable
    attachment sources (folded into the run's findings so the floor's brief
    carries real ``[n]`` sources). Never raises — a feed miss is ``ok: False``
    with empty lists.
    """
    try:
        announcements = await tool_call(
            "corporate_announcements", {"symbol": target.symbol, "limit": limit}
        )
    except Exception as exc:  # noqa: BLE001 — a feed miss is soft
        announcements = {"ok": False, "error": f"corporate_announcements failed: {exc}"}
    if not isinstance(announcements, dict):
        announcements = {"ok": False, "error": "non-dict corporate_announcements result"}
    ok = bool(announcements.get("ok"))
    items = announcements.get("announcements") if ok else []
    return {
        "ok": ok,
        "announcements": items if isinstance(items, list) else [],
        "rows": announcement_rows(announcements, symbol=target.symbol),
    }


def plan_hint(target: ResearchTarget | None) -> str:
    """One planner-prompt line telling the model the disclosure feeds exist."""
    if not is_india_target(target):
        return ""
    return (
        "Exchange disclosures are available for this Indian listing: NSE/BSE "
        "corporate announcements (results PDFs, earnings-call transcripts, "
        "dividend notices) and the results/board-meeting calendar — phrase "
        "results/earnings/dividend questions so they get consulted."
    )


async def fetch_results_calendar(symbol: str) -> dict[str, Any]:
    """The NSE results/board-meeting calendar for ``symbol`` — honest dict.

    The calendar has no registered agent tool (the capability catalog is owned
    by another track), so this wraps the service directly; tests monkeypatch
    this module attribute. Never raises.
    """
    try:
        from services import corporate_disclosures

        response = await asyncio.to_thread(corporate_disclosures.get_results_calendar, symbol)
    except Exception as exc:  # noqa: BLE001 — a feed miss is soft inside a round
        return {"ok": False, "error": f"results calendar unavailable: {exc}"}
    return {
        "ok": True,
        "symbol": response.symbol,
        "count": response.count,
        "events": [event.model_dump(mode="json") for event in response.events],
    }


def announcement_rows(
    result: dict[str, Any], *, symbol: str, sub_question: str = ""
) -> list[dict[str, Any]]:
    """Announcement attachments → web-row-shaped citable sources.

    Each row carries ``verified_symbol`` (exchange-feed provenance — it passes
    the relevance gate without a headline match) and ``source_type: filing``
    so the sources rail badges it correctly. Rows without an attachment URL
    inform the prompt context but cannot be cited/visited, so they are skipped
    here.

    For a RESULTS-shaped ``sub_question``, rows whose headline carries the
    actual results payload (:data:`_RESULTS_HEADLINE_RX` — the outcome filing,
    the results press release) rank FIRST, the filing's digital twin
    (:data:`_PRESENTATION_HEADLINE_RX` — investor/earnings presentation, press
    release) ranks at band 0.5, everything else last, newest-first within each
    band. The researcher's one visit reads the filing with the numbers, never
    the newest procedural intimation (the live R8 gate-1 failure mode); when
    the filing is a raster scan, the bounded fallback visit reads the digital
    twin at ``rows[1]`` (the live R9 V10 failure mode).
    """
    if not isinstance(result, dict) or not result.get("ok"):
        return []
    candidates: list[dict[str, Any]] = []
    for item in result.get("announcements") or []:
        if not isinstance(item, dict):
            continue
        url = item.get("attachment_url")
        if not url:
            continue
        exchange = str(item.get("exchange") or "exchange")
        bits = [exchange]
        if item.get("category"):
            bits.append(str(item["category"]))
        if item.get("ts"):
            bits.append(str(item["ts"]))
        candidates.append(
            {
                "url": str(url),
                "title": str(item.get("headline") or url),
                "excerpt": " · ".join(bits),
                "source": exchange,
                "source_type": "filing",
                "verified_symbol": symbol,
            }
        )
    low = (sub_question or "").lower()
    results_shaped = any(
        k in low for k in ("result", "earnings", "quarter", "dividend", "profit", "revenue")
    )
    if results_shaped:
        # Stable partition: results filing, then its digital twin, then the
        # rest — feed order (newest first) within each band.
        candidates.sort(key=lambda row: _results_band(row["title"]))
    return candidates[:_MAX_SOURCE_ROWS]


def _context_lines(announcements: dict[str, Any] | None, calendar: dict[str, Any] | None) -> str:
    """A compact prompt block summarising what the exchange feeds said."""
    lines: list[str] = []
    if isinstance(announcements, dict) and announcements.get("ok"):
        items = announcements.get("announcements") or []
        if items:
            lines.append("Exchange announcements (merged NSE+BSE, newest first):")
            for item in items[:_CONTEXT_LIMIT]:
                if not isinstance(item, dict):
                    continue
                ts = str(item.get("ts") or "?")
                category = str(item.get("category") or "")
                headline = str(item.get("headline") or "")
                attach = " [PDF attached]" if item.get("attachment_url") else ""
                lines.append(f"- {ts} · {category}: {headline}{attach}")
        else:
            lines.append("Exchange announcements: feed reachable, no recent items.")
    if isinstance(calendar, dict) and calendar.get("ok"):
        events = calendar.get("events") or []
        if events:
            lines.append("Results / board-meeting calendar (NSE):")
            for event in events[:6]:
                if not isinstance(event, dict):
                    continue
                lines.append(
                    f"- {event.get('date') or '?'} · {event.get('purpose') or ''}: "
                    f"{event.get('description') or ''}"
                )
        else:
            lines.append("Results calendar: feed reachable, no scheduled events.")
    return "\n".join(lines)


async def gather(
    tool_call: Any,
    *,
    target: ResearchTarget,
    sub_question: str,
) -> dict[str, Any]:
    """Pull the disclosure evidence for one researcher — never raises.

    Returns ``{"rows": [...], "context": str, "announcements": result|None}``:
    ``rows`` are citable/visitable attachment sources, ``context`` is the
    prompt block, ``announcements`` is the raw ok-result for coverage
    recording (or ``None`` on a miss).
    """
    try:
        announcements = await tool_call(
            "corporate_announcements",
            {"symbol": target.symbol, "limit": _ANNOUNCEMENT_LIMIT},
        )
    except Exception as exc:  # noqa: BLE001 — a feed miss is soft inside a round
        announcements = {"ok": False, "error": f"corporate_announcements failed: {exc}"}
    if not isinstance(announcements, dict):
        announcements = {"ok": False, "error": "non-dict corporate_announcements result"}

    calendar: dict[str, Any] | None = None
    if is_earnings_date_question(sub_question):
        calendar = await fetch_results_calendar(target.symbol)

    return {
        "rows": announcement_rows(announcements, symbol=target.symbol, sub_question=sub_question),
        "context": _context_lines(announcements, calendar),
        "announcements": announcements if announcements.get("ok") else None,
        "calendar": calendar,
    }


__all__ = [
    "announcement_rows",
    "fetch_results_calendar",
    "gather",
    "gather_floor",
    "is_disclosure_question",
    "is_earnings_date_question",
    "is_india_target",
    "plan_hint",
    "wants_disclosures",
    "wants_disclosures_floor",
]
