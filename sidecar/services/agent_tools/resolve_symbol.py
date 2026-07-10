"""Pass B (B1) agent tool — ``resolve_symbol``.

Resolves a free-text name or ticker to a concrete instrument (ticker, exchange,
region, asset class), locale-ranked, with disambiguation candidates when
confidence is low (FR-061). This is the agent's first move for a "research X" /
"look at Y" request: it turns "Tata Steel" into ``TATASTEEL`` on NSE before any
data is pulled, so JARVIS never dead-ends on a name it could have resolved.

R10 (E1): the reply carries the ONE acceptance verdict from
:mod:`services.resolution_policy` as ``status`` — ``"bound"`` /
``"disambiguate"`` / ``"unresolved"`` — and ``resolved`` is ``null`` unless
bound, so no consumer can re-judge the same resolution with a second threshold.

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
        # R13 additive identity enrichment — carried so the research target
        # (target.py) can anchor web queries + relevance on the ISIN / exchange /
        # industry, not just a colliding ≤3-char ticker. Null, never fabricated.
        "isin": instrument.isin,
        "bse_code": instrument.bse_code,
        "industry": instrument.industry,
        "former_name": instrument.former_name,
    }


async def _resolve_symbol(args: dict[str, Any]) -> dict[str, Any]:
    """Resolve ``query`` to an instrument + ranked candidates (locale-aware).

    Args:
        query: a free-text name or ticker (e.g. "Tata Steel", "GOLDBEES", "AAPL").
        region: optional locale override (``US`` / ``IN`` / ``GLOBAL``); defaults
            to the active request region.

    Returns the policy verdict on the wire: ``{"ok": True, "status": "bound",
    "resolved": {...}, "candidates": [...]}`` for a decisive match;
    ``{"ok": True, "status": "disambiguate", "resolved": None,
    "candidates": [...], "message": <which did you mean>}`` when an explicit
    choice is required; ``{"ok": False, "status": "unresolved",
    "message": <human reason>}`` when nothing trustworthy matched — never raw
    JSON, never a fabricated guess.
    """
    query = args.get("query") or args.get("symbol")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": "missing or non-string query"}

    import config
    from services import resolution_policy, symbol_resolver

    region = (
        config.normalize_region(args.get("region")) if args.get("region") else config.get_region()
    )
    resolution = symbol_resolver.resolve(query, region=region)
    decision = resolution_policy.decide(resolution)
    candidates = [_instrument_dict(c) for c in decision.candidates]

    if decision.outcome == "bound":
        return {
            "ok": True,
            "query": query,
            "region": region,
            "status": "bound",
            "reason": decision.reason,
            "resolved": _instrument_dict(decision.instrument),
            "needs_disambiguation": False,
            "candidates": candidates,
        }

    if decision.outcome == "disambiguate":
        listed = ", ".join(f"{c['symbol']} ({c['name']})" for c in candidates[:6])
        return {
            "ok": True,
            "query": query,
            "region": region,
            "status": "disambiguate",
            "reason": decision.reason,
            "resolved": None,
            "needs_disambiguation": True,
            "candidates": candidates,
            "message": (
                f"{query!r} matches more than one listed instrument — which did you mean? {listed}"
            ),
        }

    return {
        "ok": False,
        "query": query,
        "region": region,
        "status": "unresolved",
        "reason": decision.reason,
        "resolved": None,
        "needs_disambiguation": False,
        "message": (
            f"Could not resolve {query!r} to a known instrument in the bundled "
            f"US/NSE/BSE masters or a live lookup. Check the spelling, or add a "
            f"data source that covers it."
        ),
        "candidates": [],
    }


def register() -> None:
    """Register the ``resolve_symbol`` tool in the package registry."""
    register_tool("resolve_symbol", _resolve_symbol)


__all__ = ["_resolve_symbol", "register"]
