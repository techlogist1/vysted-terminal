"""Market-data Pydantic models — quotes, OHLCV bars, macro series.

These shapes are mirrored by hand in ``types/data.ts``; keep the two in sync
(see CLAUDE.md Gotchas).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Quote(BaseModel):
    """A point-in-time price quote for one instrument."""

    symbol: str
    price: float
    change: float
    change_percent: float
    volume: float | None = None
    currency: str = "USD"
    market_state: str | None = None
    timestamp: datetime
    provider: str


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


class MacroObservation(BaseModel):
    """One dated observation within a macro series."""

    date: datetime
    value: float | None


class MacroSeries(BaseModel):
    """An economic/macro time series (FRED-style)."""

    series_id: str
    title: str
    units: str | None = None
    observations: list[MacroObservation]
    provider: str
