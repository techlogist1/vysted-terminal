"""v0.5.0 agent tool — ``price_data``.

Migrated from v0.5.0's flat ``agent_tools.py`` with no behaviour change.
Registered via :func:`register` from
:func:`services.agent_tools.register_v0_5_0_tools` at sidecar startup
and from ``app.create_app``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from typing import Any

from services.agent_tools import register_tool

#: The region codes a ``region`` arg may scope to (the resolver's vocabulary).
_REGIONS = ("US", "IN", "GLOBAL")

#: Prompt-budget cap on the bars returned; the payload's counts say when it cut.
_MAX_BARS = 90


def listing_region(args: dict[str, Any]) -> str | None:
    """The per-call ``region`` override (R15-LEAD-127), or ``None``.

    An unknown value is ignored rather than coerced: ``normalize_region``
    would turn a stray 'NSE' into IN and fetch a listing the caller never named.
    """
    value = args.get("region")
    if isinstance(value, str) and value.strip().upper() in _REGIONS:
        return value.strip().upper()
    return None


async def in_region(region: str | None, fetch: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    """Await ``fetch`` with the request region scoped to ``region`` (when set).

    The bare ticker resolves through ``config.get_region()``, so a collision
    ticker (HAL, RACE, CCL) serves the session region's company unless the
    caller names the listing's region. ``to_thread`` copies the context.
    """
    if region is None:
        return await fetch
    import config

    token = config.set_request_region(region)
    try:
        return await fetch
    finally:
        config.reset_request_region(token)


async def _price_data(args: dict[str, Any]) -> dict[str, Any]:
    """``price_data`` scoped to the optional ``region`` arg (see :func:`in_region`)."""
    return await in_region(listing_region(args), _price_data_impl(args))


async def _price_data_impl(args: dict[str, Any]) -> dict[str, Any]:
    """Return a recent OHLCV slice + the latest quote for ``symbol``.

    The Strategy Critic queries this tool to corroborate (or refute)
    claims a strategy backtest implicitly makes about the symbol's
    behaviour — e.g. "is this really a low-vol name?".

    Args:
        symbol: Ticker. Required.
        timeframe: One of the yfinance-mapped timeframes. Defaults to ``"1d"``.
        range_: Provider-native range string (e.g. ``"6mo"``, ``"1y"``).
            Defaults to ``"6mo"`` — six months is enough for vol /
            drawdown context without bloating the model prompt.
        asset_class: ``"equity"`` (default) or ``"crypto"``.
        region: optional ``US`` / ``IN`` / ``GLOBAL`` listing region; omitted
            keeps the session region.

    Returns the most recent ``_MAX_BARS`` bars (compact for the model) plus
    the latest quote, with ``bars_returned`` / ``bars_available`` /
    ``window_start`` so a cut window is visible. On provider failure returns
    ``{"ok": False, ...}``.
    """
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    timeframe = str(args.get("timeframe", "1d"))
    range_ = args.get("range") or args.get("range_") or "6mo"
    asset_class = str(args.get("asset_class", "equity"))

    from services import provider_registry

    series = await asyncio.to_thread(
        provider_registry.get_history,
        symbol,
        timeframe,
        str(range_),
        asset_class,
    )
    quote = await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)

    all_bars = list(series.bars)
    recent_bars = all_bars[-_MAX_BARS:]
    bars = [
        {
            "timestamp": bar.timestamp.isoformat()
            if hasattr(bar.timestamp, "isoformat")
            else str(bar.timestamp),
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in recent_bars
    ]
    return {
        "ok": True,
        "symbol": series.symbol,
        "timeframe": series.timeframe,
        "provider": series.provider,
        "quote": quote.model_dump(by_alias=True, mode="json"),
        "bars_returned": len(bars),
        "bars_available": len(all_bars),
        "window_start": bars[0]["timestamp"] if bars else None,
        "bars": bars,
    }


def register() -> None:
    """Register the ``price_data`` tool in the package registry."""
    register_tool("price_data", _price_data)


__all__ = ["_price_data", "in_region", "listing_region", "register"]
