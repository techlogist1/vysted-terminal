"""Macro router — economic/macro series.

Phase 1.A defined the :class:`MacroSeries` contract; Phase 3 lights it up via
openbb-mcp (the Phase-3 replacement for the retired Phase-2 OpenBB plugin).
When openbb-mcp is not bundled the registry raises :class:`ProviderError` and
the router translates that into a 501 — the legacy contract from Phase 1.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from models.market import MacroSeries
from services import provider_registry
from services.errors import ProviderError

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/{series_id}")
async def get_macro_series(
    series_id: str,
    provider: str | None = Query(default=None, description="Upstream macro provider id"),
) -> MacroSeries:
    """Return a macro time-series by id via openbb-mcp."""
    try:
        return await provider_registry.get_macro_series(series_id, provider=provider)
    except ProviderError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
