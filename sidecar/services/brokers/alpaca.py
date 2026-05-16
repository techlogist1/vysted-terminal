"""Alpaca broker adapter — Phase 5 v0.5.0.

Wraps the official ``alpaca-py`` SDK (0.42.0; the modern replacement for
the deprecated ``alpaca-trade-api``) behind the safety-layer-enforced
:class:`BrokerAdapter` ABC. The SDK ships separate REST clients per
service (``TradingClient``, ``StockHistoricalDataClient``, etc.); the
adapter only owns the ``TradingClient`` because order placement is the
single concern the BLUEPRINT §6.5 surface covers — quotes flow through
the existing Phase-1 yfinance / ccxt providers.

Paper-mode default
------------------

``alpaca-py``'s ``TradingClient(paper=True)`` flips both the base URL
and the auth realm. The adapter constructs the client with ``paper=
self._mode == "paper"`` at connect time and re-builds the client on
:meth:`set_mode` so a paper→live toggle takes effect before the next
order. Live mode is therefore only reachable after both:

  1. :meth:`set_mode` is called with ``"live"`` (gated by the UI's
     live-mode disclaimer per BLUEPRINT §6.5 #8); and
  2. :meth:`connect` is called again with live credentials.

The default constructed state is paper mode; the ABC enforces #1 of
§6.5 already, this adapter just respects it.

Credentials
-----------

BYOK pattern (CLAUDE.md): the caller resolves the API key + secret
from the OS keychain via the Tauri ``keychain_get`` command (keys
``broker:alpaca:api_key`` and ``broker:alpaca:api_secret`` — see the
v0.5.0 keychain namespace commit 0ee1663). The adapter NEVER caches
these beyond the ``TradingClient`` instance lifetime.

Network calls
-------------

``alpaca-py``'s ``TradingClient`` is synchronous (``requests``-based).
The adapter wraps every call in :func:`asyncio.to_thread` so the event
loop is never blocked while waiting for an HTTP response. This matches
the pattern Teammate I uses for the India broker SDKs and keeps the
kill-switch fire latency under 2 s even when an order is in flight.
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


class AlpacaAdapter(BrokerAdapter):
    """Adapter for Alpaca commission-free US equities + crypto.

    Capabilities reflect the Alpaca v2 trading API surface — US stocks
    + ETFs (equity), options (since 2024), and crypto on supported
    pairs. Forex and futures are not supported by Alpaca and stay
    ``False`` in :attr:`CAPABILITIES`.
    """

    BROKER_ID: ClassVar[str] = "alpaca"
    CAPABILITIES: ClassVar[BrokerCapabilities] = BrokerCapabilities(
        supportsEquity=True,
        supportsOptions=True,
        supportsCrypto=True,
        supportsForex=False,
        supportsFutures=False,
        requiresStaticIp=False,
    )

    def __init__(self) -> None:
        super().__init__()
        # Lazy: imports + client instantiation happen on connect() so the
        # adapter can be constructed (and the kill-switch subscription
        # made) without the SDK being importable in a degraded
        # environment. The unit tests monkey-patch this attribute.
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Abstract surface — implementations
    # ------------------------------------------------------------------

    async def _connect(self, credentials: dict[str, str]) -> None:
        api_key = credentials.get("api_key", "")
        api_secret = credentials.get("api_secret", "")
        if not api_key or not api_secret:
            raise BrokerError("alpaca: api_key and api_secret are required")

        # Imported here so the adapter module loads even when alpaca-py
        # is not installed (tests cover the failure path via monkeypatch).
        from alpaca.trading.client import TradingClient

        paper = self._mode == "paper"

        def _make_client() -> Any:
            return TradingClient(api_key=api_key, secret_key=api_secret, paper=paper)

        self._client = await asyncio.to_thread(_make_client)

        # Fetch the account once to validate the credentials + record the
        # account id. Anything raised here propagates and the wrapper
        # writes the failure to the audit log.
        try:
            account = await asyncio.to_thread(self._client.get_account)
        except Exception as exc:  # noqa: BLE001 — SDK-native errors vary
            raise BrokerError(f"alpaca: connect failed — {exc}") from exc

        # ``account.id`` is a UUID; ``account.account_number`` is the
        # human-facing id. Prefer ``account_number`` for audit clarity.
        account_number = getattr(account, "account_number", None) or str(
            getattr(account, "id", "_unknown")
        )
        self._account_id = str(account_number)
        logger.info("alpaca: connected (paper=%s, account=%s)", paper, self._account_id)

    async def _account_info(self) -> AccountSummary:
        if self._client is None:
            raise BrokerError("alpaca: not connected")

        account = await asyncio.to_thread(self._client.get_account)
        positions = await asyncio.to_thread(self._client.get_all_positions)

        mapped_positions = [
            BrokerPosition(
                symbol=str(getattr(pos, "symbol", "")),
                quantity=float(getattr(pos, "qty", 0.0)),
                averageCost=float(getattr(pos, "avg_entry_price", 0.0) or 0.0),
                marketValue=float(getattr(pos, "market_value", 0.0) or 0.0),
                unrealizedPnl=_optional_float(getattr(pos, "unrealized_pl", None)),
            )
            for pos in positions
        ]

        return AccountSummary(
            broker="alpaca",
            accountId=self._account_id or "_unknown",
            currency=str(getattr(account, "currency", "USD")),
            equity=float(getattr(account, "equity", 0.0) or 0.0),
            cash=float(getattr(account, "cash", 0.0) or 0.0),
            buyingPower=float(getattr(account, "buying_power", 0.0) or 0.0),
            positions=mapped_positions,
            capturedAt=int(time.time() * 1000),
        )

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        if self._client is None:
            raise BrokerError("alpaca: not connected")

        from alpaca.trading.enums import OrderSide, TimeInForce
        from alpaca.trading.requests import (
            LimitOrderRequest,
            MarketOrderRequest,
            StopLimitOrderRequest,
            StopOrderRequest,
        )

        side = OrderSide.BUY if proposal.side == "buy" else OrderSide.SELL
        # GTC for limit/stop, DAY for market — matches the alpaca-py
        # defaults for the corresponding order classes and keeps the
        # paper-mode behaviour faithful to live.
        tif_market = TimeInForce.DAY
        tif_other = TimeInForce.GTC

        if proposal.type == "market":
            request: Any = MarketOrderRequest(
                symbol=proposal.symbol,
                qty=proposal.quantity,
                side=side,
                time_in_force=tif_market,
            )
        elif proposal.type == "limit":
            if proposal.limit_price is None:
                raise BrokerError("alpaca: limit order requires limit_price")
            request = LimitOrderRequest(
                symbol=proposal.symbol,
                qty=proposal.quantity,
                side=side,
                time_in_force=tif_other,
                limit_price=proposal.limit_price,
            )
        elif proposal.type == "stop":
            if proposal.stop_price is None:
                raise BrokerError("alpaca: stop order requires stop_price")
            request = StopOrderRequest(
                symbol=proposal.symbol,
                qty=proposal.quantity,
                side=side,
                time_in_force=tif_other,
                stop_price=proposal.stop_price,
            )
        else:  # "stop-limit"
            if proposal.limit_price is None or proposal.stop_price is None:
                raise BrokerError(
                    "alpaca: stop-limit order requires both limit_price and stop_price"
                )
            request = StopLimitOrderRequest(
                symbol=proposal.symbol,
                qty=proposal.quantity,
                side=side,
                time_in_force=tif_other,
                limit_price=proposal.limit_price,
                stop_price=proposal.stop_price,
            )

        try:
            order = await asyncio.to_thread(self._client.submit_order, request)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"alpaca: submit_order failed — {exc}") from exc

        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="alpaca",
            brokerOrderId=str(getattr(order, "id", "")) or None,
            status=_map_alpaca_status(getattr(order, "status", None)),
            requestPayload={
                "symbol": proposal.symbol,
                "qty": proposal.quantity,
                "side": proposal.side,
                "type": proposal.type,
                "limit_price": proposal.limit_price,
                "stop_price": proposal.stop_price,
            },
            responsePayload=_order_to_dict(order),
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        if self._client is None:
            raise BrokerError("alpaca: not connected")
        try:
            await asyncio.to_thread(self._client.cancel_order_by_id, broker_order_id)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"alpaca: cancel_order failed — {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _optional_float(value: Any) -> float | None:
    """Coerce ``value`` to ``float``, returning ``None`` on missing/invalid."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _map_alpaca_status(status: Any) -> str:
    """Map an alpaca-py order status enum/value to the BrokerOrderResult literal.

    Alpaca's order-status taxonomy is wider than the Vysted one (it
    distinguishes ``pending_new`` / ``new`` / ``accepted`` etc.); the
    Vysted ``BrokerOrderResult.status`` literal collapses those to
    ``open``. Anything terminal-fail maps to ``rejected``.
    """
    raw = str(status).lower() if status is not None else ""
    if "filled" == raw or raw == "orderstatus.filled":
        return "filled"
    if "partial" in raw:
        return "partial"
    if "cancel" in raw or "expired" in raw:
        return "cancelled"
    if "reject" in raw or "denied" in raw:
        return "rejected"
    return "open"


def _order_to_dict(order: Any) -> dict[str, Any]:
    """Best-effort dict shaping for an alpaca-py order response.

    The SDK returns Pydantic models for most responses; ``model_dump``
    works when available, otherwise we fall back to attribute scraping.
    Kept defensive so the audit log records something useful regardless
    of SDK-internal type changes.
    """
    dump = getattr(order, "model_dump", None)
    if callable(dump):
        try:
            return {k: _jsonify(v) for k, v in dump().items()}
        except Exception:  # noqa: BLE001
            pass
    keys = ("id", "client_order_id", "symbol", "qty", "side", "status", "type")
    return {k: _jsonify(getattr(order, k, None)) for k in keys}


def _jsonify(value: Any) -> Any:
    """Make a value safe to JSON-encode for the audit log payload."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, list):
        return [_jsonify(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _jsonify(v) for k, v in value.items()}
    return str(value)
