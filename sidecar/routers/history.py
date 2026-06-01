"""History router — OHLCV time series for charting."""

from __future__ import annotations

from fastapi import APIRouter, Query

import config
from models.market import OHLCVSeries
from services import provider_registry
from services.locale import freshness_for

router = APIRouter(prefix="/history", tags=["history"])


def _label_series_freshness(series: OHLCVSeries, asset_class: str, timeframe: str) -> OHLCVSeries:
    """Stamp the calendar-aware staleness of the LAST bar (FR-041 / SC-019).

    So the chart never shows a stale series as current. Crypto is 24/7 (``live``);
    equity/ETF freshness reads the last bar's date against the locale calendar —
    intraday timeframes (minute/hour) classify as live while the session is open,
    daily+ bars as the legitimate end-of-day close.
    """
    if not series.bars:
        return series
    if asset_class == "crypto":
        series.freshness = "live"
        return series
    tf = timeframe.lower()
    intraday = ("m" in tf or "h" in tf) and "mo" not in tf
    try:
        series.freshness = freshness_for(
            config.get_region(), series.bars[-1].timestamp.date(), intraday=intraday
        ).state
    except Exception:  # noqa: BLE001 — a label failure must never drop the series
        series.freshness = None
    return series


@router.get("/{symbol}")
def get_history(
    symbol: str,
    timeframe: str = "1d",
    range_: str | None = Query(None, alias="range"),
    asset_class: str = "equity",
) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at the requested timeframe."""
    series = provider_registry.get_history(symbol, timeframe, range_, asset_class)
    return _label_series_freshness(series, asset_class, timeframe)
