"""Disclosures router — India corporate announcements / results / shareholding.

R7 Component 3. Serves the typed feeds from
:mod:`services.corporate_disclosures` (merged BSE+NSE announcements deduped by
``(symbol, headline-hash, date)``, the NSE+BSE results calendar, and the quarterly
shareholding patterns) through :mod:`services.data_cache` with domain-tuned
TTLs:

* announcements — 15 minutes, cached inside the service
  (:func:`corporate_disclosures.get_announcements_cached`, shared with the agent
  tool and research; also respects the NSE throttle)
* results calendar — 6 hours
* shareholding — 24 hours (a quarterly series)
* corporate actions — 6 hours (NSE+BSE dividends/bonuses/splits/rights/buybacks)
* deals — 6 hours (bulk/block deals and SAST disclosures)

The service functions are synchronous (they drive the sync exchange lanes), so
each route runs them in ``asyncio.to_thread``. Registration: see
``docs/redesign/INTEGRATION_NOTES_R7.md`` (this router is tested standalone).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from models.announcements import (
    AnnouncementsResponse,
    CorporateActionsResponse,
    ExchangeDealsResponse,
    ResultsCalendarResponse,
    ShareholdingResponse,
)
from services import corporate_disclosures, data_cache, sec_ownership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disclosures", tags=["disclosures"])

_TTL_RESULTS = 6 * 60 * 60  # 6 hours
_TTL_SHAREHOLDING = 24 * 60 * 60  # 24 hours
_TTL_CORPORATE_ACTIONS = 6 * 60 * 60  # 6 hours
_TTL_DEALS = 6 * 60 * 60  # 6 hours (the exchanges publish deals end of day)


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
    return await corporate_disclosures.get_announcements_cached(symbol, exchange, limit)


@router.get("/results")
async def get_results(
    symbol: Annotated[str, Query(min_length=1, description="NSE/BSE ticker, e.g. RELIANCE")],
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
    response = await asyncio.to_thread(corporate_disclosures.get_results_calendar, normalized)
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/shareholding")
async def get_shareholding(
    symbol: Annotated[str, Query(min_length=1, description="NSE/BSE ticker, e.g. RELIANCE")],
) -> ShareholdingResponse:
    """Quarterly shareholding patterns for ``symbol``, newest quarter first; a
    US-listed ADR answers its 20-F major holders instead (R15-DATA-060)."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:shareholding:{normalized}"
    cached = await data_cache.get(cache_key, _TTL_SHAREHOLDING)
    if isinstance(cached, dict):
        try:
            return ShareholdingResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    response = await asyncio.to_thread(corporate_disclosures.get_shareholding, normalized)
    response = await sec_ownership.attach_major_shareholders(response)
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/corporate-actions")
async def get_corporate_actions(
    symbol: Annotated[str, Query(min_length=1, description="NSE/BSE ticker, e.g. JONJUA")],
) -> CorporateActionsResponse:
    """Dividends, bonuses, splits, rights and buybacks (NSE+BSE), newest first."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:corporate-actions:{normalized}"
    cached = await data_cache.get(cache_key, _TTL_CORPORATE_ACTIONS)
    if isinstance(cached, dict):
        try:
            return CorporateActionsResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    response = await asyncio.to_thread(corporate_disclosures.get_corporate_actions, normalized)
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/deals")
async def get_deals(
    symbol: Annotated[str, Query(min_length=1, description="NSE/BSE ticker, e.g. KOPRAN")],
    kind: Annotated[
        Literal["bulk", "block", "sast"] | None,
        Query(description="Optional filter; omit for bulk, block and SAST together."),
    ] = None,
) -> ExchangeDealsResponse:
    """Bulk deals, block deals and SAST disclosures for ``symbol``, newest first."""
    normalized = symbol.strip().upper()
    cache_key = f"disclosures:deals:{normalized}:{kind or 'ALL'}"
    cached = await data_cache.get(cache_key, _TTL_DEALS)
    if isinstance(cached, dict):
        try:
            return ExchangeDealsResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("disclosures: cache deserialise failed for %s; refetching", cache_key)
    response = await asyncio.to_thread(corporate_disclosures.get_deals, normalized, kind)
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


__all__ = ["router"]
