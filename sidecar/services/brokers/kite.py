"""Kite Connect (Zerodha) broker adapter — India equities + F&O + currencies.

Distinctive feature vs Dhan / Angel One: ``CAPABILITIES.requires_static_ip``
is ``True``. SEBI/NSE retail-algo compliance (in effect 2026-04-01) requires
a static IP registered with the broker for order-placement API calls. The
adapter does NOT pre-block placement (the user may be behind a VPN/VPS with
the registered IP even when the detected default-route IP differs); it
overrides :meth:`set_mode` so that the live-mode toggle records a
``StaticIpStatus`` snapshot to the audit log. The frontend banner
component (``src/modules/broker-connect/kite-static-ip-banner.tsx``) polls
``GET /safety/static-ip-status`` and surfaces the visual cue.

Kite's session model uses a per-day access token derived from a one-time
``request_token`` (the user logs in at kite.zerodha.com and pastes the
URL back into the plugin); the access token expires daily. The adapter
expects the frontend to handle the token-refresh dance — the credentials
dict at ``_connect`` time carries the resolved ``api_key`` + ``access_token``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, ClassVar

from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerMode,
    BrokerOrderProposal,
    BrokerOrderResult,
    BrokerPosition,
)
from models.broker_reads import (
    BrokerHolding,
    BrokerHoldingsResult,
    BrokerLegPosition,
    BrokerMarginsResult,
    BrokerPositionsResult,
    BrokerSegmentMargin,
)
from models.safety import AuditLogAppendRequest
from services import audit_log, static_ip_detector
from services.broker_base import BrokerAdapter, BrokerError
from services.brokers.dhan import _synthetic_paper_result

logger = logging.getLogger(__name__)


class KiteAdapter(BrokerAdapter):
    """Kite Connect execution adapter — the static-IP-aware broker."""

    BROKER_ID: ClassVar = "kite"
    CAPABILITIES: ClassVar = BrokerCapabilities(
        supportsEquity=True,
        supportsOptions=True,
        supportsCrypto=False,
        supportsForex=True,
        supportsFutures=True,
        # The load-bearing line for the static-IP UX path.
        requiresStaticIp=True,
    )

    def __init__(self) -> None:
        super().__init__()
        self._client: Any | None = None
        #: Last user-configured static IP — frontend posts it via
        #: ``POST /brokers/kite/static-ip`` and the adapter persists it for
        #: the audit-log record on mode toggle. ``None`` until set.
        self._configured_static_ip: str | None = None

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    async def _connect(self, credentials: dict[str, str]) -> None:
        """Open a Kite Connect session.

        Required credentials: ``api_key``, ``access_token`` (resolved from
        the daily login dance). The user id (clientId) is fetched from
        ``profile()`` and stored as ``_account_id``.
        """
        api_key = credentials.get("api_key") or credentials.get("apiKey")
        access_token = credentials.get("access_token") or credentials.get("accessToken")
        if not api_key or not access_token:
            raise BrokerError(
                "kite: connect requires both 'api_key' and 'access_token' credentials"
            )

        # Optional: the frontend may include the configured static IP at
        # connect time to seed the detector comparison.
        configured_ip = credentials.get("static_ip") or credentials.get("staticIp")
        if configured_ip:
            self._configured_static_ip = configured_ip.strip()

        try:
            from kiteconnect import KiteConnect  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise BrokerError(f"kite: kiteconnect SDK not installed: {exc}") from exc

        client = await asyncio.to_thread(KiteConnect, api_key=api_key)
        await asyncio.to_thread(client.set_access_token, access_token)
        try:
            profile = await asyncio.to_thread(client.profile)
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"kite: profile lookup failed: {exc}") from exc

        self._client = client
        self._account_id = str((profile or {}).get("user_id") or "_unset")

    # ------------------------------------------------------------------
    # Static-IP UX path
    # ------------------------------------------------------------------

    def set_configured_static_ip(self, ip: str | None) -> None:
        """Persist the user's configured static IP in-memory.

        The frontend writes this through ``POST /brokers/kite/static-ip``;
        the value is consumed by :meth:`set_mode` (which audit-logs the
        detected-vs-configured comparison on the live-mode toggle) and by
        the banner component which polls
        ``GET /safety/static-ip-status?configured=<ip>``.
        """
        if ip is None or not ip.strip():
            self._configured_static_ip = None
        else:
            self._configured_static_ip = ip.strip()

    def configured_static_ip(self) -> str | None:
        """Return the currently-configured static IP (for the router)."""
        return self._configured_static_ip

    async def set_mode(self, mode: BrokerMode) -> None:
        """Switch between paper and live, with a static-IP audit-log on live.

        When the user toggles to live mode the adapter:

          1. Defers to the base ``set_mode`` for the standard mode-changed
             audit row.
          2. Runs the static-IP detector against the user's configured IP
             (which the frontend should have posted via
             ``POST /brokers/kite/static-ip`` before flipping the toggle).
          3. Writes a second audit row carrying the detection result so the
             user has a record of "the live toggle happened, here is what
             the static-IP status looked like at that moment" — load-bearing
             for the "we did not silently violate SEBI rule" defence if a
             rejection happens later.
        """
        await super().set_mode(mode)
        if mode != "live":
            return

        try:
            status = await static_ip_detector.static_ip_status(self._configured_static_ip)
        except Exception as exc:  # noqa: BLE001 - never raise inside set_mode
            logger.warning("kite: static-ip detection raised %s", exc)
            return

        audit_log.append(
            AuditLogAppendRequest(
                timestampMs=int(time.time() * 1000),
                broker=self.BROKER_ID,
                accountId=self._account_id or "_meta",
                action="mode-changed",
                payload={
                    "staticIpStatus": status.model_dump(by_alias=True, exclude_none=False),
                },
                source="system",
                outcome="ok" if status.matches else "static-ip-mismatch",
            )
        )

    # ------------------------------------------------------------------
    # Account
    # ------------------------------------------------------------------

    async def _account_info(self) -> AccountSummary:
        if self._mode == "paper" or self._client is None:
            return AccountSummary(
                broker="kite",
                accountId=self._account_id or "paper-kite",
                currency="INR",
                equity=1_000_000.0,
                cash=500_000.0,
                buyingPower=1_000_000.0,
                positions=[],
                capturedAt=int(time.time() * 1000),
            )

        try:
            margins = await asyncio.to_thread(self._client.margins)
            holdings = await asyncio.to_thread(self._client.holdings)
            positions = await asyncio.to_thread(self._client.positions)
        except Exception as exc:  # noqa: BLE001
            _raise_kite_read_error(exc)

        # Kite's margins returns ``{"equity": {"available": {"cash": n},
        # "net": n, ...}, ...}``. Use ``net`` for equity + buying power (the old
        # code used ``available.cash`` for all three, hiding F&O/used margin);
        # keep ``available.cash`` for the cash line.
        equity_block = (margins or {}).get("equity") or {}
        available = equity_block.get("available") or {}
        net = float(equity_block.get("net") or 0.0)
        cash = float(available.get("cash") or 0.0)
        return AccountSummary(
            broker="kite",
            accountId=self._account_id,
            currency="INR",
            equity=net,
            cash=cash,
            buyingPower=net,
            # Long-term holdings + intraday/F&O net positions (the old code
            # fetched holdings only, so open F&O/intraday P&L was invisible).
            positions=_translate_kite_positions_and_holdings(positions or {}, holdings or []),
            capturedAt=int(time.time() * 1000),
        )

    # ------------------------------------------------------------------
    # Granular read-only reads (FR-042) — NET-NEW, not on the LOCKED ABC.
    #
    # Each calls the DISTINCT kiteconnect read endpoint and returns the
    # unmerged real shape. Paper / disconnected → a clearly-labelled
    # synthetic result (synthetic=True, mode="paper") rather than a
    # fabricated real-looking holding. No order/cancel path is reachable
    # from here — these are pure reads (§6.5 untouched).
    # ------------------------------------------------------------------

    def _provenance_kwargs(self) -> dict[str, Any]:
        """Shared FR-041 provenance fields for a granular read result."""
        synthetic = self._mode == "paper" or self._client is None
        return {
            "broker": "kite",
            "accountId": self._account_id or ("paper-kite" if synthetic else "_unset"),
            "synthetic": synthetic,
            "mode": self._mode,
            "provider": "kite",
            "capturedAt": int(time.time() * 1000),
        }

    async def positions_info(self) -> BrokerPositionsResult:
        """Intraday / F&O positions via the distinct ``positions()`` call."""
        if self._mode == "paper" or self._client is None:
            return BrokerPositionsResult(**self._provenance_kwargs())
        try:
            positions = await asyncio.to_thread(self._client.positions)
        except Exception as exc:  # noqa: BLE001
            _raise_kite_read_error(exc)
        positions = positions or {}
        return BrokerPositionsResult(
            net=_translate_kite_legs(positions.get("net") or []),
            day=_translate_kite_legs(positions.get("day") or []),
            **self._provenance_kwargs(),
        )

    async def holdings_info(self) -> BrokerHoldingsResult:
        """Settled long-term holdings via the distinct ``holdings()`` call."""
        if self._mode == "paper" or self._client is None:
            return BrokerHoldingsResult(**self._provenance_kwargs())
        try:
            holdings = await asyncio.to_thread(self._client.holdings)
        except Exception as exc:  # noqa: BLE001
            _raise_kite_read_error(exc)
        return BrokerHoldingsResult(
            holdings=_translate_kite_holdings_granular(holdings or []),
            **self._provenance_kwargs(),
        )

    async def margins_info(self) -> BrokerMarginsResult:
        """Per-segment funds via the distinct ``margins()`` call."""
        if self._mode == "paper" or self._client is None:
            return BrokerMarginsResult(**self._provenance_kwargs())
        try:
            margins = await asyncio.to_thread(self._client.margins)
        except Exception as exc:  # noqa: BLE001
            _raise_kite_read_error(exc)
        return BrokerMarginsResult(
            segments=_translate_kite_margins(margins or {}),
            **self._provenance_kwargs(),
        )

    # ------------------------------------------------------------------
    # Order placement
    # ------------------------------------------------------------------

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        """Place a confirmed order at Kite Connect.

        Paper mode short-circuits before any SDK call. Live mode runs the
        Kite SDK's ``place_order`` on a thread; any SDK exception (including
        the static-IP rejection from SEBI/NSE) propagates and the ABC will
        audit-log it as ``order-rejected``. The Kite static-IP rejection
        manifests as a ``kiteconnect.exceptions.NetworkException`` or
        ``InputException`` depending on which gateway returned the 403 —
        downstream UX surfaces the audit-log line.
        """
        if self._mode == "paper":
            return _synthetic_paper_result("kite", proposal)

        if self._client is None:
            raise BrokerError("kite: live order placement requires a connected client")

        params = {
            "variety": "regular",
            "exchange": _kite_exchange(proposal.symbol),
            "tradingsymbol": proposal.symbol,
            "transaction_type": "BUY" if proposal.side == "buy" else "SELL",
            "quantity": int(proposal.quantity),
            "product": "CNC",
            "order_type": _kite_order_type(proposal.type),
            "price": proposal.limit_price or 0.0,
            "trigger_price": proposal.stop_price or 0.0,
        }

        try:
            response = await asyncio.to_thread(self._client.place_order, **params)
        except Exception as exc:  # noqa: BLE001 — Kite SDK raises bespoke exception classes
            raise BrokerError(f"kite: place_order failed: {exc}") from exc

        # Kite returns the broker-side order id directly (string) on success.
        broker_order_id: str | None
        if isinstance(response, str):
            broker_order_id = response
        elif isinstance(response, dict):
            broker_order_id = response.get("order_id")
        else:
            broker_order_id = None

        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="kite",
            brokerOrderId=broker_order_id,
            status="open" if broker_order_id else "rejected",
            requestPayload=params,
            responsePayload=(
                {"order_id": broker_order_id} if broker_order_id else {"raw": str(response)}
            ),
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        if self._mode == "paper":
            return
        if self._client is None:
            raise BrokerError("kite: live cancel requires a connected client")
        try:
            await asyncio.to_thread(
                self._client.cancel_order, variety="regular", order_id=broker_order_id
            )
        except Exception as exc:  # noqa: BLE001
            raise BrokerError(f"kite: cancel_order failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kite_exchange(symbol: str) -> str:
    upper = symbol.upper()
    if upper.endswith("BSE"):
        return "BSE"
    return "NSE"


def _kite_order_type(order_type: str) -> str:
    mapping = {
        "market": "MARKET",
        "limit": "LIMIT",
        "stop": "SL-M",
        "stop-limit": "SL",
    }
    return mapping.get(order_type, "MARKET")


def _translate_kite_holdings(holdings: list[dict[str, Any]]) -> list[BrokerPosition]:
    out: list[BrokerPosition] = []
    for h in holdings or []:
        quantity = float(h.get("quantity") or 0.0)
        if quantity == 0:
            continue
        avg_cost = float(h.get("average_price") or 0.0)
        last_price = float(h.get("last_price") or avg_cost)
        out.append(
            BrokerPosition(
                symbol=str(h.get("tradingsymbol") or ""),
                quantity=quantity,
                averageCost=avg_cost,
                marketValue=quantity * last_price,
                unrealizedPnl=float(h.get("pnl") or 0.0),
            )
        )
    return out


def _translate_kite_positions_and_holdings(
    positions: dict[str, Any], holdings: list[dict[str, Any]]
) -> list[BrokerPosition]:
    """Merge long-term holdings with intraday/F&O net positions."""
    out = _translate_kite_holdings(holdings)
    for p in (positions or {}).get("net") or []:
        quantity = float(p.get("quantity") or 0.0)
        if quantity == 0:
            continue
        avg_cost = float(p.get("average_price") or 0.0)
        last_price = float(p.get("last_price") or avg_cost)
        out.append(
            BrokerPosition(
                symbol=str(p.get("tradingsymbol") or ""),
                quantity=quantity,
                averageCost=avg_cost,
                marketValue=quantity * last_price,
                unrealizedPnl=float(p.get("pnl") or 0.0),
            )
        )
    return out


def _translate_kite_legs(legs: list[dict[str, Any]]) -> list[BrokerLegPosition]:
    """Map Kite ``positions()`` net/day legs to :class:`BrokerLegPosition`.

    Unlike the merged ``_account_info`` path this keeps the genuine intraday/F&O
    shape — including realized P&L, which the merged ``BrokerPosition`` has no
    field for."""
    out: list[BrokerLegPosition] = []
    for leg in legs or []:
        quantity = float(leg.get("quantity") or 0.0)
        avg_cost = float(leg.get("average_price") or 0.0)
        last_price = float(leg.get("last_price") or avg_cost)
        out.append(
            BrokerLegPosition(
                symbol=str(leg.get("tradingsymbol") or ""),
                quantity=quantity,
                averageCost=avg_cost,
                lastPrice=last_price,
                unrealizedPnl=float(leg.get("unrealised") or leg.get("pnl") or 0.0),
                realizedPnl=float(leg["realised"]) if leg.get("realised") is not None else None,
                product=str(leg.get("product")) if leg.get("product") else None,
            )
        )
    return out


def _translate_kite_holdings_granular(holdings: list[dict[str, Any]]) -> list[BrokerHolding]:
    """Map Kite ``holdings()`` rows to :class:`BrokerHolding` (settled long-term)."""
    out: list[BrokerHolding] = []
    for h in holdings or []:
        quantity = float(h.get("quantity") or 0.0)
        avg_cost = float(h.get("average_price") or 0.0)
        last_price = float(h.get("last_price") or avg_cost)
        out.append(
            BrokerHolding(
                symbol=str(h.get("tradingsymbol") or ""),
                quantity=quantity,
                averageCost=avg_cost,
                lastPrice=last_price,
                marketValue=quantity * last_price,
                unrealizedPnl=float(h.get("pnl") or 0.0),
            )
        )
    return out


def _translate_kite_margins(margins: dict[str, Any]) -> list[BrokerSegmentMargin]:
    """Map Kite ``margins()`` to per-segment available/used/net rows.

    Kite returns ``{"equity": {"available": {"cash": n, ...}, "utilised":
    {...}, "net": n}, "commodity": {...}}``. We sum the ``available`` and
    ``utilised`` sub-maps and read ``net`` directly — one row per segment."""
    out: list[BrokerSegmentMargin] = []
    for segment, block in (margins or {}).items():
        if not isinstance(block, dict):
            continue
        available_block = block.get("available") or {}
        utilised_block = block.get("utilised") or block.get("used") or {}
        available = (
            sum(float(v or 0.0) for v in available_block.values())
            if isinstance(available_block, dict)
            else float(available_block or 0.0)
        )
        used = (
            sum(float(v or 0.0) for v in utilised_block.values())
            if isinstance(utilised_block, dict)
            else float(utilised_block or 0.0)
        )
        out.append(
            BrokerSegmentMargin(
                segment=str(segment),
                currency="INR",
                available=available,
                used=used,
                net=float(block.get("net") or 0.0),
            )
        )
    return out


def _raise_kite_read_error(exc: Exception) -> None:
    """Map a Kite read failure to a typed BrokerError. The daily token expiry
    (``TokenException``, HTTP 403) is flagged distinctly so the route can surface
    a 419 'reconnect' cue rather than a generic red error."""
    if type(exc).__name__ == "TokenException":
        raise BrokerError("kite: session expired — reconnect (daily token expiry)") from exc
    raise BrokerError(f"kite: account fetch failed: {exc}") from exc


async def exchange_request_token(
    api_key: str, api_secret: str, request_token: str
) -> dict[str, Any]:
    """Exchange a one-time ``request_token`` for a daily ``access_token`` via the
    real Kite Connect login flow.

    ``KiteConnect.generate_session`` computes the SHA-256 checksum
    (``api_key + request_token + api_secret``) and POSTs ``/session/token``
    internally — this is the genuine OAuth login-token exchange, NOT a static
    pasted token. The ``api_secret`` is used ONLY here; the resolved
    ``access_token`` is what :meth:`KiteAdapter._connect` consumes.
    """
    if not api_key or not api_secret or not request_token:
        raise BrokerError("kite: api_key, api_secret, and request_token are all required")
    try:
        from kiteconnect import KiteConnect  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise BrokerError(f"kite: kiteconnect SDK not installed: {exc}") from exc
    client = await asyncio.to_thread(KiteConnect, api_key=api_key)
    try:
        data = await asyncio.to_thread(
            client.generate_session, request_token, api_secret=api_secret
        )
    except Exception as exc:  # noqa: BLE001
        raise BrokerError(f"kite: login exchange failed: {exc}") from exc
    access_token = (data or {}).get("access_token")
    if not access_token:
        raise BrokerError("kite: login exchange returned no access_token")
    return {
        "access_token": access_token,
        "user_id": (data or {}).get("user_id"),
        "login_time": str((data or {}).get("login_time") or ""),
    }
