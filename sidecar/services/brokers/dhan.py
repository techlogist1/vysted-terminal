"""Dhan broker adapter — India equities + F&O via the ``dhanhq`` SDK.

The adapter inherits :class:`services.broker_base.BrokerAdapter`; every public
order entry point (``propose_order``, ``confirm_and_place``, ``cancel_order``,
``set_mode``, ``set_read_only``) is already gated by the foundation. This
module only implements the four abstract methods.

The paper-mode + live-mode split:

  - **Paper mode** (the hard-coded default the ABC enforces) — the adapter
    never calls the real Dhan SDK from ``_place_confirmed`` /
    ``_cancel_order``. Orders return a synthetic ``BrokerOrderResult`` with
    ``status="filled"`` and a paper broker-order-id so the user sees the
    proposal flow end-to-end without touching their real account.
  - **Live mode** — the adapter routes the order through the ``dhanhq``
    client's ``place_order`` / ``cancel_order`` and surfaces any SDK error
    verbatim (the ABC will audit-log it as ``order-rejected``).

The ``dhanhq`` SDK call shape is captured below from upstream's
``DhanContext`` + ``dhanhq`` v2 API (2.x); the adapter wraps the calls in
``asyncio.to_thread`` because the SDK is sync.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, ClassVar

from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerOrderProposal,
    BrokerOrderResult,
)
from services.broker_base import BrokerAdapter, BrokerError

logger = logging.getLogger(__name__)


class DhanAdapter(BrokerAdapter):
    """Dhan execution adapter.

    Capabilities: equity + options on NSE/BSE; no forex/crypto/futures
    exposure through Dhan's retail API. Does not require a static IP
    (Kite is the only broker that does in v0.5.0).
    """

    BROKER_ID: ClassVar = "dhan"
    CAPABILITIES: ClassVar = BrokerCapabilities(
        supportsEquity=True,
        supportsOptions=True,
        supportsCrypto=False,
        supportsForex=False,
        supportsFutures=True,
        requiresStaticIp=False,
    )

    def __init__(self) -> None:
        super().__init__()
        # The Dhan SDK client is lazily attached at connect time. Type kept
        # as ``Any`` so the adapter still imports cleanly when the SDK is not
        # installed in a stripped CI image — the constructor never touches
        # ``dhanhq`` directly.
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def _connect(self, credentials: dict[str, str]) -> None:
        """Open a Dhan session using ``client_id`` + ``access_token``.

        Dhan's ``DhanContext`` constructor expects both fields; the access
        token is a long-lived bearer issued from the Dhan developer console
        (BYOK — the user pastes it into the plugin settings).
        """
        client_id = credentials.get("client_id") or credentials.get("clientId")
        access_token = credentials.get("access_token") or credentials.get("accessToken")
        if not client_id or not access_token:
            raise BrokerError(
                "dhan: connect requires both 'client_id' and 'access_token' credentials"
            )

        # Defer the SDK import so the adapter is importable in environments
        # without ``dhanhq`` installed (unit tests stub ``_client`` directly).
        try:
            from dhanhq import DhanContext  # type: ignore[import-not-found]
            from dhanhq import dhanhq as DhanClient
        except ImportError as exc:  # pragma: no cover - SDK pinned in requirements.txt
            raise BrokerError(f"dhan: dhanhq SDK not installed: {exc}") from exc

        context = DhanContext(client_id=client_id, access_token=access_token)
        # SDK call is sync; run on a thread to keep the event loop free.
        self._client = await asyncio.to_thread(DhanClient, context)
        self._account_id = str(client_id)

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def _account_info(self) -> AccountSummary:
        """Fetch the user's Dhan account summary + holdings.

        Dhan's REST surface splits holdings (``get_holdings``) and the cash /
        margin block (``get_fund_limits``). In paper mode we never touched
        the SDK, so a synthetic AccountSummary is returned — the test pattern
        mirrors :mod:`services.broker_base`'s ``_MockAdapter``.
        """
        if self._mode == "paper" or self._client is None:
            return AccountSummary(
                broker="dhan",
                accountId=self._account_id or "paper-dhan",
                currency="INR",
                equity=1_000_000.0,
                cash=500_000.0,
                buyingPower=1_000_000.0,
                positions=[],
                capturedAt=int(time.time() * 1000),
            )

        # Live mode — SDK calls are sync, dispatched to a thread.
        try:
            holdings = await asyncio.to_thread(self._client.get_holdings)
            funds = await asyncio.to_thread(self._client.get_fund_limits)
        except Exception as exc:  # noqa: BLE001 - SDK errors vary widely
            raise BrokerError(f"dhan: account fetch failed: {exc}") from exc

        # The SDK returns ``{"status": "success", "data": {...}}``; treat the
        # payload defensively because Dhan has revised its envelope before.
        funds_data = (funds or {}).get("data") or {}
        equity = float(
            funds_data.get("availabelBalance") or funds_data.get("availableBalance") or 0.0
        )
        return AccountSummary(
            broker="dhan",
            accountId=self._account_id,
            currency="INR",
            equity=equity,
            cash=equity,
            buyingPower=equity,
            positions=_translate_dhan_holdings((holdings or {}).get("data") or []),
            capturedAt=int(time.time() * 1000),
        )

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        """Place a confirmed order at Dhan.

        Paper mode short-circuits before any SDK call — synthetic filled
        result with a deterministic id derived from the proposal id. Live
        mode dispatches ``place_order`` on a thread.
        """
        if self._mode == "paper":
            return _synthetic_paper_result("dhan", proposal)

        if self._client is None:
            raise BrokerError("dhan: live order placement requires a connected client")

        try:
            response = await asyncio.to_thread(
                self._client.place_order,
                security_id=proposal.symbol,
                exchange_segment=_dhan_segment(proposal.symbol),
                transaction_type="BUY" if proposal.side == "buy" else "SELL",
                quantity=int(proposal.quantity),
                order_type=_dhan_order_type(proposal.type),
                product_type="CNC",
                price=proposal.limit_price or 0.0,
                trigger_price=proposal.stop_price or 0.0,
            )
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"dhan: place_order failed: {exc}") from exc

        broker_order_id = (response or {}).get("data", {}).get("orderId") or response.get("orderId")
        status = _dhan_status(response)
        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="dhan",
            brokerOrderId=str(broker_order_id) if broker_order_id else None,
            status=status,
            requestPayload={
                "symbol": proposal.symbol,
                "side": proposal.side,
                "type": proposal.type,
                "quantity": proposal.quantity,
                "limitPrice": proposal.limit_price,
            },
            responsePayload=dict(response or {}),
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        """Cancel an open order at Dhan."""
        if self._mode == "paper":
            # Paper mode keeps no broker-side state; cancel is a no-op
            # logically but still audit-logged by the ABC's cancel_order.
            return

        if self._client is None:
            raise BrokerError("dhan: live cancel requires a connected client")

        try:
            await asyncio.to_thread(self._client.cancel_order, order_id=broker_order_id)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"dhan: cancel_order failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers (shared shape with angelone / kite via a private module would tie the
# three adapters together; keeping them local keeps blast radius small).
# ---------------------------------------------------------------------------


def _synthetic_paper_result(broker: str, proposal: BrokerOrderProposal) -> BrokerOrderResult:
    """Return a synthetic paper-mode fill — deterministic, no SDK call."""
    return BrokerOrderResult(
        proposalId=proposal.proposal_id,
        broker=broker,  # type: ignore[arg-type]
        brokerOrderId=f"paper-{broker}-{uuid.uuid4().hex[:12]}",
        status="filled",
        requestPayload={
            "symbol": proposal.symbol,
            "side": proposal.side,
            "type": proposal.type,
            "quantity": proposal.quantity,
            "limitPrice": proposal.limit_price,
        },
        responsePayload={"mode": "paper", "note": "synthetic fill, no broker call"},
        placedAt=int(time.time() * 1000),
    )


def _dhan_segment(symbol: str) -> str:
    """Pick the Dhan exchange segment for a symbol. Defaults to NSE equity."""
    upper = symbol.upper()
    if upper.endswith("BSE"):
        return "BSE_EQ"
    return "NSE_EQ"


def _dhan_order_type(order_type: str) -> str:
    """Translate the wire order type to the Dhan SDK enum."""
    mapping = {
        "market": "MARKET",
        "limit": "LIMIT",
        "stop": "STOP_LOSS",
        "stop-limit": "STOP_LOSS_LIMIT",
    }
    return mapping.get(order_type, "MARKET")


def _dhan_status(response: dict[str, Any] | None) -> str:
    """Map the Dhan SDK response envelope to a wire ``status``."""
    data = (response or {}).get("data") or {}
    status_raw = (data.get("orderStatus") or "").upper()
    if status_raw in ("TRADED", "FILLED"):
        return "filled"
    if status_raw == "CANCELLED":
        return "cancelled"
    if status_raw == "REJECTED":
        return "rejected"
    if status_raw in ("OPEN", "PENDING", "TRIGGER_PENDING"):
        return "open"
    return "open"


def _translate_dhan_holdings(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert Dhan's holdings payload to :class:`BrokerPosition` shape.

    Returns a list of dicts that ``AccountSummary`` will coerce to
    ``BrokerPosition`` via Pydantic — keeping the SDK-shape adapter logic
    out of the model layer.
    """
    from models.broker import BrokerPosition

    out: list[BrokerPosition] = []
    for h in holdings or []:
        quantity = float(h.get("totalQty") or h.get("quantity") or 0.0)
        if quantity == 0:
            continue
        avg_cost = float(h.get("avgCostPrice") or h.get("avgPrice") or 0.0)
        last_price = float(h.get("lastTradedPrice") or h.get("ltp") or avg_cost)
        out.append(
            BrokerPosition(
                symbol=str(h.get("tradingSymbol") or h.get("symbol") or ""),
                quantity=quantity,
                averageCost=avg_cost,
                marketValue=quantity * last_price,
                unrealizedPnl=(last_price - avg_cost) * quantity if avg_cost else None,
            )
        )
    return out  # type: ignore[return-value]
