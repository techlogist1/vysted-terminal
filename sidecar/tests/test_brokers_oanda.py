"""Tests for the OANDA v20 broker adapter.

The ``oandapyV20`` SDK is synchronous and HTTP-only — we mock the
``API.request`` method to return canned dicts that match the OANDA v20
REST shape. Real OANDA practice endpoints are free but would still
need credentials at CI time; we keep the suite hermetic by patching
the SDK at the module boundary.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from config import DATA_DIR_ENV
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers.oanda import (
    OandaAdapter,
    _extract_order_outcome,
    _to_float,
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
# Mock OANDA scaffolding
# ---------------------------------------------------------------------------


def _patch_oanda(
    monkeypatch: pytest.MonkeyPatch,
    *,
    response_map: dict[str, Any] | None = None,
    request_side_effect: BaseException | None = None,
) -> MagicMock:
    """Replace ``oandapyV20.API`` with a factory returning a configurable mock."""
    import oandapyV20

    client = MagicMock()
    captured: dict[str, Any] = {"env": None}
    response_map = response_map or {}

    def _request(req: Any) -> Any:
        if request_side_effect is not None:
            raise request_side_effect
        kind = type(req).__name__
        return response_map.get(kind, {})

    client.request.side_effect = _request

    def _factory(**kwargs: Any) -> MagicMock:
        captured["env"] = kwargs.get("environment")
        captured["token"] = kwargs.get("access_token")
        return client

    monkeypatch.setattr(oandapyV20, "API", _factory)
    client._captured = captured  # type: ignore[attr-defined]
    return client


# ---------------------------------------------------------------------------
# §6.5 #1 — practice / demo is the paper default
# ---------------------------------------------------------------------------


def test_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = OandaAdapter()
    assert adapter.mode == "paper"


def test_capabilities_advertise_oanda_surface(temp_data_dir: object) -> None:
    caps = OandaAdapter.CAPABILITIES
    assert caps.supports_forex is True
    assert caps.supports_equity is False
    assert caps.supports_options is False
    assert caps.supports_crypto is False
    assert caps.supports_futures is False
    assert caps.requires_static_ip is False


@pytest.mark.asyncio
async def test_connect_uses_practice_environment_by_default(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _patch_oanda(monkeypatch)
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    assert client._captured["env"] == "practice"  # type: ignore[attr-defined]
    assert client._captured["token"] == "tok"  # type: ignore[attr-defined]
    assert adapter._account_id == "101-001-1-001"


@pytest.mark.asyncio
async def test_connect_after_set_mode_live_uses_live_environment(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _patch_oanda(monkeypatch)
    adapter = OandaAdapter()
    await adapter.set_mode("live")
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    assert client._captured["env"] == "live"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_connect_missing_credentials_raises(temp_data_dir: object) -> None:
    adapter = OandaAdapter()
    with pytest.raises(BrokerError, match="access_token and account_id are required"):
        await adapter.connect({"access_token": "tok"})


@pytest.mark.asyncio
async def test_connect_failure_audits_error(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_oanda(monkeypatch, request_side_effect=RuntimeError("bad token"))
    adapter = OandaAdapter()
    with pytest.raises(BrokerError, match="connect failed"):
        await adapter.connect({"access_token": "bad", "account_id": "101-001-1-001"})
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
    response_map = {
        "AccountSummary": {"account": {"currency": "USD", "balance": "10000.00"}},
        "AccountDetails": {
            "account": {
                "currency": "USD",
                "balance": "10000.00",
                "NAV": "10500.00",
                "marginAvailable": "9500.00",
                "positions": [
                    {
                        "instrument": "EUR_USD",
                        "long": {"units": "1000", "averagePrice": "1.0850"},
                        "short": {"units": "0", "averagePrice": "0"},
                        "unrealizedPL": "10.50",
                    },
                    {
                        "instrument": "GBP_USD",
                        "long": {"units": "0", "averagePrice": "0"},
                        "short": {"units": "-500", "averagePrice": "1.2500"},
                        "unrealizedPL": "-2.00",
                    },
                ],
            }
        },
    }
    _patch_oanda(monkeypatch, response_map=response_map)
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    summary = await adapter.account_info()

    assert summary.broker == "oanda"
    assert summary.currency == "USD"
    assert summary.equity == 10500.0
    assert summary.cash == 10000.0
    assert summary.buying_power == 9500.0
    assert len(summary.positions) == 2
    eur = next(p for p in summary.positions if p.symbol == "EUR_USD")
    assert eur.quantity == 1000.0
    assert eur.average_cost == 1.0850
    gbp = next(p for p in summary.positions if p.symbol == "GBP_USD")
    assert gbp.quantity == -500.0


@pytest.mark.asyncio
async def test_account_info_before_connect_raises(temp_data_dir: object) -> None:
    adapter = OandaAdapter()
    with pytest.raises(BrokerError, match="not connected"):
        await adapter.account_info()


# ---------------------------------------------------------------------------
# Order placement — verify wire shapes
# ---------------------------------------------------------------------------


def _capturing_oanda(
    monkeypatch: pytest.MonkeyPatch,
    final_response: Any,
) -> dict[str, Any]:
    """Patch and capture every request body submitted to OrderCreate."""
    import oandapyV20

    captured: dict[str, Any] = {"order_create_body": None}

    def _factory(**kwargs: Any) -> MagicMock:
        return client

    def _request(req: Any) -> Any:
        if type(req).__name__ == "OrderCreate":
            captured["order_create_body"] = getattr(req, "data", None)
            return final_response
        if type(req).__name__ == "OrderCancel":
            captured["order_cancel"] = {
                "accountID": getattr(req, "_account_id", None) or req.__dict__.get("accountID"),
            }
            return final_response
        return {"account": {}}

    client = MagicMock()
    client.request.side_effect = _request
    monkeypatch.setattr(oandapyV20, "API", _factory)
    return captured


@pytest.mark.asyncio
async def test_market_buy_constructs_positive_units(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _capturing_oanda(
        monkeypatch,
        final_response={"orderFillTransaction": {"id": "txn-1", "orderID": "ord-1"}},
    )
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    proposal = adapter.propose_order(
        symbol="EUR_USD", side="buy", order_type="market", quantity=1000
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)

    body = captured["order_create_body"]
    assert body["order"]["type"] == "MARKET"
    assert body["order"]["units"] == "1000.0"
    assert body["order"]["instrument"] == "EUR_USD"
    assert result.status == "filled"
    assert result.broker_order_id == "ord-1"


@pytest.mark.asyncio
async def test_market_sell_constructs_negative_units(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _capturing_oanda(
        monkeypatch,
        final_response={"orderFillTransaction": {"id": "txn-2", "orderID": "ord-2"}},
    )
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    proposal = adapter.propose_order(
        symbol="EUR_USD", side="sell", order_type="market", quantity=1000
    )
    await adapter.confirm_and_place(proposal, human_confirmed=True)

    body = captured["order_create_body"]
    assert body["order"]["units"] == "-1000.0"


@pytest.mark.asyncio
async def test_limit_order_includes_price(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured = _capturing_oanda(
        monkeypatch,
        final_response={"orderCreateTransaction": {"id": "ord-3"}},
    )
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    proposal = adapter.propose_order(
        symbol="EUR_USD",
        side="buy",
        order_type="limit",
        quantity=500,
        limit_price=1.0800,
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    body = captured["order_create_body"]
    assert body["order"]["type"] == "LIMIT"
    assert body["order"]["price"] == "1.08"
    assert result.broker_order_id == "ord-3"
    assert result.status == "open"


@pytest.mark.asyncio
async def test_order_reject_transaction_maps_to_rejected(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    _capturing_oanda(
        monkeypatch,
        final_response={"orderRejectTransaction": {"id": "ord-4"}},
    )
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    proposal = adapter.propose_order(
        symbol="EUR_USD", side="buy", order_type="market", quantity=100
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "rejected"


# ---------------------------------------------------------------------------
# Position limits — §6.5 #3
# ---------------------------------------------------------------------------


def test_propose_order_above_limit_raises(temp_data_dir: object) -> None:
    adapter = OandaAdapter()
    # 100 units @ 200 = 20000 > default 10_000 cap
    with pytest.raises(BrokerError, match="exceeds limit"):
        adapter.propose_order(
            symbol="EUR_USD", side="buy", order_type="limit", quantity=100, limit_price=200.0
        )


# ---------------------------------------------------------------------------
# Kill switch — §6.5 #5
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kill_switch_sets_adapter_read_only(temp_data_dir: object) -> None:
    adapter = OandaAdapter()
    await kill_switch.get_bus().fire(reason="emergency", fired_by="user-keyboard")
    assert adapter.read_only is True


@pytest.mark.asyncio
async def test_propose_after_kill_switch_raises(temp_data_dir: object) -> None:
    adapter = OandaAdapter()
    await kill_switch.get_bus().fire(reason="test", fired_by="user-toolbar")
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="EUR_USD", side="buy", order_type="limit", quantity=1, limit_price=1.0
        )


# ---------------------------------------------------------------------------
# Cancel order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_order_calls_sdk(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_oanda(
        monkeypatch,
        response_map={"OrderCancel": {"orderCancelTransaction": {"orderID": "ord-99"}}},
    )
    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    await adapter.cancel_order("ord-99")
    rows = audit_log.tail(limit=2)
    assert rows[0].action == "order-cancelled"


@pytest.mark.asyncio
async def test_cancel_order_failure_audits(
    temp_data_dir: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    import oandapyV20

    client = MagicMock()

    def _request(req: Any) -> Any:
        if type(req).__name__ == "OrderCancel":
            raise RuntimeError("cancel failed")
        return {}

    client.request.side_effect = _request
    monkeypatch.setattr(oandapyV20, "API", lambda **_kw: client)

    adapter = OandaAdapter()
    await adapter.connect({"access_token": "tok", "account_id": "101-001-1-001"})
    with pytest.raises(BrokerError, match="cancel order failed"):
        await adapter.cancel_order("ord-99")
    rows = audit_log.tail(limit=5)
    outcomes = [r.outcome for r in rows]
    assert any("cancel-rejected" in o for o in outcomes)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def test_to_float_handles_strings_and_none() -> None:
    assert _to_float(None) == 0.0
    assert _to_float("1.5") == 1.5
    assert _to_float("not-a-number") == 0.0
    assert _to_float(2) == 2.0


def test_extract_order_outcome_dispatch() -> None:
    fill = {"orderFillTransaction": {"orderID": "1"}}
    create = {"orderCreateTransaction": {"id": "2"}}
    reject = {"orderRejectTransaction": {"id": "3"}}
    cancel = {"orderCancelTransaction": {"orderID": "4"}}
    other = {"foo": "bar"}
    assert _extract_order_outcome(fill) == ("1", "filled")
    assert _extract_order_outcome(create) == ("2", "open")
    assert _extract_order_outcome(reject) == ("3", "rejected")
    assert _extract_order_outcome(cancel) == ("4", "cancelled")
    assert _extract_order_outcome(other) == (None, "open")
