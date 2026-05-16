"""OANDA v20 broker adapter — Phase 5 v0.5.0.

Wraps the ``oandapyV20`` SDK (0.7.2; last released 2021-08, stable but
low-maintenance — documented in ``docs/BROKER_INTEGRATIONS.md``) behind
the safety-layer-enforced :class:`BrokerAdapter` ABC.

Environments
------------

OANDA exposes two REST environments:

- ``practice`` — demo account, paper mode default per BLUEPRINT §6.5 #1
- ``live`` — funded fxTrade account, only reachable after
  :meth:`set_mode` flips to ``"live"`` (gated by the UI's live-mode
  disclaimer)

The adapter constructs the ``API`` client with
``environment=self._mode == "paper" and "practice" or "live"`` at
connect time and re-builds the client on :meth:`set_mode`.

Credentials
-----------

OANDA auth is a single bearer token (the "access token" from the
fxTrade dashboard). The user also supplies their account id (a
v20-prefixed identifier like ``101-001-12345678-001``). Both come from
the OS keychain (``broker:oanda:access_token`` and
``broker:oanda:account_id``).

Network calls
-------------

The ``oandapyV20`` SDK is synchronous (``requests``-based). As with
the Alpaca adapter, every call is wrapped in :func:`asyncio.to_thread`
to keep the event loop responsive — kill-switch fires must complete
under 2 s even with an order request in flight.
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

logger = logging.getLogger(__name__)


class OandaAdapter(BrokerAdapter):
    """Adapter for OANDA fxTrade (forex + CFD)."""

    BROKER_ID: ClassVar[str] = "oanda"
    CAPABILITIES: ClassVar[BrokerCapabilities] = BrokerCapabilities(
        supportsEquity=False,
        supportsOptions=False,
        supportsCrypto=False,
        supportsForex=True,
        supportsFutures=False,
        requiresStaticIp=False,
    )

    def __init__(self) -> None:
        super().__init__()
        self._client: Any | None = None
        # OANDA account id (e.g. "101-001-12345678-001"). Stored
        # separately from BrokerAdapter._account_id because OANDA
        # requires it on every endpoint URL.
        self._oanda_account_id: str = ""

    # ------------------------------------------------------------------
    # Abstract surface — implementations
    # ------------------------------------------------------------------

    async def _connect(self, credentials: dict[str, str]) -> None:
        access_token = credentials.get("access_token", "")
        oanda_account_id = credentials.get("account_id", "")
        if not access_token or not oanda_account_id:
            raise BrokerError("oanda: access_token and account_id are required")

        # Imported here so the adapter can be constructed without
        # oandapyV20 being installed (mirrors the other adapters).
        from oandapyV20 import API
        from oandapyV20.endpoints.accounts import AccountSummary as AccountSummaryEP

        environment = "practice" if self._mode == "paper" else "live"

        def _make_client() -> Any:
            return API(access_token=access_token, environment=environment)

        self._client = await asyncio.to_thread(_make_client)
        self._oanda_account_id = oanda_account_id
        self._account_id = oanda_account_id

        # Validate the credentials + account id by hitting the
        # account-summary endpoint once. Any failure bubbles up and
        # the wrapper writes the error to the audit log.
        request = AccountSummaryEP(accountID=oanda_account_id)
        try:
            await asyncio.to_thread(self._client.request, request)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"oanda: connect failed — {exc}") from exc

        logger.info("oanda: connected (env=%s account=%s)", environment, self._oanda_account_id)

    async def _account_info(self) -> AccountSummary:
        if self._client is None:
            raise BrokerError("oanda: not connected")

        from oandapyV20.endpoints.accounts import AccountDetails

        request = AccountDetails(accountID=self._oanda_account_id)
        try:
            response = await asyncio.to_thread(self._client.request, request)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"oanda: account details fetch failed — {exc}") from exc

        # response is a plain dict in oandapyV20 — the SDK does not use
        # response models. Defensive extraction so a schema drift in a
        # later v20 spec revision does not nuke the adapter.
        account = response.get("account", {}) if isinstance(response, dict) else {}
        currency = str(account.get("currency", "USD"))
        equity = _to_float(account.get("NAV", account.get("balance", 0.0)))
        balance = _to_float(account.get("balance", 0.0))
        # OANDA's "marginAvailable" is the closest analogue to buying power.
        buying_power = _to_float(account.get("marginAvailable", balance))

        positions_raw = account.get("positions", []) or []
        mapped_positions: list[BrokerPosition] = []
        for pos in positions_raw:
            if not isinstance(pos, dict):
                continue
            symbol = str(pos.get("instrument", ""))
            long_units = _to_float((pos.get("long") or {}).get("units", 0.0))
            short_units = _to_float((pos.get("short") or {}).get("units", 0.0))
            quantity = long_units + short_units  # short_units is negative in OANDA
            if quantity == 0:
                continue
            # Average price: pick the side with non-zero units
            avg_price = 0.0
            if long_units != 0:
                avg_price = _to_float((pos.get("long") or {}).get("averagePrice", 0.0))
            elif short_units != 0:
                avg_price = _to_float((pos.get("short") or {}).get("averagePrice", 0.0))
            unrealized = (
                _to_float(pos.get("unrealizedPL", 0.0)) if pos.get("unrealizedPL") else None
            )
            mapped_positions.append(
                BrokerPosition(
                    symbol=symbol,
                    quantity=quantity,
                    averageCost=avg_price,
                    marketValue=quantity * avg_price,
                    unrealizedPnl=unrealized,
                )
            )

        return AccountSummary(
            broker="oanda",
            accountId=self._oanda_account_id,
            currency=currency,
            equity=equity,
            cash=balance,
            buyingPower=buying_power,
            positions=mapped_positions,
            capturedAt=int(time.time() * 1000),
        )

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        if self._client is None:
            raise BrokerError("oanda: not connected")

        from oandapyV20.endpoints.orders import OrderCreate

        # OANDA "units" is signed: positive = long, negative = short.
        units = proposal.quantity if proposal.side == "buy" else -proposal.quantity

        if proposal.type == "market":
            order_body = {
                "order": {
                    "type": "MARKET",
                    "instrument": proposal.symbol,
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                }
            }
        elif proposal.type == "limit":
            if proposal.limit_price is None:
                raise BrokerError("oanda: limit order requires limit_price")
            order_body = {
                "order": {
                    "type": "LIMIT",
                    "instrument": proposal.symbol,
                    "units": str(units),
                    "price": str(proposal.limit_price),
                    "timeInForce": "GTC",
                    "positionFill": "DEFAULT",
                }
            }
        elif proposal.type == "stop":
            if proposal.stop_price is None:
                raise BrokerError("oanda: stop order requires stop_price")
            order_body = {
                "order": {
                    "type": "STOP",
                    "instrument": proposal.symbol,
                    "units": str(units),
                    "price": str(proposal.stop_price),
                    "timeInForce": "GTC",
                    "positionFill": "DEFAULT",
                }
            }
        else:  # "stop-limit"
            if proposal.limit_price is None or proposal.stop_price is None:
                raise BrokerError(
                    "oanda: stop-limit order requires both limit_price and stop_price"
                )
            order_body = {
                "order": {
                    "type": "STOP",
                    "instrument": proposal.symbol,
                    "units": str(units),
                    "price": str(proposal.stop_price),
                    "priceBound": str(proposal.limit_price),
                    "timeInForce": "GTC",
                    "positionFill": "DEFAULT",
                }
            }

        request = OrderCreate(accountID=self._oanda_account_id, data=order_body)
        try:
            response = await asyncio.to_thread(self._client.request, request)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"oanda: order create failed — {exc}") from exc

        broker_order_id, status = _extract_order_outcome(response)
        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="oanda",
            brokerOrderId=broker_order_id,
            status=status,
            requestPayload=order_body,
            responsePayload=response if isinstance(response, dict) else {"raw": str(response)},
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        if self._client is None:
            raise BrokerError("oanda: not connected")

        from oandapyV20.endpoints.orders import OrderCancel

        request = OrderCancel(accountID=self._oanda_account_id, orderID=broker_order_id)
        try:
            await asyncio.to_thread(self._client.request, request)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"oanda: cancel order failed — {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_float(value: Any) -> float:
    """Coerce OANDA's string-typed numeric fields to ``float``."""
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _extract_order_outcome(response: Any) -> tuple[str | None, str]:
    """Parse an OANDA OrderCreate response into ``(order_id, status_literal)``.

    OANDA returns either an ``orderFillTransaction`` (market filled
    immediately), an ``orderCreateTransaction`` (limit/stop accepted),
    or an ``orderRejectTransaction``. The status literal matches the
    BrokerOrderResult enum.
    """
    if not isinstance(response, dict):
        return None, "open"

    if "orderFillTransaction" in response:
        fill = response["orderFillTransaction"] or {}
        return str(fill.get("orderID") or fill.get("id") or ""), "filled"
    if "orderCreateTransaction" in response:
        create = response["orderCreateTransaction"] or {}
        return str(create.get("id") or ""), "open"
    if "orderRejectTransaction" in response:
        reject = response["orderRejectTransaction"] or {}
        return str(reject.get("id") or "") or None, "rejected"
    if "orderCancelTransaction" in response:
        cancel = response["orderCancelTransaction"] or {}
        return str(cancel.get("orderID") or cancel.get("id") or "") or None, "cancelled"

    # Unknown shape — record open + leave reconciliation to a future
    # phase. The audit log will still capture the raw response.
    return None, "open"
