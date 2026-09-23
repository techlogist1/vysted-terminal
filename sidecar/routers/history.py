"""History router — OHLCV time series for charting."""

from __future__ import annotations

from fastapi import APIRouter, Query

import config
from models.market import OHLCVSeries
from services import provider_registry, symbol_resolver
from services.correctness_gate import EmptySeriesError
from services.locale import REGION_IN, freshness_for, instrument_region, region_for_suffix

router = APIRouter(prefix="/history", tags=["history"])


def _is_intraday(timeframe: str) -> bool:
    tf = timeframe.lower()
    return ("m" in tf or "h" in tf) and "mo" not in tf


def _empty_series_reason(symbol: str, timeframe: str) -> str | None:
    """A typed reason for an empty series the chart can state honestly.

    ``in_eod_only`` (keyless BSE/NSE serve end-of-day only, so no intraday lane
    exists) is true only for an INTRADAY timeframe on a KNOWN IN listing (a
    ``.NS``/``.BO`` suffix or an NSE/BSE master member) in an IN context. An empty
    daily series (a no-trade year), a caret index or an unknown symbol has some
    other cause, so it gets ``None`` and the chart keeps its generic copy
    (R15-DATA-064).
    """
    if not _is_intraday(timeframe):
        return None
    known_in = (
        region_for_suffix(symbol) == REGION_IN
        or symbol_resolver.is_nse_symbol(symbol)
        or symbol_resolver.is_bse_symbol(symbol)
    )
    region = symbol_resolver.region_hint(symbol) or config.get_region()
    return "in_eod_only" if known_in and region == REGION_IN else None


def _label_series_freshness(series: OHLCVSeries, asset_class: str, timeframe: str) -> OHLCVSeries:
    """Stamp the calendar-aware staleness of the LAST bar (FR-041 / SC-019).

    So the chart never shows a stale series as current. Crypto is 24/7 (``live``);
    equity/ETF freshness reads the last bar's date against the calendar of the
    instrument's own exchange, not the session region (R15-UI-090) —
    intraday timeframes (minute/hour) classify as live while the session is open,
    daily+ bars as the legitimate end-of-day close.
    """
    if not series.bars:
        return series
    if asset_class == "crypto":
        series.freshness = "live"
        return series
    intraday = _is_intraday(timeframe)
    try:
        region = instrument_region(series.symbol, series.provider)
        series.freshness = freshness_for(
            region, series.bars[-1].timestamp.date(), intraday=intraday
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
            reason=_empty_series_reason(symbol, timeframe),
        )
    return _label_series_freshness(series, asset_class, timeframe)
