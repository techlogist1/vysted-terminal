"""Backtest router — Phase 4 wire surfaces.

Routes:

  - ``POST /backtest/run``         — SSE stream of :class:`BacktestRunEvent`
  - ``GET  /backtest/strategies``  — list registered strategies
  - ``GET  /backtest/runs``        — list cached run ids
  - ``GET  /backtest/runs/{run_id}`` — load cached BacktestResult

The ``run`` route consumes ``services.bar_loader.load_bars`` (Teammate K,
v0.5.0) for production OHLCV loading via the Phase 1 ``provider_registry``
(yfinance / ccxt / openbb-mcp). The v0.5.0-era 503-stub fallback is no
longer reachable — the loader is unconditionally wired.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.backtest import BacktestRequest, BacktestResult, BacktestRunEvent
from services import backtest_engine, backtest_store
from services.backtest_strategies import list_strategy_specs
from services.bar_loader import load_bars

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtest", tags=["backtest"])


# ---------------------------------------------------------------------------
# Run (SSE)
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_backtest(request: BacktestRequest) -> StreamingResponse:
    """Open an SSE stream of BacktestRunEvent JSON frames."""

    async def _generator() -> AsyncIterator[bytes]:
        import asyncio

        queue: asyncio.Queue[BacktestRunEvent | None] = asyncio.Queue()

        async def _on_event(event: BacktestRunEvent) -> None:
            await queue.put(event)

        async def _run() -> None:
            try:
                result = await backtest_engine.run_backtest(
                    request,
                    bar_loader=load_bars,
                    on_event=_on_event,
                )
                backtest_store.put(result)
            except NotImplementedError as exc:
                # Foundation has no default bar_loader; v0.5.0 production
                # wiring lives in Teammate K's branch. Surface a clean
                # error event.
                await queue.put(
                    BacktestRunEvent(
                        kind="run-error",
                        runId="_no_loader",
                        message=str(exc),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("backtest run crashed: %s", exc)
                await queue.put(
                    BacktestRunEvent(
                        kind="run-error",
                        runId="_engine_error",
                        message=str(exc),
                    )
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(_run())
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield _encode_event(event)
        finally:
            if not task.done():
                task.cancel()

    return StreamingResponse(_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Discovery + cache
# ---------------------------------------------------------------------------


@router.get("/strategies")
def list_strategies() -> dict[str, list[dict]]:
    """List registered strategies with their metadata + paramsSchema.

    The frontend's strategy picker renders a form from each spec's
    ``paramsSchema`` — returning the full Teammate K shape (id + name +
    description + paramsSchema) is strictly more useful than ids alone.
    Filtered to the intersection of (registered with engine) and
    (Teammate K spec catalogued) so plugin-contributed strategies in
    future phases that skip the catalogue surface as ids elsewhere.
    """
    engine_ids = set(backtest_engine.registered_strategies())
    specs = [spec for spec in list_strategy_specs() if spec["id"] in engine_ids]
    return {"strategies": specs}


@router.get("/runs")
def list_runs() -> dict[str, list[str]]:
    """List run ids currently in the in-memory cache (newest first)."""
    return {"runs": [r.run_id for r in backtest_store.list_runs()]}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> BacktestResult:
    """Return the cached BacktestResult for ``run_id``."""
    result = backtest_store.get(run_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"unknown run_id {run_id!r}")
    return result


# ---------------------------------------------------------------------------
# SSE encoder
# ---------------------------------------------------------------------------


def _encode_event(event: BacktestRunEvent) -> bytes:
    return f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}\n\n".encode()


def _encode_event_dict(payload: dict) -> bytes:  # pragma: no cover - kept for parity
    return f"data: {json.dumps(payload)}\n\n".encode()
