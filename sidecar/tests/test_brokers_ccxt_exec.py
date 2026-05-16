"""Tests for ``services.brokers.ccxt_exec.CcxtExecutionAdapter``.

The adapter inherits :class:`BrokerAdapter` so the ABC-level guarantees
(paper default, kill-switch subscription, propose → confirm → place audit
trail, position limits, read-only mode) are already covered by
``test_broker_base.py``. This file pins the ccxt-specific surface:

  - Each supported ccxt exchange maps to a distinct ``BrokerId``.
  - Per-exchange capability matrix is correct (futures support varies).
  - Constructor validates exchange whitelist.
  - ``_connect`` requires ``api_key`` + ``secret``; testnet flag honoured.
  - Paper-mode ``_place_confirmed`` synthesises a filled result WITHOUT
    calling ccxt.
  - Bybit testnet end-to-end paper trade produces the expected audit-log
    trail (propose → confirm → place → cancel).

ccxt is mocked via the existing ``mock_ccxt`` fixture; no live exchange
call ever runs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from config import DATA_DIR_ENV
from models.broker import BrokerOrderProposal
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers.ccxt_exec import (
    BROKER_ID_TO_EXCHANGE,
    EXCHANGE_TO_BROKER_ID,
    CcxtExecutionAdapter,
    _ccxt_status_to_result_status,
    build_all_adapters,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def fresh_bus() -> None:
    """Reset the kill-switch module singleton between tests."""
    kill_switch.reset_bus_for_tests()
    yield
    kill_switch.reset_bus_for_tests()


class _FakeCcxtExchange:
    """Stand-in for a synchronous ccxt exchange used for execution tests.

    Captures ``create_order`` / ``cancel_order`` calls so the test can
    assert the adapter forwards correctly in live mode. ``fetch_balance``
    returns a balance shaped like a real ccxt unified response.
    """

    sandbox_calls: list[bool]
    create_order_calls: list[dict[str, Any]]
    cancel_order_calls: list[str]

    def __init__(self, options: dict[str, Any] | None = None) -> None:
        self.options = options or {}
        self.sandbox_calls = []
        self.create_order_calls = []
        self.cancel_order_calls = []

    def set_sandbox_mode(self, enabled: bool) -> None:
        self.sandbox_calls.append(enabled)

    def fetch_balance(self) -> dict[str, Any]:
        return {
            "USDT": {"free": 1_000.0, "used": 200.0, "total": 1_200.0},
            "BTC": {"free": 0.5, "used": 0.0, "total": 0.5},
            "ETH": {"free": 0.0, "used": 0.0, "total": 0.0},
            "info": {"raw": "exchange-payload"},
        }

    def create_order(
        self,
        symbol: str,
        order_type: str,
        side: str,
        amount: float,
        price: float | None,
    ) -> dict[str, Any]:
        record = {
            "symbol": symbol,
            "type": order_type,
            "side": side,
            "amount": amount,
            "price": price,
        }
        self.create_order_calls.append(record)
        return {
            "id": "live-order-abc",
            "status": "open",
            "symbol": symbol,
            "amount": amount,
            "filled": 0.0,
        }

    def cancel_order(self, broker_order_id: str) -> None:
        self.cancel_order_calls.append(broker_order_id)


@pytest.fixture
def fake_ccxt(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Patch ``services.brokers.ccxt_exec.ccxt`` with fake exchanges.

    Returns the SimpleNamespace so a test can introspect the class
    factory (e.g. assert it was called with the right options).
    """
    from services.brokers import ccxt_exec

    fake = SimpleNamespace(
        bybit=_FakeCcxtExchange,
        binance=_FakeCcxtExchange,
        kraken=_FakeCcxtExchange,
        coinbase=_FakeCcxtExchange,
    )
    monkeypatch.setattr(ccxt_exec, "ccxt", fake)
    return fake


# ---------------------------------------------------------------------------
# Identity / capability matrix
# ---------------------------------------------------------------------------


def test_each_supported_exchange_maps_to_distinct_broker_id() -> None:
    assert EXCHANGE_TO_BROKER_ID == {
        "bybit": "ccxt-bybit",
        "binance": "ccxt-binance",
        "kraken": "ccxt-kraken",
        "coinbase": "ccxt-coinbase",
    }
    # Round-trip
    for exchange, broker_id in EXCHANGE_TO_BROKER_ID.items():
        assert BROKER_ID_TO_EXCHANGE[broker_id] == exchange


def test_unsupported_exchange_raises(temp_data_dir: object) -> None:
    with pytest.raises(BrokerError, match="unsupported ccxt exchange"):
        CcxtExecutionAdapter("ftx")


@pytest.mark.parametrize(
    "exchange,expected_futures",
    [
        ("bybit", True),
        ("binance", True),
        ("kraken", False),
        ("coinbase", False),
    ],
)
def test_capabilities_per_exchange(
    temp_data_dir: object,
    exchange: str,
    expected_futures: bool,
) -> None:
    adapter = CcxtExecutionAdapter(exchange)
    caps = adapter.CAPABILITIES
    assert caps.supports_crypto is True
    assert caps.supports_equity is False
    assert caps.supports_options is False
    assert caps.supports_forex is False
    assert caps.supports_futures is expected_futures
    assert caps.requires_static_ip is False


def test_broker_id_set_at_construction(temp_data_dir: object) -> None:
    adapter = CcxtExecutionAdapter("bybit")
    assert adapter.BROKER_ID == "ccxt-bybit"
    assert adapter.exchange_id == "bybit"


def test_kill_switch_subscriber_uses_per_exchange_id(temp_data_dir: object) -> None:
    """Each ccxt adapter subscribes under its own broker id — so firing
    the kill switch reaches all four independently."""
    bus = kill_switch.get_bus()
    before = bus.subscriber_count()
    bybit = CcxtExecutionAdapter("bybit")
    binance = CcxtExecutionAdapter("binance")
    after = bus.subscriber_count()
    assert after - before == 2
    # Keep references alive so the unsubscribe closure does not run early.
    _ = (bybit, binance)


def test_build_all_adapters_returns_one_per_supported_exchange(temp_data_dir: object) -> None:
    adapters = build_all_adapters()
    assert set(adapters.keys()) == {
        "ccxt-bybit",
        "ccxt-binance",
        "ccxt-kraken",
        "ccxt-coinbase",
    }
    for broker_id, adapter in adapters.items():
        assert adapter.BROKER_ID == broker_id
        assert adapter.mode == "paper"  # §6.5 #1


# ---------------------------------------------------------------------------
# _connect
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_requires_api_key_and_secret(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    adapter = CcxtExecutionAdapter("bybit")
    with pytest.raises(BrokerError, match="api_key.*secret"):
        await adapter.connect({})
    # The base class wraps the failure in an audit row with outcome="error".
    rows = audit_log.tail(limit=5)
    assert any(r.action == "connection" and r.outcome == "error" for r in rows)


@pytest.mark.asyncio
async def test_connect_initialises_ccxt_with_testnet_options(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    adapter = CcxtExecutionAdapter("bybit", testnet=True)
    await adapter.connect({"api_key": "testkey", "secret": "testsecret"})
    assert adapter.connected is True
    assert isinstance(adapter.client, _FakeCcxtExchange)
    # Bybit testnet -> options.testnet=True is set on the ccxt class options dict.
    assert adapter.client.options["apiKey"] == "testkey"
    assert adapter.client.options["secret"] == "testsecret"
    assert adapter.client.options["options"] == {"testnet": True}
    # The shared sandbox toggle is also exercised when available.
    assert adapter.client.sandbox_calls == [True]


@pytest.mark.asyncio
async def test_connect_passes_passphrase_when_supplied(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    """Coinbase auth requires a passphrase — credential plumbing must pass it through."""
    adapter = CcxtExecutionAdapter("coinbase", testnet=False)
    await adapter.connect(
        {"api_key": "k", "secret": "s", "passphrase": "p"},
    )
    assert adapter.client is not None
    assert adapter.client.options["password"] == "p"


# ---------------------------------------------------------------------------
# _account_info
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_account_info_summary_uses_quote_currency(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    adapter = CcxtExecutionAdapter("bybit")
    await adapter.connect({"api_key": "k", "secret": "s"})
    summary = await adapter.account_info()
    assert summary.broker == "ccxt-bybit"
    assert summary.currency == "USDT"
    assert summary.equity == 1_200.0  # USDT total
    assert summary.cash == 1_000.0  # USDT free
    assert summary.buying_power == 1_000.0
    symbols = {p.symbol for p in summary.positions}
    assert "BTC" in symbols
    assert "ETH" not in symbols  # zero-balance assets filtered
    assert "USDT" not in symbols  # quote currency filtered


@pytest.mark.asyncio
async def test_account_info_kraken_uses_usd_quote(
    temp_data_dir: object, fake_ccxt: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kraken/Coinbase summary should default to USD as the quote currency."""

    class _UsdBalance(_FakeCcxtExchange):
        def fetch_balance(self) -> dict[str, Any]:
            return {
                "USD": {"free": 500.0, "used": 0.0, "total": 500.0},
                "BTC": {"free": 0.1, "used": 0.0, "total": 0.1},
                "info": {},
            }

    from services.brokers import ccxt_exec

    monkeypatch.setattr(ccxt_exec, "ccxt", SimpleNamespace(kraken=_UsdBalance))
    adapter = CcxtExecutionAdapter("kraken", testnet=False)
    await adapter.connect({"api_key": "k", "secret": "s"})
    summary = await adapter.account_info()
    assert summary.currency == "USD"
    assert summary.equity == 500.0


# ---------------------------------------------------------------------------
# _place_confirmed — paper mode synthesises, does NOT call ccxt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_paper_place_does_not_call_ccxt(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    adapter = CcxtExecutionAdapter("bybit")
    await adapter.connect({"api_key": "k", "secret": "s"})
    proposal = adapter.propose_order(
        symbol="BTC/USDT",
        side="buy",
        order_type="limit",
        quantity=0.01,
        limit_price=50_000.0,
        currency="USDT",
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "filled"
    assert result.broker_order_id is not None
    assert result.broker_order_id.startswith("paper-bybit-")  # noqa: PT017
    assert result.response_payload["synthetic"] is True
    assert result.response_payload["mode"] == "paper"
    # The synthetic fill MUST NOT have touched ccxt.
    assert adapter.client is not None
    assert adapter.client.create_order_calls == []


@pytest.mark.asyncio
async def test_live_mode_calls_ccxt_create_order(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    adapter = CcxtExecutionAdapter("bybit")
    await adapter.connect({"api_key": "k", "secret": "s"})
    await adapter.set_mode("live")
    proposal = adapter.propose_order(
        symbol="BTC/USDT",
        side="buy",
        order_type="limit",
        quantity=0.01,
        limit_price=50_000.0,
        currency="USDT",
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert adapter.client is not None
    assert len(adapter.client.create_order_calls) == 1
    call = adapter.client.create_order_calls[0]
    assert call == {
        "symbol": "BTC/USDT",
        "type": "limit",
        "side": "buy",
        "amount": 0.01,
        "price": 50_000.0,
    }
    assert result.broker_order_id == "live-order-abc"
    assert result.status == "open"


# ---------------------------------------------------------------------------
# Bybit testnet end-to-end paper trade — the v0.5.0 plan deliverable
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bybit_testnet_paper_trade_end_to_end(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    """The plan's marquee Teammate-X test: paper trade end-to-end on
    Bybit testnet, asserting the propose → confirm → place → cancel
    audit-log trail with broker='ccxt-bybit'."""
    adapter = CcxtExecutionAdapter("bybit", testnet=True)
    await adapter.connect({"api_key": "test", "secret": "test"})

    proposal: BrokerOrderProposal = adapter.propose_order(
        symbol="BTC/USDT",
        side="buy",
        order_type="limit",
        quantity=0.01,
        limit_price=50_000.0,
        currency="USDT",
    )
    assert proposal.broker == "ccxt-bybit"

    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "filled"
    assert result.broker == "ccxt-bybit"
    assert result.broker_order_id is not None

    await adapter.cancel_order(result.broker_order_id)

    # Verify the audit-log trail in chronological order.
    rows = audit_log.tail(limit=20)
    # tail() is newest-first; reverse to read order of events.
    actions_chrono = [r.action for r in reversed(rows)]
    # Connection row sits at the head; the order trail follows.
    assert "connection" in actions_chrono
    order_actions = [
        a
        for a in actions_chrono
        if a in ("order-proposed", "order-confirmed", "order-placed", "order-cancelled")
    ]
    assert order_actions == [
        "order-proposed",
        "order-confirmed",
        "order-placed",
        "order-cancelled",
    ]
    # Every row in the order trail carries broker='ccxt-bybit'.
    order_rows = [
        r
        for r in rows
        if r.action in ("order-proposed", "order-confirmed", "order-placed", "order-cancelled")
    ]
    assert {r.broker for r in order_rows} == {"ccxt-bybit"}


@pytest.mark.asyncio
async def test_paper_cancel_does_not_call_ccxt(
    temp_data_dir: object, fake_ccxt: SimpleNamespace
) -> None:
    """Paper-synthetic order ids are no-ops at the cancel boundary —
    they only exist in the audit log, so we MUST NOT hit ccxt."""
    adapter = CcxtExecutionAdapter("binance")
    await adapter.connect({"api_key": "k", "secret": "s"})
    proposal = adapter.propose_order(
        symbol="ETH/USDT",
        side="sell",
        order_type="market",
        quantity=0.5,
        currency="USDT",
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.broker_order_id is not None and result.broker_order_id.startswith("paper-")
    await adapter.cancel_order(result.broker_order_id)
    assert adapter.client is not None
    assert adapter.client.cancel_order_calls == []
    # The audit-log row is still written by the base class.
    rows = audit_log.tail(limit=5)
    assert rows[0].action == "order-cancelled"


# ---------------------------------------------------------------------------
# ccxt status mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("open", "open"),
        ("closed", "filled"),
        ("canceled", "cancelled"),
        ("cancelled", "cancelled"),
        ("expired", "cancelled"),
        ("rejected", "rejected"),
        ("partial", "partial"),
        ("partially_filled", "partial"),
        ("CLOSED", "filled"),  # case-insensitive
        ("weird-unknown-thing", "open"),  # fallback
        (None, "open"),  # non-string fallback
    ],
)
def test_ccxt_status_mapping(raw: Any, expected: str) -> None:
    assert _ccxt_status_to_result_status(raw) == expected
