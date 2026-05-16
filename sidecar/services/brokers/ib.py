"""Interactive Brokers adapter — Phase 5 v0.5.0.

Wraps ``ib_async`` (2.1.0; the maintained fork of ``ib_insync`` from
``ib-api-reloaded/ib_async``) behind the safety-layer-enforced
:class:`BrokerAdapter` ABC.

Hard dependency: TWS or IB Gateway
----------------------------------

Interactive Brokers does NOT expose a hosted REST API. The
``ib_async`` library speaks IB's proprietary TWS API over a TCP socket
to a locally-running Java app — either Trader Workstation (TWS) or IB
Gateway. The user must install one of those separately from Vysted
Terminal; documented in ``docs/BROKER_INTEGRATIONS.md``.

Default endpoints (BLUEPRINT §6.5 #1 — paper first):

- Paper:    ``127.0.0.1:7497`` (TWS paper) — adapter default
- Live:     ``127.0.0.1:7496`` (TWS live)
- Gateway paper: ``127.0.0.1:4002`` (IB Gateway paper)
- Gateway live:  ``127.0.0.1:4001`` (IB Gateway live)

The user can override the host/port via the connect ``credentials``
dict (keys ``host``, ``port``, ``client_id``); the adapter selects the
paper or live default port from the current :attr:`mode` if the user
does not override.

Connection failures
-------------------

If TWS / IB Gateway is not running, ``ib_async.IB.connectAsync``
raises ``ConnectionRefusedError``. The adapter wraps this in a
clear :class:`BrokerError` message so the broker-connect UI can render
a useful "TWS or IB Gateway not detected on 127.0.0.1:7497 — start the
Gateway and retry" string rather than a stack trace.

Threading
---------

``ib_async`` is natively asyncio-friendly: ``connectAsync``,
``placeOrder`` returning a ``Trade`` object that fills via events,
``accountSummaryAsync``. The adapter awaits these directly. The
synchronous-blocking dance the Alpaca adapter performs via
``asyncio.to_thread`` is therefore unnecessary here.
"""

from __future__ import annotations

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

# ---------------------------------------------------------------------------
# Default endpoints — paper-first per BLUEPRINT §6.5 #1
# ---------------------------------------------------------------------------

DEFAULT_TWS_PAPER_PORT = 7497
DEFAULT_TWS_LIVE_PORT = 7496
DEFAULT_GATEWAY_PAPER_PORT = 4002
DEFAULT_GATEWAY_LIVE_PORT = 4001
DEFAULT_HOST = "127.0.0.1"
DEFAULT_CLIENT_ID = 1


class IBAdapter(BrokerAdapter):
    """Adapter for Interactive Brokers (TWS / IB Gateway).

    Capabilities: stocks (equity), options, futures, forex. IB supports
    crypto through Paxos but only on the live account; we mark
    ``supportsCrypto=False`` here since paper-mode default precludes a
    crypto test path. Users who want crypto via IB should use the
    Phase-5 ``ccxt`` plugin instead.
    """

    BROKER_ID: ClassVar[str] = "ib"
    CAPABILITIES: ClassVar[BrokerCapabilities] = BrokerCapabilities(
        supportsEquity=True,
        supportsOptions=True,
        supportsCrypto=False,
        supportsForex=True,
        supportsFutures=True,
        requiresStaticIp=False,
    )

    def __init__(self) -> None:
        super().__init__()
        # The active ``ib_async.IB`` instance, or ``None`` when not
        # connected. Tests monkey-patch this directly so they don't
        # need TWS running.
        self._ib: Any | None = None
        self._host: str = DEFAULT_HOST
        self._port: int = DEFAULT_TWS_PAPER_PORT
        self._client_id: int = DEFAULT_CLIENT_ID

    # ------------------------------------------------------------------
    # Abstract surface — implementations
    # ------------------------------------------------------------------

    async def _connect(self, credentials: dict[str, str]) -> None:
        # Imported here so the adapter can be constructed without the
        # SDK available (mirrors AlpacaAdapter).
        from ib_async import IB

        self._host = credentials.get("host", DEFAULT_HOST)
        # Pick the paper / live port from the mode unless explicitly
        # overridden in the credentials blob.
        if "port" in credentials and credentials["port"]:
            try:
                self._port = int(credentials["port"])
            except (TypeError, ValueError) as exc:
                raise BrokerError(f"ib: invalid port {credentials['port']!r}") from exc
        else:
            self._port = DEFAULT_TWS_PAPER_PORT if self._mode == "paper" else DEFAULT_TWS_LIVE_PORT
        try:
            self._client_id = int(credentials.get("client_id", DEFAULT_CLIENT_ID))
        except (TypeError, ValueError) as exc:
            raise BrokerError(f"ib: invalid client_id {credentials.get('client_id')!r}") from exc

        ib = IB()
        try:
            await ib.connectAsync(
                host=self._host, port=self._port, clientId=self._client_id, timeout=10
            )
        except ConnectionRefusedError as exc:
            raise BrokerError(
                f"ib: TWS or IB Gateway not detected on {self._host}:{self._port} — "
                "start TWS (or IB Gateway) and retry"
            ) from exc
        except TimeoutError as exc:
            raise BrokerError(f"ib: connect timed out reaching {self._host}:{self._port}") from exc
        except Exception as exc:  # noqa: BLE001 — ib_async surfaces many error shapes
            raise BrokerError(f"ib: connect failed — {exc}") from exc

        self._ib = ib

        # Read the managed-accounts list once so we can stamp the
        # primary account id into the audit-log rows.
        accounts = ib.managedAccounts()
        if accounts:
            self._account_id = str(accounts[0])
        else:
            self._account_id = "_unknown"
        logger.info(
            "ib: connected (%s:%s clientId=%s mode=%s account=%s)",
            self._host,
            self._port,
            self._client_id,
            self._mode,
            self._account_id,
        )

    async def _account_info(self) -> AccountSummary:
        if self._ib is None:
            raise BrokerError("ib: not connected")

        # accountSummaryAsync returns a list of AccountValue items
        # keyed by tag; positions() is sync but cheap (cached snapshot).
        summary_rows = await self._ib.accountSummaryAsync()
        positions_raw = self._ib.positions()

        def _value_for(tag: str, currency_filter: str | None = None) -> float:
            for row in summary_rows:
                if str(getattr(row, "tag", "")) == tag and (
                    currency_filter is None or str(getattr(row, "currency", "")) == currency_filter
                ):
                    try:
                        return float(getattr(row, "value", 0.0))
                    except (TypeError, ValueError):
                        return 0.0
            return 0.0

        # IB summary rows have a per-currency variant for some tags
        # ("EquityWithLoanValue" with currency="USD", or "BASE"). Use
        # "BASE" when present, falling back to the unfiltered match.
        currency = "USD"
        for row in summary_rows:
            if str(getattr(row, "tag", "")) == "AccountType":
                pass
            if str(getattr(row, "tag", "")) == "Currency":
                currency = str(getattr(row, "value", currency))
                break

        equity = _value_for("NetLiquidation", "BASE") or _value_for("NetLiquidation")
        cash = _value_for("TotalCashValue", "BASE") or _value_for("TotalCashValue")
        buying_power = _value_for("BuyingPower", "BASE") or _value_for("BuyingPower")

        mapped_positions = [
            BrokerPosition(
                symbol=str(getattr(getattr(pos, "contract", None), "symbol", "")),
                quantity=float(getattr(pos, "position", 0.0) or 0.0),
                averageCost=float(getattr(pos, "avgCost", 0.0) or 0.0),
                marketValue=0.0,  # ib_async positions don't include mark; left zero
                unrealizedPnl=None,
            )
            for pos in positions_raw
        ]

        return AccountSummary(
            broker="ib",
            accountId=self._account_id or "_unknown",
            currency=currency,
            equity=equity,
            cash=cash,
            buyingPower=buying_power,
            positions=mapped_positions,
            capturedAt=int(time.time() * 1000),
        )

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        if self._ib is None:
            raise BrokerError("ib: not connected")

        from ib_async import LimitOrder, MarketOrder, Stock, StopLimitOrder, StopOrder

        # IB requires a Contract; for v0.5.0 we ship Stock only and let
        # future phases extend to Forex / Future contract types. The
        # contract is fully qualified by ib_async at order time.
        contract = Stock(proposal.symbol, "SMART", proposal.currency)

        action = "BUY" if proposal.side == "buy" else "SELL"
        qty = proposal.quantity

        if proposal.type == "market":
            order = MarketOrder(action, qty)
        elif proposal.type == "limit":
            if proposal.limit_price is None:
                raise BrokerError("ib: limit order requires limit_price")
            order = LimitOrder(action, qty, proposal.limit_price)
        elif proposal.type == "stop":
            if proposal.stop_price is None:
                raise BrokerError("ib: stop order requires stop_price")
            order = StopOrder(action, qty, proposal.stop_price)
        else:  # "stop-limit"
            if proposal.limit_price is None or proposal.stop_price is None:
                raise BrokerError("ib: stop-limit order requires both limit_price and stop_price")
            order = StopLimitOrder(action, qty, proposal.limit_price, proposal.stop_price)

        try:
            trade = self._ib.placeOrder(contract, order)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"ib: placeOrder failed — {exc}") from exc

        # ``placeOrder`` returns synchronously with a Trade object; the
        # actual fill arrives via events. We capture the initial status
        # and let the post-placement reconciliation route (future
        # phase) keep tracking. status field maps to BrokerOrderResult.
        order_status = getattr(getattr(trade, "orderStatus", None), "status", "Submitted")
        order_id = getattr(getattr(trade, "order", None), "orderId", None)

        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="ib",
            brokerOrderId=str(order_id) if order_id is not None else None,
            status=_map_ib_status(order_status),
            requestPayload={
                "symbol": proposal.symbol,
                "qty": proposal.quantity,
                "side": proposal.side,
                "type": proposal.type,
                "limit_price": proposal.limit_price,
                "stop_price": proposal.stop_price,
                "currency": proposal.currency,
            },
            responsePayload={
                "orderId": order_id,
                "status": str(order_status),
                "contract": proposal.symbol,
            },
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        if self._ib is None:
            raise BrokerError("ib: not connected")

        # ib_async cancelOrder takes the Order object, not the id —
        # we have to resolve via openOrders() first.
        try:
            order_id_int = int(broker_order_id)
        except (TypeError, ValueError) as exc:
            raise BrokerError(f"ib: invalid broker_order_id {broker_order_id!r}") from exc

        open_trades = self._ib.openTrades()
        target = None
        for trade in open_trades:
            if int(getattr(getattr(trade, "order", None), "orderId", -1)) == order_id_int:
                target = trade.order
                break
        if target is None:
            raise BrokerError(f"ib: open order with id {order_id_int} not found")

        try:
            self._ib.cancelOrder(target)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"ib: cancelOrder failed — {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _map_ib_status(status: Any) -> str:
    """Map an IB order-status string to the BrokerOrderResult literal."""
    raw = str(status).lower() if status is not None else ""
    if raw == "filled":
        return "filled"
    if raw in ("partiallyfilled", "partially_filled"):
        return "partial"
    if raw in ("cancelled", "apicancelled", "pendingcancel"):
        return "cancelled"
    if raw in ("inactive", "apicancelfailed"):
        return "rejected"
    return "open"
