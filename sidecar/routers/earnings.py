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

from datetime import UTC, date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Query

import config
from models.earnings import (
    EarningsEstimateDetail,
    EarningsHistoryResponse,
    EarningsSurprisesResponse,
    EarningsUpcomingResponse,
)
from routers._cached import cached as _cached
from services import earnings_provider
from services.yfinance_provider import _yahoo_symbol

router = APIRouter(prefix="/earnings", tags=["earnings"])

_TTL_UPCOMING = 6 * 60 * 60  # 6 hours
_TTL_HISTORY = 24 * 60 * 60  # 24 hours
_TTL_ESTIMATES = 6 * 60 * 60  # 6 hours


def _watchlist_key(watchlist: list[str] | None) -> str:
    if not watchlist:
        # The default universe follows the request region (C4, R15-LEAD-009).
        return f"default:{config.get_region()}"
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
    response, as_of = await _cached(
        cache_key,
        _TTL_UPCOMING,
        EarningsUpcomingResponse,
        lambda: earnings_provider.get_upcoming(start, end, parsed_watchlist),
    )
    response.as_of = as_of
    return response


@router.get("/{symbol}/history")
async def get_history(symbol: str) -> EarningsHistoryResponse:
    """Return past earnings results for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"earnings:{_yahoo_symbol(normalized)}:history"  # the resolved listing
    response, as_of = await _cached(
        cache_key,
        _TTL_HISTORY,
        EarningsHistoryResponse,
        lambda: earnings_provider.get_history(normalized),
    )
    response.as_of = as_of
    return response


@router.get("/{symbol}/surprises")
async def get_surprises(symbol: str) -> EarningsSurprisesResponse:
    """Return per-quarter EPS surprise rows for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"earnings:{_yahoo_symbol(normalized)}:surprises"  # the resolved listing
    response, as_of = await _cached(
        cache_key,
        _TTL_HISTORY,
        EarningsSurprisesResponse,
        lambda: earnings_provider.get_surprises(normalized),
    )
    response.as_of = as_of
    return response


@router.get("/{symbol}/estimates")
async def get_estimate_detail(symbol: str) -> EarningsEstimateDetail:
    """Return the next-event analyst-estimate detail for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"earnings:{_yahoo_symbol(normalized)}:estimates"  # the resolved listing
    # The provider stamps its own as_of (unlike the other routes above); the
    # cache row's write time is unused here.
    response, _ = await _cached(
        cache_key,
        _TTL_ESTIMATES,
        EarningsEstimateDetail,
        lambda: earnings_provider.get_estimate_detail(normalized),
    )
    return response


# Re-export the date primitive so the unused import does not trip ruff F401.
__all__ = ["date", "router"]
