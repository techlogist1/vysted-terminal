"""Tests for the Alpaca broker adapter.

These tests fully mock the ``alpaca-py`` SDK — they verify the
:class:`AlpacaAdapter` correctly wires the BrokerAdapter ABC, drives
the SDK with the right request shapes, and surfaces the SDK responses
through the BrokerOrderResult / AccountSummary contract.

We do NOT hit Alpaca's real endpoints from CI — paper-mode endpoints
are free but unstable for a deterministic test suite. The mock surface
is narrow on purpose: an ``alpaca-py`` upgrade that breaks the assumed
attributes is the kind of thing the integration tests + the
"populated screenshot" checkpoint catch.
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from config import DATA_DIR_ENV
from models.broker import BrokerOrderProposal
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers.alpaca import AlpacaAdapter, _map_alpaca_status


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def fresh_bus() -> None:
    kill_switch.reset_bus_for_tests()
    yield
    kill_switch.reset_bus_for_tests()


# ---------------------------------------------------------------------------
# Test scaffolding — a fake TradingClient
# ---------------------------------------------------------------------------


def _fake_account(**overrides: Any) -> SimpleNamespace:
    defaults = dict(
        account_number="PA1234567",
        id="acct-uuid",
        currency="USD",
        equity="100000.00",
        cash="50000.00",
        buying_power="200000.00",
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _fake_position(symbol: str, qty: float, price: float) -> SimpleNamespace:
    return SimpleNamespace(
        symbol=symbol,
        qty=str(qty),
        avg_entry_price=str(price),
        market_value=str(qty * price),
        unrealized_pl="0.00",
    )


def _fake_order(order_id: str = "alpaca-order-1", status: str = "accepted") -> SimpleNamespace:
    return SimpleNamespace(
        id=order_id,
        client_order_id="cli-1",
        symbol="AAPL",
        qty="10",
        side="buy",
        status=status,
        type="limit",
    )


def _patch_trading_client(monkeypatch: pytest.MonkeyPatch, fake: Any) -> None:
    """Replace ``alpaca.trading.client.TradingClient`` with a factory returning ``fake``."""
    import alpaca.trading.client as ac

    monkeypatch.setattr(ac, "TradingClient", lambda **kwargs: fake)


# ---------------------------------------------------------------------------
# Construction + paper-mode default — §6.5 #1
# ---------------------------------------------------------------------------


def test_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    assert adapter.mode == "paper"
    assert adapter.connected is False
    assert adapter.read_only is False


def test_capabilities_advertise_alpaca_surface(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    caps = adapter.CAPABILITIES
    assert caps.supports_equity is True
    assert caps.supports_options is True
    assert caps.supports_crypto is True
    assert caps.supports_forex is False
    assert caps.supports_futures is False
    assert caps.requires_static_ip is False


# ---------------------------------------------------------------------------
# Connection lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_uses_paper_endpoint_and_records_account(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def _factory(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        client = MagicMock()
        client.get_account.return_value = _fake_account()
        return client

    import alpaca.trading.client as ac

    monkeypatch.setattr(ac, "TradingClient", _factory)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})

    assert captured["paper"] is True  # paper-mode default — §6.5 #1
    assert captured["api_key"] == "ak"
    assert captured["secret_key"] == "sk"
    assert adapter.connected is True
    assert adapter._account_id == "PA1234567"


@pytest.mark.asyncio
async def test_connect_after_set_mode_live_uses_live_endpoint(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, Any] = {}

    def _factory(**kwargs: Any) -> SimpleNamespace:
        captured.update(kwargs)
        client = MagicMock()
        client.get_account.return_value = _fake_account()
        return client

    import alpaca.trading.client as ac

    monkeypatch.setattr(ac, "TradingClient", _factory)

    adapter = AlpacaAdapter()
    await adapter.set_mode("live")
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})

    assert captured["paper"] is False


@pytest.mark.asyncio
async def test_connect_missing_credentials_raises(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    with pytest.raises(BrokerError, match="api_key and api_secret are required"):
        await adapter.connect({"api_key": ""})


@pytest.mark.asyncio
async def test_connect_failure_audits_error(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _factory(**_kwargs: Any) -> MagicMock:
        client = MagicMock()
        client.get_account.side_effect = RuntimeError("invalid key")
        return client

    import alpaca.trading.client as ac

    monkeypatch.setattr(ac, "TradingClient", _factory)

    adapter = AlpacaAdapter()
    with pytest.raises(BrokerError, match="connect failed"):
        await adapter.connect({"api_key": "bad", "api_secret": "bad"})

    rows = audit_log.tail(limit=5)
    actions = [r.action for r in rows]
    outcomes = [r.outcome for r in rows]
    assert "connection" in actions
    assert "error" in outcomes


# ---------------------------------------------------------------------------
# Account info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_info_maps_positions(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = MagicMock()
    client.get_account.return_value = _fake_account()
    client.get_all_positions.return_value = [
        _fake_position("AAPL", 10, 190.5),
        _fake_position("MSFT", 5, 350.0),
    ]
    _patch_trading_client(monkeypatch, client)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})
    summary = await adapter.account_info()

    assert summary.broker == "alpaca"
    assert summary.account_id == "PA1234567"
    assert summary.equity == 100000.0
    assert len(summary.positions) == 2
    assert summary.positions[0].symbol == "AAPL"
    assert summary.positions[0].quantity == 10.0


@pytest.mark.asyncio
async def test_account_info_before_connect_raises(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    with pytest.raises(BrokerError, match="not connected"):
        await adapter.account_info()


# ---------------------------------------------------------------------------
# Order placement — §6.5 #2 (propose → confirm two-step)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_market_order_round_trip(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    submitted: list[Any] = []
    client = MagicMock()
    client.get_account.return_value = _fake_account()
    client.submit_order.side_effect = lambda req: (
        submitted.append(req) or _fake_order(status="filled")
    )
    _patch_trading_client(monkeypatch, client)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})
    proposal = adapter.propose_order(symbol="AAPL", side="buy", order_type="market", quantity=10)
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)

    assert len(submitted) == 1
    assert result.status == "filled"
    assert result.broker_order_id == "alpaca-order-1"
    assert result.broker == "alpaca"


@pytest.mark.asyncio
async def test_limit_order_passes_limit_price(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    submitted: list[Any] = []
    client = MagicMock()
    client.get_account.return_value = _fake_account()
    client.submit_order.side_effect = lambda req: (
        submitted.append(req) or _fake_order(status="accepted")
    )
    _patch_trading_client(monkeypatch, client)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})
    proposal = adapter.propose_order(
        symbol="AAPL",
        side="buy",
        order_type="limit",
        quantity=10,
        limit_price=190.0,
    )
    await adapter.confirm_and_place(proposal, human_confirmed=True)

    request = submitted[0]
    assert request.limit_price == 190.0
    assert request.symbol == "AAPL"


@pytest.mark.asyncio
async def test_limit_order_without_price_raises(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = MagicMock()
    client.get_account.return_value = _fake_account()
    _patch_trading_client(monkeypatch, client)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})
    proposal = BrokerOrderProposal(
        proposalId="p1",
        broker="alpaca",
        accountId="acct",
        symbol="AAPL",
        side="buy",
        type="limit",
        quantity=10,
        limitPrice=None,
        stopPrice=None,
        currency="USD",
        estimatedValue=0.0,
        source="manual",
        sourceDetails={},
        proposedAt=int(time.time() * 1000),
    )
    with pytest.raises(BrokerError, match="limit order requires limit_price"):
        await adapter.confirm_and_place(proposal, human_confirmed=True)


# ---------------------------------------------------------------------------
# Position limits — §6.5 #3
# ---------------------------------------------------------------------------


def test_propose_order_above_limit_raises(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    # 100 shares @ 200 = 20000 > default 10_000 cap
    with pytest.raises(BrokerError, match="exceeds limit"):
        adapter.propose_order(
            symbol="AAPL",
            side="buy",
            order_type="limit",
            quantity=100,
            limit_price=200.0,
        )


# ---------------------------------------------------------------------------
# Kill switch — §6.5 #5
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_sets_adapter_read_only(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    assert adapter.read_only is False
    await kill_switch.get_bus().fire(reason="test", fired_by="user-keyboard")
    assert adapter.read_only is True


@pytest.mark.asyncio
async def test_propose_after_kill_switch_raises(temp_data_dir: object) -> None:
    adapter = AlpacaAdapter()
    await kill_switch.get_bus().fire(reason="test", fired_by="user-toolbar")
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=1, limit_price=1.0
        )


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_order_calls_sdk(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = MagicMock()
    client.get_account.return_value = _fake_account()
    _patch_trading_client(monkeypatch, client)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})
    await adapter.cancel_order("alpaca-order-99")
    client.cancel_order_by_id.assert_called_once_with("alpaca-order-99")


@pytest.mark.asyncio
async def test_cancel_order_failure_audits(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = MagicMock()
    client.get_account.return_value = _fake_account()
    client.cancel_order_by_id.side_effect = RuntimeError("not found")
    _patch_trading_client(monkeypatch, client)

    adapter = AlpacaAdapter()
    await adapter.connect({"api_key": "ak", "api_secret": "sk"})
    with pytest.raises(BrokerError, match="cancel_order failed"):
        await adapter.cancel_order("missing")

    rows = audit_log.tail(limit=5)
    outcomes = [r.outcome for r in rows]
    assert any("cancel-rejected" in o for o in outcomes)


# ---------------------------------------------------------------------------
# Status mapping helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("filled", "filled"),
        ("OrderStatus.FILLED", "filled"),
        ("partially_filled", "partial"),
        ("canceled", "cancelled"),
        ("expired", "cancelled"),
        ("rejected", "rejected"),
        ("accepted", "open"),
        ("new", "open"),
        (None, "open"),
    ],
)
def test_map_alpaca_status(raw: Any, expected: str) -> None:
    assert _map_alpaca_status(raw) == expected
