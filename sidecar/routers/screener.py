"""Screener router — Phase 6 (Teammate Sc); R7 Pillar 3 formula layer; R10 SSE.

Four endpoints:

  - ``POST /screener/run``              — run the screener (unary, now wall-
    budget-bounded — D40); returns :class:`ScreenerResult`.
  - ``POST /screener/run/stream``        — the same run as an SSE stream:
    ``{"event":"progress",phase,done,total,detail}`` frames per engine
    phase/chunk, then one ``{"event":"result", …ScreenerResult}``. A client
    disconnect cancels the engine task; the engine finalizes its partial
    (the store keeps every completed chunk) and stops.
  - ``GET  /screener/universe``          — resolve a universe by id; returns
    :class:`ScreenerUniverse`.
  - ``POST /screener/formula/validate``  — validate a custom formula against
    the restricted expression grammar; returns :class:`FormulaValidation`
    (``ok`` / ``error`` / caret ``position`` / referenced ``fields``) — never
    a 4xx for a bad formula.

The screener engine ( :mod:`services.screener` ) owns the filter
semantics; this router is a thin adapter that validates the request
body against the Pydantic shapes in :mod:`models.screener` and shapes
provider failures into the standard 502 response handled by the
ProviderError exception handler in :mod:`app`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from models.screener import (
    FormulaValidation,
    ScreenerRequest,
    ScreenerResult,
    ScreenerUniverse,
    ScreenerUniverseId,
)
from services import screener, screener_formula
from services.errors import ProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/screener", tags=["screener"])


class FormulaValidateRequest(BaseModel):
    """Body for ``POST /screener/formula/validate``."""

    model_config = ConfigDict(extra="forbid")

    formula: str


@router.post("/run", response_model=ScreenerResult)
async def run_screener(request: ScreenerRequest) -> ScreenerResult:
    """Run the screener and return the matching rows.

    AND-combines every criterion. The universe is resolved on-the-fly
    (custom universes use the request's ``custom_symbols``). Provider
    failures during the fan-out are swallowed per-symbol so a single
    upstream hiccup does not fail the whole run; if the universe itself
    cannot be resolved the route returns 502.

    ``ScreenerRequest.universe`` is required (no default), so the universe is
    always explicit here — region-aware default selection (US→sp500, IN→nifty50,
    FR-060) lives in ``services.screener.default_universe_for_region`` for the
    callers that must *choose* a default rather than override an explicit one.
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


def _sse_frame(payload: dict) -> bytes:
    """One SSE ``data:`` frame (precedent ``routers/backtest.py``)."""
    return f"data: {json.dumps(payload)}\n\n".encode()


@router.post("/run/stream")
async def run_screener_stream(request: ScreenerRequest) -> StreamingResponse:
    """Run the screener with live progress over SSE (R10, D40).

    Frames are ``{"event":"progress",phase,done,total,detail}`` (mirrors
    ``ScreenerProgressFrame`` in ``types/screener.ts``) followed by one
    ``{"event":"result", …ScreenerResult}``. The engine runs as a separate
    task; when the client disconnects the generator is torn down and the task
    cancelled — the engine catches the cancellation, finalizes an honest
    partial, and stops (no orphaned sweep).
    """

    async def _generator() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def _on_progress(phase: str, done: int, total: int, detail: str) -> None:
            frame = {"event": "progress", "phase": phase, "done": done, "total": total}
            queue.put_nowait({**frame, "detail": detail})

        async def _run() -> None:
            try:
                result = await screener.run_screener(request, on_progress=_on_progress)
                await queue.put({"event": "result", **result.model_dump(mode="json")})
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — surface a clean error frame
                logger.exception("screener stream run crashed")
                await queue.put({"event": "error", "message": str(exc)})
            finally:
                queue.put_nowait(None)

        task = asyncio.create_task(_run())
        try:
            while True:
                frame = await queue.get()
                if frame is None:
                    break
                yield _sse_frame(frame)
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(_generator(), media_type="text/event-stream")


@router.post("/formula/validate", response_model=FormulaValidation)
async def validate_formula(request: FormulaValidateRequest) -> FormulaValidation:
    """Validate a custom screener formula (R7 Pillar 3).

    The recovery-first inline-validation surface: a malformed formula is an
    ``ok: false`` body carrying the parser's message and 0-based caret
    ``position`` — never an HTTP error — so an editor or the agent can render
    the ``^`` marker and self-correct. A valid formula returns the sorted
    canonical fields it references.
    """
    return FormulaValidation(**screener_formula.validate_formula(request.formula))


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
