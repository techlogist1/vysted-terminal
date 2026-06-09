"""Disclosures router — India corporate announcements / results / shareholding.

R7 Component 3. Serves the typed feeds from
:mod:`services.corporate_disclosures` (merged BSE+NSE announcements deduped by
``(symbol, headline-hash, date)``, the NSE results calendar, and the quarterly
shareholding patterns) through :mod:`services.data_cache` with domain-tuned
TTLs:

* announcements — 15 minutes (the live-ish feed; also respects the NSE
  throttle by not re-walking the cookie dance per panel refresh)
* results calendar — 6 hours
* shareholding — 24 hours (a quarterly series)

The service functions are synchronous (they drive the sync exchange lanes), so
each route runs them in ``asyncio.to_thread``. Registration: see
``docs/redesign/INTEGRATION_NOTES_R7.md`` (this router is tested standalone).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query

from models.announcements import (
    AnnouncementsResponse,
    ResultsCalendarResponse,
    ShareholdingResponse,
)
from services import corporate_disclosures, data_cache
from services.errors import ProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disclosures", tags=["disclosures"])

_TTL_ANNOUNCEMENTS = 15 * 60  # 15 minutes
_TTL_RESULTS = 6 * 60 * 60  # 6 hours
_TTL_SHAREHOLDING = 24 * 60 * 60  # 24 hours


@router.get("/announcements")
async def get_announcements(
    symbol: Annotated[str, Query(min_length=1, description="NSE/BSE ticker, e.g. RELIANCE")],
    exchange: Annotated[
        Literal["NSE", "BSE"] | None,
        Query(description="Optional single-exchange filter; omit to merge both feeds."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=corporate_disclosures.MAX_LIMIT)] = (
        corporate_disclosures.DEFAULT_LIMIT
    ),
) -> AnnouncementsResponse:
    """Merged BSE+NSE corporate announcements for ``symbol``, newest first."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:announcements:{normalized}:{exchange or 'ALL'}:{limit}"
    cached = await data_cache.get(cache_key, _TTL_ANNOUNCEMENTS)
    if isinstance(cached, dict):
        try:
            return AnnouncementsResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await asyncio.to_thread(
            corporate_disclosures.get_announcements, normalized, exchange, limit
        )
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/results")
async def get_results(
    symbol: Annotated[str, Query(min_length=1, description="NSE ticker, e.g. RELIANCE")],
) -> ResultsCalendarResponse:
    """Results-calendar / board-meeting events for ``symbol``, newest first."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:results:{normalized}"
    cached = await data_cache.get(cache_key, _TTL_RESULTS)
    if isinstance(cached, dict):
        try:
            return ResultsCalendarResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await asyncio.to_thread(corporate_disclosures.get_results_calendar, normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/shareholding")
async def get_shareholding(
    symbol: Annotated[str, Query(min_length=1, description="NSE ticker, e.g. RELIANCE")],
) -> ShareholdingResponse:
    """Quarterly shareholding patterns for ``symbol``, newest quarter first."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:shareholding:{normalized}"
    cached = await data_cache.get(cache_key, _TTL_SHAREHOLDING)
    if isinstance(cached, dict):
        try:
            return ShareholdingResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await asyncio.to_thread(corporate_disclosures.get_shareholding, normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


__all__ = ["router"]
