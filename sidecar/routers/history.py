"""History router — OHLCV time series for charting."""

from __future__ import annotations

from fastapi import APIRouter, Query

from models.market import OHLCVSeries
from services import provider_registry

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/{symbol}")
def get_history(
    symbol: str,
    timeframe: str = "1d",
    range_: str | None = Query(None, alias="range"),
    asset_class: str = "equity",
) -> OHLCVSeries:
    """Return an OHLCV series for ``symbol`` at the requested timeframe."""
    return provider_registry.get_history(symbol, timeframe, range_, asset_class)
