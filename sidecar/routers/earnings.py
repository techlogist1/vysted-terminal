"""Earnings router — calendar / history / surprises / estimate-detail.

Backs the Earnings Calendar panel (Phase 6, Teammate E). Reads through
:mod:`services.data_cache` with domain-tuned TTLs:

* upcoming-calendar reads — TTL 6 hours
* history + surprises reads — TTL 24 hours
* estimate detail reads — TTL 6 hours (estimates refresh more aggressively)

The provider lives in :mod:`services.earnings_provider`; the router
serialises Pydantic responses through the cache (set on miss, hit on
fresh) so repeat calls within the TTL skip the upstream entirely.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from models.earnings import (
    EarningsEstimateDetail,
    EarningsHistoryResponse,
    EarningsSurprisesResponse,
    EarningsUpcomingResponse,
)
from services import data_cache, earnings_provider
from services.errors import ProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/earnings", tags=["earnings"])

_TTL_UPCOMING = 6 * 60 * 60  # 6 hours
_TTL_HISTORY = 24 * 60 * 60  # 24 hours
_TTL_ESTIMATES = 6 * 60 * 60  # 6 hours


def _watchlist_key(watchlist: list[str] | None) -> str:
    if not watchlist:
        return "default"
    return ",".join(sorted({s.strip().upper() for s in watchlist if s.strip()}))


@router.get("/upcoming")
async def get_upcoming(
    days: Annotated[int, Query(ge=1, le=60)] = 7,
    watchlist: Annotated[str | None, Query(description="Comma-separated symbols")] = None,
) -> EarningsUpcomingResponse:
    """Return scheduled earnings events in the next ``days`` days.

    ``watchlist`` is a comma-separated symbol list; empty / missing means
    "use the provider's default universe of large-caps so the panel
    populates out-of-the-box".
    """
    today = datetime.now(tz=UTC).date()
    start = today
    end = today + timedelta(days=days)
    parsed_watchlist: list[str] | None = None
    if watchlist:
        parsed_watchlist = [s.strip() for s in watchlist.split(",") if s.strip()]
    cache_key = (
        f"earnings:upcoming:{start.isoformat()}:{end.isoformat()}:"
        f"{_watchlist_key(parsed_watchlist)}"
    )
    cached = await data_cache.get(cache_key, _TTL_UPCOMING)
    if isinstance(cached, dict):
        try:
            return EarningsUpcomingResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("earnings: cache deserialise failed for %s; refetching", cache_key)

    try:
        response = await earnings_provider.get_upcoming(start, end, parsed_watchlist)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/{symbol}/history")
async def get_history(symbol: str) -> EarningsHistoryResponse:
    """Return past earnings results for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"earnings:{normalized}:history"
    cached = await data_cache.get(cache_key, _TTL_HISTORY)
    if isinstance(cached, dict):
        try:
            return EarningsHistoryResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("earnings: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await earnings_provider.get_history(normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/{symbol}/surprises")
async def get_surprises(symbol: str) -> EarningsSurprisesResponse:
    """Return per-quarter EPS surprise rows for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"earnings:{normalized}:surprises"
    cached = await data_cache.get(cache_key, _TTL_HISTORY)
    if isinstance(cached, dict):
        try:
            return EarningsSurprisesResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("earnings: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await earnings_provider.get_surprises(normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/{symbol}/estimates")
async def get_estimate_detail(symbol: str) -> EarningsEstimateDetail:
    """Return the next-event analyst-estimate detail for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"earnings:{normalized}:estimates"
    cached = await data_cache.get(cache_key, _TTL_ESTIMATES)
    if isinstance(cached, dict):
        try:
            return EarningsEstimateDetail.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("earnings: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await earnings_provider.get_estimate_detail(normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


# Re-export the date primitive so the unused import does not trip ruff F401.
__all__ = ["date", "router"]
