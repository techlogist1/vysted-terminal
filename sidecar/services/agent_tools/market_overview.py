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


async def _headlines(limit: int) -> list[dict[str, Any]]:
    """Pull broad (symbol-less) market headlines; degrade to [] on failure."""
    import httpx

    from services import news_provider
    from services.errors import ProviderError

    try:
        async with httpx.AsyncClient() as client:
            items = await news_provider.fetch_news(client, [], limit)
    except (ProviderError, Exception):  # noqa: BLE001 — headlines are a best-effort add-on
        return []
    return [item.model_dump(mode="json") for item in items]


async def _market_overview(args: dict[str, Any]) -> dict[str, Any]:
    """Return a locale-aware market-state snapshot: indices + market headlines.

    Args:
        region: optional locale override (``US`` / ``IN`` / ``GLOBAL``); defaults
            to the active request region.

    Returns ``{"ok": True, "region", "indices": [...], "headlines": [...]}``.
    Index quotes that fail carry a per-symbol ``error`` field (a coverage gap for
    THAT index, not a feed outage). ``ok`` is False only when every index failed.
    """
    region = (
        config.normalize_region(args.get("region")) if args.get("region") else config.get_region()
    )
    symbols = _indices_for_region(region)

    indices, headlines = await asyncio.gather(
        asyncio.gather(*(_quote_one(symbol, region) for symbol in symbols)),
        _headlines(_HEADLINE_LIMIT),
    )
    indices = list(indices)

    resolved = [idx for idx in indices if "error" not in idx]
    if not resolved:
        return {
            "ok": False,
            "region": region,
            "indices": indices,
            "headlines": headlines,
            "message": "no index data resolved for this region — the quote feed returned nothing",
        }

    return {
        "ok": True,
        "region": region,
        "indices": indices,
        "headlines": headlines,
    }


def register() -> None:
    """Register the ``market_overview`` tool in the package registry."""
    register_tool("market_overview", _market_overview)


__all__ = ["_market_overview", "register"]
