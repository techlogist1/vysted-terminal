"""Angel One (SmartAPI) broker adapter — India equities + F&O.

Uses the ``smartapi-python`` SDK (imported as ``SmartApi.SmartConnect``).
The connection flow is OAuth-style: ``generate_session`` exchanges the
client code + password + TOTP for an access token; subsequent calls use the
token via the same client instance.

Paper / live split: identical to the Dhan adapter — paper mode never
touches the SDK and returns a synthetic filled order; live mode dispatches
the sync SDK call onto a thread.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, ClassVar

from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerOrderProposal,
    BrokerOrderResult,
    BrokerPosition,
)
from services.broker_base import BrokerAdapter, BrokerError
from services.brokers.dhan import _synthetic_paper_result

logger = logging.getLogger(__name__)


class AngelOneAdapter(BrokerAdapter):
    """Angel One execution adapter."""

    BROKER_ID: ClassVar = "angelone"
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
        self._client: Any | None = None
        self._refresh_token: str | None = None

    async def _connect(self, credentials: dict[str, str]) -> None:
        """Open an Angel One SmartAPI session.

        Required credentials: ``api_key``, ``client_code``, ``password``,
        ``totp``. The TOTP must be the current 6-digit code (rotates every
        30s); the frontend prompts the user immediately before triggering
        connect to keep the window tight.
        """
        api_key = credentials.get("api_key") or credentials.get("apiKey")
        client_code = credentials.get("client_code") or credentials.get("clientCode")
        password = credentials.get("password")
        totp = credentials.get("totp")
        if not api_key or not client_code or not password or not totp:
            raise BrokerError(
                "angelone: connect requires 'api_key', 'client_code', "
                "'password', and 'totp' credentials"
            )

        try:
            from SmartApi import SmartConnect  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise BrokerError(f"angelone: smartapi-python not installed: {exc}") from exc

        client = await asyncio.to_thread(SmartConnect, api_key=api_key)
        try:
            session = await asyncio.to_thread(client.generateSession, client_code, password, totp)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"angelone: generateSession failed: {exc}") from exc

        if not session or not (session.get("status") or session.get("data")):
            raise BrokerError(f"angelone: session refused: {session!r}")

        self._client = client
        self._refresh_token = ((session or {}).get("data") or {}).get("refreshToken")
        self._account_id = str(client_code)

    async def _account_info(self) -> AccountSummary:
        """Read RMS limits + holdings from Angel One."""
        if self._mode == "paper" or self._client is None:
            return AccountSummary(
                broker="angelone",
                accountId=self._account_id or "paper-angelone",
                currency="INR",
                equity=1_000_000.0,
                cash=500_000.0,
                buyingPower=1_000_000.0,
                positions=[],
                capturedAt=int(time.time() * 1000),
            )

        try:
            rms = await asyncio.to_thread(self._client.rmsLimit)
            holdings = await asyncio.to_thread(self._client.holding)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"angelone: account fetch failed: {exc}") from exc

        rms_data = (rms or {}).get("data") or {}
        equity = float(rms_data.get("net") or rms_data.get("availablecash") or 0.0)
        return AccountSummary(
            broker="angelone",
            accountId=self._account_id,
            currency="INR",
            equity=equity,
            cash=equity,
            buyingPower=equity,
            positions=_translate_angel_holdings((holdings or {}).get("data") or []),
            capturedAt=int(time.time() * 1000),
        )

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        """Place a confirmed order at Angel One."""
        if self._mode == "paper":
            return _synthetic_paper_result("angelone", proposal)

        if self._client is None:
            raise BrokerError("angelone: live order placement requires a connected client")

        params = {
            "variety": "NORMAL",
            "tradingsymbol": proposal.symbol,
            "symboltoken": proposal.source_details.get("symboltoken", ""),
            "transactiontype": "BUY" if proposal.side == "buy" else "SELL",
            "exchange": _angel_exchange(proposal.symbol),
            "ordertype": _angel_order_type(proposal.type),
            "producttype": "DELIVERY",
            "duration": "DAY",
            "price": str(proposal.limit_price or 0.0),
            "triggerprice": str(proposal.stop_price or 0.0),
            "quantity": str(int(proposal.quantity)),
        }

        try:
            response = await asyncio.to_thread(self._client.placeOrderFullResponse, params)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"angelone: placeOrder failed: {exc}") from exc

        data = (response or {}).get("data") or {}
        broker_order_id = data.get("orderid") or data.get("uniqueorderid")
        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="angelone",
            brokerOrderId=str(broker_order_id) if broker_order_id else None,
            status="open" if broker_order_id else "rejected",
            requestPayload=params,
            responsePayload=dict(response or {}),
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        """Cancel an open order at Angel One."""
        if self._mode == "paper":
            return
        if self._client is None:
            raise BrokerError("angelone: live cancel requires a connected client")
        try:
            await asyncio.to_thread(self._client.cancelOrder, broker_order_id, "NORMAL")
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"angelone: cancelOrder failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _angel_exchange(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith("BSE"):
        return "BSE"
    return "NSE"


def _angel_order_type(order_type: str) -> str:
    mapping = {
        "market": "MARKET",
        "limit": "LIMIT",
        "stop": "STOPLOSS_MARKET",
        "stop-limit": "STOPLOSS_LIMIT",
    }
    return mapping.get(order_type, "MARKET")


def _translate_angel_holdings(holdings: list[dict[str, Any]]) -> list[BrokerPosition]:
    out: list[BrokerPosition] = []
    for h in holdings or []:
        quantity = float(h.get("quantity") or 0.0)
        if quantity == 0:
            continue
        avg_cost = float(h.get("averageprice") or h.get("avgPrice") or 0.0)
        last_price = float(h.get("ltp") or avg_cost)
        out.append(
            BrokerPosition(
                symbol=str(h.get("tradingsymbol") or h.get("symbol") or ""),
                quantity=quantity,
                averageCost=avg_cost,
                marketValue=quantity * last_price,
                unrealizedPnl=(last_price - avg_cost) * quantity if avg_cost else None,
            )
        )
    return out
