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
from models.broker_reads import (
    BrokerHoldingsResult,
    BrokerMarginsResult,
    BrokerPositionsResult,
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
    """Open a session at the broker using BYOK credentials.

    FR-051: brokers are not registered at boot. The connect path lazily
    registers the adapter (``ensure_registered``) the first time its
    marketplace plugin connects — read routes still 404 until you connect.
    """
    if payload.broker != broker_id:
        raise HTTPException(
            status_code=400,
            detail=f"path broker {broker_id!r} does not match body broker {payload.broker!r}",
        )
    try:
        adapter = brokers_registry.ensure_registered(broker_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        await adapter.connect(payload.credentials)
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"connect failed: {exc}") from exc
    return adapter.state()


def _read_error_to_http(exc: BrokerError) -> HTTPException:
    """Map a broker read error to HTTP. A daily-token expiry becomes 419 so the
    frontend shows a 'reconnect' cue instead of a generic red error."""
    if str(exc).startswith("kite: session expired"):
        return HTTPException(status_code=419, detail="kite-session-expired")
    return HTTPException(status_code=400, detail=str(exc))


async def _read_granular(broker_id: BrokerId, method_name: str):  # noqa: ANN202 - union return
    """Call a granular read (``positions_info`` / ``holdings_info`` /
    ``margins_info``) when the adapter implements it, else fall back to the
    ``AccountSummary`` from ``account_info()`` for adapters without granular
    reads. Read-only by construction — no order path is reachable here (§6.5)."""
    adapter = _get_adapter(broker_id)
    fn = getattr(adapter, method_name, None)
    try:
        return await (fn() if callable(fn) else adapter.account_info())
    except BrokerError as exc:
        raise _read_error_to_http(exc) from exc


@router.get("/{broker_id}/account")
async def get_broker_account(broker_id: BrokerId) -> AccountSummary:
    """Read the account summary + positions from the broker."""
    adapter = _get_adapter(broker_id)
    try:
        return await adapter.account_info()
    except BrokerError as exc:
        raise _read_error_to_http(exc) from exc


@router.get("/{broker_id}/positions")
async def get_broker_positions(broker_id: BrokerId) -> BrokerPositionsResult | AccountSummary:
    """Read intraday/F&O positions (net + day) — read-only.

    Adapters with ``positions_info`` return the granular
    :class:`BrokerPositionsResult`; adapters without it fall back to the
    ``AccountSummary``."""
    return await _read_granular(broker_id, "positions_info")


@router.get("/{broker_id}/holdings")
async def get_broker_holdings(broker_id: BrokerId) -> BrokerHoldingsResult | AccountSummary:
    """Read settled long-term holdings — read-only.

    Adapters with ``holdings_info`` return the granular
    :class:`BrokerHoldingsResult`; others fall back to the ``AccountSummary``."""
    return await _read_granular(broker_id, "holdings_info")


@router.get("/{broker_id}/margins")
async def get_broker_margins(broker_id: BrokerId) -> BrokerMarginsResult | AccountSummary:
    """Read per-segment funds / buying power — read-only.

    Adapters with ``margins_info`` return the granular
    :class:`BrokerMarginsResult`; others fall back to the ``AccountSummary``."""
    return await _read_granular(broker_id, "margins_info")


@router.post("/{broker_id}/disconnect")
async def disconnect_broker(broker_id: BrokerId) -> BrokerState:
    """Drop the broker session — a state reset, never an order. Clears the
    cached client + connected flag so a stale/expired session is cleanly reset
    (closes the latent 404 the frontend store already POSTs to)."""
    adapter = _get_adapter(broker_id)
    if hasattr(adapter, "_client"):
        adapter._client = None  # noqa: SLF001 — deliberate read-state reset
    adapter._connected = False  # noqa: SLF001
    return adapter.state()


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


# ---------------------------------------------------------------------------
# Kite-specific — the real OAuth login-token exchange (replaces static paste)
# ---------------------------------------------------------------------------


class KiteSessionRequest(BaseModel):
    """``POST /brokers/kite/session`` — exchange a one-time request_token.

    The ``api_secret`` is used ONLY for this checksum/exchange and is never
    stored or echoed; the response carries only the resolved access token +
    identity. Transport is loopback-only (sidecar binds 127.0.0.1)."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_key: str = Field(alias="apiKey")
    api_secret: str = Field(alias="apiSecret")
    request_token: str = Field(alias="requestToken")


class KiteSessionResponse(BaseModel):
    """Resolved Kite session — the access token the adapter then connects with."""

    model_config = ConfigDict(populate_by_name=True)

    access_token: str = Field(alias="accessToken")
    user_id: str | None = Field(default=None, alias="userId")
    login_time: str | None = Field(default=None, alias="loginTime")


@router.post("/kite/session")
async def kite_exchange_session(payload: KiteSessionRequest) -> KiteSessionResponse:
    """Run the real Kite Connect login exchange: a one-time ``request_token``
    (from the browser login) + ``api_key`` + ``api_secret`` -> a daily
    ``access_token``. The SDK computes the SHA-256 checksum and POSTs
    ``/session/token`` internally. This replaces the old static-token paste —
    the user does the genuine OAuth dance and the token expires daily."""
    from services.brokers.kite import exchange_request_token

    try:
        data = await exchange_request_token(
            payload.api_key, payload.api_secret, payload.request_token
        )
    except BrokerError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return KiteSessionResponse(
        accessToken=data["access_token"],
        userId=data.get("user_id"),
        loginTime=data.get("login_time"),
    )


__all__ = [
    "_reset_pending_proposals_for_tests",
    "router",
]
