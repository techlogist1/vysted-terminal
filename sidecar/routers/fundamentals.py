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

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException

from config import get_region
from models.analyst_extended import (
    IndividualAnalystResponse,
    PriceTargetHistoryResponse,
    RatingsHistoryResponse,
)
from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    CompanyNarrative,
    Fundamentals,
    IncomeStatement,
)
from services import (
    analyst_ratings_extended,
    company_narrative,
    data_cache,
    identity_crosscheck,
    provider_registry,
    resolution_policy,
    symbol_resolver,
)
from services.errors import ProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])

_TTL_RATINGS = 6 * 60 * 60  # 6 hours


async def _identity_note(symbol: str, fundamentals: Fundamentals) -> str | None:
    """R13 ledger #8 (bounded, additive): flag a resolver/provider identity
    disagreement on the plain REST surface.

    Today the SAME cross-check (:mod:`services.identity_crosscheck`, D67) only
    rides research briefs — ``/resolve`` can say "CDG Petchem Ltd" (the
    bundled master's canonical name) while ``/fundamentals`` says "Jujhar
    Logistics Limited" (the provider's, post-rename) with nothing reconciling
    them for a caller that only hits this endpoint. Resolves ``symbol`` via
    the SAME policy ``/resolve`` uses (:mod:`services.symbol_resolver` +
    :mod:`services.resolution_policy` — called, never reimplemented) and
    defers to :func:`identity_crosscheck.identity_conflict` for the
    similarity judgement + note text. Returns ``None`` (never raises) when
    the provider carried no name, the symbol did not bind, or the names
    agree — an identity cross-check must never break the endpoint it rides.
    """
    if not fundamentals.name:
        return None
    try:
        resolution = await asyncio.to_thread(symbol_resolver.resolve, symbol, get_region())
    except Exception:  # noqa: BLE001 — a resolver failure must not break /fundamentals
        return None
    decision = resolution_policy.decide(resolution)
    if decision.outcome != "bound" or decision.instrument is None:
        return None
    conflict = identity_crosscheck.identity_conflict(
        canonical_name=decision.instrument.name,
        provider_name=fundamentals.name,
        provider=fundamentals.provider,
        symbol=symbol,
    )
    return conflict["note"] if conflict else None


@router.get("/{symbol}")
async def get_fundamentals(symbol: str) -> Fundamentals:
    """Return valuation ratios and a company profile for ``symbol``.

    A provider failure surfaces as an honest 502 (mirroring the ratings
    endpoints) rather than an unhandled 500; a throttle (R11 ``ProviderError``
    ``kind='rate_limited'``) is a 429 so the client backs off instead of reading
    it as a permanent no-data miss.

    R13 ledger #8 (bounded): the response additively carries ``identity_note``
    (:func:`_identity_note`) when the resolver's canonical name and this
    provider's company name materially disagree — e.g. an exchange rename the
    provider has not caught up with. ``None`` when they agree; never a swap.
    """
    try:
        fundamentals = await provider_registry.get_fundamentals(symbol)
    except ProviderError as exc:
        if exc.kind == "rate_limited":
            raise HTTPException(
                status_code=429,
                detail="Data provider is throttled — try again shortly.",
            ) from exc
        if exc.kind == "not_found":
            raise HTTPException(
                status_code=404,
                detail=f"No instrument matches {symbol!r} — check the symbol.",
            ) from exc
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    fundamentals.identity_note = await _identity_note(symbol, fundamentals)
    return fundamentals


# ---------------------------------------------------------------------------
# AI narrative — LLM-written, numerically-verified company overview
# ---------------------------------------------------------------------------
#
# BYOK credentials arrive in HEADERS (read-only GET path, never the body):
#   X-LLM-Provider   — one of the seven provider ids (anthropic, openai, …)
#   X-LLM-Model      — provider-specific model id
#   X-LLM-Api-Key    — the BYOK key, read from the OS keychain by the renderer
#
# The sidecar CANNOT read the keychain; the renderer forwards the secret per
# request. It is held in memory for the call only — never logged, echoed, or
# persisted. Loopback transport only. Missing credentials are NOT an error: the
# service returns a 200 with summary=None + a reason so the panel renders a quiet
# "AI narrative unavailable" state rather than a failure banner.

LlmProviderHeader = Annotated[
    str | None,
    Header(alias="X-LLM-Provider", description="BYOK LLM provider id for the narrative."),
]
LlmModelHeader = Annotated[
    str | None,
    Header(alias="X-LLM-Model", description="Provider-specific model id."),
]
LlmApiKeyHeader = Annotated[
    str | None,
    Header(alias="X-LLM-Api-Key", description="BYOK key — held in memory for the call only."),
]
RegionHeader = Annotated[
    str | None,
    Header(alias="X-Vysted-Region", description="Optional market region hint for the quote."),
]


@router.get("/{symbol}/narrative")
async def get_company_narrative(
    symbol: str,
    provider: LlmProviderHeader = None,
    model: LlmModelHeader = None,
    api_key: LlmApiKeyHeader = None,
    region: RegionHeader = None,
) -> CompanyNarrative:
    """Return an LLM-written, numerically-verified narrative for ``symbol``.

    Every number in the returned prose has been matched against the real
    fundamentals/quote the panel renders; hallucinated figures are redacted and
    listed in ``unverified_claims``. Always 200 — no key / no model / no data
    yields ``summary=None`` + a ``reason`` for a graceful empty state.
    """
    return await company_narrative.generate_narrative(
        symbol,
        provider=provider,
        model=model,
        api_key=api_key,
        region=region,
    )


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
