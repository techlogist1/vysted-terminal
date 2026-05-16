"""Session-scoped disclaimer acknowledgments.

BLUEPRINT §6.5 #8 — Layered Disclaimers, in three surfaces:

  - ``first-launch-tos`` — persisted (keychain, frontend-side).
  - ``broker-first-connect`` — persisted per broker (keychain, frontend-side).
  - ``first-live-order-this-session`` — in-memory, resets on app restart.

This module is the in-memory store for the third surface. The first two
acks live in the keychain because they need to survive process restarts;
the session ack lives in this module because it MUST be re-acked each
time the sidecar process starts (a sidecar restart implies a new session).

The store is module-singleton; tests reset it via :func:`reset_for_tests`.
"""

from __future__ import annotations

import time

from models.broker import BrokerId
from models.safety import AuditLogAppendRequest, DisclaimerAcknowledgment
from services import audit_log

#: Per-broker first-live-order session acks. Keys are broker ids; values are
#: epoch-ms when the user clicked Confirm on the per-session live disclaimer.
_session_acks: dict[BrokerId, int] = {}


def has_session_ack(broker: BrokerId) -> bool:
    """Whether the user has acked the first-live-order dialog this session."""
    return broker in _session_acks


def record_session_ack(broker: BrokerId) -> DisclaimerAcknowledgment:
    """Record a first-live-order ack for ``broker``; audit-log it."""
    now_ms = int(time.time() * 1000)
    _session_acks[broker] = now_ms
    audit_log.append(
        AuditLogAppendRequest(
            timestampMs=now_ms,
            broker=broker,
            accountId="_meta",
            action="disclaimer-ack",
            payload={"kind": "first-live-order-this-session"},
            source="manual",
            outcome="ok",
        )
    )
    return DisclaimerAcknowledgment(
        kind="first-live-order-this-session",
        broker=broker,
        ackedAt=now_ms,
    )


def list_session_acks() -> list[DisclaimerAcknowledgment]:
    """List every session ack currently recorded — UI snapshot endpoint."""
    return [
        DisclaimerAcknowledgment(
            kind="first-live-order-this-session",
            broker=broker,
            ackedAt=acked_at,
        )
        for broker, acked_at in _session_acks.items()
    ]


def reset_for_tests() -> None:
    """Test helper — drop all session acks."""
    _session_acks.clear()
