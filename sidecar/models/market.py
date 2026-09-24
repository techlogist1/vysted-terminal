"""Market-data Pydantic models — quotes, OHLCV bars, macro series.

These shapes are mirrored by hand in ``types/data.ts``; keep the two in sync
(see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class Quote(BaseModel):
    """A point-in-time price quote for one instrument."""

    symbol: str
    price: float
    change: float
    change_percent: float
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
    # Calendar-aware staleness label ("live" | "eod" | "stale"), set by the
    # quotes router from ``locale.freshness_for`` so the UI never shows a stale
    # value as live (FR-041 / SC-019). Optional + additive.
    freshness: str | None = None


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
    # Calendar-aware staleness of the LAST bar ("live" | "eod" | "stale"), set by
    # the history router so the chart never shows a stale series as current
    # (FR-041 / SC-019). Optional + additive.
    freshness: str | None = None
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
