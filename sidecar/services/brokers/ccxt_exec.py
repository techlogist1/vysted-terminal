"""ccxt execution adapter — Phase-5 broker layer on top of Phase-1 ccxt data.

The Phase-1 ``services.ccxt_provider`` module wraps ``ccxt`` for read-only
market data (ticker / OHLCV / ticker stream). This module extends that
foundation to *execution* — balances, place/cancel order — while leaving
the Phase-1 contract untouched. The data layer is consumed by composition
only: this module imports ``ccxt`` directly (same package the data layer
uses) and reuses ``services.ccxt_provider.SUPPORTED_EXCHANGES`` as the
single source of truth for the exchange whitelist.

Each ccxt exchange counts as a distinct :class:`BrokerId`:
``ccxt-bybit``, ``ccxt-binance``, ``ccxt-kraken``, ``ccxt-coinbase``. The
:class:`CcxtExecutionAdapter` is one class parametrised by exchange id;
its ``BROKER_ID`` and ``CAPABILITIES`` are populated at construction time
from the per-exchange tables below. The broker-connect UI lists each
exchange independently so the user can keep, e.g., Bybit on testnet while
Binance is paper-only.

Safety-layer behaviour comes free from :class:`BrokerAdapter`:
``propose_order`` and ``confirm_and_place`` enforce paper-mode default,
position limits, kill-switch state, read-only mode, audit logging, and
the human-confirmed gate. This module only implements the four abstract
broker primitives:

  - :meth:`_connect`        — open a ccxt session with the supplied creds
  - :meth:`_account_info`   — fetch balances + (best-effort) positions
  - :meth:`_place_confirmed` — synthesise a paper fill OR call ccxt live
  - :meth:`_cancel_order`   — cancel a live order by broker id

In paper mode the adapter never reaches the ccxt network — the synthetic
filled result is enough for the audit-log trail proof (this matches the
v0.5.0 plan: live ccxt trades happen during the 60-day paper-soak,
post-ship). In live mode the adapter calls ``exchange.create_order`` /
``exchange.cancel_order``; the ccxt response is captured verbatim into
``responsePayload`` for the audit log.

Tests mock ``ccxt`` end-to-end (``sidecar/tests/conftest.py``'s ``mock_ccxt``
fixture); no live exchange call ever runs in CI.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, ClassVar, cast

import ccxt

from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerId,
    BrokerOrderProposal,
    BrokerOrderResult,
    BrokerPosition,
)
from services.broker_base import BrokerAdapter, BrokerError
from services.ccxt_provider import SUPPORTED_EXCHANGES

# ---------------------------------------------------------------------------
# Per-exchange registry
# ---------------------------------------------------------------------------

#: ccxt exchange id → BrokerId. Mirrors ``types/broker.ts`` BrokerId union.
EXCHANGE_TO_BROKER_ID: dict[str, BrokerId] = {
    "bybit": "ccxt-bybit",
    "binance": "ccxt-binance",
    "kraken": "ccxt-kraken",
    "coinbase": "ccxt-coinbase",
}

#: Reverse map for convenience.
BROKER_ID_TO_EXCHANGE: dict[BrokerId, str] = {v: k for k, v in EXCHANGE_TO_BROKER_ID.items()}

#: Per-exchange capability matrix. Crypto spot is supported everywhere;
#: futures support differs:
#:   * Bybit + Binance support unified futures on the same exchange object.
#:   * Kraken's futures product lives on a separate endpoint
#:     (``krakenfutures``); from a v0.5.0 capability standpoint we report
#:     ``supports_futures=False`` because this adapter targets spot Kraken.
#:   * Coinbase does not offer futures via the public ccxt class.
_FUTURES_SUPPORT: dict[str, bool] = {
    "bybit": True,
    "binance": True,
    "kraken": False,
    "coinbase": False,
}


def _capabilities_for(exchange: str) -> BrokerCapabilities:
    """Build the static capability snapshot for an exchange."""
    return BrokerCapabilities(
        supportsEquity=False,
        supportsOptions=False,
        supportsCrypto=True,
        supportsForex=False,
        supportsFutures=_FUTURES_SUPPORT[exchange],
        requiresStaticIp=False,
    )


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class CcxtExecutionAdapter(BrokerAdapter):
    """Unified ccxt execution adapter parametrised by exchange id.

    One class, four broker ids — the constructor takes the ccxt exchange
    name (``"bybit"`` / ``"binance"`` / ``"kraken"`` / ``"coinbase"``) and
    instantiates the matching ccxt class on connect. ``BROKER_ID`` and
    ``CAPABILITIES`` are populated from the per-exchange tables above
    before the base ``__init__`` runs, so the kill-switch subscription
    registers under the correct broker-specific name.

    The ABC's ``BROKER_ID``/``CAPABILITIES`` are ``ClassVar`` annotations;
    the adapter overrides them as instance attributes — that is the
    intended pattern for parametrised adapters (the base class only reads
    these via ``self.BROKER_ID`` and ``self.CAPABILITIES``).
    """

    #: ABC-required class-level placeholders. Each instance overrides these
    #: with the exchange-specific values; the base class reads via ``self``.
    BROKER_ID: ClassVar[BrokerId] = "ccxt-bybit"
    CAPABILITIES: ClassVar[BrokerCapabilities] = _capabilities_for("bybit")

    def __init__(self, exchange: str, *, testnet: bool = True) -> None:
        if exchange not in SUPPORTED_EXCHANGES:
            raise BrokerError(
                f"unsupported ccxt exchange {exchange!r}; "
                f"supported: {', '.join(SUPPORTED_EXCHANGES)}"
            )
        self._exchange_id: str = exchange
        self._testnet: bool = testnet
        # Override the class-level defaults BEFORE ``super().__init__`` so
        # the kill-switch subscription uses the correct broker id.
        self.BROKER_ID = EXCHANGE_TO_BROKER_ID[exchange]
        self.CAPABILITIES = _capabilities_for(exchange)

        super().__init__()

        #: Held-open ccxt exchange instance — set in ``_connect``.
        self._client: ccxt.Exchange | None = None
        #: Credentials snapshot for diagnostic logging only (no secret).
        self._account_id = ""

    # ------------------------------------------------------------------
    # Accessors / introspection helpers (test-friendly)
    # ------------------------------------------------------------------

    @property
    def exchange_id(self) -> str:
        """Return the ccxt exchange id this adapter is bound to."""
        return self._exchange_id

    @property
    def client(self) -> ccxt.Exchange | None:
        """Return the held-open ccxt client, or None when disconnected."""
        return self._client

    # ------------------------------------------------------------------
    # _connect — open a ccxt session
    # ------------------------------------------------------------------

    async def _connect(self, credentials: dict[str, str]) -> None:
        """Initialise the ccxt instance with the supplied credentials.

        BYOK pattern: the credentials dict is consumed and not retained
        beyond the ccxt instance fields. Per-exchange options:

          * ``bybit`` — testnet flag honoured via ``options.testnet``.
          * ``binance`` — testnet flag honoured via ``options.test`` AND
            ``set_sandbox_mode(True)`` if available.
          * ``kraken`` / ``coinbase`` — no sandbox in ccxt's public class;
            adapter falls through to live endpoints (paper mode still keeps
            the network call from happening; ``_place_confirmed`` short-
            circuits before reaching ccxt).

        The adapter does NOT validate the credentials against the live
        exchange here — that would be a network round-trip. Validation
        happens lazily on the first ``account_info()`` call.
        """
        api_key = credentials.get("api_key", "")
        secret = credentials.get("secret", "")
        passphrase = credentials.get("passphrase", "")  # Coinbase requires this
        if not api_key or not secret:
            raise BrokerError(
                f"{self.BROKER_ID}: connect requires 'api_key' and 'secret' credentials"
            )

        ccxt_cls = getattr(ccxt, self._exchange_id)
        options: dict[str, Any] = {
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        }
        if passphrase:
            options["password"] = passphrase

        per_exchange_options: dict[str, Any] = {}
        if self._exchange_id == "bybit" and self._testnet:
            per_exchange_options["testnet"] = True
        elif self._exchange_id == "binance" and self._testnet:
            per_exchange_options["test"] = True
        if per_exchange_options:
            options["options"] = per_exchange_options

        client = ccxt_cls(options)

        # ccxt's recommended sandbox toggle, available on most exchanges.
        if self._testnet and hasattr(client, "set_sandbox_mode"):
            try:
                client.set_sandbox_mode(True)
            except (AttributeError, NotImplementedError):
                # Some ccxt classes raise NotImplementedError — paper-mode
                # short-circuit in _place_confirmed still protects us.
                pass

        self._client = client
        self._account_id = f"{self._exchange_id}:{api_key[:6]}"

    # ------------------------------------------------------------------
    # _account_info — read balances + positions
    # ------------------------------------------------------------------

    async def _account_info(self) -> AccountSummary:
        """Fetch balances from the exchange and translate to AccountSummary.

        ccxt ``fetch_balance`` returns a dict shaped:

          ``{"USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}, "info": {...}}``

        The adapter sums ``free`` + ``used`` across the quote currency
        (USDT by default, USD for Kraken/Coinbase) into ``equity`` / ``cash`` /
        ``buyingPower``. Open positions are best-effort: ccxt's unified
        ``fetch_positions`` is supported by most exchanges in derivatives
        mode; for spot we surface the non-zero balances as ``BrokerPosition``
        rows so the UI can show them.
        """
        if self._client is None:
            raise BrokerError(f"{self.BROKER_ID}: not connected")

        try:
            balance: dict[str, Any] = self._client.fetch_balance()
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"{self.BROKER_ID}: fetch_balance failed: {exc}") from exc

        quote_currency = _quote_currency_for(self._exchange_id)
        quote = balance.get(quote_currency, {})
        free = float(quote.get("free", 0.0) or 0.0)
        used = float(quote.get("used", 0.0) or 0.0)
        total = float(quote.get("total", free + used) or 0.0)

        positions: list[BrokerPosition] = []
        for asset, detail in balance.items():
            if asset in ("info", "free", "used", "total", "timestamp", "datetime"):
                continue
            if not isinstance(detail, dict):
                continue
            qty = float(detail.get("total", 0.0) or 0.0)
            if qty <= 0 or asset == quote_currency:
                continue
            positions.append(
                BrokerPosition(
                    symbol=asset,
                    quantity=qty,
                    averageCost=0.0,
                    marketValue=0.0,
                    unrealizedPnl=None,
                )
            )

        return AccountSummary(
            broker=self.BROKER_ID,
            accountId=self._account_id or f"{self._exchange_id}:_meta",
            currency=quote_currency,
            equity=total,
            cash=free,
            buyingPower=free,
            positions=positions,
            capturedAt=int(time.time() * 1000),
        )

    # ------------------------------------------------------------------
    # _place_confirmed — paper-synthesise OR live ccxt call
    # ------------------------------------------------------------------

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        """Place an already-confirmed order at the exchange.

        Called ONLY from ``confirm_and_place`` (the ABC enforces that).

        Paper mode: returns a synthetic ``filled`` result without touching
        ccxt. The audit log still records ``order-placed`` with the
        synthetic response — that is the BLUEPRINT §6.5 #1 + #4 promise
        (paper trades produce real audit-log entries with an honest
        ``filled (paper)`` outcome).

        Live mode: calls ``exchange.create_order`` and captures the raw
        response into ``responsePayload``. The ccxt response shape varies
        per exchange; the adapter does not normalise beyond extracting the
        broker order id and the status string.
        """
        request_payload: dict[str, Any] = {
            "exchange": self._exchange_id,
            "symbol": proposal.symbol,
            "type": proposal.type,
            "side": proposal.side,
            "amount": proposal.quantity,
            "price": proposal.limit_price,
            "stopPrice": proposal.stop_price,
        }

        if self._mode == "paper":
            # Synthesise a filled paper result without touching the network.
            broker_order_id = f"paper-{self._exchange_id}-{uuid.uuid4().hex[:12]}"
            return BrokerOrderResult(
                proposalId=proposal.proposal_id,
                broker=self.BROKER_ID,
                brokerOrderId=broker_order_id,
                status="filled",
                requestPayload=request_payload,
                responsePayload={
                    "synthetic": True,
                    "mode": "paper",
                    "exchange": self._exchange_id,
                    "filledQty": proposal.quantity,
                    "fillPrice": proposal.limit_price,
                    "note": "paper-mode synthetic fill (no network call)",
                },
                placedAt=int(time.time() * 1000),
            )

        # Live path.
        if self._client is None:
            raise BrokerError(f"{self.BROKER_ID}: cannot place live order — not connected")

        try:
            response: dict[str, Any] = self._client.create_order(
                proposal.symbol,
                proposal.type,
                proposal.side,
                proposal.quantity,
                proposal.limit_price,
            )
        except Exception as exc:  # noqa: BLE001 — ccxt errors vary widely
            raise BrokerError(f"{self.BROKER_ID}: create_order failed: {exc}") from exc

        broker_order_id = str(response.get("id") or "")
        status = _ccxt_status_to_result_status(response.get("status"))

        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker=self.BROKER_ID,
            brokerOrderId=broker_order_id or None,
            status=status,
            requestPayload=request_payload,
            responsePayload=response,
            placedAt=int(time.time() * 1000),
        )

    # ------------------------------------------------------------------
    # _cancel_order — cancel by broker id
    # ------------------------------------------------------------------

    async def _cancel_order(self, broker_order_id: str) -> None:
        """Cancel an open order at the exchange.

        Paper-synthetic ids (prefixed ``paper-``) are no-ops at the network
        level — they only exist in the audit log. The base class still
        writes the ``order-cancelled`` audit row, which is what the user
        sees in the Audit Log Viewer.
        """
        if broker_order_id.startswith("paper-"):
            return
        if self._mode == "paper":
            # Live-id arriving in paper mode is suspect, but we still
            # short-circuit rather than reach out to the exchange.
            return
        if self._client is None:
            raise BrokerError(f"{self.BROKER_ID}: cannot cancel — not connected")
        try:
            self._client.cancel_order(broker_order_id)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(
                f"{self.BROKER_ID}: cancel_order failed for {broker_order_id}: {exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _quote_currency_for(exchange: str) -> str:
    """Per-exchange default quote currency used for balance summary."""
    return {
        "bybit": "USDT",
        "binance": "USDT",
        "kraken": "USD",
        "coinbase": "USD",
    }.get(exchange, "USDT")


_CCXT_STATUS_MAP: dict[str, str] = {
    "open": "open",
    "closed": "filled",
    "canceled": "cancelled",
    "cancelled": "cancelled",
    "expired": "cancelled",
    "rejected": "rejected",
    "partial": "partial",
    "partially_filled": "partial",
}


def _ccxt_status_to_result_status(raw: Any) -> str:
    """Map a ccxt order status string to BrokerOrderResult.status.

    Falls back to ``"open"`` on unknown statuses so an unrecognised live
    response still produces a valid Pydantic model rather than crashing
    the audit-log write path.
    """
    if not isinstance(raw, str):
        return "open"
    return cast(str, _CCXT_STATUS_MAP.get(raw.lower(), "open"))


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def build_all_adapters(*, testnet: bool = True) -> dict[BrokerId, CcxtExecutionAdapter]:
    """Construct one adapter per supported ccxt exchange.

    Used by the sidecar startup path to populate the broker registry with
    one entry per ``ccxt-*`` BrokerId. Caller is responsible for calling
    ``connect`` on each adapter when the user supplies credentials.
    """
    return {
        EXCHANGE_TO_BROKER_ID[ex]: CcxtExecutionAdapter(ex, testnet=testnet)
        for ex in SUPPORTED_EXCHANGES
    }
