"""Tests for the BrokerAdapter ABC.

BLUEPRINT §6.5 enforcement at the ABC level:

  - #1 Paper mode is the default — every adapter starts in paper mode
  - #2 Per-order confirm — propose_order writes audit + returns proposal;
    placement requires confirm_and_place(human_confirmed=True)
  - #3 Position-size limits enforced at propose_order
  - #4 Every order audit-logged on the propose / confirm / place / cancel path
  - #5 Adapters subscribe to the kill-switch bus on construction
  - #6 AI-order gate — proposals with source="ai-agent" follow the same
    propose → confirm path; nothing else exists
  - #7 Read-only mode raises in propose_order before any broker call
  - (#8 disclaimer flow tested in test_safety_router via the routes)
"""

from __future__ import annotations

import time

import pytest

from config import DATA_DIR_ENV
from models.broker import (
    AccountSummary,
    BrokerCapabilities,
    BrokerOrderProposal,
    BrokerOrderResult,
)
from services import audit_log, kill_switch
from services.broker_base import BrokerAdapter, BrokerError


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


# ---------------------------------------------------------------------------
# A minimal concrete adapter for testing the ABC
# ---------------------------------------------------------------------------


class _MockAdapter(BrokerAdapter):
    BROKER_ID = "alpaca"
    CAPABILITIES = BrokerCapabilities(
        supportsEquity=True,
        supportsOptions=False,
        supportsCrypto=False,
        supportsForex=False,
        supportsFutures=False,
        requiresStaticIp=False,
    )

    def __init__(self) -> None:
        super().__init__()
        self._account_id = "test-acct"
        self.connect_calls: list[dict[str, str]] = []
        self.place_calls: list[BrokerOrderProposal] = []
        self.cancel_calls: list[str] = []

    async def _connect(self, credentials: dict[str, str]) -> None:
        self.connect_calls.append(credentials)
        self._account_id = "test-acct"

    async def _account_info(self) -> AccountSummary:
        return AccountSummary(
            broker="alpaca",
            accountId="test-acct",
            currency="USD",
            equity=100_000.0,
            cash=50_000.0,
            buyingPower=100_000.0,
            positions=[],
            capturedAt=int(time.time() * 1000),
        )

    async def _place_confirmed(self, proposal: BrokerOrderProposal) -> BrokerOrderResult:
        self.place_calls.append(proposal)
        return BrokerOrderResult(
            proposalId=proposal.proposal_id,
            broker="alpaca",
            brokerOrderId=f"broker-{proposal.proposal_id[:8]}",
            status="filled",
            requestPayload={"symbol": proposal.symbol, "qty": proposal.quantity},
            responsePayload={"id": "broker-123", "status": "filled"},
            placedAt=int(time.time() * 1000),
        )

    async def _cancel_order(self, broker_order_id: str) -> None:
        self.cancel_calls.append(broker_order_id)


# ---------------------------------------------------------------------------
# §6.5 #1 — paper mode default
# ---------------------------------------------------------------------------


def test_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    assert adapter.mode == "paper"
    assert adapter.read_only is False
    assert adapter.connected is False


@pytest.mark.asyncio
async def test_set_mode_audit_logs(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    await adapter.set_mode("live")
    assert adapter.mode == "live"
    rows = audit_log.tail(limit=5)
    assert rows[0].action == "mode-changed"
    assert rows[0].payload["previous"] == "paper"
    assert rows[0].payload["current"] == "live"


# ---------------------------------------------------------------------------
# §6.5 #2 — propose → confirm two-step
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_propose_writes_audit_and_returns_proposal(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    proposal = adapter.propose_order(
        symbol="AAPL", side="buy", order_type="limit", quantity=10, limit_price=190.0
    )
    assert proposal.symbol == "AAPL"
    assert proposal.broker == "alpaca"
    assert adapter.place_calls == []  # propose did NOT place
    rows = audit_log.tail(limit=1)
    assert rows[0].action == "order-proposed"


@pytest.mark.asyncio
async def test_confirm_false_raises_and_writes_declined(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    proposal = adapter.propose_order(
        symbol="AAPL", side="buy", order_type="limit", quantity=10, limit_price=190.0
    )
    with pytest.raises(BrokerError, match="declined"):
        await adapter.confirm_and_place(proposal, human_confirmed=False)
    assert adapter.place_calls == []
    rows = audit_log.tail(limit=5)
    assert "order-declined" in [r.action for r in rows]


@pytest.mark.asyncio
async def test_confirm_true_places_and_writes_placed(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    proposal = adapter.propose_order(
        symbol="AAPL", side="buy", order_type="limit", quantity=10, limit_price=190.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "filled"
    assert len(adapter.place_calls) == 1
    actions = [r.action for r in audit_log.tail(limit=10)]
    assert "order-confirmed" in actions
    assert "order-placed" in actions


# ---------------------------------------------------------------------------
# §6.5 #3 — position-size limits
# ---------------------------------------------------------------------------


def test_order_value_exceeding_limit_raises(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    # default maxOrderValueAccountCurrency is 10_000. 100 shares @ 200 = 20_000.
    with pytest.raises(BrokerError, match="exceeds limit"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=100, limit_price=200.0
        )


def test_quantity_exceeding_per_symbol_cap_raises(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    # default maxPositionSizePerSymbol is 1000.
    with pytest.raises(BrokerError, match="per-symbol cap"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=1001, limit_price=1.0
        )


def test_invalid_side_raises(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    with pytest.raises(BrokerError, match="invalid side"):
        adapter.propose_order(symbol="AAPL", side="sideways", order_type="limit", quantity=10)


def test_zero_quantity_raises(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    with pytest.raises(BrokerError, match="quantity must be positive"):
        adapter.propose_order(symbol="AAPL", side="buy", order_type="limit", quantity=0)


# ---------------------------------------------------------------------------
# §6.5 #5 — kill switch subscription forced; propose raises after fire
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_adapter_subscribes_to_kill_switch_on_construction(
    temp_data_dir: object,
) -> None:
    initial = kill_switch.get_bus().subscriber_count()
    adapter = _MockAdapter()
    assert kill_switch.get_bus().subscriber_count() == initial + 1
    _ = adapter  # keep alive


@pytest.mark.asyncio
async def test_propose_after_kill_switch_raises(temp_data_dir: object) -> None:
    adapter = _MockAdapter()  # subscribes to the bus
    await kill_switch.get_bus().fire(reason="test", fired_by="user-toolbar")
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=1, limit_price=1.0
        )


@pytest.mark.asyncio
async def test_kill_switch_sets_adapter_to_read_only(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    await kill_switch.get_bus().fire(reason="emergency", fired_by="user-keyboard")
    # The kill-switch handler forces read-only mode + audit-logs the ack.
    assert adapter.read_only is True
    actions = [r.action for r in audit_log.tail(limit=10)]
    assert "kill-switch-fired" in actions


# ---------------------------------------------------------------------------
# §6.5 #6 — AI-order gate (source = "ai-agent" follows same flow)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_proposed_order_writes_source_ai_agent(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    proposal = adapter.propose_order(
        symbol="AAPL",
        side="buy",
        order_type="limit",
        quantity=10,
        limit_price=190.0,
        source="ai-agent",
        source_details={"originatorId": "buffett", "originatorName": "Warren Buffett"},
    )
    assert proposal.source == "ai-agent"
    rows = audit_log.tail(limit=1)
    assert rows[0].source == "ai-agent"
    # AI proposal did NOT auto-place — it landed in audit log only.
    assert adapter.place_calls == []


@pytest.mark.asyncio
async def test_ai_proposed_order_still_requires_human_confirm(
    temp_data_dir: object,
) -> None:
    adapter = _MockAdapter()
    proposal = adapter.propose_order(
        symbol="AAPL",
        side="buy",
        order_type="limit",
        quantity=10,
        limit_price=190.0,
        source="ai-agent",
        source_details={"originatorId": "buffett", "originatorName": "Warren Buffett"},
    )
    # No auto-approve path — declining still raises.
    with pytest.raises(BrokerError, match="declined"):
        await adapter.confirm_and_place(proposal, human_confirmed=False)
    assert adapter.place_calls == []


# ---------------------------------------------------------------------------
# §6.5 #7 — read-only mode raises before any broker call
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_only_mode_blocks_propose(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    await adapter.set_read_only(True)
    with pytest.raises(BrokerError, match="read-only mode"):
        adapter.propose_order(
            symbol="AAPL", side="buy", order_type="limit", quantity=1, limit_price=1.0
        )
    assert adapter.place_calls == []


# ---------------------------------------------------------------------------
# Connection lifecycle audit logging
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connect_audit_logs_on_success(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    await adapter.connect({"api_key": "test"})
    assert adapter.connected is True
    rows = audit_log.tail(limit=5)
    actions = [r.action for r in rows]
    assert "connection" in actions


@pytest.mark.asyncio
async def test_cancel_order_audit_logs(temp_data_dir: object) -> None:
    adapter = _MockAdapter()
    await adapter.cancel_order("broker-xyz")
    assert adapter.cancel_calls == ["broker-xyz"]
    rows = audit_log.tail(limit=2)
    assert rows[0].action == "order-cancelled"
