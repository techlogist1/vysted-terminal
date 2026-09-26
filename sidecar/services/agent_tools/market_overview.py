"""Agent tool — ``market_overview``.

Answers a BROAD market-state question ("how's the market today", "what moved")
in one call: it resolves the user's locale benchmark indices (US: the S&P 500 /
Nasdaq / Dow + the SPY/QQQ ETFs; IN: the Nifty 50 / Sensex), fetches a live quote
for each via the SAME ``provider_registry`` path the rest of the terminal uses,
and pulls symbol-less market headlines via the existing news provider. The result
is a structured ``{region, indices, headlines}`` bundle the copilot synthesises —
so a "how's the market" turn is grounded in live data instead of answered from a
stale training prior.

Read-only by design (no broker / order side effects — the §6.5 registry grep
finds no forbidden substring here). Per-index failure is isolated: one bad
provider call degrades that index to an ``error`` field rather than tanking the
whole bundle.
"""

from __future__ import annotations

import asyncio
from typing import Any

import config
from services.agent_tools import register_tool

#: Locale benchmark sets. The cash indices anchor the market-state read; the
#: liquid ETFs (US only) give a tradable proxy + extended-hours signal.
_INDICES_BY_REGION: dict[str, list[str]] = {
    "US": ["^GSPC", "^IXIC", "^DJI", "SPY", "QQQ"],
    "IN": ["^NSEI", "^BSESN"],
}
#: GLOBAL (and any unknown locale) falls back to the US benchmark set — it is the
#: broadest single proxy for "the market" when no region is set.
_DEFAULT_INDICES = _INDICES_BY_REGION["US"]

#: Human labels so the model names the index instead of echoing a caret-ticker.
_INDEX_LABELS = {
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq Composite",
    "^DJI": "Dow Jones Industrial Average",
    "SPY": "S&P 500 ETF (SPY)",
    "QQQ": "Nasdaq 100 ETF (QQQ)",
    "^NSEI": "Nifty 50",
    "^BSESN": "BSE Sensex",
}

#: Headlines to pull for the broad market read.
_HEADLINE_LIMIT = 12


def _indices_for_region(region: str) -> list[str]:
    return _INDICES_BY_REGION.get(region, _DEFAULT_INDICES)


async def _quote_one(symbol: str, region: str) -> dict[str, Any]:
    """Fetch a single index/ETF quote, isolating provider failure to this entry."""
    from services import provider_registry
    from services.errors import ProviderError

    label = _INDEX_LABELS.get(symbol, symbol)
    try:
        quote = await asyncio.to_thread(provider_registry.get_quote, symbol, "equity", region)
    except ProviderError as exc:
        return {"symbol": symbol, "name": label, "error": f"no data for {symbol}: {exc}"}
    except Exception as exc:  # noqa: BLE001 — surface to the model, never crash the turn
        return {"symbol": symbol, "name": label, "error": f"unexpected error for {symbol}: {exc}"}

    return {
        "symbol": quote.symbol,
        "name": label,
        "price": quote.price,
        "change": quote.change,
        "change_percent": quote.change_percent,
        "currency": quote.currency,
        "market_state": quote.market_state,
        "provider": quote.provider,
    }


async def _headlines(limit: int) -> tuple[list[dict[str, Any]], str | None]:
    """Pull broad (symbol-less) market headlines as ``(items, error)``.

    ``fetch_news`` raises rather than return an empty list, so a failure is a
    feed outage: it comes back as ``([], error)`` so the model never reads the
    outage as "no notable headlines".
    """
    import httpx

    from services import news_provider

    try:
        async with httpx.AsyncClient() as client:
            items = await news_provider.fetch_news(client, [], limit)
    except Exception as exc:  # noqa: BLE001 — headlines are a best-effort add-on
        return [], f"news feed unavailable: {exc}"
    return [item.model_dump(mode="json") for item in items], None


async def _market_overview(args: dict[str, Any]) -> dict[str, Any]:
    """Return a locale-aware market-state snapshot: indices + market headlines.

    Args:
        region: optional locale override (``US`` / ``IN`` / ``GLOBAL``); defaults
            to the active request region.

    Returns ``{"ok": True, "region", "indices": [...], "headlines": [...]}``,
    plus ``headlines_error`` when the news feed failed (``headlines`` is then
    ``[]`` because of the outage, not because there was no news).
    Index quotes that fail carry a per-symbol ``error`` field (a coverage gap for
    THAT index, not a feed outage). ``ok`` is False only when every index failed.
    """
    region = (
        config.normalize_region(args.get("region")) if args.get("region") else config.get_region()
    )
    symbols = _indices_for_region(region)

    raw_indices, (headlines, headlines_error) = await asyncio.gather(
        asyncio.gather(*(_quote_one(symbol, region) for symbol in symbols), return_exceptions=True),
        _headlines(_HEADLINE_LIMIT),
    )
    # ``_quote_one`` already catches every known failure path internally, but
    # ``return_exceptions=True`` is the outer backstop so a truly unexpected
    # exception still degrades to a per-symbol error row instead of raising
    # out of ``gather`` (R15-AGENT-069).
    indices = [
        {
            "symbol": symbol,
            "name": _INDEX_LABELS.get(symbol, symbol),
            "error": f"unexpected error for {symbol}: {r}",
        }
        if isinstance(r, BaseException)
        else r
        for symbol, r in zip(symbols, raw_indices, strict=True)
    ]

    resolved = [idx for idx in indices if "error" not in idx]
    payload: dict[str, Any] = {
        "ok": bool(resolved),
        "region": region,
        "indices": indices,
        "headlines": headlines,
    }
    if region not in _INDICES_BY_REGION:
        # GLOBAL (and any other unmapped region) silently reuses the US index
        # set — name that substitution so the model doesn't read "GLOBAL" as
        # its own benchmark (R15-DATA-101).
        payload["note"] = f"no index set for region {region!r} — showing the US proxy benchmark"
    if headlines_error:
        payload["headlines_error"] = headlines_error
    if not resolved:
        payload["message"] = (
            "no index data resolved for this region — the quote feed returned nothing"
        )
    return payload


def register() -> None:
    """Register the ``market_overview`` tool in the package registry."""
    register_tool("market_overview", _market_overview)


__all__ = ["_market_overview", "register"]
