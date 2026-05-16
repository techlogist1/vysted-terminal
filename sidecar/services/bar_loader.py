"""Production bar loader for the backtest engine.

The Phase-4 foundation declared a ``BarLoader`` callable shape in
``backtest_engine.py`` but bundled no default — Teammate K's
deliverable is to wire it against the Phase-1 ``provider_registry``
(yfinance for equities, ccxt for crypto, openbb-mcp where bundled).

``load_bars`` is the production callable: routers and the end-to-end
Strategy Critic test inject it via ``run_backtest(bar_loader=...)``.
The signature mirrors ``backtest_engine.BarLoader``:

    async def load_bars(symbols: list[str], start: str, end: str) -> list[Bar]

What this module owns:

- Pulling daily OHLCV from the provider registry per symbol. The
  registry is synchronous (yfinance is sync; the registry's openbb-mcp
  paths are async, but ``get_history`` is the sync equity path). We
  call it on a thread so the FastAPI event loop is never blocked.
- Filtering the returned series to the requested ``[start, end]``
  inclusive date window — providers return whole calendar lookups by
  default.
- Normalising the provider's ``OHLCVBar`` (timezoned ``datetime``
  timestamps) to the engine's ``Bar`` (string-shaped ``YYYY-MM-DD``
  timestamps).
- Concatenating per-symbol series into one flat list; the engine
  sorts by ``(timestamp, symbol)`` itself so this list does not need
  to interleave.

Asset class detection: a symbol containing ``/`` is treated as crypto
(``BTC/USDT``); everything else is equity. The dispatch is
deliberately tiny — Phase 5 broker integrations can wrap their own
``BarLoader``s through this same surface if they bundle proprietary
historical APIs.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date
from typing import Any

from services import provider_registry
from services.backtest_engine import Bar
from services.errors import ProviderError

logger = logging.getLogger(__name__)


def _is_crypto_symbol(symbol: str) -> bool:
    """Detect crypto pairs from their ``BASE/QUOTE`` shape."""
    return "/" in symbol


def _coerce_iso_date(value: Any) -> str:
    """Render a timestamp/date as ``YYYY-MM-DD``.

    The provider returns Python ``datetime`` objects (yfinance), naive
    or tz-aware. The engine works in ISO date strings so equality
    comparisons stay cheap and slice-by-date is a string compare.
    """
    if hasattr(value, "date"):
        return value.date().isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat().split("T", 1)[0]
    return str(value)[:10]


def _within(timestamp: str, start: str, end: str) -> bool:
    """Inclusive date-string window check."""
    return start <= timestamp <= end


def _to_bars(symbol: str, ohlcv_bars: list[Any], start: str, end: str) -> list[Bar]:
    """Convert provider bars to engine bars, filtered to the date window."""
    out: list[Bar] = []
    for bar in ohlcv_bars:
        timestamp = _coerce_iso_date(bar.timestamp)
        if not _within(timestamp, start, end):
            continue
        out.append(
            Bar(
                timestamp=timestamp,
                symbol=symbol,
                open=float(bar.open),
                high=float(bar.high),
                low=float(bar.low),
                close=float(bar.close),
                volume=float(bar.volume),
            )
        )
    return out


def _provider_range(start: str, end: str) -> str:
    """Map a ``[start, end]`` window onto a yfinance ``period``.

    yfinance accepts both ``period`` (e.g. ``"1y"``) and explicit
    ``start``/``end``. Phase 1's ``get_history`` takes ``range_`` and
    forwards it to yfinance. For simplicity at this layer we choose a
    safe over-fetch (``"max"`` for very long windows, otherwise an
    explicit multi-year period) and clip to the exact window in
    ``_to_bars``. This trades a few extra bytes per backtest for not
    having to thread an explicit start/end through ``get_history``.
    """
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError:
        return "1y"
    days = (end_date - start_date).days
    if days <= 0:
        return "1mo"
    if days < 35:
        return "3mo"
    if days < 100:
        return "6mo"
    if days < 400:
        return "2y"
    if days < 2000:
        return "5y"
    return "max"


async def _load_one_symbol(
    symbol: str,
    start: str,
    end: str,
    timeframe: str,
) -> list[Bar]:
    """Pull one symbol's history through the provider registry."""
    asset_class = "crypto" if _is_crypto_symbol(symbol) else "equity"
    range_ = _provider_range(start, end)
    # provider_registry.get_history is synchronous (yfinance + ccxt path)
    # — run it on the default thread executor so we don't stall the
    # event loop in a multi-symbol backtest.
    try:
        series = await asyncio.to_thread(
            provider_registry.get_history,
            symbol,
            timeframe,
            range_,
            asset_class,
        )
    except ProviderError as exc:
        logger.warning(
            "bar_loader: provider error for %s (%s); returning empty series", symbol, exc
        )
        return []
    return _to_bars(symbol, list(series.bars), start, end)


async def load_bars(symbols: list[str], start: str, end: str) -> list[Bar]:
    """Load OHLCV bars for every symbol across the date window.

    Symbols are loaded concurrently. The result list is the concatenation
    of every per-symbol series; the engine sorts by
    ``(timestamp, symbol)`` itself.
    """
    if not symbols:
        return []
    coros = [_load_one_symbol(symbol, start, end, "1d") for symbol in symbols]
    series_lists = await asyncio.gather(*coros)
    out: list[Bar] = []
    for series in series_lists:
        out.extend(series)
    return out
