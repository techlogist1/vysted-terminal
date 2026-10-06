"""Corporate-disclosure agent tools (R7 Component 3).

Registers read-only tools the copilot + research agents can invoke so a
research run on an Indian name can pull real filings:

* ``corporate_announcements(symbol, exchange=None, limit=20)`` — the merged
  BSE+NSE announcement feed (deduped, newest first) from
  :mod:`services.corporate_disclosures`.
* ``shareholding_pattern(symbol)`` — the quarterly shareholding patterns
  (promoter/public/employee-trust percentages, the FII/DII split and the
  promoter pledge; each pattern's ``source``/``split_source``/``split_as_of``/
  ``split_basis`` carry the provenance — never fabricated).
* ``corporate_actions(symbol)`` — dividends, bonuses, splits, rights and
  buybacks from both exchanges with ex/record/payment dates.
* ``exchange_deals(symbol, kind=None)`` — bulk/block deals and SAST (Reg 29)
  disclosures, newest first.
* ``earnings_call_transcript(symbol, quarter=None)`` — the newest (or the
  requested quarter's) earnings-call transcript filed on NSE/BSE, its PDF read
  to text (R15-RESEARCH-030).

A provider error propagates to :func:`services.agent_tools.invoke_tool`,
which converts it to ``{"ok": False, "error": "<msg>"}`` so the agent
surfaces the failure verbatim instead of crashing the run. A symbol
the Indian exchanges do not cover answers ``ok: True`` with ``coverage`` and a
``note`` (C3); a US-listed ADR's shareholding carries its 20-F major holders
(``provider`` ``"sec-20f"``). All are read-only data tools (no trading path, D81).
"""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any

from services import corporate_disclosures, sec_ownership
from services.agent_tools import register_tool
from services.search import extract

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100
# Compact context: at most this many quarters of shareholding history.
_MAX_QUARTERS = 12
#: A quarter's call transcript is filed within weeks of its results, well inside
#: the following quarter.
_TRANSCRIPT_FILING_WINDOW = timedelta(days=92)


def _coverage(response: Any) -> dict[str, Any]:
    """``coverage`` always; ``note`` only when the service stated one."""
    out: dict[str, Any] = {"coverage": response.coverage}
    if response.note:
        out["note"] = response.note
    return out


async def _corporate_announcements(args: dict[str, Any]) -> dict[str, Any]:
    """Merged BSE+NSE corporate announcements for ``symbol``."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        return {"ok": False, "error": "missing or non-string symbol"}
    exchange_arg = args.get("exchange")
    exchange: str | None = None
    if exchange_arg is not None:
        exchange = str(exchange_arg).strip().upper()
        if exchange not in corporate_disclosures.EXCHANGES:
            return {"ok": False, "error": f"unknown exchange {exchange_arg!r} (use NSE or BSE)"}
    try:
        limit = int(args.get("limit", _DEFAULT_LIMIT) or _DEFAULT_LIMIT)
    except (TypeError, ValueError):
        return {"ok": False, "error": "limit must be an integer"}
    limit = max(1, min(limit, _MAX_LIMIT))
    response = await corporate_disclosures.get_announcements_cached(symbol, exchange, limit)
    return {
        "ok": True,
        "symbol": response.symbol,
        "exchange": response.exchange,
        **_coverage(response),
        "sources": response.sources,
        "errors": response.errors,
        "count": response.count,
        "announcements": [item.model_dump(mode="json") for item in response.announcements],
    }


async def _shareholding_pattern(args: dict[str, Any]) -> dict[str, Any]:
    """Quarterly shareholding patterns for ``symbol``, newest quarter first."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        return {"ok": False, "error": "missing or non-string symbol"}
    response = await asyncio.to_thread(corporate_disclosures.get_shareholding, symbol)
    response = await sec_ownership.attach_major_shareholders(response)
    patterns = response.patterns[:_MAX_QUARTERS]
    holders = {}
    if response.major_shareholders:
        holders = {
            "provider": response.provider,
            "major_shareholders": [h.model_dump(mode="json") for h in response.major_shareholders],
            "source_url": response.source_url,
        }
    return {
        "ok": True,
        "symbol": response.symbol,
        **_coverage(response),
        "count": len(patterns),
        "patterns": [pattern.model_dump(mode="json") for pattern in patterns],
        **holders,
    }


async def _corporate_actions(args: dict[str, Any]) -> dict[str, Any]:
    """NSE+BSE corporate actions for ``symbol``, newest ex-date first."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        return {"ok": False, "error": "missing or non-string symbol"}
    response = await asyncio.to_thread(corporate_disclosures.get_corporate_actions, symbol)
    return {
        "ok": True,
        "symbol": response.symbol,
        **_coverage(response),
        "sources": response.sources,
        "errors": response.errors,
        "count": response.count,
        "actions": [action.model_dump(mode="json") for action in response.actions],
    }


async def _exchange_deals(args: dict[str, Any]) -> dict[str, Any]:
    """Bulk/block deals and SAST disclosures for ``symbol``, newest first."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        return {"ok": False, "error": "missing or non-string symbol"}
    kind = args.get("kind")
    if kind is not None and kind not in corporate_disclosures.DEAL_KINDS:
        return {"ok": False, "error": f"unknown kind {kind!r} (use bulk, block or sast)"}
    response = await asyncio.to_thread(corporate_disclosures.get_deals, symbol, kind)
    return {
        "ok": True,
        "symbol": response.symbol,
        "kind": response.kind,
        **_coverage(response),
        "sources": response.sources,
        "errors": response.errors,
        "count": response.count,
        "deals": [deal.model_dump(mode="json") for deal in response.deals],
    }


async def _earnings_call_transcript(args: dict[str, Any]) -> dict[str, Any]:
    """The newest (or ``quarter``'s) earnings-call transcript for ``symbol``, as text."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        return {"ok": False, "error": "missing or non-string symbol"}
    quarter: date | None = None
    if args.get("quarter") is not None:
        try:
            quarter = date.fromisoformat(str(args["quarter"]))
        except ValueError:
            return {"ok": False, "error": "quarter must be the quarter-end date, YYYY-MM-DD"}
    response = await corporate_disclosures.get_announcements_cached(
        symbol, None, corporate_disclosures.MAX_LIMIT
    )
    if response.coverage != "covered":
        return {"ok": True, "symbol": response.symbol, "available": False, "reason": response.note}
    transcripts = [
        item
        for item in response.announcements
        if item.attachment_url
        and corporate_disclosures.is_earnings_call_transcript(item.headline, item.category)
        and (
            quarter is None
            or (item.ts and quarter < item.ts.date() <= quarter + _TRANSCRIPT_FILING_WINDOW)
        )
    ]
    if not transcripts:
        which = f"for the quarter ended {quarter} " if quarter else ""
        return {
            "ok": True,
            "symbol": response.symbol,
            "available": False,
            "reason": (
                f"no earnings-call transcript {which}among {response.symbol}'s "
                f"{response.count} newest NSE/BSE announcements"
            ),
        }
    filing = transcripts[0]  # the feed is newest first
    found = {
        "symbol": response.symbol,
        "filing_date": filing.ts.date().isoformat() if filing.ts else None,
        "url": filing.attachment_url,
        "source": filing.exchange,
    }
    page = await extract.fetch_page(filing.attachment_url, max_chars=extract.PDF_EXCHANGE_MAX_CHARS)
    if not page.get("ok"):
        return {"ok": False, **found, "error": f"transcript PDF unreadable: {page.get('error')}"}
    return {
        "ok": True,
        "available": True,
        **found,
        "text": page["content"],
        "truncated": bool(page.get("truncated")),
    }


def register() -> None:
    """Register the disclosure family with the agent-tool registry."""
    register_tool("corporate_announcements", _corporate_announcements)
    register_tool("shareholding_pattern", _shareholding_pattern)
    register_tool("corporate_actions", _corporate_actions)
    register_tool("exchange_deals", _exchange_deals)
    register_tool("earnings_call_transcript", _earnings_call_transcript)


__all__ = [
    "_corporate_actions",
    "_corporate_announcements",
    "_earnings_call_transcript",
    "_exchange_deals",
    "_shareholding_pattern",
    "register",
]
