"""History router — OHLCV time series for charting."""

from __future__ import annotations

from fastapi import APIRouter, Query

import config
from models.market import OHLCVSeries
from services import provider_registry, symbol_resolver
from services.correctness_gate import EmptySeriesError
from services.locale import REGION_IN, freshness_for

router = APIRouter(prefix="/history", tags=["history"])


def _empty_series_reason(symbol: str) -> str | None:
    """A typed reason for an empty IN series so the chart can be region-aware.

    When an IN symbol (a `.NS`/`.BO` suffix, a BSE/NSE master member, or an IN
    active locale) has no EOD data from any provider, the honest cause is that
    keyless BSE/NSE serve **EOD only** — intraday/realtime needs a BYOK broker.
    The chart surfaces that instead of the generic "No price data" (WS6 Step 4).
    Returns ``None`` for a non-IN symbol (the generic message stays correct).
    """
    region = symbol_resolver.region_hint(symbol)
    if region is None:
        region = config.get_region()
    return "in_eod_only" if region == REGION_IN else None


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
    """Return an OHLCV series for ``symbol`` at the requested timeframe.

    Bug-2: if every provider returns an *empty* series (a transient gap, an
    illiquid/newly-listed/delisted name — not a server fault), the correctness
    gate raises :class:`EmptySeriesError`. We downgrade that one case to a clean
    ``200`` empty series so the chart renders its honest "No price data" state
    instead of a scary ``(502)``. A genuine integrity failure (non-positive
    close, symbol mismatch, no-provider) still propagates to the 502 handler.
    """
    try:
        series = provider_registry.get_history(symbol, timeframe, range_, asset_class)
    except EmptySeriesError:
        return OHLCVSeries(
            symbol=symbol,
            timeframe=timeframe,
            bars=[],
            provider="none",
            reason=_empty_series_reason(symbol),
        )
    return _label_series_freshness(series, asset_class, timeframe)
