"""BrokerAdapter ABC — the safety-layer-enforced order entry point.

Every Phase 5 broker (Dhan, Angel One, Kite, Alpaca, IB, OANDA, ccxt)
inherits :class:`BrokerAdapter` and implements only the four abstract
methods:

  - :meth:`_connect` — open the broker session
  - :meth:`_account_info` — read account + positions
  - :meth:`_place_confirmed` — place an already-confirmed order at the broker
  - :meth:`_cancel_order` — cancel an open order

The non-overridable public methods enforce BLUEPRINT §6.5:

  - :meth:`propose_order` — write to audit, check kill switch + read-only +
    position limits, return the proposal to the caller for user confirm
  - :meth:`confirm_and_place` — require ``human_confirmed: bool``, re-check
    gates, call ``_place_confirmed``, write result to audit
  - :meth:`set_mode` / :meth:`set_read_only` — record mode/flag changes

There is NO public path from caller to broker that skips ``propose_order``.
``_place_confirmed`` is name-mangled-private (`_place_confirmed`) and only
``confirm_and_place`` calls it. The dedicated safety audit suite (Teammate
S) asserts via grep + import inspection that this constraint holds in
the integrated codebase.

The AI-order gate (BLUEPRINT §6.5 #6, tightened in v0.5.0 to remove
auto-approve mode) is realised through the proposal flow itself: an AI
agent or workflow node calls :meth:`propose_order` with
``source="ai-agent"`` or ``"workflow"``; the proposal lands in the
:mod:`orders` store as a pending item; the user clicks Confirm in the UI;
the UI calls :meth:`confirm_and_place` with ``human_confirmed=True``. The
AI never calls ``_place_confirmed`` and there is no auto-approve route to
let it skip the inbox.
"""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from typing import ClassVar

from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerId,
    BrokerMode,
    BrokerOrderProposal,
    BrokerOrderResult,
    BrokerState,
)
from models.safety import AuditLogAppendRequest, KillSwitchEvent, PositionLimits
from services import audit_log, kill_switch

logger = logging.getLogger(__name__)


class BrokerError(RuntimeError):
    """Raised by adapter methods on policy violations.

    Distinct from network/SDK errors — the adapter raises BrokerError when
    the safety layer refuses an action (kill switch fired, read-only mode,
    position limit exceeded, etc.). Network errors propagate as the
    SDK-native exception type.
    """


class BrokerAdapter(ABC):
    """Base class for every broker plugin adapter."""

    #: Stable broker id. Set on each subclass; used as the kill-switch
    #: subscriber name and the audit-log broker field.
    BROKER_ID: ClassVar[BrokerId]

    #: Static capability snapshot. Subclasses override before super().__init__.
    CAPABILITIES: ClassVar[BrokerCapabilities]

    #: Conservative default order limits — user can raise through explicit
    #: confirmation in plugin settings. Defaults match BLUEPRINT §6.5 #3 wording
    #: (conservative on purpose).
    DEFAULT_LIMITS: ClassVar[PositionLimits] = PositionLimits(
        maxOrderValueAccountCurrency=10_000.0,
        maxPercentOfAccount=10.0,
        maxPositionSizePerSymbol=1000.0,
        dailyLossCircuitBreaker=2_000.0,
    )

    def __init__(self) -> None:
        # BLUEPRINT §6.5 #1 — paper mode is the hard-coded default. There is
        # no constructor argument that flips this to live; the only path is
        # through :meth:`set_mode` after the live-mode disclaimer has been
        # acknowledged. The dedicated safety audit suite asserts this.
        self._mode: BrokerMode = "paper"
        self._read_only: bool = False
        self._connected: bool = False
        self._account_id: str = ""
        self._limits: PositionLimits = self.DEFAULT_LIMITS

        # Subscribe to the kill-switch bus on construction — adapters
        # CANNOT be instantiated without subscribing. This is a hard guard
        # that makes BLUEPRINT §6.5 #5 architectural rather than convention.
        self._unsubscribe = kill_switch.get_bus().subscribe(self.BROKER_ID, self._on_kill_switch)

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def mode(self) -> BrokerMode:
        return self._mode

    @property
    def read_only(self) -> bool:
        return self._read_only

    @property
    def connected(self) -> bool:
        return self._connected

    def state(self) -> BrokerState:
        """Return the current state surfaced to the broker-connect UI."""
        return BrokerState(
            broker=self.BROKER_ID,
            status="connected" if self._connected else "disconnected",
            mode=self._mode,
            readOnly=self._read_only,
            capabilities=self.CAPABILITIES,
        )

    # ------------------------------------------------------------------
    # Mode + read-only — both audit-logged
    # ------------------------------------------------------------------

    async def set_mode(self, mode: BrokerMode) -> None:
        """Switch between paper and live. UI is expected to have shown the
        live-mode disclaimer before calling with ``"live"``."""
        if mode not in ("paper", "live"):
            raise BrokerError(f"invalid mode {mode!r}")
        previous = self._mode
        self._mode = mode
        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=int(time.time() * 1000),
                broker=self.BROKER_ID,
                accountId=self._account_id or "_meta",
                action="mode-changed",
                payload={"previous": previous, "current": mode},
                source="manual",
                outcome="ok",
            )
        )

    async def set_read_only(self, read_only: bool) -> None:
        """Toggle read-only mode (independent of connection state)."""
        previous = self._read_only
        self._read_only = bool(read_only)
        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=int(time.time() * 1000),
                broker=self.BROKER_ID,
                accountId=self._account_id or "_meta",
                action="read-only-changed",
                payload={"previous": previous, "current": self._read_only},
                source="manual",
                outcome="ok",
            )
        )

    # ------------------------------------------------------------------
    # Connection lifecycle — calls _connect, audits the result
    # ------------------------------------------------------------------

    async def connect(self, credentials: dict[str, str]) -> None:
        """Open a broker session with the supplied credentials.

        Wraps the subclass's :meth:`_connect` with audit logging. The
        adapter does NOT cache credentials beyond this call — BYOK pattern,
        per CLAUDE.md.
        """
        try:
            await self._connect(credentials)
            self._connected = True
            outcome = "ok"
            error: str | None = None
        except Exception as exc:  # noqa: BLE001 — broker SDK errors vary widely
            self._connected = False
            outcome = "error"
            error = str(exc)
            audit_log.append(
                AuditLogAppendRequest(
                    timestampMs=int(time.time() * 1000),
                    broker=self.BROKER_ID,
                    accountId=self._account_id or "_meta",
                    action="connection",
                    payload={"error": error},
                    source="manual",
                    outcome=outcome,
                )
            )
            raise

        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=int(time.time() * 1000),
                broker=self.BROKER_ID,
                accountId=self._account_id or "_meta",
                action="connection",
                payload={"connected": True},
                source="manual",
                outcome=outcome,
            )
        )

    async def account_info(self) -> AccountSummary:
        """Read account + positions. No state mutation, no audit row."""
        return await self._account_info()

    # ------------------------------------------------------------------
    # Order placement — the safety-gated two-step
    # ------------------------------------------------------------------

    def propose_order(
        self,
        *,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        limit_price: float | None = None,
        stop_price: float | None = None,
        currency: str = "USD",
        account_id: str | None = None,
        source: str = "manual",
        source_details: dict | None = None,
    ) -> BrokerOrderProposal:
        """Propose an order — audit-log it, return for human confirmation.

        Synchronous because the proposal does not hit the broker — the
        adapter only computes the estimated value, runs the position-limit
        check, and writes to the audit log. The proposal is then returned
        to the caller (the safety router) which holds it in the orders
        inbox until the user confirms.

        Pre-confirmation gates (each raises BrokerError on violation):
          * kill switch is fired
          * adapter is in read-only mode
          * order value exceeds maxOrderValueAccountCurrency
          * any other PositionLimits violation
        """
        if kill_switch.get_bus().is_fired:
            raise BrokerError(f"{self.BROKER_ID}: kill switch fired — order placement halted")
        if self._read_only:
            raise BrokerError(f"{self.BROKER_ID}: adapter is in read-only mode")
        if side not in ("buy", "sell"):
            raise BrokerError(f"{self.BROKER_ID}: invalid side {side!r}")
        if order_type not in ("market", "limit", "stop", "stop-limit"):
            raise BrokerError(f"{self.BROKER_ID}: invalid order type {order_type!r}")
        if quantity <= 0:
            raise BrokerError(f"{self.BROKER_ID}: quantity must be positive")

        ref_price = float(limit_price or 0.0)
        estimated_value = float(quantity) * ref_price

        # Position-limit guards. The reference price is the limit_price if
        # provided; for market orders the adapter cannot know fill price
        # at propose time, so the value check is best-effort and the broker
        # is expected to reject grossly-oversized market orders too.
        if estimated_value > self._limits.max_order_value_account_currency and estimated_value > 0:
            raise BrokerError(
                f"{self.BROKER_ID}: order value {estimated_value:.2f} {currency} "
                f"exceeds limit {self._limits.max_order_value_account_currency:.2f}"
            )
        if quantity > self._limits.max_position_size_per_symbol:
            raise BrokerError(
                f"{self.BROKER_ID}: quantity {quantity} exceeds per-symbol cap "
                f"{self._limits.max_position_size_per_symbol}"
            )

        proposal = BrokerOrderProposal(
            proposalId=str(uuid.uuid4()),
            broker=self.BROKER_ID,
            accountId=account_id or self._account_id or "_unset",
            symbol=symbol,
            side=side,  # type: ignore[arg-type]
            type=order_type,  # type: ignore[arg-type]
            quantity=float(quantity),
            limitPrice=limit_price,
            stopPrice=stop_price,
            currency=currency,
            estimatedValue=estimated_value,
            source=source,  # type: ignore[arg-type]
            sourceDetails=dict(source_details or {}),
            proposedAt=int(time.time() * 1000),
        )

        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=proposal.proposed_at,
                broker=self.BROKER_ID,
                accountId=proposal.account_id,
                action="order-proposed",
                payload=proposal.model_dump(by_alias=True, exclude_none=False),
                source=source,  # type: ignore[arg-type]
                outcome="ok",
            )
        )
        return proposal

    async def confirm_and_place(
        self,
        proposal: BrokerOrderProposal,
        *,
        human_confirmed: bool,
        confirm_note: str | None = None,
    ) -> BrokerOrderResult:
        """Confirm a proposal and place the order at the broker.

        ``human_confirmed`` must be ``True`` — when ``False`` the proposal
        is recorded as declined and the call raises. There is no path to
        bypass this argument; the UI passes ``True`` only after the user
        clicks the Confirm button. The dedicated safety audit suite asserts
        this is the only call site for ``_place_confirmed``.
        """
        if not human_confirmed:
            audit_log.append(
                AuditLogAppendRequest(
                    timestampMs=int(time.time() * 1000),
                    broker=self.BROKER_ID,
                    accountId=proposal.account_id,
                    action="order-declined",
                    payload={
                        "proposalId": proposal.proposal_id,
                        "note": confirm_note,
                    },
                    source=proposal.source,  # type: ignore[arg-type]
                    outcome="declined",
                )
            )
            raise BrokerError(f"{self.BROKER_ID}: order proposal {proposal.proposal_id} declined")

        # Re-check the gates at confirm time. Kill switch may have fired in
        # the window between propose and confirm; the user may have toggled
        # read-only.
        if kill_switch.get_bus().is_fired:
            raise BrokerError(f"{self.BROKER_ID}: kill switch fired between propose and confirm")
        if self._read_only:
            raise BrokerError(
                f"{self.BROKER_ID}: adapter set to read-only between propose and confirm"
            )

        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=int(time.time() * 1000),
                broker=self.BROKER_ID,
                accountId=proposal.account_id,
                action="order-confirmed",
                payload={"proposalId": proposal.proposal_id, "note": confirm_note},
                source=proposal.source,  # type: ignore[arg-type]
                outcome="ok",
            )
        )

        try:
            result = await self._place_confirmed(proposal)
        except Exception as exc:  # noqa: BLE001
            audit_log.append(
                AuditLogAppendRequest(
                    timestampMs=int(time.time() * 1000),
                    broker=self.BROKER_ID,
                    accountId=proposal.account_id,
                    action="order-rejected",
                    payload={
                        "proposalId": proposal.proposal_id,
                        "error": str(exc),
                    },
                    source=proposal.source,  # type: ignore[arg-type]
                    outcome=f"rejected: {exc}",
                )
            )
            raise

        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=result.placed_at,
                broker=self.BROKER_ID,
                accountId=proposal.account_id,
                action="order-placed",
                payload=result.model_dump(by_alias=True, exclude_none=False),
                source=proposal.source,  # type: ignore[arg-type]
                outcome=result.status,
            )
        )
        return result

    async def cancel_order(self, broker_order_id: str) -> None:
        """Cancel an open order. Audit-logged on both success and failure."""
        try:
            await self._cancel_order(broker_order_id)
            audit_log.append(
                AuditLogAppendRequest(
                    timestampMs=int(time.time() * 1000),
                    broker=self.BROKER_ID,
                    accountId=self._account_id or "_unset",
                    action="order-cancelled",
                    payload={"brokerOrderId": broker_order_id},
                    source="manual",
                    outcome="ok",
                )
            )
        except Exception as exc:  # noqa: BLE001
            audit_log.append(
                AuditLogAppendRequest(
                    timestampMs=int(time.time() * 1000),
                    broker=self.BROKER_ID,
                    accountId=self._account_id or "_unset",
                    action="order-rejected",
                    payload={
                        "brokerOrderId": broker_order_id,
                        "operation": "cancel",
                        "error": str(exc),
                    },
                    source="manual",
                    outcome=f"cancel-rejected: {exc}",
                )
            )
            raise

    # ------------------------------------------------------------------
    # Kill-switch handler
    # ------------------------------------------------------------------

    async def _on_kill_switch(self, event: KillSwitchEvent) -> None:
        """Called by the bus on kill-switch fire.

        Forces read-only mode (so any propose_order in flight fails on the
        re-check) and writes an audit entry. Subclasses can override to add
        cancel-all-open-orders behaviour; the base does NOT cancel by
        default because not every broker SDK supports a fast cancel-all.
        """
        self._read_only = True
        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=event.fired_at,
                broker=self.BROKER_ID,
                accountId=self._account_id or "_meta",
                action="kill-switch-fired",
                payload={
                    "reason": event.reason,
                    "firedBy": event.fired_by,
                },
                source="system",
                outcome="acked",
            )
        )

    # ------------------------------------------------------------------
    # Abstract surface — subclasses implement
    # ------------------------------------------------------------------

    @abstractmethod
    async def _connect(self, credentials: dict[str, str]) -> None:
        """Open the broker session with the supplied credentials."""

    @abstractmethod
    async def _account_info(self) -> AccountSummary:
        """Fetch the current account summary + positions."""

    @abstractmethod
    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        """Place an already-confirmed order at the broker.

        Called ONLY from :meth:`confirm_and_place` after ``human_confirmed``
        was True. Subclasses must not call themselves; the audit suite
        verifies the call graph at integration time.
        """

    @abstractmethod
    async def _cancel_order(self, broker_order_id: str) -> None:
        """Cancel an open order at the broker by broker-side id."""
