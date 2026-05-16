"""Macro router — economic / macro time series with provider routing.

Phase 1.A defined the :class:`MacroSeries` contract with a single dispatch
through ``provider_registry.get_macro_series``. Phase 3 lit it up via the
openbb-mcp subprocess for FRED. Phase 6 (v0.6.0) extends the surface with
four explicit providers — FRED / ECB / IMF / World Bank — each speaking the
richer :class:`MacroSeriesExtended` contract from
:mod:`models.macro_extended`. The Phase 6 dispatch lives in
:mod:`services.macro.macro_router`; the original Phase-1/3 ``/macro/{series_id}``
behaviour is kept for backwards-compatibility when the caller does not pass a
v0.6.0 provider literal.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from models.macro_extended import (
    MacroCatalog,
    MacroProvider,
    MacroSearchResult,
    MacroSeriesExtended,
)
from models.market import MacroSeries
from services import provider_registry
from services.errors import ProviderError
from services.macro import macro_router as macro_dispatcher

router = APIRouter(prefix="/macro", tags=["macro"])

_log = logging.getLogger(__name__)

# Providers v0.6.0 understands as first-class macro upstreams. The Phase-6
# router accepts the literal forms below and dispatches via
# :mod:`services.macro.macro_router`; anything else falls back to the
# Phase-1/3 openbb-mcp path (which keeps the legacy ``/macro/{series_id}``
# behaviour intact for any caller still passing "fred" via the legacy
# upstream path).
_V0_6_0_PROVIDERS: frozenset[str] = frozenset({"fred", "ecb", "imf", "world-bank"})


@router.get("/search", response_model=list[MacroSearchResult])
async def search_macro_series(
    q: Annotated[str, Query(min_length=1, description="Free-text query.")],
    provider: Annotated[MacroProvider, Query(description="Upstream provider to search.")],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[MacroSearchResult]:
    """Search the dispatched provider's catalog. Phase 6."""
    try:
        return await macro_dispatcher.search(q, provider, limit=limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/catalog", response_model=MacroCatalog)
async def get_macro_catalog(
    provider: Annotated[MacroProvider, Query(description="Upstream provider to list.")],
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> MacroCatalog:
    """Return the curated featured catalog for the dispatched provider. Phase 6."""
    try:
        return await macro_dispatcher.get_catalog(provider, limit=limit)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{series_id}")
async def get_macro_series(
    series_id: str,
    provider: str | None = Query(default=None, description="Upstream macro provider id"),
) -> MacroSeriesExtended | MacroSeries:
    """Return a macro time series by id.

    When ``provider`` is one of the four v0.6.0 providers (``fred``, ``ecb``,
    ``imf``, ``world-bank``), the response is a :class:`MacroSeriesExtended`
    with provider routing + caching via :mod:`services.macro.macro_router`.

    When ``provider`` is not provided or is any other value, the legacy
    Phase-1/3 ``provider_registry.get_macro_series`` path is used and the
    response is the original :class:`MacroSeries` — kept for backwards
    compatibility with any caller still on the v0.5.x contract.
    """
    if provider and provider.lower() in _V0_6_0_PROVIDERS:
        try:
            return await macro_dispatcher.get_series(series_id, provider.lower())
        except ProviderError as exc:
            # 502 keeps shape parity with the global ProviderError handler;
            # an explicit translate here lets the search/catalog endpoints
            # use the same status code.
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Legacy path — Phase 1.A / Phase 3 openbb-mcp.
    try:
        return await provider_registry.get_macro_series(series_id, provider=provider)
    except ProviderError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
