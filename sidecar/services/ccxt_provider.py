"""ccxt crypto provider — unified REST + WebSocket access across exchanges.

Phase 1 supports four exchanges: Bybit, Binance, Kraken, Coinbase. REST calls
(``get_ticker``, ``get_ohlcv``) use synchronous ccxt and run on a FastAPI worker
thread. The streaming path (``watch_ticker``) uses ccxt.pro's asyncio exchanges
and is consumed by the ``/crypto/stream`` WebSocket route.

Tests mock the ``ccxt`` / ``ccxtpro`` modules — no live exchange calls in CI.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import ccxt
import ccxt.pro as ccxtpro

from models.market import OHLCVBar, OHLCVSeries, Quote
from services import yfinance_provider
from services.errors import ProviderError

SUPPORTED_EXCHANGES = ("bybit", "binance", "kraken", "coinbase")

# Public timeframe -> ccxt timeframe.
_CCXT_TIMEFRAME: dict[str, str] = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
    "1wk": "1w",
    "1mo": "1M",
}


# The /history range vocabulary (Yahoo's periods) in days; ``ytd``/``max`` are
# handled in :func:`_since_ms`.
_RANGE_DAYS: dict[str, int] = {
    "1d": 1,
    "5d": 5,
    "1mo": 30,
    "3mo": 91,
    "6mo": 182,
    "1y": 365,
    "2y": 730,
    "5y": 1826,
    "10y": 3652,
}
_UNIT_MS = {"m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000, "M": 2_592_000_000}
_PAGE_LIMIT = 1000
# ponytail: a range longer than this many bars serves its newest bars only (a
# ``max`` 1m request would otherwise page thousands of rate-limited calls).
_MAX_BARS = 10_000


def _since_ms(range_: str, ccxt_timeframe: str, now: datetime) -> int:
    """The epoch-ms start of ``range_`` back from ``now``, clamped to :data:`_MAX_BARS`."""
    now_ms = int(now.timestamp() * 1000)
    if range_ == "max":
        since = 0
    elif range_ == "ytd":
        since = int(datetime(now.year, 1, 1, tzinfo=UTC).timestamp() * 1000)
    elif range_ in _RANGE_DAYS:
        since = now_ms - _RANGE_DAYS[range_] * _UNIT_MS["d"]
    else:
        raise ProviderError(f"unsupported range {range_!r}; supported: {', '.join(_RANGE_DAYS)}")
    bar_ms = int(ccxt_timeframe[:-1] or 1) * _UNIT_MS[ccxt_timeframe[-1]]
    return max(since, now_ms - _MAX_BARS * bar_ms)


def _check_exchange(exchange: str) -> None:
    if exchange not in SUPPORTED_EXCHANGES:
        raise ProviderError(
            f"unsupported exchange {exchange!r}; supported: {', '.join(SUPPORTED_EXCHANGES)}"
        )


def _sync_exchange(exchange: str) -> ccxt.Exchange:
    _check_exchange(exchange)
    return getattr(ccxt, exchange)({"enableRateLimit": True})


def _ticker_to_quote(ticker: dict[str, Any], exchange: str, symbol: str) -> Quote:
    price = ticker.get("last") or ticker.get("close")
    if price is None:
        raise ProviderError(f"ccxt ticker for {exchange}:{symbol} carries no last or close price")
    change = ticker.get("change")
    if change is None and ticker.get("previousClose"):
        change = float(price) - float(ticker["previousClose"])
    percentage = ticker.get("percentage")
    timestamp_ms = ticker.get("timestamp")
    timestamp = (
        datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
        if timestamp_ms
        else datetime.now(tz=UTC)
    )
    return Quote(
        symbol=symbol,
        price=float(price),
        change=float(change) if change is not None else 0.0,
        change_percent=float(percentage) if percentage is not None else 0.0,
        volume=float(ticker["baseVolume"]) if ticker.get("baseVolume") is not None else None,
        currency=symbol.split("/")[-1] if "/" in symbol else "USD",
        market_state="open",
        timestamp=timestamp,
        provider=f"ccxt:{exchange}",
    )


def get_ticker(exchange: str, symbol: str) -> Quote:
    """Return the latest REST ticker for ``symbol`` on ``exchange``."""
    instance = _sync_exchange(exchange)
    try:
        ticker = instance.fetch_ticker(symbol)
    except Exception as exc:  # noqa: BLE001 - any ccxt failure is a provider error
        raise ProviderError(f"ccxt ticker failed for {exchange}:{symbol}: {exc}") from exc
    return _ticker_to_quote(ticker, exchange, symbol)


def get_ohlcv(
    exchange: str, symbol: str, timeframe: str = "1d", range_: str | None = None
) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` on ``exchange`` covering ``range_``.

    ``range_`` uses the /history vocabulary (``1mo``, ``1y``, ``5y``, ``max`` ...);
    ``None`` takes the timeframe's default lookback, the same one yfinance uses.
    The range becomes ``since`` and ``fetch_ohlcv`` is paged from there to now
    (R15-DATA-037: a fixed 200-bar fetch made every range the same series).
    """
    instance = _sync_exchange(exchange)
    ccxt_timeframe = _CCXT_TIMEFRAME.get(timeframe, timeframe)
    period = range_ or yfinance_provider._TIMEFRAME_MAP.get(timeframe, ("1d", "1y"))[1]
    cursor = _since_ms(period, ccxt_timeframe, datetime.now(tz=UTC))
    rows: list[list[Any]] = []
    try:
        while True:
            page = instance.fetch_ohlcv(symbol, ccxt_timeframe, since=cursor, limit=_PAGE_LIMIT)
            rows.extend(row for row in page if not rows or row[0] > rows[-1][0])
            if len(page) < _PAGE_LIMIT:
                break
            cursor = page[-1][0] + 1
    except Exception as exc:  # noqa: BLE001
        raise ProviderError(f"ccxt OHLCV failed for {exchange}:{symbol}: {exc}") from exc

    bars = [
        OHLCVBar(
            timestamp=datetime.fromtimestamp(row[0] / 1000, tz=UTC),
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
        )
        for row in rows
    ]
    return OHLCVSeries(symbol=symbol, timeframe=timeframe, bars=bars, provider=f"ccxt:{exchange}")


async def watch_ticker(exchange: str, symbol: str) -> AsyncIterator[Quote]:
    """Yield live ticker quotes for ``symbol`` on ``exchange`` until cancelled."""
    _check_exchange(exchange)
    instance = getattr(ccxtpro, exchange)({"enableRateLimit": True})
    if not instance.has.get("watchTicker"):
        await instance.close()
        raise ProviderError(f"{exchange} does not support live ticker streaming")
    try:
        while True:
            ticker = await instance.watch_ticker(symbol)
            yield _ticker_to_quote(ticker, exchange, symbol)
    finally:
        await instance.close()
