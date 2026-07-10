"""Agents router — first-party agent discovery + streaming invocation.

Endpoints:

- ``GET /agents`` — list the registered first-party agents (id, name,
  philosophy, tools, default provider). The Custom Agent Builder's
  user-defined agents are NOT merged here — that union lives on the
  frontend ``useAgentsStore`` (Teammate C contributes the custom side at
  ``GET /custom-agents``).
- ``POST /agents/{agent_id}/invoke`` — open an SSE stream of
  :class:`LLMStreamEvent` JSON frames, identical wire shape to
  ``POST /llm/chat``.
- ``POST /agents/actions/ack`` — the frontend's host-action read-back (R10,
  E3.3): after applying (or declining) a streamed host action it reports the
  outcome keyed by ``tool_call_id`` so the runtime's end-of-stream divergence
  check has ground truth instead of optimism.

The agent runtime composes the system + context + user messages list and
forwards into the resolved provider adapter — see
``services/agent_runtime.py``. The router stays thin (transport only).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from models.agent import AgentInvocationRequest, AgentSummary
from services import action_ledger, agent_runtime
from services.errors import error_frame as _human_error_frame
from services.llm.base import LLMStreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


class ActionAckRequest(BaseModel):
    """``POST /agents/actions/ack`` body — the host-action read-back (E3.3)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    tool_call_id: str = Field(alias="toolCallId", min_length=1)
    status: Literal["applied", "kept_previous", "failed"]
    #: Optional applied-brief identity ({run_id, created_at, symbol,
    #: source_count}) so the divergence notice can name what actually rendered.
    brief: dict[str, Any] | None = None
    #: Optional generic host-action descriptor ({action, symbol/panel}) — the
    #: read-back the runtime folds into the in-loop grounded tool-result so the
    #: model narrates the real outcome of EVERY host action (R13 JARVIS), not
    #: just publish_brief. Additive; older frontends omit it.
    detail: dict[str, Any] | None = None


@router.post("/actions/ack")
def ack_action(payload: ActionAckRequest) -> dict[str, bool]:
    """Record the frontend's outcome for one dispatched host action."""
    action_ledger.record(payload.tool_call_id, payload.status, payload.brief, payload.detail)
    return {"ok": True}


@router.get("")
def list_agents() -> list[AgentSummary]:
    """Return summaries for every registered first-party agent."""
    return [
        AgentSummary(
            id=spec.id,
            name=spec.name,
            philosophy=spec.philosophy,
            tools=spec.tools,
            default_provider=spec.default_provider,
            default_model=spec.default_model,
            icon=spec.icon,
        )
        for spec in agent_runtime.list_agents()
    ]


@router.post("/{agent_id}/invoke")
async def invoke_agent(agent_id: str, payload: AgentInvocationRequest) -> StreamingResponse:
    """Open an SSE stream of :class:`LLMStreamEvent` JSON frames."""
    if agent_runtime.get_agent(agent_id) is None:
        raise HTTPException(status_code=404, detail=f"unknown agent: {agent_id!r}")

    async def _generator() -> AsyncIterator[bytes]:
        try:
            async for event in agent_runtime.invoke_agent(
                agent_id=agent_id,
                prompt=payload.prompt,
                context_snapshot=payload.context_snapshot,
                api_key=payload.api_key,
                provider=payload.provider,
                model=payload.model,
                options=payload.options,
                mode=payload.mode,
                autonomy=payload.autonomy,
            ):
                yield _encode_event(event)
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            logger.exception("agent invoke crashed: %s", exc)
            # E9: the last-resort guard humanizes too — chat never renders a
            # naked provider blob; message + action + detail + code all flow.
            yield _encode_event_dict(_human_error_frame(exc))
            yield _encode_event_dict({"kind": "done"})

    return StreamingResponse(_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# SSE encoding helpers (mirror routers/llm.py)
# ---------------------------------------------------------------------------


def _encode_event(event: LLMStreamEvent) -> bytes:
    return _encode_event_dict(event.model_dump())


def _encode_event_dict(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()
