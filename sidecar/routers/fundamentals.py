"""Fundamentals router — valuation ratios, financial statements, analyst ratings.

Backs the equity-overview panel. Phase 1.A served these from yfinance; Phase 3
prefers openbb-mcp (the replacement for the retired Phase-2 OpenBB plugin)
with a yfinance fallback. The registry handles the dispatch; the router only
awaits the resulting coroutine.

Phase 6 (Teammate E) extends the surface with three additional ratings
endpoints — history / price-target-history / individual — backed by
:mod:`services.analyst_ratings_extended` and routed through the shared
:mod:`services.data_cache` (TTL 6h).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from models.analyst_extended import (
    IndividualAnalystResponse,
    PriceTargetHistoryResponse,
    RatingsHistoryResponse,
)
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
)
from services import analyst_ratings_extended, data_cache, provider_registry
from services.errors import ProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])

_TTL_RATINGS = 6 * 60 * 60  # 6 hours


@router.get("/{symbol}")
async def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``."""
    return await provider_registry.get_fundamentals(symbol)


@router.get("/{symbol}/income")
async def get_income_statement(symbol: str) -> IncomeStatement:
    """Return the income statement excerpt for ``symbol``."""
    return await provider_registry.get_income_statement(symbol)


@router.get("/{symbol}/balance")
async def get_balance_sheet(symbol: str) -> BalanceSheet:
    """Return the balance sheet excerpt for ``symbol``."""
    return await provider_registry.get_balance_sheet(symbol)


@router.get("/{symbol}/cashflow")
async def get_cash_flow(symbol: str) -> CashFlowStatement:
    """Return the cash-flow statement excerpt for ``symbol``."""
    return await provider_registry.get_cash_flow(symbol)


@router.get("/{symbol}/ratings")
async def get_analyst_rating(symbol: str) -> AnalystRating:
    """Return aggregated analyst ratings and price targets for ``symbol``."""
    return await provider_registry.get_analyst_rating(symbol)


# ---------------------------------------------------------------------------
# Phase 6 — extended analyst ratings (Teammate E)
# ---------------------------------------------------------------------------


@router.get("/{symbol}/ratings/history")
async def get_ratings_history(symbol: str) -> RatingsHistoryResponse:
    """Return every recorded rating change for ``symbol`` (newest-first)."""
    normalized = symbol.strip().upper()
    cache_key = f"ratings:{normalized}:history"
    cached = await data_cache.get(cache_key, _TTL_RATINGS)
    if isinstance(cached, dict):
        try:
            return RatingsHistoryResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("ratings: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await analyst_ratings_extended.get_ratings_history(normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/{symbol}/ratings/price-target-history")
async def get_price_target_history(symbol: str) -> PriceTargetHistoryResponse:
    """Return price-target changes for ``symbol`` (newest-first)."""
    normalized = symbol.strip().upper()
    cache_key = f"ratings:{normalized}:price-targets"
    cached = await data_cache.get(cache_key, _TTL_RATINGS)
    if isinstance(cached, dict):
        try:
            return PriceTargetHistoryResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("ratings: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await analyst_ratings_extended.get_price_target_history(normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response


@router.get("/{symbol}/ratings/individual")
async def get_individual_analysts(symbol: str) -> IndividualAnalystResponse:
    """Return per-firm currently-active forecasts for ``symbol``."""
    normalized = symbol.strip().upper()
    cache_key = f"ratings:{normalized}:individual"
    cached = await data_cache.get(cache_key, _TTL_RATINGS)
    if isinstance(cached, dict):
        try:
            return IndividualAnalystResponse.model_validate(cached)
        except Exception:  # noqa: BLE001
            logger.warning("ratings: cache deserialise failed for %s; refetching", cache_key)
    try:
        response = await analyst_ratings_extended.get_individual_analysts(normalized)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    await data_cache.set(cache_key, response.model_dump(mode="json"))
    return response
