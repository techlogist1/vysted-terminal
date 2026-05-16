"""Safety router — BLUEPRINT §6.5 wire surfaces.

Routes:

  - ``GET  /safety/audit-log?limit=200`` — tail the append-only audit log
  - ``GET  /safety/audit-log/export.csv?start_ms&end_ms`` — CSV export
  - ``POST /safety/kill-switch`` — fire the global kill switch
  - ``POST /safety/kill-switch/reset`` — reset after fire (re-ack required)
  - ``GET  /safety/kill-switch/status`` — current state + last fire result
  - ``GET  /safety/disclaimer-status`` — list session-scoped acks
  - ``POST /safety/disclaimer-ack`` — record a session-scoped ack
  - ``GET  /safety/static-ip-status?configured=<ip>`` — Kite static-IP UX surface

The persisted disclaimer acks (first-launch TOS, per-broker first-connect)
live in the OS keychain and are read by the frontend through the Tauri
``keychain_get`` command. This router only handles the session-scoped
first-live-order-per-session ack (which resets when the sidecar restarts).
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from models.broker import BrokerId
from models.safety import (
    AuditLogEntry,
    DisclaimerAcknowledgment,
    KillSwitchFireResult,
    StaticIpStatus,
)
from services import audit_log, disclaimer_session, kill_switch, static_ip_detector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/safety", tags=["safety"])


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@router.get("/audit-log")
def get_audit_log(limit: int = 200) -> dict[str, list[AuditLogEntry]]:
    """Return the newest ``limit`` entries from the append-only audit log."""
    if limit < 1 or limit > 5000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 5000")
    return {"entries": audit_log.tail(limit=limit)}


@router.get("/audit-log/export.csv")
def export_audit_log_csv(
    start_ms: int | None = None,
    end_ms: int | None = None,
) -> Response:
    """Stream the audit log as a CSV download.

    ``start_ms`` + ``end_ms`` together constrain the export to a time range;
    either both must be set, or both omitted (full export). Half-set is
    rejected so the caller cannot accidentally export everything since
    epoch.
    """
    if (start_ms is None) ^ (end_ms is None):
        raise HTTPException(
            status_code=400,
            detail="start_ms and end_ms must be specified together (or both omitted)",
        )
    body = audit_log.export_csv(start_ms=start_ms, end_ms=end_ms)
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="vysted-audit-log.csv"'},
    )


# ---------------------------------------------------------------------------
# Kill switch
# ---------------------------------------------------------------------------


class KillSwitchFireRequest(BaseModel):
    """``POST /safety/kill-switch`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    reason: str = Field(default="user-initiated")
    fired_by: Literal["user-toolbar", "user-keyboard", "user-tray", "user-command"] = Field(
        alias="firedBy", default="user-toolbar"
    )


class KillSwitchResetRequest(BaseModel):
    """``POST /safety/kill-switch/reset`` request body — requires re-ack."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    acknowledged: bool


class KillSwitchStatus(BaseModel):
    """``GET /safety/kill-switch/status`` response."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fired: bool
    last_result: KillSwitchFireResult | None = Field(default=None, alias="lastResult")


@router.post("/kill-switch")
async def fire_kill_switch(payload: KillSwitchFireRequest) -> KillSwitchFireResult:
    """Fire the global kill switch — broadcasts to every subscriber."""
    return await kill_switch.get_bus().fire(payload.reason, payload.fired_by)


@router.post("/kill-switch/reset")
def reset_kill_switch(payload: KillSwitchResetRequest) -> dict[str, bool]:
    """Reset the kill switch after a fire.

    The ``acknowledged`` flag must be true — the UI prompts a re-confirmation
    dialog before issuing the reset. Anything else is rejected so a stray
    POST cannot un-halt trading silently.
    """
    if not payload.acknowledged:
        raise HTTPException(
            status_code=400,
            detail="kill-switch reset requires acknowledged=true",
        )
    kill_switch.get_bus().reset()
    return {"reset": True}


@router.get("/kill-switch/status")
def get_kill_switch_status() -> KillSwitchStatus:
    """Return whether the kill switch is currently fired + last fire result."""
    bus = kill_switch.get_bus()
    return KillSwitchStatus(fired=bus.is_fired, lastResult=bus.last_result)


# ---------------------------------------------------------------------------
# Disclaimers — session-scoped (first-live-order-this-session)
# ---------------------------------------------------------------------------


class DisclaimerAckRequest(BaseModel):
    """``POST /safety/disclaimer-ack`` request body.

    Only the session-scoped ``first-live-order-this-session`` ack lives on
    the sidecar; the other two disclaimer kinds (first-launch TOS,
    per-broker first-connect) are persisted in the OS keychain by the
    frontend.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: Literal["first-live-order-this-session"]
    broker: BrokerId


@router.get("/disclaimer-status")
def get_disclaimer_status() -> dict[str, list[DisclaimerAcknowledgment]]:
    """List session-scoped acks for this sidecar process lifetime."""
    return {"sessionAcks": disclaimer_session.list_session_acks()}


@router.post("/disclaimer-ack")
def record_disclaimer_ack(payload: DisclaimerAckRequest) -> DisclaimerAcknowledgment:
    """Record a session-scoped disclaimer ack."""
    return disclaimer_session.record_session_ack(payload.broker)


# ---------------------------------------------------------------------------
# Static-IP detector (Kite Connect UX path)
# ---------------------------------------------------------------------------


@router.get("/static-ip-status")
async def get_static_ip_status(configured: str | None = None) -> StaticIpStatus:
    """Return the configured-vs-detected public IP comparison.

    Used by the Kite plugin's broker-connect banner. Other brokers can use
    the same surface — the comparison logic is broker-agnostic.
    """
    return await static_ip_detector.static_ip_status(configured)
