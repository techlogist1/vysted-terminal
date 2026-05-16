"""Phase 6 (Teammate E) agent tools — analyst-ratings expansion family.

Registers three agent tools the research / Strategy Critic agents can
invoke to ground their commentary in concrete rating changes + price
targets:

* ``analyst_history(symbol)`` — every recorded rating change.
* ``analyst_individual(symbol)`` — per-firm currently-active forecast.
* ``price_target_history(symbol)`` — price-target timeline.

The tools wrap :mod:`services.analyst_ratings_extended`; provider errors
surface as ``{"ok": False, "error": "<msg>"}``.

None of these tools place orders or touch the §6.5 broker execution
surface — they are read-only data tools.
"""

from __future__ import annotations

from typing import Any

from services import analyst_ratings_extended
from services.agent_tools import register_tool
from services.errors import ProviderError

# Cap per-tool returns so a chatty backfill (200+ rows) doesn't blow up the
# model prompt budget. The frontend always paginates these locally so this
# cap is the agent prompt envelope, not the UX envelope.
_MAX_HISTORY_ROWS = 60


async def _analyst_history(args: dict[str, Any]) -> dict[str, Any]:
    """Return every recorded rating change for ``symbol`` (newest-first)."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    try:
        response = await analyst_ratings_extended.get_ratings_history(symbol)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    rows = response.history[:_MAX_HISTORY_ROWS]
    return {
        "ok": True,
        "symbol": response.symbol,
        "count": len(rows),
        "history": [entry.model_dump(mode="json") for entry in rows],
    }


async def _analyst_individual(args: dict[str, Any]) -> dict[str, Any]:
    """Return per-firm currently-active forecasts for ``symbol``."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    try:
        response = await analyst_ratings_extended.get_individual_analysts(symbol)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    rows = response.analysts[:_MAX_HISTORY_ROWS]
    return {
        "ok": True,
        "symbol": response.symbol,
        "count": len(rows),
        "analysts": [entry.model_dump(mode="json") for entry in rows],
    }


async def _price_target_history(args: dict[str, Any]) -> dict[str, Any]:
    """Return price-target changes for ``symbol`` (newest-first)."""
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    try:
        response = await analyst_ratings_extended.get_price_target_history(symbol)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}
    rows = response.history[:_MAX_HISTORY_ROWS]
    return {
        "ok": True,
        "symbol": response.symbol,
        "count": len(rows),
        "history": [entry.model_dump(mode="json") for entry in rows],
    }


def register() -> None:
    """Register the analyst-ratings family with the agent-tool registry."""
    register_tool("analyst_history", _analyst_history)
    register_tool("analyst_individual", _analyst_individual)
    register_tool("price_target_history", _price_target_history)


__all__ = [
    "_analyst_history",
    "_analyst_individual",
    "_price_target_history",
    "register",
]
