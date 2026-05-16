"""Safety-layer Pydantic models — mirror of ``types/safety.ts``.

BLUEPRINT §6.5's eight non-negotiables, in code:

  1. Paper-mode default → ``BrokerState.mode == "paper"`` in ``models/broker.py``;
     ``BrokerAdapter.__init__`` in ``services/broker_base.py`` sets it.
  2. Per-order confirm → ``BrokerOrderProposal`` is the only object returned
     by ``propose_order``; placement requires ``confirm_and_place`` with
     ``human_confirmed: bool``.
  3. Position limits → ``PositionLimits`` here, enforced in propose_order.
  4. Append-only audit log → ``AuditLogEntry`` + the SQL triggers in
     ``models/audit_log.py``.
  5. Kill switch → ``KillSwitchEvent`` + ``KillSwitchBus`` in
     ``services/kill_switch.py``; adapters subscribe in __init__.
  6. AI-order gate → ``AiOrderGateProposal`` narrows the proposal source;
     v0.5.0 ships NO auto-approve mode.
  7. Read-only mode → ``BrokerState.read_only`` honored at adapter boundary.
  8. Layered disclaimers → ``DisclaimerKind`` + ``DisclaimerAcknowledgment``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from models.broker import BrokerId, BrokerOrderProposal

KillSwitchFiredBy = Literal[
    "user-toolbar",
    "user-keyboard",
    "user-tray",
    "user-command",
]


class KillSwitchEvent(BaseModel):
    """Kill-switch fire event broadcast to every adapter."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    fired_at: int = Field(alias="firedAt")
    reason: str
    fired_by: KillSwitchFiredBy = Field(alias="firedBy")


class KillSwitchFireResult(BaseModel):
    """Per-subscriber ack timing returned by ``KillSwitchBus.fire``.

    The dedicated safety-layer audit checkpoint asserts ``max_ack_ms < 2000``
    (BLUEPRINT §6.5 #5 — instrumented, not approximated).
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    event: KillSwitchEvent
    ack_times_ms: dict[str, float] = Field(alias="ackTimesMs")
    p50_ack_ms: float = Field(alias="p50AckMs")
    p95_ack_ms: float = Field(alias="p95AckMs")
    max_ack_ms: float = Field(alias="maxAckMs")


AuditLogAction = Literal[
    "order-proposed",
    "order-confirmed",
    "order-declined",
    "order-placed",
    "order-cancelled",
    "order-rejected",
    "kill-switch-fired",
    "kill-switch-reset",
    "mode-changed",
    "read-only-changed",
    "connection",
    "disclaimer-ack",
]

AuditLogSource = Literal["manual", "ai-agent", "workflow", "system"]


class AuditLogEntry(BaseModel):
    """One row in the append-only audit log."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: int
    timestamp_ms: int = Field(alias="timestampMs")
    broker: str  # BrokerId | "_meta"
    account_id: str = Field(alias="accountId")
    action: AuditLogAction
    payload: dict[str, Any] = Field(default_factory=dict)
    source: AuditLogSource
    outcome: str


class AuditLogAppendRequest(BaseModel):
    """The shape ``audit_log.append`` accepts (no id; the DB assigns one)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    timestamp_ms: int = Field(alias="timestampMs")
    broker: str
    account_id: str = Field(alias="accountId")
    action: AuditLogAction
    payload: dict[str, Any] = Field(default_factory=dict)
    source: AuditLogSource
    outcome: str


class PositionLimits(BaseModel):
    """Per-broker order limits."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    max_order_value_account_currency: float = Field(alias="maxOrderValueAccountCurrency")
    max_percent_of_account: float = Field(alias="maxPercentOfAccount")
    max_position_size_per_symbol: float = Field(alias="maxPositionSizePerSymbol")
    daily_loss_circuit_breaker: float = Field(alias="dailyLossCircuitBreaker")


DisclaimerKind = Literal[
    "first-launch-tos",
    "broker-first-connect",
    "first-live-order-this-session",
]


class DisclaimerAcknowledgment(BaseModel):
    """One user disclaimer acknowledgment."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    kind: DisclaimerKind
    broker: BrokerId | None = None
    acked_at: int = Field(alias="ackedAt")


class StaticIpStatus(BaseModel):
    """Detected vs configured public-IP comparison for Kite (and future brokers)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    detected_ip: str | None = Field(default=None, alias="detectedIp")
    configured_ip: str | None = Field(default=None, alias="configuredIp")
    matches: bool
    message: str
    detected_at: int = Field(alias="detectedAt")


class AiOrderGateSourceDetails(BaseModel):
    """Narrowed ``sourceDetails`` for AI-originated proposals."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    originator_id: str = Field(alias="originatorId")
    originator_name: str = Field(alias="originatorName")
    node_id: str | None = Field(default=None, alias="nodeId")
    rationale: str | None = None


class AiOrderGateProposal(BrokerOrderProposal):
    """Specialised ``BrokerOrderProposal`` for AI-originated orders.

    Identical wire shape; typing narrows ``source`` and ``sourceDetails``.
    The order-confirmation dialog uses this to render the agent-named
    banner and to keep the Confirm button disabled until the user
    actively confirms.
    """

    source: Literal["ai-agent", "workflow"]  # type: ignore[assignment]
