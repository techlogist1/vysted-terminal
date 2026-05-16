"""v0.5.0 agent tool — ``price_data``.

Migrated from v0.5.0's flat ``agent_tools.py`` with no behaviour change.
Registered via :func:`register` from
:func:`services.agent_tools.register_v0_5_0_tools` at sidecar startup
and from ``app.create_app``.
"""

from __future__ import annotations

import asyncio
from typing import Any

from services.agent_tools import register_tool


async def _price_data(args: dict[str, Any]) -> dict[str, Any]:
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

    Returns the most recent 90 bars (compact for the model) plus the
    latest quote. On provider failure returns ``{"ok": False, ...}``.
    """
    symbol = args.get("symbol")
    if not isinstance(symbol, str) or not symbol:
        return {"ok": False, "error": "missing or non-string symbol"}
    timeframe = str(args.get("timeframe", "1d"))
    range_ = args.get("range") or args.get("range_") or "6mo"
    asset_class = str(args.get("asset_class", "equity"))

    from services import provider_registry
    from services.errors import ProviderError

    try:
        series = await asyncio.to_thread(
            provider_registry.get_history,
            symbol,
            timeframe,
            str(range_),
            asset_class,
        )
        quote = await asyncio.to_thread(provider_registry.get_quote, symbol, asset_class)
    except ProviderError as exc:
        return {"ok": False, "error": f"provider error: {exc}"}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"unexpected error: {exc}"}

    recent_bars = list(series.bars)[-90:]
    return {
        "ok": True,
        "symbol": series.symbol,
        "timeframe": series.timeframe,
        "provider": series.provider,
        "quote": quote.model_dump(by_alias=True, mode="json"),
        "bars": [
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
        ],
    }


def register() -> None:
    """Register the ``price_data`` tool in the package registry."""
    register_tool("price_data", _price_data)


__all__ = ["_price_data", "register"]
