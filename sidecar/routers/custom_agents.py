"""Custom-agents router — CRUD for user-defined agents (BLUEPRINT module 36).

Owned by Teammate C (Phase 3, Custom Agent Builder). The Custom Agent
Builder UI in the frontend writes through these endpoints; the chat
sidebar's agent picker reads ``GET /custom-agents`` and unions the result
with the first-party ``GET /agents`` response (Teammate A's router).

Path mismatch protection: the URL-path id and any body that carries an id
must agree, and the id MUST start with ``custom:``. Validation lives in
``models.custom_agent`` so the test suite hits the same code path the wire
does. Unknown tool ids are rejected at the same layer — the host's tool
allow-list is the single source of truth.

This file is mounted by ``app.create_app`` — only edit this file, not the
``app.py`` router list (apart from the one-line tuple addition).
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, HTTPException, Response, status

from models.custom_agent import (
    CUSTOM_AGENT_ID_PREFIX,
    CustomAgentCreate,
    CustomAgentRead,
    CustomAgentUpdate,
)
from services import agents_store

router = APIRouter(prefix="/custom-agents", tags=["custom-agents"])


def _ensure_custom_prefix(agent_id: str) -> None:
    """Reject any id that does not start with the ``custom:`` prefix.

    The Pydantic model rejects this on the create path; the path-only
    update/delete endpoints rely on this helper so the router never trusts a
    URL parameter blindly.
    """
    if not agent_id.startswith(CUSTOM_AGENT_ID_PREFIX):
        raise HTTPException(
            status_code=400,
            detail=(
                f"custom-agent id must start with {CUSTOM_AGENT_ID_PREFIX!r} (got {agent_id!r})"
            ),
        )


@router.get("")
def list_custom_agents() -> list[CustomAgentRead]:
    """Return every stored custom agent."""
    return agents_store.list_agents()


@router.get("/{agent_id:path}")
def get_custom_agent(agent_id: str) -> CustomAgentRead:
    """Return one custom agent; 404 if it does not exist."""
    _ensure_custom_prefix(agent_id)
    record = agents_store.get_agent(agent_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"custom agent {agent_id!r} not found")
    return record


@router.post("", status_code=status.HTTP_201_CREATED)
def create_custom_agent(payload: CustomAgentCreate) -> CustomAgentRead:
    """Insert a new custom agent.

    The Pydantic model has already verified the id has the ``custom:``
    prefix and that the tool ids resolve against the host's allow-list.
    This handler only adds the uniqueness check (409 on collision).
    """
    try:
        return agents_store.create_agent(payload)
    except sqlite3.IntegrityError as exc:
        # SQLite's UNIQUE-constraint failures all surface as IntegrityError;
        # there is no other unique column on the table, so this is always
        # the id collision case.
        raise HTTPException(
            status_code=409,
            detail=f"custom agent {payload.id!r} already exists",
        ) from exc


@router.put("/{agent_id:path}")
def update_custom_agent(agent_id: str, payload: CustomAgentUpdate) -> CustomAgentRead:
    """Replace an existing custom agent's mutable fields.

    The id and ``created_at`` are immutable — a "rename" is delete + create.
    Returns 404 if the agent does not exist.
    """
    _ensure_custom_prefix(agent_id)
    updated = agents_store.update_agent(agent_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"custom agent {agent_id!r} not found")
    return updated


@router.delete("/{agent_id:path}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_agent(agent_id: str) -> Response:
    """Delete a custom agent; 404 if it does not exist."""
    _ensure_custom_prefix(agent_id)
    if not agents_store.delete_agent(agent_id):
        raise HTTPException(status_code=404, detail=f"custom agent {agent_id!r} not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
