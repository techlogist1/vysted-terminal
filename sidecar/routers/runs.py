"""Delegate-runs router — launch / observe / control durable background runs.

The transport layer over ``services.run_manager`` (US9 / FR-026/027/028 /
SC-008). A *Delegate run* is an autonomous background agent task with a hard
spend ceiling; this router exposes the exact wire shapes the run-tray UI
consumes. The router stays thin — all orchestration lives in ``run_manager``,
all persistence in ``runs_store``.

Routes span two path roots, so this module uses ONE prefix-less router with
fully-qualified paths (a single ``module.router`` is what ``app.create_app``
mounts):

- ``POST /agents/{agent_id}/runs``  — launch a detached run → 201 ``{runId}``.
- ``GET  /runs``                    — list runs, newest first.
- ``GET  /runs/{run_id}``           — one run + its transcript digest.
- ``POST /runs/{run_id}/cancel``    — cancel a run (Discard for a planned one).
- ``POST /runs/{run_id}/start``     — start a planned run (its plan approved).
- ``POST /runs/{run_id}/answer``    — deliver a human-in-the-loop reply (FR-028).
- ``POST /runs/{run_id}/resume``    — re-enter an aborted run from its checkpoint.

Resume and answer take the BYOK key in the ``X-LLM-Api-Key`` header and re-use
the provider and model persisted at launch.

The BYOK ``api_key`` crosses for the run only — it is never stored in the runs
database and never echoed back in any response (asserted in
``test_runs_router``). Loopback transport only.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from models.run import RunAnswerRequest, RunLaunchRequest
from services import run_manager, runs_store
from services.run_manager import RunManagerError
from services.runs_store import RunNotFound, RunStateError

logger = logging.getLogger(__name__)

# No prefix — the launch route lives under /agents while the rest live under
# /runs, so each route carries its full path.
router = APIRouter(tags=["runs"])


def _dual_case(model: BaseModel) -> dict[str, Any]:
    """Serialise a run model with BOTH camelCase aliases and snake_case names.

    The documented wire contract is camelCase (``spendUsd``, ``agentId``,
    ``createdAt``), but the lead's run-tray poller reads snake_case
    (``spend_usd``, ``agent_id``). Emitting BOTH spellings on every GET keeps
    either consumer working without a contract negotiation — a JSON object with
    duplicate-meaning keys is cheap and the frontend picks whichever it reads.
    Nested ``cost`` / ``budget`` objects get the same dual treatment.
    """
    camel = model.model_dump(mode="json", by_alias=True)
    snake = model.model_dump(mode="json", by_alias=False)
    merged: dict[str, Any] = {**snake, **camel}
    for key in ("cost", "budget"):
        if isinstance(camel.get(key), dict) and isinstance(snake.get(key), dict):
            merged[key] = {**snake[key], **camel[key]}
    return merged


@router.post("/agents/{agent_id}/runs", status_code=status.HTTP_201_CREATED)
async def launch_run(agent_id: str, payload: RunLaunchRequest) -> dict[str, str]:
    """Launch a detached Delegate run; return its id (201).

    The run keeps executing after this request closes (FR-027). ``api_key`` is
    used for the run only and is never persisted. The id is emitted as BOTH
    ``runId`` and ``run_id`` so either spelling the frontend reads resolves.
    """
    try:
        run_id = run_manager.launch_run(
            agent_id=agent_id,
            prompt=payload.prompt,
            context_snapshot=payload.context_snapshot,
            provider=payload.provider,
            model=payload.model,
            api_key=payload.api_key,
            budget=payload.budget,
            options=payload.options,
        )
    except RunManagerError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"runId": run_id, "run_id": run_id}


@router.get("/runs")
def list_runs() -> dict[str, list[dict[str, Any]]]:
    """List every run, newest first.

    Each run is serialised dual-case (camelCase + snake_case) so the run-tray
    poller reads either spelling — see :func:`_dual_case`.
    """
    return {"runs": [_dual_case(run) for run in runs_store.list_runs()]}


@router.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    """Return one run with its transcript / checkpoint summary (dual-case)."""
    run = runs_store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"unknown run: {run_id!r}")
    return _dual_case(run)


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str) -> dict[str, bool]:
    """Cancel a live (planned, running or paused) run."""
    with _run_errors():
        run_manager.cancel_run(run_id)
    return {"cancelled": True}


#: The BYOK provider key for a resumed segment: a header, never the body; held
#: in memory for the run only, never persisted or echoed (R15-AGENT-035).
_API_KEY_HEADER = Header(default=None, alias="X-LLM-Api-Key")


@router.post("/runs/{run_id}/start")
async def start_run(run_id: str, api_key: str | None = _API_KEY_HEADER) -> dict[str, bool]:
    """Start a planned run: the user approved its plan (R15-AGENT-039)."""
    with _run_errors():
        run_manager.start_run(run_id, api_key=api_key)
    return {"started": True}


@router.post("/runs/{run_id}/answer")
async def answer_run(
    run_id: str,
    payload: RunAnswerRequest,
    api_key: str | None = _API_KEY_HEADER,
) -> dict[str, bool]:
    """Deliver a human-in-the-loop reply and resume the run (FR-028)."""
    with _run_errors():
        run_manager.answer_run(run_id, payload.answer, api_key=api_key)
    return {"resumed": True}


@router.post("/runs/{run_id}/resume")
async def resume_run(run_id: str, api_key: str | None = _API_KEY_HEADER) -> dict[str, bool]:
    """Re-enter an errored or cancelled run from its checkpoint (FR-028)."""
    with _run_errors():
        run_manager.resume_run(run_id, api_key=api_key)
    return {"resumed": True}


@contextmanager
def _run_errors() -> Iterator[None]:
    """Map the store's typed run errors: unknown run 404, illegal transition 409."""
    try:
        yield
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
