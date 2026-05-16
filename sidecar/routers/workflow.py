"""Workflow router — Phase 4 wire surfaces.

Routes:

  - ``POST /workflow/run``        — SSE stream of :class:`WorkflowRunEvent`
  - ``POST /workflow/save``       — persist a workflow spec (upsert)
  - ``GET  /workflow/saved``      — list all saved workflows
  - ``GET  /workflow/saved/{id}`` — load one saved workflow
  - ``DELETE /workflow/saved/{id}`` — delete a saved workflow

The run route streams over SSE in the same shape as the v0.4.0
``POST /llm/chat`` and ``POST /agents/{id}/invoke`` routes — JSON event
frames separated by ``\\n\\n``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.workflow import WorkflowRunEvent, WorkflowRunRequest, WorkflowSpec
from services import workflow_engine, workflow_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])


# ---------------------------------------------------------------------------
# Run — SSE
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_workflow(payload: WorkflowRunRequest) -> StreamingResponse:
    """Open an SSE stream that emits :class:`WorkflowRunEvent` JSON frames."""

    async def _generator() -> AsyncIterator[bytes]:
        import asyncio

        queue: asyncio.Queue[WorkflowRunEvent | None] = asyncio.Queue()

        async def _on_event(event: WorkflowRunEvent) -> None:
            await queue.put(event)

        async def _run() -> None:
            try:
                await workflow_engine.run_workflow(
                    payload.spec, inputs=payload.inputs, on_event=_on_event
                )
            except Exception as exc:  # noqa: BLE001 — last-resort guard
                logger.exception("workflow run crashed: %s", exc)
                # The engine emits run-error on validation failures already;
                # this catches engine-implementation bugs only.
            finally:
                await queue.put(None)  # sentinel — end of stream

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
# Persistence
# ---------------------------------------------------------------------------


@router.post("/save")
def save_workflow(spec: WorkflowSpec) -> WorkflowSpec:
    """Insert or replace a workflow spec; returns the persisted record."""
    return workflow_store.save_workflow(spec)


@router.get("/saved")
def list_saved_workflows() -> dict[str, list[WorkflowSpec]]:
    """Return every saved workflow, newest-updated first."""
    return {"workflows": workflow_store.list_workflows()}


@router.get("/saved/{workflow_id}")
def get_saved_workflow(workflow_id: str) -> WorkflowSpec:
    """Load one saved workflow."""
    spec = workflow_store.get_workflow(workflow_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"unknown workflow {workflow_id!r}")
    return spec


@router.delete("/saved/{workflow_id}")
def delete_saved_workflow(workflow_id: str) -> dict[str, bool]:
    """Delete one saved workflow."""
    removed = workflow_store.delete_workflow(workflow_id)
    if not removed:
        raise HTTPException(status_code=404, detail=f"unknown workflow {workflow_id!r}")
    return {"deleted": True}


# ---------------------------------------------------------------------------
# SSE encoding helpers (mirror routers/llm.py)
# ---------------------------------------------------------------------------


def _encode_event(event: WorkflowRunEvent) -> bytes:
    return f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}\n\n".encode()


def _encode_event_dict(payload: dict) -> bytes:  # pragma: no cover - kept for parity
    return f"data: {json.dumps(payload)}\n\n".encode()
