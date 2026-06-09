"""Pass B (B1) agent tool — ``resolve_symbol``.

Resolves a free-text name or ticker to a concrete instrument (ticker, exchange,
region, asset class), locale-ranked, with disambiguation candidates when
confidence is low (FR-061). This is the agent's first move for a "research X" /
"look at Y" request: it turns "Tata Steel" into ``TATASTEEL`` on NSE before any
data is pulled, so JARVIS never dead-ends on a name it could have resolved.

Read-only, keyless: backed by :mod:`services.symbol_resolver` (bundled SEC +
NSE + BSE masters + a best-effort live fallback). Registered via :func:`register`.
"""

from __future__ import annotations

from typing import Any

from services.agent_tools import register_tool


def _instrument_dict(instrument: Any) -> dict[str, Any]:
    return {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "exchange": instrument.exchange,
        "region": instrument.region,
        "asset_class": instrument.asset_class,
        "yahoo_symbol": instrument.yahoo_symbol,
        "confidence": round(instrument.score, 3),
    }


async def _resolve_symbol(args: dict[str, Any]) -> dict[str, Any]:
    """Resolve ``query`` to an instrument + ranked candidates (locale-aware).

    Args:
        query: a free-text name or ticker (e.g. "Tata Steel", "GOLDBEES", "AAPL").
        region: optional locale override (``US`` / ``IN`` / ``GLOBAL``); defaults
            to the active request region.

    Returns ``{"ok": True, "resolved": {...}, "candidates": [...],
    "needs_disambiguation": bool}`` — or, when nothing resolves, ``{"ok": False,
    "message": <human reason>}`` (never raw JSON, never a fabricated guess).
    """
    query = args.get("query") or args.get("symbol")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "missing or non-string query"}

    import config
    from services import symbol_resolver

    region = (
        config.normalize_region(args.get("region")) if args.get("region") else config.get_region()
    )
    resolution = symbol_resolver.resolve(query, region)

    if resolution.best is None:
        return {
            "ok": False,
            "query": query,
            "message": (
                f"Could not resolve {query!r} to a known instrument in the bundled "
                f"US/NSE/BSE masters or a live lookup. Check the spelling, or add a "
                f"data source that covers it."
            ),
            "candidates": [],
        }

    return {
        "ok": True,
        "query": query,
        "region": region,
        "resolved": _instrument_dict(resolution.best),
        "needs_disambiguation": resolution.needs_disambiguation,
        "candidates": [_instrument_dict(c) for c in resolution.candidates],
    }


def register() -> None:
    """Register the ``resolve_symbol`` tool in the package registry."""
    register_tool("resolve_symbol", _resolve_symbol)


__all__ = ["_resolve_symbol", "register"]
