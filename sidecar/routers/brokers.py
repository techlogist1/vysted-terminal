"""Brokers router — per-broker connect / mode / read-only / order routes.

Every route resolves the adapter through :mod:`services.brokers.registry`
(NOT a direct adapter import) so tests can register fakes. The route layer
is intentionally thin — the safety gates live in
:class:`services.broker_base.BrokerAdapter`. This router only:

  - parses + validates the request body
  - resolves the adapter
  - awaits the adapter method
  - translates :class:`BrokerError` into HTTP 400

The propose/confirm two-step is exposed as two routes:

  - ``POST /brokers/{id}/orders`` — propose, returns the
    :class:`BrokerOrderProposal` (also written to the audit log)
  - ``POST /brokers/{id}/orders/{proposal_id}/confirm`` — confirm + place

The frontend orders inbox is the canonical holder of pending proposals; this
sidecar keeps a small in-memory pending-proposal cache keyed by
``proposal_id`` so the confirm route can resolve the original proposal
object without the frontend round-tripping every field.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from models.broker import (
    AccountSummary,
    BrokerConfirmRequest,
    BrokerConnectRequest,
    BrokerId,
    BrokerMode,
    BrokerOrderProposal,
    BrokerOrderResult,
    BrokerOrderSide,
    BrokerOrderSource,
    BrokerOrderType,
    BrokerState,
)
from services.broker_base import BrokerError
from services.brokers import registry as brokers_registry
from services.brokers.kite import KiteAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/brokers", tags=["brokers"])


# ---------------------------------------------------------------------------
# Wire models — request bodies + lightweight in-memory pending-order cache
# ---------------------------------------------------------------------------


class BrokerProposeOrderRequest(BaseModel):
    """``POST /brokers/{id}/orders`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: str
    side: BrokerOrderSide
    type: BrokerOrderType
    quantity: float
    limit_price: float | None = Field(default=None, alias="limitPrice")
    stop_price: float | None = Field(default=None, alias="stopPrice")
    currency: str = "INR"
    account_id: str | None = Field(default=None, alias="accountId")
    source: BrokerOrderSource = "manual"
    source_details: dict[str, Any] = Field(alias="sourceDetails", default_factory=dict)


class BrokerSetModeRequest(BaseModel):
    """``POST /brokers/{id}/mode`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    mode: BrokerMode


class BrokerSetReadOnlyRequest(BaseModel):
    """``POST /brokers/{id}/read-only`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    read_only: bool = Field(alias="readOnly")


class BrokerSetStaticIpRequest(BaseModel):
    """``POST /brokers/kite/static-ip`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    static_ip: str | None = Field(default=None, alias="staticIp")


class BrokerCancelOrderRequest(BaseModel):
    """``POST /brokers/{id}/orders/{broker_order_id}/cancel`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    broker_order_id: str = Field(alias="brokerOrderId")


# In-memory pending-proposal cache — keyed by ``proposal_id``.
#
# The frontend orders inbox is the canonical holder, but the confirm route
# needs the proposal object to call ``confirm_and_place``. Keeping a small
# cache here is simpler than asking the frontend to round-trip every field
# back over HTTP. Entries expire on confirm / decline / cancel; the dict
# fits in a single process so the sidecar restart loses pending proposals,
# which matches the BLUEPRINT §6.5 promise that paper-mode orders do not
# survive a sidecar crash (live orders survive because the broker keeps
# them).
_pending_proposals: dict[str, BrokerOrderProposal] = {}


def _reset_pending_proposals_for_tests() -> None:
    """Test helper — drop every cached proposal."""
    _pending_proposals.clear()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def _get_adapter(broker_id: BrokerId | str):  # noqa: ANN202 - dynamic Adapter
    """Resolve the registered adapter or raise HTTP 404."""
    try:
        return brokers_registry.get(broker_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("")
def list_brokers() -> dict[str, list[BrokerState]]:
    """List the state of every registered broker adapter."""
    states = [adapter.state() for adapter in brokers_registry.all_adapters().values()]
    return {"brokers": states}


@router.get("/{broker_id}/state")
def get_broker_state(broker_id: BrokerId) -> BrokerState:
    """Return one broker's :class:`BrokerState` snapshot."""
    return _get_adapter(broker_id).state()


@router.post("/{broker_id}/connect")
async def connect_broker(broker_id: BrokerId, payload: BrokerConnectRequest) -> BrokerState:
    """Open a session at the broker using BYOK credentials."""
    if payload.broker != broker_id:
        raise HTTPException(
            status_code=400,
            detail=f"path broker {broker_id!r} does not match body broker {payload.broker!r}",
        )
    adapter = _get_adapter(broker_id)
    try:
        await adapter.connect(payload.credentials)
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"connect failed: {exc}") from exc
    return adapter.state()


@router.get("/{broker_id}/account")
async def get_broker_account(broker_id: BrokerId) -> AccountSummary:
    """Read the account summary + positions from the broker."""
    adapter = _get_adapter(broker_id)
    try:
        return await adapter.account_info()
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{broker_id}/orders")
def propose_broker_order(
    broker_id: BrokerId, payload: BrokerProposeOrderRequest
) -> BrokerOrderProposal:
    """Propose a new order; the broker adapter writes the audit row.

    Synchronous — propose_order does not hit the broker. The frontend then
    holds the proposal in the orders inbox until the user confirms.
    """
    adapter = _get_adapter(broker_id)
    try:
        proposal = adapter.propose_order(
            symbol=payload.symbol,
            side=payload.side,
            order_type=payload.type,
            quantity=payload.quantity,
            limit_price=payload.limit_price,
            stop_price=payload.stop_price,
            currency=payload.currency,
            account_id=payload.account_id,
            source=payload.source,
            source_details=payload.source_details,
        )
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _pending_proposals[proposal.proposal_id] = proposal
    return proposal


@router.post("/{broker_id}/orders/{proposal_id}/confirm")
async def confirm_broker_order(
    broker_id: BrokerId, proposal_id: str, payload: BrokerConfirmRequest
) -> BrokerOrderResult:
    """Confirm + place an order proposal.

    ``human_confirmed=False`` is allowed (so the UI can record a decline);
    the adapter raises ``BrokerError`` which we surface as HTTP 400.
    """
    adapter = _get_adapter(broker_id)
    proposal = _pending_proposals.get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"no pending proposal {proposal_id!r}")

    try:
        result = await adapter.confirm_and_place(
            proposal,
            human_confirmed=payload.human_confirmed,
            confirm_note=payload.confirm_note,
        )
    except BrokerError as exc:
        # Decline or gate violation. Drop the proposal so it cannot be
        # re-confirmed accidentally.
        _pending_proposals.pop(proposal_id, None)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _pending_proposals.pop(proposal_id, None)
    return result


@router.post("/{broker_id}/orders/cancel")
async def cancel_broker_order(
    broker_id: BrokerId, payload: BrokerCancelOrderRequest
) -> dict[str, str]:
    """Cancel an open order at the broker."""
    adapter = _get_adapter(broker_id)
    try:
        await adapter.cancel_order(payload.broker_order_id)
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"cancelled": payload.broker_order_id}


@router.post("/{broker_id}/mode")
async def set_broker_mode(broker_id: BrokerId, payload: BrokerSetModeRequest) -> BrokerState:
    """Switch a broker between paper and live mode.

    Kite's adapter overrides ``set_mode`` to also audit-log the static-IP
    detection — see :class:`KiteAdapter.set_mode`. The route does not
    short-circuit; it simply awaits the adapter, which lets the override
    fire when the broker is Kite.
    """
    adapter = _get_adapter(broker_id)
    try:
        await adapter.set_mode(payload.mode)
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return adapter.state()


@router.post("/{broker_id}/read-only")
async def set_broker_read_only(
    broker_id: BrokerId, payload: BrokerSetReadOnlyRequest
) -> BrokerState:
    """Toggle a broker's read-only flag."""
    adapter = _get_adapter(broker_id)
    await adapter.set_read_only(payload.read_only)
    return adapter.state()


# ---------------------------------------------------------------------------
# Kite-specific — configured static-IP storage
# ---------------------------------------------------------------------------


class KiteStaticIpStatus(BaseModel):
    """``GET /brokers/kite/static-ip`` response — the currently-configured IP."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    configured_ip: str | None = Field(default=None, alias="configuredIp")


@router.get("/kite/static-ip")
def get_kite_configured_static_ip() -> KiteStaticIpStatus:
    """Return the configured static IP for the Kite adapter."""
    adapter = _get_adapter("kite")
    if not isinstance(adapter, KiteAdapter):  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="kite adapter type mismatch")
    return KiteStaticIpStatus(configuredIp=adapter.configured_static_ip())


@router.post("/kite/static-ip")
def set_kite_configured_static_ip(payload: BrokerSetStaticIpRequest) -> KiteStaticIpStatus:
    """Set the configured static IP that the live-mode toggle compares against."""
    adapter = _get_adapter("kite")
    if not isinstance(adapter, KiteAdapter):  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail="kite adapter type mismatch")
    adapter.set_configured_static_ip(payload.static_ip)
    return KiteStaticIpStatus(configuredIp=adapter.configured_static_ip())


__all__ = [
    "_reset_pending_proposals_for_tests",
    "router",
]
