"""Market-data Pydantic models — quotes, OHLCV bars, macro series.

These shapes are mirrored by hand in ``types/data.ts``; keep the two in sync
(see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

#: Calendar-aware staleness label. ``unknown`` = the label could not be computed
#: (R15-DATA-105) — still badged, never read as live.
Freshness = Literal["live", "eod", "stale", "unknown"]


class Quote(BaseModel):
    """A point-in-time price quote for one instrument."""

    symbol: str
    price: float
    # ``None`` when the lane does not know the day's change (no prior close) —
    # never a fabricated 0.0 (R15-DATA-103).
    change: float | None
    change_percent: float | None
    volume: float | None = None
    # The session's open/high/low and the prior close, where the lane reports
    # them (R15-DATA-053); null when it does not.
    open: float | None = None
    high: float | None = None
    low: float | None = None
    prev_close: float | None = None
    currency: str = "USD"
    market_state: str | None = None
    timestamp: datetime
    provider: str
    # Calendar-aware staleness label, set by the quotes router from
    # ``locale.freshness_for`` so the UI never shows a stale value as live
    # (FR-041 / SC-019). Optional + additive.
    freshness: Freshness | None = None


class OHLCVBar(BaseModel):
    """A single open/high/low/close/volume bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCVSeries(BaseModel):
    """An ordered series of OHLCV bars for one symbol and timeframe."""

    symbol: str
    timeframe: str
    bars: list[OHLCVBar]
    provider: str
    # Calendar-aware staleness of the LAST bar, set by the history router so the
    # chart never shows a stale series as current (FR-041 / SC-019). Optional +
    # additive.
    freshness: Freshness | None = None
    # A typed reason for an EMPTY series, set by the history router when every
    # provider returned no data, so the chart shows a region-aware honest message
    # instead of the generic "No price data" (WS6 Step 4).
    # in_eod_only = BSE/NSE serve end-of-day data only; no intraday/realtime lane exists for this listing  # noqa: E501
    # unknown_symbol = no bundled equity/ETF master knows the symbol at all (R15-LEAD-026)
    # None for a populated series or a non-region-specific empty.
    reason: str | None = None
    # True when day files are missing inside the requested range; the series is
    # complete from ``coverage_start`` on (R15-DATA-071).
    partial: bool = False
    coverage_start: date | None = None


class MacroObservation(BaseModel):
    """One dated observation within a macro series."""

    date: datetime
    value: float | None
    # A forecast, not an outturn (e.g. an IMF WEO year at or after the
    # vintage) — R15-LEAD-024.
    is_projection: bool = False


class MacroSeries(BaseModel):
    """An economic/macro time series (FRED-style)."""

    series_id: str
    title: str
    units: str | None = None
    observations: list[MacroObservation]
    provider: str


class OptionContract(BaseModel):
    """One listed option contract's end-of-day row in an option chain (R15-DATA-079)."""

    expiry: date
    strike: float
    option_type: Literal["call", "put"]
    # Exchange-published open interest and its change on the session; null
    # where the source does not report it.
    open_interest: float | None = None
    change_in_oi: float | None = None
    last_price: float | None = None
    # The exchange settlement price (NSE F&O); null on the US leg.
    settle_price: float | None = None
    volume: float | None = None
    # The source's implied volatility (US leg, yfinance); null on the NSE leg.
    implied_volatility: float | None = None


class OptionChain(BaseModel):
    """One expiry of a symbol's listed option chain, as the source published it.

    Research data only (D81): exchange-published EOD OI and prices, never a
    trading surface. ``as_of`` is the session the values describe.
    """

    symbol: str
    expiry: date
    #: Every expiry the source lists for the symbol, nearest first.
    expiries: list[date]
    underlying_price: float | None = None
    contracts: list[OptionContract]
    as_of: date
    provider: str
    currency: str
    #: Calendar-aware staleness of ``as_of`` ("eod" | "stale").
    freshness: str | None = None
