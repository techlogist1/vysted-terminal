"""Corporate-disclosure agent tools (R7 Component 3).

Registers two read-only tools the copilot + research agents can invoke so a
research run on an Indian name can pull real filings:

* ``corporate_announcements(symbol, exchange=None, limit=20)`` — the merged
  BSE+NSE announcement feed (deduped, newest first) from
  :mod:`services.corporate_disclosures`.
* ``shareholding_pattern(symbol)`` — the quarterly shareholding patterns
  (promoter/public/employee-trust percentages; the FII/DII split rides the
  linked XBRL filing and is honest ``None`` here — never fabricated).

On any provider error the tools return ``{"ok": False, "error": "<msg>"}`` so
the agent surfaces the failure verbatim instead of crashing the run. Both are
read-only — nothing here touches the §6.5 broker execution surface.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services import corporate_disclosures
from services.agent_tools import register_tool
from services.errors import ProviderError

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100
# Compact context: at most this many quarters of shareholding history.
_MAX_QUARTERS = 12


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
    try:
        response = await asyncio.to_thread(
            corporate_disclosures.get_announcements, symbol, exchange, limit
        )
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    return {
        "ok": True,
        "symbol": response.symbol,
        "exchange": response.exchange,
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
    try:
        response = await asyncio.to_thread(corporate_disclosures.get_shareholding, symbol)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    patterns = response.patterns[:_MAX_QUARTERS]
    return {
        "ok": True,
        "symbol": response.symbol,
        "count": len(patterns),
        "patterns": [pattern.model_dump(mode="json") for pattern in patterns],
        "note": (
            "promoter/public/employee-trust percentages come from the NSE master; "
            "the FII/DII split lives in each quarter's linked xbrl_url filing."
        ),
    }


def register() -> None:
    """Register the disclosure family with the agent-tool registry."""
    register_tool("corporate_announcements", _corporate_announcements)
    register_tool("shareholding_pattern", _shareholding_pattern)


__all__ = [
    "_corporate_announcements",
    "_shareholding_pattern",
    "register",
]
