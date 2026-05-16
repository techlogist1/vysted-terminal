"""Tests for the Angel One broker adapter."""

from __future__ import annotations

import pytest

from config import DATA_DIR_ENV
from models.broker import AccountSummary
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers.angelone import AngelOneAdapter


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def fresh_bus() -> None:
    kill_switch.reset_bus_for_tests()
    yield
    kill_switch.reset_bus_for_tests()


class _FakeAngelClient:
    def __init__(self) -> None:
        self.place_calls: list[dict] = []
        self.cancel_calls: list[tuple[str, str]] = []
        self.place_response: dict = {
            "status": True,
            "data": {"orderid": "ANGEL-001"},
        }
        self.rms_response: dict = {"data": {"net": 250_000.0}}
        self.holding_response: dict = {"data": []}

    def placeOrderFullResponse(self, params: dict) -> dict:  # noqa: N802 - SDK name
        self.place_calls.append(params)
        return self.place_response

    def cancelOrder(self, order_id: str, variety: str) -> dict:  # noqa: N802
        self.cancel_calls.append((order_id, variety))
        return {"status": True}

    def rmsLimit(self) -> dict:  # noqa: N802
        return self.rms_response

    def holding(self) -> dict:
        return self.holding_response


# ---------------------------------------------------------------------------
# Paper-mode behaviour
# ---------------------------------------------------------------------------


def test_angelone_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    assert adapter.mode == "paper"
    assert adapter.BROKER_ID == "angelone"
    assert adapter.CAPABILITIES.requires_static_ip is False


@pytest.mark.asyncio
async def test_angelone_paper_place_returns_synthetic_fill(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    proposal = adapter.propose_order(
        symbol="HDFCBANK", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "filled"
    assert result.broker == "angelone"
    assert result.broker_order_id.startswith("paper-angelone-")
    assert adapter._client is None


@pytest.mark.asyncio
async def test_angelone_paper_account_info(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    summary = await adapter.account_info()
    assert isinstance(summary, AccountSummary)
    assert summary.broker == "angelone"
    assert summary.currency == "INR"


# ---------------------------------------------------------------------------
# Live-mode SDK dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_angelone_live_place_calls_sdk(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    fake = _FakeAngelClient()
    adapter._client = fake
    adapter._account_id = "ANGEL-001"
    await adapter.set_mode("live")

    proposal = adapter.propose_order(
        symbol="HDFCBANK", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "open"
    assert result.broker_order_id == "ANGEL-001"
    assert len(fake.place_calls) == 1
    assert fake.place_calls[0]["tradingsymbol"] == "HDFCBANK"
    assert fake.place_calls[0]["transactiontype"] == "BUY"


@pytest.mark.asyncio
async def test_angelone_live_account_info_calls_rms_and_holding(
    temp_data_dir: object,
) -> None:
    adapter = AngelOneAdapter()
    fake = _FakeAngelClient()
    fake.holding_response = {
        "data": [
            {
                "tradingsymbol": "HDFCBANK",
                "quantity": 10,
                "averageprice": 90.0,
                "ltp": 105.0,
            }
        ]
    }
    adapter._client = fake
    adapter._account_id = "ANGEL-001"
    await adapter.set_mode("live")

    summary = await adapter.account_info()
    assert summary.equity == 250_000.0
    assert len(summary.positions) == 1
    assert summary.positions[0].symbol == "HDFCBANK"


@pytest.mark.asyncio
async def test_angelone_live_sdk_error_audit_logs_rejection(
    temp_data_dir: object,
) -> None:
    class _Boom(_FakeAngelClient):
        def placeOrderFullResponse(self, params: dict) -> dict:  # noqa: N802
            raise RuntimeError("angel boom")

    adapter = AngelOneAdapter()
    adapter._client = _Boom()
    adapter._account_id = "ANGEL-001"
    await adapter.set_mode("live")

    proposal = adapter.propose_order(
        symbol="HDFCBANK", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    with pytest.raises(BrokerError, match="placeOrder failed"):
        await adapter.confirm_and_place(proposal, human_confirmed=True)
    actions = [r.action for r in audit_log.tail(limit=10)]
    assert "order-rejected" in actions


# ---------------------------------------------------------------------------
# Foundation safety gates
# ---------------------------------------------------------------------------


def test_angelone_position_limits_raise(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    with pytest.raises(BrokerError, match="exceeds limit"):
        adapter.propose_order(
            symbol="HDFCBANK", side="buy", order_type="limit", quantity=300, limit_price=100.0
        )


@pytest.mark.asyncio
async def test_angelone_kill_switch_propagates(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    await kill_switch.get_bus().fire(reason="test", fired_by="user-toolbar")
    assert adapter.read_only is True
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="HDFCBANK", side="buy", order_type="limit", quantity=1, limit_price=10.0
        )


@pytest.mark.asyncio
async def test_angelone_connect_rejects_partial_credentials(
    temp_data_dir: object,
) -> None:
    adapter = AngelOneAdapter()
    with pytest.raises(BrokerError, match="credentials"):
        await adapter.connect({"api_key": "x", "client_code": "y"})


def test_angelone_state(temp_data_dir: object) -> None:
    adapter = AngelOneAdapter()
    state = adapter.state()
    assert state.broker == "angelone"
    assert state.mode == "paper"
    assert state.status == "disconnected"
    assert state.capabilities.supports_equity is True
    assert state.capabilities.requires_static_ip is False
