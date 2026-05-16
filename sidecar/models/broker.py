"""Broker integration Pydantic models — mirror of ``types/broker.ts``.

Phase 5 ships six broker execution plugins plus a ccxt crypto execution
extension on the locked ``VystedPlugin`` contract. Every adapter inherits
the safety-layer-enforced ``BrokerAdapter`` ABC in ``services/broker_base.py``.

BLUEPRINT §6.5's eight non-negotiables are enforced where Python can
enforce them: paper-mode default in the ABC constructor, append-only audit
log via SQLite triggers, kill-switch subscription forced in __init__, the
``propose_order → confirm_and_place`` two-step ordering, position-limit
guards in propose_order, read-only flag checked at propose_order entry.

The local-portfolio ``Position`` model in ``models/portfolio.py`` is a
different shape — this one is renamed ``BrokerPosition`` to avoid the
collision, matching the TS rename.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BrokerId = Literal[
    "dhan",
    "angelone",
    "kite",
    "alpaca",
    "ib",
    "oanda",
    "ccxt-bybit",
    "ccxt-binance",
    "ccxt-kraken",
    "ccxt-coinbase",
]

BrokerMode = Literal["paper", "live"]

BrokerConnectionStatus = Literal["disconnected", "connecting", "connected", "error"]

BrokerOrderSide = Literal["buy", "sell"]

BrokerOrderType = Literal["market", "limit", "stop", "stop-limit"]

BrokerOrderSource = Literal["manual", "ai-agent", "workflow"]


class BrokerCapabilities(BaseModel):
    """What the broker adapter can do."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    supports_equity: bool = Field(alias="supportsEquity", default=False)
    supports_options: bool = Field(alias="supportsOptions", default=False)
    supports_crypto: bool = Field(alias="supportsCrypto", default=False)
    supports_forex: bool = Field(alias="supportsForex", default=False)
    supports_futures: bool = Field(alias="supportsFutures", default=False)
    requires_static_ip: bool = Field(alias="requiresStaticIp", default=False)


class BrokerOrderProposal(BaseModel):
    """A proposed order — written to audit log at propose time, held until confirm."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    broker: BrokerId
    account_id: str = Field(alias="accountId")
    symbol: str
    side: BrokerOrderSide
    type: BrokerOrderType
    quantity: float
    limit_price: float | None = Field(default=None, alias="limitPrice")
    stop_price: float | None = Field(default=None, alias="stopPrice")
    currency: str
    estimated_value: float = Field(alias="estimatedValue")
    source: BrokerOrderSource
    source_details: dict[str, Any] = Field(alias="sourceDetails", default_factory=dict)
    proposed_at: int = Field(alias="proposedAt")


class BrokerOrderResult(BaseModel):
    """Outcome of placing a confirmed order at the broker."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    broker: BrokerId
    broker_order_id: str | None = Field(default=None, alias="brokerOrderId")
    status: Literal["filled", "partial", "open", "cancelled", "rejected"]
    request_payload: dict[str, Any] = Field(alias="requestPayload")
    response_payload: dict[str, Any] = Field(alias="responsePayload")
    error: str | None = None
    placed_at: int = Field(alias="placedAt")


class BrokerPosition(BaseModel):
    """A single open position at a broker."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    symbol: str
    quantity: float
    average_cost: float = Field(alias="averageCost")
    market_value: float = Field(alias="marketValue")
    unrealized_pnl: float | None = Field(default=None, alias="unrealizedPnl")


class AccountSummary(BaseModel):
    """Account summary returned by ``GET /brokers/{id}/account``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    broker: BrokerId
    account_id: str = Field(alias="accountId")
    currency: str
    equity: float
    cash: float
    buying_power: float = Field(alias="buyingPower")
    positions: list[BrokerPosition]
    captured_at: int = Field(alias="capturedAt")


class BrokerState(BaseModel):
    """Per-broker connection state surfaced to the broker-connect UI."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    broker: BrokerId
    status: BrokerConnectionStatus
    mode: BrokerMode = "paper"
    read_only: bool = Field(alias="readOnly", default=False)
    capabilities: BrokerCapabilities
    error: str | None = None
    last_seen_at: int | None = Field(default=None, alias="lastSeenAt")


class BrokerConnectRequest(BaseModel):
    """``POST /brokers/{id}/connect`` request body.

    Credentials are referenced by keychain account name (e.g.
    ``broker:dhan:client_id``); the sidecar resolves the values at connect
    time via the Tauri ``keychain_get`` command issued by the frontend.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    broker: BrokerId
    credentials: dict[str, str] = Field(default_factory=dict)


class BrokerConfirmRequest(BaseModel):
    """``POST /brokers/{id}/orders/{proposal-id}/confirm`` request body."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    human_confirmed: bool = Field(alias="humanConfirmed")
    confirm_note: str | None = Field(default=None, alias="confirmNote")
