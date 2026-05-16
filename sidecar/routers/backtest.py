"""Backtest router — Phase 4 wire surfaces.

Routes:

  - ``POST /backtest/run``         — SSE stream of :class:`BacktestRunEvent`
  - ``GET  /backtest/strategies``  — list registered strategies
  - ``GET  /backtest/runs``        — list cached run ids
  - ``GET  /backtest/runs/{run_id}`` — load cached BacktestResult

The default ``run`` route requires a ``bar_loader`` injection point that
the foundation does not bundle (Teammate K wires production OHLCV
loading). For v0.5.0 foundation the route is a 503 stub when invoked
without a registered loader so a frontend probe surfaces a clean error
rather than a 500.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.backtest import BacktestRequest, BacktestResult, BacktestRunEvent
from services import backtest_engine, backtest_store

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
                result = await backtest_engine.run_backtest(request, on_event=_on_event)
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
def list_strategies() -> dict[str, list[str]]:
    """List ids of strategies currently registered with the engine."""
    return {"strategies": backtest_engine.registered_strategies()}


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
