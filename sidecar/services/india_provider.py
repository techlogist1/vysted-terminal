"""India NSE data provider — the keyless, correctness-first India default (B1).

FR-064: India equity/ETF data ships keyless and pre-installed via jugaad-data
(the maintained wrapper over the NSE site), serving **T+1 EOD** OHLCV for every
NSE equity + ETF (GOLDBEES / NIFTYBEES / SILVERBEES included) — the symbols
yfinance is documented-unreliable for (issues #2612 "possibly delisted" + #2055
silent-wrong OHLC). Ranked **above** gated yfinance for the IN region in
:mod:`services.provider_registry`.

Scope (keyless, correctness-over-coverage):

  * ``get_history`` — EOD OHLCV (daily; weekly/monthly resampled from daily).
    Intraday is **not** served keyless (NSE's live JSON is session-locked and
    geo-fragile) — it raises so the registry surfaces an honest "needs a BYOK
    broker (Angel One / Dhan)" rather than a wrong/empty intraday chart.
  * ``get_quote`` — derived from the two most-recent EOD closes (last close,
    official prior close → change/%). INR, IST, ``provider="nse"``, EOD-labelled.
  * Fundamentals are intentionally **not** served here — the registry falls
    through to yfinance for IN fundamentals (no reliable keyless NSE source).

Two live quirks handled (verified against the running NSE, 2026-06-01):

  * jugaad returns rows **newest-first** — we sort ascending so the chart and the
    derived quote read the *latest* bar, not the oldest.
  * jugaad's ``DATE`` is IST-midnight expressed in UTC (``18:30:00``); its naive
    ``.date()`` yields impossible Sundays. We add 5.5h to recover the true IST
    trading date (so a Friday close is dated Friday, and the staleness gate
    compares the right day).
  * the first ``stock_df`` call can raise ``FileExistsError`` racing its on-disk
    cache dir — :func:`_stock_df` pre-creates the dir and retries.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, date, datetime, timedelta

import pandas as pd

from models.market import OHLCVBar, OHLCVSeries, Quote
from services import locale, symbol_resolver
from services.errors import ProviderError

logger = logging.getLogger(__name__)

PROVIDER = "nse"

# EOD timeframes we serve from daily jugaad data (weekly/monthly are resampled).
_EOD_TIMEFRAMES = {"1d", "1wk", "1mo"}
# Approximate lookback (calendar days) per public range token → jugaad window.
_RANGE_DAYS = {
    "5d": 12,
    "1mo": 38,
    "3mo": 100,
    "6mo": 190,
    "1y": 380,
    "2y": 760,
    "5y": 1850,
    "max": 3700,
}
_DEFAULT_RANGE_DAYS = 380
# IST trading date = jugaad's UTC-encoded IST-midnight + 5.5h.
_IST_OFFSET = timedelta(hours=5, minutes=30)


def is_available() -> bool:
    """True if the keyless India backend (jugaad-data) is importable.

    Gates the registry declaration so ``/health`` is honest and a build without
    jugaad-data cleanly skips the ``nse`` provider (US data is unaffected).
    """
    try:
        import jugaad_data.nse  # noqa: F401

        return True
    except Exception:  # noqa: BLE001 - any import failure means "not available"
        return False


def _ist_trading_date(raw: object) -> date:
    """Recover the true IST trading date from jugaad's UTC-encoded ``DATE``."""
    ts = pd.Timestamp(raw)
    return (ts + _IST_OFFSET).date()


def _bar_timestamp(trading_day: date) -> datetime:
    """Represent a daily bar at UTC midnight of its IST trading date.

    Daily bars carry the trading day, not an intraday instant; UTC-midnight of
    the trading date is the unambiguous representation the chart renders by date.
    """
    return datetime(trading_day.year, trading_day.month, trading_day.day, tzinfo=UTC)


def _stock_df(symbol: str, from_date: date, to_date: date) -> pd.DataFrame:
    """Fetch EOD rows for ``symbol`` via jugaad, resilient to its cache-dir race.

    jugaad's ``stock_df`` writes a CSV cache under the OS cache dir; the very
    first call can raise ``FileExistsError`` racing that directory. We ensure the
    dir exists and retry once; a persistent failure raises so the registry falls
    through.
    """
    try:
        import appdirs
        from jugaad_data.nse import stock_df
    except Exception as exc:  # pragma: no cover - import/runtime bundling failure
        raise ProviderError(f"nse: jugaad-data unavailable: {exc}") from exc

    cache_dir = appdirs.user_cache_dir("nsehistory-stock")
    last_exc: Exception | None = None
    for _attempt in range(2):
        try:
            os.makedirs(cache_dir, exist_ok=True)
            frame = stock_df(symbol=symbol, from_date=from_date, to_date=to_date, series="EQ")
            if frame is None or frame.empty:
                raise ProviderError(f"nse: no EOD data for {symbol!r}")
            return frame.sort_values("DATE").reset_index(drop=True)
        except ProviderError:
            raise
        except FileExistsError as exc:
            last_exc = exc  # cache-dir race — retry after ensuring the dir
        except Exception as exc:  # noqa: BLE001 - any jugaad failure is a provider error
            raise ProviderError(f"nse: EOD fetch failed for {symbol!r}: {exc}") from exc
    raise ProviderError(f"nse: EOD fetch failed for {symbol!r}: {last_exc}")


def _require_nse(symbol: str) -> str:
    """Return the bare NSE symbol, or raise so the registry falls through fast.

    A non-NSE ticker (e.g. AAPL requested in an IN session) is rejected without a
    network call — the registry then resolves it via the next provider.
    """
    bare = locale.strip_exchange_suffix(symbol)
    if not symbol_resolver.is_nse_symbol(bare):
        raise ProviderError(f"nse: {symbol!r} is not a known NSE instrument")
    return bare


def get_quote(symbol: str) -> Quote:
    """Return the latest EOD quote for an NSE instrument (INR, T+1 EOD)."""
    bare = _require_nse(symbol)
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    frame = _stock_df(bare, today - timedelta(days=14), today)

    last = frame.iloc[-1]
    close = float(last["CLOSE"])
    prev_close = _num(last.get("PREV. CLOSE"))
    if prev_close is None and len(frame) >= 2:
        prev_close = float(frame.iloc[-2]["CLOSE"])
    change = close - prev_close if prev_close else 0.0
    change_percent = (change / prev_close * 100.0) if prev_close else 0.0
    trading_day = _ist_trading_date(last["DATE"])

    return Quote(
        symbol=bare,
        price=close,
        change=change,
        change_percent=change_percent,
        volume=_num(last.get("VOLUME")),
        currency="INR",
        market_state="REGULAR" if locale.is_market_open(locale.REGION_IN) else "CLOSED",
        timestamp=_bar_timestamp(trading_day),
        provider=PROVIDER,
    )


def get_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
    """Return an EOD OHLCV series for an NSE instrument.

    Daily for ``1d``; weekly/monthly resampled from daily for ``1wk``/``1mo``.
    Intraday timeframes raise (keyless NSE is EOD-only).
    """
    if timeframe not in _EOD_TIMEFRAMES:
        raise ProviderError(
            f"nse: intraday timeframe {timeframe!r} is not available keyless — "
            "add a BYOK broker (Angel One / Dhan) for NSE intraday"
        )
    bare = _require_nse(symbol)
    days = _RANGE_DAYS.get(range_ or "", _DEFAULT_RANGE_DAYS)
    today = datetime.now(tz=UTC).astimezone(locale.market_timezone(locale.REGION_IN)).date()
    frame = _stock_df(bare, today - timedelta(days=days), today)

    daily = _frame_to_bars(frame)
    bars = _resample(daily, timeframe) if timeframe in {"1wk", "1mo"} else daily
    return OHLCVSeries(symbol=bare, timeframe=timeframe, bars=bars, provider=PROVIDER)


def _frame_to_bars(frame: pd.DataFrame) -> list[OHLCVBar]:
    bars: list[OHLCVBar] = []
    for _, row in frame.iterrows():
        trading_day = _ist_trading_date(row["DATE"])
        bars.append(
            OHLCVBar(
                timestamp=_bar_timestamp(trading_day),
                open=float(row["OPEN"]),
                high=float(row["HIGH"]),
                low=float(row["LOW"]),
                close=float(row["CLOSE"]),
                volume=float(_num(row.get("VOLUME")) or 0.0),
            )
        )
    return bars


def _resample(bars: list[OHLCVBar], timeframe: str) -> list[OHLCVBar]:
    """Resample daily bars to weekly/monthly OHLCV (right-labelled)."""
    if not bars:
        return bars
    rule = "W" if timeframe == "1wk" else "ME"
    frame = pd.DataFrame(
        {
            "timestamp": [b.timestamp for b in bars],
            "open": [b.open for b in bars],
            "high": [b.high for b in bars],
            "low": [b.low for b in bars],
            "close": [b.close for b in bars],
            "volume": [b.volume for b in bars],
        }
    ).set_index("timestamp")
    agg = frame.resample(rule).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    agg = agg.dropna(subset=["open", "close"])
    out: list[OHLCVBar] = []
    for ts, row in agg.iterrows():
        out.append(
            OHLCVBar(
                timestamp=ts.to_pydatetime(),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
        )
    return out


def _num(value: object) -> float | None:
    """Coerce a possibly-missing/NaN jugaad cell to ``float | None``."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["PROVIDER", "get_history", "get_quote"]
