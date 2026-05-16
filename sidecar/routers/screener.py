"""Screener router — Phase 6 (Teammate Sc).

Two endpoints:

  - ``POST /screener/run``        — run the screener; returns
    :class:`ScreenerResult`.
  - ``GET  /screener/universe``    — resolve a universe by id; returns
    :class:`ScreenerUniverse`.

The screener engine ( :mod:`services.screener` ) owns the filter
semantics; this router is a thin adapter that validates the request
body against the Pydantic shapes in :mod:`models.screener` and shapes
provider failures into the standard 502 response handled by the
ProviderError exception handler in :mod:`app`.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from models.screener import ScreenerRequest, ScreenerResult, ScreenerUniverse, ScreenerUniverseId
from services import screener
from services.errors import ProviderError

router = APIRouter(prefix="/screener", tags=["screener"])


@router.post("/run", response_model=ScreenerResult)
async def run_screener(request: ScreenerRequest) -> ScreenerResult:
    """Run the screener and return the matching rows.

    AND-combines every criterion. The universe is resolved on-the-fly
    (custom universes use the request's ``custom_symbols``). Provider
    failures during the fan-out are swallowed per-symbol so a single
    upstream hiccup does not fail the whole run; if the universe itself
    cannot be resolved the route returns 502.
    """
    try:
        return await screener.run_screener(request)
    except ProviderError:
        # Re-raised so the app-level exception handler maps it to 502.
        raise
    except ValueError as exc:
        # Pydantic-style validation surface beyond what the request model
        # already enforces (e.g. an unknown universe id is a ValueError
        # in the engine).
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/universe", response_model=ScreenerUniverse)
async def get_universe(
    id: ScreenerUniverseId = Query(..., description="Universe id to resolve"),  # noqa: A002, B008
) -> ScreenerUniverse:
    """Return the resolved :class:`ScreenerUniverse` for ``id``.

    For ``"custom"`` this is a 400 — custom universes only make sense
    in the context of a screener run that carries the ``custom_symbols``
    list. The frontend uses this endpoint to populate the universe-picker
    dropdown counts ("S&P 500 (100 tickers)").
    """
    if id == "custom":
        raise HTTPException(
            status_code=400,
            detail="custom universe is resolved per-request; pass custom_symbols on /screener/run",
        )
    try:
        return await screener.resolve_universe(id)
    except ProviderError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
