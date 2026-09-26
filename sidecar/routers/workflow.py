"""Workflow router — Phase 4 wire surfaces.

Routes:

  - ``POST /workflow/run``        — SSE stream of :class:`WorkflowRunEvent`
  - ``GET  /workflow/node-types`` — the node type ids the engine can run
  - ``POST /workflow/save``       — persist a workflow spec (upsert)
  - ``GET  /workflow/saved``      — list saved workflows (+ ``unreadable`` rows)
  - ``GET  /workflow/saved/{id}`` — load one saved workflow
  - ``DELETE /workflow/saved/{id}`` — delete a saved workflow
  - ``GET/POST /workflow/schedules``, ``PATCH/DELETE /workflow/schedules/{id}``
    — unattended-run schedules (``services/workflow_scheduler.py``)
  - ``PUT /workflow/webhooks/{ref}`` — hold an ``action.webhook`` URL (header
    ``X-Vysted-Webhook-Url``) in process memory; ``GET /workflow/webhooks``
    lists the refs only

The run route streams over SSE in the same shape as the v0.4.0
``POST /llm/chat`` and ``POST /agents/{id}/invoke`` routes — JSON event
frames separated by ``\\n\\n``.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

import config
from models.workflow import (
    SavedWorkflows,
    ScheduleCreate,
    ScheduleUpdate,
    WebhookRefs,
    WorkflowRunEvent,
    WorkflowRunRequest,
    WorkflowSchedule,
    WorkflowSpec,
)
from services import workflow_engine, workflow_store
from services.workflow_nodes import builtin as workflow_builtin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workflow", tags=["workflow"])


# ---------------------------------------------------------------------------
# Run — SSE
# ---------------------------------------------------------------------------


@router.post("/run")
async def run_workflow(payload: WorkflowRunRequest) -> StreamingResponse:
    """Open an SSE stream that emits :class:`WorkflowRunEvent` JSON frames."""
    if payload.mode != "full":
        raise HTTPException(
            status_code=400,
            detail=f"unsupported run mode {payload.mode!r}; only 'full' is implemented",
        )

    async def _generator() -> AsyncIterator[bytes]:
        import asyncio

        queue: asyncio.Queue[WorkflowRunEvent | None] = asyncio.Queue()
        run_id: str | None = None

        async def _on_event(event: WorkflowRunEvent) -> None:
            nonlocal run_id
            run_id = event.run_id
            await queue.put(event)

        async def _run() -> None:
            nonlocal run_id
            # Publish the request's creds for this run's agent nodes (task-local;
            # the key stays in process memory and is reset when the run ends).
            creds_token = (
                config.set_request_llm_creds(payload.provider, payload.model or "", payload.api_key)
                if payload.provider
                else None
            )
            try:
                await workflow_engine.run_workflow(
                    payload.spec, inputs=payload.inputs, on_event=_on_event
                )
            except Exception as exc:  # noqa: BLE001 — every stream ends on a terminal frame
                # A spec the engine rejects (WorkflowEngineError) raises before
                # run-start; an engine bug can raise mid-run. Either way the
                # client gets the reason as a run-error, opened by a run-start
                # when the engine never emitted one (the client keys runs on it).
                if not isinstance(exc, workflow_engine.WorkflowEngineError):
                    logger.exception("workflow run crashed: %s", exc)
                if run_id is None:
                    run_id = str(uuid.uuid4())
                    await queue.put(
                        WorkflowRunEvent(
                            kind="run-start", runId=run_id, startedAt=int(time.time() * 1000)
                        )
                    )
                await queue.put(
                    WorkflowRunEvent(kind="run-error", runId=run_id, message=str(exc), durationMs=0)
                )
            finally:
                if creds_token is not None:
                    config.reset_request_llm_creds(creds_token)
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


@router.get("/node-types")
def list_node_types() -> list[str]:
    """The node type ids the engine can run (those with a registered handler)."""
    return workflow_engine.registered_node_types()


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


@router.post("/save")
def save_workflow(spec: WorkflowSpec) -> WorkflowSpec:
    """Insert or replace a workflow spec; returns the persisted record."""
    return workflow_store.save_workflow(spec)


@router.get("/saved")
def list_saved_workflows() -> SavedWorkflows:
    """Return every openable saved workflow (newest first) plus the unreadable rows."""
    return workflow_store.list_workflows()


@router.get("/saved/{workflow_id}")
def get_saved_workflow(workflow_id: str) -> WorkflowSpec:
    """Load one saved workflow; 409 when it is another schema major."""
    try:
        spec = workflow_store.get_workflow(workflow_id)
    except workflow_store.UnsupportedWorkflowVersion as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
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
# Schedules + webhook URLs (R15-AGENT-023)
# ---------------------------------------------------------------------------


@router.get("/schedules")
def list_schedules() -> list[WorkflowSchedule]:
    return workflow_store.list_schedules()


@router.post("/schedules")
def create_schedule(body: ScheduleCreate) -> WorkflowSchedule:
    """Schedule a saved workflow; 404 when it is not saved."""
    if workflow_store.get_workflow(body.workflow_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown workflow {body.workflow_id!r}")
    return workflow_store.create_schedule(body)


@router.patch("/schedules/{schedule_id}")
def update_schedule(schedule_id: str, body: ScheduleUpdate) -> WorkflowSchedule:
    updated = workflow_store.set_schedule_enabled(schedule_id, body.enabled)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"unknown schedule {schedule_id!r}")
    return updated


@router.delete("/schedules/{schedule_id}")
def delete_schedule(schedule_id: str) -> dict[str, bool]:
    if not workflow_store.delete_schedule(schedule_id):
        raise HTTPException(status_code=404, detail=f"unknown schedule {schedule_id!r}")
    return {"deleted": True}


@router.put("/webhooks/{ref}")
def register_webhook(ref: str, url: str = Header(alias="X-Vysted-Webhook-Url")) -> WebhookRefs:
    """Hold the keychain-read URL for ``ref`` in memory; the response lists refs only."""
    try:
        workflow_builtin.register_webhook_url(ref, url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return WebhookRefs(refs=workflow_builtin.webhook_refs())


@router.get("/webhooks")
def list_webhooks() -> WebhookRefs:
    return WebhookRefs(refs=workflow_builtin.webhook_refs())


# ---------------------------------------------------------------------------
# SSE encoding helpers (mirror routers/llm.py)
# ---------------------------------------------------------------------------


def _encode_event(event: WorkflowRunEvent) -> bytes:
    return f"data: {event.model_dump_json(by_alias=True, exclude_none=True)}\n\n".encode()
