"""Tests for the Interactive Brokers adapter.

The ``ib_async`` library talks to a locally-running TWS / IB Gateway
over TCP; we mock the ``IB`` class entirely so the test suite can run
in any environment, with or without TWS installed. The integration
shape (port selection, error handling on connection refusal, request
shaping for placeOrder) is the contract we verify here.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from config import DATA_DIR_ENV
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers.ib import (
    DEFAULT_GATEWAY_PAPER_PORT,
    DEFAULT_TWS_LIVE_PORT,
    DEFAULT_TWS_PAPER_PORT,
    IBAdapter,
    _map_ib_status,
)


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
# Mock IB scaffolding
# ---------------------------------------------------------------------------


def _account_value(tag: str, value: str, currency: str = "USD") -> SimpleNamespace:
    return SimpleNamespace(tag=tag, value=value, currency=currency, account="DU1234567")


def _fake_ib(
    *,
    summary_rows: list[Any] | None = None,
    positions: list[Any] | None = None,
    managed_accounts: list[str] | None = None,
    connect_error: BaseException | None = None,
    place_result: Any | None = None,
    open_trades: list[Any] | None = None,
) -> Any:
    ib = MagicMock()
    if connect_error is not None:
        ib.connectAsync = AsyncMock(side_effect=connect_error)
    else:
        ib.connectAsync = AsyncMock(return_value=None)
    ib.managedAccounts.return_value = managed_accounts or ["DU1234567"]
    ib.accountSummaryAsync = AsyncMock(return_value=summary_rows or [])
    ib.positions.return_value = positions or []
    ib.placeOrder = MagicMock(return_value=place_result)
    ib.openTrades.return_value = open_trades or []
    ib.cancelOrder = MagicMock(return_value=None)
    return ib


def _patch_ib(monkeypatch: pytest.MonkeyPatch, fake_ib: Any) -> None:
    import ib_async

    monkeypatch.setattr(ib_async, "IB", lambda: fake_ib)


# ---------------------------------------------------------------------------
# §6.5 #1 — paper-mode default + port selection
# ---------------------------------------------------------------------------


def test_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = IBAdapter()
    assert adapter.mode == "paper"


def test_capabilities_advertise_ib_surface(temp_data_dir: object) -> None:
    caps = IBAdapter.CAPABILITIES
    assert caps.supports_equity is True
    assert caps.supports_options is True
    assert caps.supports_forex is True
    assert caps.supports_futures is True
    assert caps.supports_crypto is False  # IB crypto is live-only; route via ccxt
    assert caps.requires_static_ip is False


@pytest.mark.asyncio
async def test_connect_defaults_to_paper_port(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_ib()
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    fake.connectAsync.assert_awaited_once()
    kwargs = fake.connectAsync.call_args.kwargs
    assert kwargs["port"] == DEFAULT_TWS_PAPER_PORT
    assert kwargs["host"] == "127.0.0.1"


@pytest.mark.asyncio
async def test_connect_after_live_mode_uses_live_port(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_ib()
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.set_mode("live")
    await adapter.connect({})
    kwargs = fake.connectAsync.call_args.kwargs
    assert kwargs["port"] == DEFAULT_TWS_LIVE_PORT


@pytest.mark.asyncio
async def test_connect_credential_port_override(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_ib()
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({"port": str(DEFAULT_GATEWAY_PAPER_PORT)})
    kwargs = fake.connectAsync.call_args.kwargs
    assert kwargs["port"] == DEFAULT_GATEWAY_PAPER_PORT


# ---------------------------------------------------------------------------
# Connection-refused UX
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_refused_surfaces_tws_hint(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_ib(connect_error=ConnectionRefusedError())
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    with pytest.raises(BrokerError, match="TWS or IB Gateway not detected"):
        await adapter.connect({})


@pytest.mark.asyncio
async def test_connect_timeout_surfaces_message(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_ib(connect_error=TimeoutError())
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    with pytest.raises(BrokerError, match="timed out"):
        await adapter.connect({})


@pytest.mark.asyncio
async def test_connect_invalid_port_raises(temp_data_dir: object) -> None:
    adapter = IBAdapter()
    with pytest.raises(BrokerError, match="invalid port"):
        await adapter.connect({"port": "not-a-port"})


# ---------------------------------------------------------------------------
# Account info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_info_aggregates_summary(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary_rows = [
        _account_value("NetLiquidation", "100000.00", "USD"),
        _account_value("NetLiquidation", "100000.00", "BASE"),
        _account_value("TotalCashValue", "50000.00", "BASE"),
        _account_value("BuyingPower", "200000.00", "BASE"),
    ]
    pos = SimpleNamespace(
        contract=SimpleNamespace(symbol="AAPL"),
        position=10,
        avgCost=190.5,
    )
    fake = _fake_ib(summary_rows=summary_rows, positions=[pos])
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    summary = await adapter.account_info()

    assert summary.broker == "ib"
    assert summary.equity == 100000.0
    assert summary.cash == 50000.0
    assert summary.buying_power == 200000.0
    assert len(summary.positions) == 1
    assert summary.positions[0].symbol == "AAPL"


@pytest.mark.asyncio
async def test_account_info_before_connect_raises(temp_data_dir: object) -> None:
    adapter = IBAdapter()
    with pytest.raises(BrokerError, match="not connected"):
        await adapter.account_info()


# ---------------------------------------------------------------------------
# Order placement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_market_order_constructs_market_order(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    trade = SimpleNamespace(
        order=SimpleNamespace(orderId=42),
        orderStatus=SimpleNamespace(status="Submitted"),
    )
    fake = _fake_ib(place_result=trade)
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    proposal = adapter.propose_order(symbol="AAPL", side="buy", order_type="market", quantity=10)
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)

    fake.placeOrder.assert_called_once()
    args = fake.placeOrder.call_args.args
    contract, order = args
    assert contract.symbol == "AAPL"
    assert order.action == "BUY"
    assert order.totalQuantity == 10
    assert result.broker_order_id == "42"
    assert result.status == "open"  # Submitted → open


@pytest.mark.asyncio
async def test_limit_order_sets_limit_price(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    trade = SimpleNamespace(
        order=SimpleNamespace(orderId=43),
        orderStatus=SimpleNamespace(status="Submitted"),
    )
    fake = _fake_ib(place_result=trade)
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    proposal = adapter.propose_order(
        symbol="AAPL", side="buy", order_type="limit", quantity=10, limit_price=190.0
    )
    await adapter.confirm_and_place(proposal, human_confirmed=True)

    args = fake.placeOrder.call_args.args
    _, order = args
    assert order.lmtPrice == 190.0


@pytest.mark.asyncio
async def test_sell_translates_to_action_sell(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    trade = SimpleNamespace(
        order=SimpleNamespace(orderId=44),
        orderStatus=SimpleNamespace(status="Filled"),
    )
    fake = _fake_ib(place_result=trade)
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    proposal = adapter.propose_order(symbol="AAPL", side="sell", order_type="market", quantity=5)
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    _, order = fake.placeOrder.call_args.args
    assert order.action == "SELL"
    assert result.status == "filled"


# ---------------------------------------------------------------------------
# Position limits — §6.5 #3
# ---------------------------------------------------------------------------


def test_propose_order_above_limit_raises(temp_data_dir: object) -> None:
    adapter = IBAdapter()
    with pytest.raises(BrokerError, match="exceeds limit"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=100, limit_price=200.0
        )


# ---------------------------------------------------------------------------
# Kill switch — §6.5 #5
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_sets_adapter_read_only(temp_data_dir: object) -> None:
    adapter = IBAdapter()
    await kill_switch.get_bus().fire(reason="emergency", fired_by="user-keyboard")
    assert adapter.read_only is True


@pytest.mark.asyncio
async def test_propose_after_kill_switch_raises(temp_data_dir: object) -> None:
    adapter = IBAdapter()
    await kill_switch.get_bus().fire(reason="test", fired_by="user-toolbar")
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=1, limit_price=1.0
        )


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_resolves_open_order_by_id(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_order = SimpleNamespace(orderId=99)
    open_trade = SimpleNamespace(order=target_order)
    fake = _fake_ib(open_trades=[open_trade])
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    await adapter.cancel_order("99")
    fake.cancelOrder.assert_called_once_with(target_order)


@pytest.mark.asyncio
async def test_cancel_missing_order_raises(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake = _fake_ib(open_trades=[])
    _patch_ib(monkeypatch, fake)

    adapter = IBAdapter()
    await adapter.connect({})
    with pytest.raises(BrokerError, match="not found"):
        await adapter.cancel_order("123")
    # Failure path audits
    rows = audit_log.tail(limit=5)
    outcomes = [r.outcome for r in rows]
    assert any("cancel-rejected" in o for o in outcomes)


# ---------------------------------------------------------------------------
# Status mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Filled", "filled"),
        ("PartiallyFilled", "partial"),
        ("Cancelled", "cancelled"),
        ("PendingCancel", "cancelled"),
        ("ApiCancelled", "cancelled"),
        ("Inactive", "rejected"),
        ("Submitted", "open"),
        ("PreSubmitted", "open"),
        (None, "open"),
    ],
)
def test_map_ib_status(raw: Any, expected: str) -> None:
    assert _map_ib_status(raw) == expected
