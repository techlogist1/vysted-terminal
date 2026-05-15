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

The agent runtime composes the system + context + user messages list and
forwards into the resolved provider adapter — see
``services/agent_runtime.py``. The router stays thin (transport only).
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from models.agent import AgentInvocationRequest, AgentSummary
from services import agent_runtime
from services.llm.base import LLMStreamEvent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


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
            ):
                yield _encode_event(event)
        except Exception as exc:  # noqa: BLE001 — last-resort guard
            logger.exception("agent invoke crashed: %s", exc)
            yield _encode_event_dict({"kind": "error", "message": str(exc)})
            yield _encode_event_dict({"kind": "done"})

    return StreamingResponse(_generator(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# SSE encoding helpers (mirror routers/llm.py)
# ---------------------------------------------------------------------------


def _encode_event(event: LLMStreamEvent) -> bytes:
    return _encode_event_dict(event.model_dump())


def _encode_event_dict(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()
