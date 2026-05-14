"""Macro router — economic/macro series.

Phase 1.A ships the :class:`MacroSeries` contract and this hook endpoint. Full
macro coverage (FRED, ECB, IMF, World Bank) arrives with the Phase 2 OpenBB ODP
wrap plugin; until then the endpoint returns 501 with the contract documented in
docs/SIDECAR_API.md.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from models.market import MacroSeries

router = APIRouter(prefix="/macro", tags=["macro"])


@router.get("/{series_id}")
def get_macro_series(series_id: str) -> MacroSeries:
    """Hook for macro series — implemented by the Phase 2 OpenBB ODP wrap."""
    raise HTTPException(
        status_code=501,
        detail=(
            f"Macro series {series_id!r}: macro data is served by the OpenBB ODP "
            "wrap plugin, scheduled for Phase 2. The MacroSeries contract is "
            "defined and ready — see docs/SIDECAR_API.md."
        ),
    )
