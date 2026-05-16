"""Tests for the Dhan broker adapter.

The adapter inherits :class:`services.broker_base.BrokerAdapter`; the safety
gates (paper-default, kill switch, position limits, audit log, AI-order
gate, read-only mode) are exercised against the ABC in
``test_broker_base.py``. This file focuses on Dhan-specific surface:

  - paper-mode synthetic fill (no SDK call)
  - live-mode dispatches the SDK call onto a thread
  - live-mode SDK errors propagate as ``BrokerError`` and the ABC
    audit-logs them as ``order-rejected``
  - account_info has a paper-mode short-circuit
"""

from __future__ import annotations

import pytest

from config import DATA_DIR_ENV
from models.broker import AccountSummary, BrokerOrderResult
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers.dhan import DhanAdapter


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
# Paper-mode behaviour
# ---------------------------------------------------------------------------


def test_dhan_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    assert adapter.mode == "paper"
    assert adapter.read_only is False
    assert adapter.BROKER_ID == "dhan"
    assert adapter.CAPABILITIES.supports_equity is True
    assert adapter.CAPABILITIES.requires_static_ip is False


@pytest.mark.asyncio
async def test_dhan_paper_place_returns_synthetic_fill_without_sdk(
    temp_data_dir: object,
) -> None:
    adapter = DhanAdapter()
    proposal = adapter.propose_order(
        symbol="RELIANCE", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert isinstance(result, BrokerOrderResult)
    assert result.status == "filled"
    assert result.broker_order_id is not None
    assert result.broker_order_id.startswith("paper-dhan-")
    # Adapter never instantiated the SDK in paper mode.
    assert adapter._client is None


@pytest.mark.asyncio
async def test_dhan_paper_account_info_returns_paper_summary(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    summary = await adapter.account_info()
    assert isinstance(summary, AccountSummary)
    assert summary.broker == "dhan"
    assert summary.currency == "INR"
    assert summary.account_id.startswith("paper-")
    assert summary.positions == []


@pytest.mark.asyncio
async def test_dhan_paper_cancel_is_noop(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    # Paper cancel must not require a client and must audit-log via the ABC.
    await adapter.cancel_order("paper-dhan-xyz")
    actions = [r.action for r in audit_log.tail(limit=2)]
    assert "order-cancelled" in actions


# ---------------------------------------------------------------------------
# Live-mode SDK dispatch
# ---------------------------------------------------------------------------


class _FakeDhanClient:
    """Fake SDK client — captures calls + returns canned envelopes."""

    def __init__(self) -> None:
        self.place_calls: list[dict] = []
        self.cancel_calls: list[str] = []
        self.place_response: dict = {
            "status": "success",
            "data": {"orderId": "DHAN-123", "orderStatus": "TRADED"},
        }
        self.holdings_response: dict = {"data": []}
        self.funds_response: dict = {"data": {"availabelBalance": 250_000.0}}

    def place_order(self, **kwargs) -> dict:
        self.place_calls.append(kwargs)
        return self.place_response

    def cancel_order(self, order_id: str) -> dict:
        self.cancel_calls.append(order_id)
        return {"status": "success"}

    def get_holdings(self) -> dict:
        return self.holdings_response

    def get_fund_limits(self) -> dict:
        return self.funds_response


@pytest.mark.asyncio
async def test_dhan_live_mode_dispatches_sdk_call(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    fake = _FakeDhanClient()
    adapter._client = fake
    adapter._account_id = "DHAN-LIVE-001"
    await adapter.set_mode("live")

    proposal = adapter.propose_order(
        symbol="RELIANCE", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "filled"
    assert result.broker_order_id == "DHAN-123"
    # SDK was actually invoked once with the propose'd symbol.
    assert len(fake.place_calls) == 1
    assert fake.place_calls[0]["security_id"] == "RELIANCE"


@pytest.mark.asyncio
async def test_dhan_live_account_info_reads_funds_and_holdings(
    temp_data_dir: object,
) -> None:
    adapter = DhanAdapter()
    fake = _FakeDhanClient()
    fake.holdings_response = {
        "data": [
            {
                "tradingSymbol": "RELIANCE",
                "totalQty": 10,
                "avgCostPrice": 90.0,
                "lastTradedPrice": 100.0,
            }
        ]
    }
    adapter._client = fake
    adapter._account_id = "DHAN-LIVE-001"
    await adapter.set_mode("live")

    summary = await adapter.account_info()
    assert summary.equity == 250_000.0
    assert len(summary.positions) == 1
    assert summary.positions[0].symbol == "RELIANCE"


@pytest.mark.asyncio
async def test_dhan_live_sdk_error_propagates_and_audit_logs_rejection(
    temp_data_dir: object,
) -> None:
    class _Boom(_FakeDhanClient):
        def place_order(self, **kwargs) -> dict:
            raise RuntimeError("dhan boom")

    adapter = DhanAdapter()
    adapter._client = _Boom()
    adapter._account_id = "DHAN-LIVE-001"
    await adapter.set_mode("live")

    proposal = adapter.propose_order(
        symbol="RELIANCE", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    with pytest.raises(BrokerError, match="place_order failed"):
        await adapter.confirm_and_place(proposal, human_confirmed=True)

    actions = [r.action for r in audit_log.tail(limit=10)]
    assert "order-rejected" in actions


# ---------------------------------------------------------------------------
# Foundation safety gates exercised through Dhan
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dhan_position_limits_raise_at_propose(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    with pytest.raises(BrokerError, match="exceeds limit"):
        adapter.propose_order(
            symbol="RELIANCE", side="buy", order_type="limit", quantity=200, limit_price=100.0
        )


@pytest.mark.asyncio
async def test_dhan_kill_switch_blocks_propose(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    await kill_switch.get_bus().fire(reason="test", fired_by="user-toolbar")
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="RELIANCE", side="buy", order_type="limit", quantity=1, limit_price=10.0
        )
    # The kill-switch handler forces read-only on subscribers.
    assert adapter.read_only is True


@pytest.mark.asyncio
async def test_dhan_ai_proposed_order_routes_through_propose_confirm(
    temp_data_dir: object,
) -> None:
    adapter = DhanAdapter()
    proposal = adapter.propose_order(
        symbol="RELIANCE",
        side="buy",
        order_type="limit",
        quantity=5,
        limit_price=100.0,
        source="ai-agent",
        source_details={"originatorId": "buffett", "originatorName": "Warren Buffett"},
    )
    assert proposal.source == "ai-agent"
    # Decline still requires the ABC to write the declined audit row.
    with pytest.raises(BrokerError, match="declined"):
        await adapter.confirm_and_place(proposal, human_confirmed=False)
    actions = [r.action for r in audit_log.tail(limit=5)]
    assert "order-declined" in actions


@pytest.mark.asyncio
async def test_dhan_connect_rejects_missing_credentials(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    with pytest.raises(BrokerError, match="credentials"):
        await adapter.connect({})
    # The ABC's connect() writes the failure audit row.
    actions = [r.action for r in audit_log.tail(limit=2)]
    assert "connection" in actions


@pytest.mark.asyncio
async def test_dhan_connection_marks_connected_at_safety_boundary(
    temp_data_dir: object,
) -> None:
    """The adapter's ABC connect() sets the connected flag on success.

    We bypass the dhanhq SDK by patching ``_connect`` to skip the SDK call,
    which proves the ABC wiring (connected flag, audit row) works on the
    Dhan subclass.
    """

    class _NoSdkDhan(DhanAdapter):
        async def _connect(self, credentials: dict[str, str]) -> None:
            self._account_id = "DHAN-LIVE-001"

    adapter = _NoSdkDhan()
    await adapter.connect({"client_id": "x", "access_token": "y"})
    assert adapter.connected is True
    assert adapter.state().status == "connected"


def test_dhan_state_reflects_paper_default(temp_data_dir: object) -> None:
    adapter = DhanAdapter()
    state = adapter.state()
    assert state.broker == "dhan"
    assert state.mode == "paper"
    assert state.read_only is False
    assert state.status == "disconnected"
    assert state.capabilities.requires_static_ip is False
