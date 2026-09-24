"""Indicators router — technical-indicator computation for the chart panel.

Computes the requested indicators server-side (numpy/pandas) against a symbol's
OHLCV history fetched through the provider registry, and returns them in the
``IndicatorResponse`` shape the chart panel overlays. This file is already
mounted by ``app.create_app`` — only edit this file, not ``app.py``.

Provider failures raise ``services.errors.ProviderError``, which the app-level
handler translates to HTTP 502. Unknown indicator keys return HTTP 400.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from models.indicators import IndicatorResponse
from services import indicators as indicator_service
from services import provider_registry
from services.correctness_gate import EmptySeriesError
from services.research.fast import _suggested_indicators

router = APIRouter(prefix="/indicators", tags=["indicators"])


def _parse_indicators(raw: str) -> list[str]:
    """Split the comma-separated ``indicators`` query value into clean tokens."""
    return [token.strip() for token in raw.split(",") if token.strip()]


# NOTE: both static routes (``""`` and ``"/suggested"``) are declared before
# ``/{symbol}`` so FastAPI matches them first rather than treating their path
# segment as a symbol.


@router.get("")
def list_indicators() -> dict[str, list[str]]:
    """Return every indicator key the chart panel may request."""
    return {"indicators": list(indicator_service.SUPPORTED_INDICATORS)}


@router.get("/suggested")
def suggested_indicators(
    timeframe: str = "1d", asset_class: str = "equity"
) -> dict[str, list[str]]:
    """The chart's opening indicator set for an (asset class, timeframe) pair
    (FR-092 / R15-UI-091) — a fresh, untouched chart seeds from this so its
    defaults are never blank. ``_suggested_indicators`` is the ONE source
    (also used by the research cockpit's own suggestion) — no second table."""
    return {"indicators": _suggested_indicators(timeframe=timeframe, asset_class=asset_class)}


@router.get("/{symbol:path}")  # a crypto pair carries "/" (R15-DATA-081)
def get_indicators(
    symbol: str,
    indicators: str = Query(
        ...,
        description="Comma-separated indicator keys, e.g. rsi,macd,bollinger.",
    ),
    timeframe: str = "1d",
    range_: str | None = Query(None, alias="range"),
    asset_class: str = "equity",
) -> IndicatorResponse:
    """Compute the requested indicators for ``symbol`` over its OHLCV history."""
    requested = _parse_indicators(indicators)
    if not requested:
        raise HTTPException(status_code=400, detail="No indicators requested.")

    unknown = [token for token in requested if indicator_service.normalize_key(token) is None]
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown indicator(s): {', '.join(unknown)}. "
                f"Supported: {', '.join(indicator_service.SUPPORTED_INDICATORS)}."
            ),
        )

    try:
        series = provider_registry.get_history(symbol, timeframe, range_, asset_class)
    except EmptySeriesError:
        # The /history downgrade (R15-DATA-063): no bars is an honest empty
        # chart, not a 502 overlay error beside it.
        return IndicatorResponse(symbol=symbol, timeframe=timeframe, provider="none", indicators=[])
    return indicator_service.compute(series, requested)
