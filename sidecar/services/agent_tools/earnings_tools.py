"""Phase 6 (Teammate E) agent tools — earnings family.

Registers three agent tools the Strategy Critic + research agents can
invoke to enrich their context with earnings information:

* ``earnings_upcoming(days=7, watchlist=...)`` — upcoming earnings events.
* ``earnings_history(symbol)`` — past earnings reports for the symbol.
* ``earnings_estimates(symbol)`` — analyst estimate detail for the next
  upcoming report.

The tools wrap :mod:`services.earnings_provider`; a provider error propagates
to :func:`services.agent_tools.invoke_tool`, which converts it to
``{"ok": False, "error": "<msg>"}`` so the agent can surface the failure
verbatim rather than crashing the run.

These are read-only data tools (Vysted has no trading path, D81).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from services import earnings_provider
from services.agent_tools import register_tool


async def _earnings_upcoming(args: dict[str, Any]) -> dict[str, Any]:
    """Return scheduled earnings events in the next ``days`` days."""
    days = int(args.get("days", 7) or 7)
    if days < 1 or days > 60:
        return {"ok": False, "error": "days must be in [1, 60]"}
    watchlist_arg = args.get("watchlist")
    watchlist: list[str] | None
    if isinstance(watchlist_arg, str):
        watchlist = [s.strip() for s in watchlist_arg.split(",") if s.strip()]
    elif isinstance(watchlist_arg, list):
        watchlist = [str(s).strip() for s in watchlist_arg if str(s).strip()]
    else:
        watchlist = None

    today = datetime.now(tz=UTC).date()
    response = await earnings_provider.get_upcoming(today, today + timedelta(days=days), watchlist)

    return {
        "ok": True,
        "window": {
            "start": response.start_date.isoformat(),
            "end": response.end_date.isoformat(),
        },
        "count": len(response.events),
        "events": [event.model_dump(mode="json") for event in response.events],
    }


async def _earnings_history(args: dict[str, Any]) -> dict[str, Any]:
    """Return historical earnings reports for ``symbol``."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    response = await earnings_provider.get_history(symbol)
    history = response.history[:12]  # compact: keep at most 12 most recent quarters
    return {
        "ok": True,
        "symbol": response.symbol,
        "count": len(history),
        "history": [entry.model_dump(mode="json") for entry in history],
    }


async def _earnings_estimates(args: dict[str, Any]) -> dict[str, Any]:
    """Return the analyst estimate detail for the next upcoming report."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    detail = await earnings_provider.get_estimate_detail(symbol)
    return {
        "ok": True,
        "estimate": detail.model_dump(mode="json"),
    }


def register() -> None:
    """Register the earnings family with the agent-tool registry."""
    register_tool("earnings_upcoming", _earnings_upcoming)
    register_tool("earnings_history", _earnings_history)
    register_tool("earnings_estimates", _earnings_estimates)


__all__ = [
    "_earnings_estimates",
    "_earnings_history",
    "_earnings_upcoming",
    "register",
]
