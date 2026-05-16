"""Tests for the Kite Connect broker adapter.

Kite is the broker with ``requires_static_ip = True``. The adapter overrides
:meth:`BrokerAdapter.set_mode` to also audit-log the detected-vs-configured
public IP comparison whenever the user toggles to live mode. These tests
patch :func:`services.static_ip_detector.static_ip_status` to drive the
audit-log outcome without actually hitting ``api.ipify.org``.
"""

from __future__ import annotations

import pytest

from config import DATA_DIR_ENV
from models.broker import AccountSummary
from models.safety import StaticIpStatus
from services import audit_log, kill_switch
from services.broker_base import BrokerError
from services.brokers import kite as kite_module
from services.brokers.kite import KiteAdapter


@pytest.fixture
def temp_data_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


@pytest.fixture(autouse=True)
def fresh_bus() -> None:
    kill_switch.reset_bus_for_tests()
    yield
    kill_switch.reset_bus_for_tests()


class _FakeKiteClient:
    def __init__(self) -> None:
        self.place_calls: list[dict] = []
        self.cancel_calls: list[tuple[str, str]] = []
        self.place_response: str | dict = "KITE-001"
        self.margins_response: dict = {"equity": {"available": {"cash": 300_000.0}}}
        self.holdings_response: list = []

    def place_order(self, **kwargs) -> str | dict:
        self.place_calls.append(kwargs)
        return self.place_response

    def cancel_order(self, variety: str, order_id: str) -> dict:
        self.cancel_calls.append((variety, order_id))
        return {"order_id": order_id}

    def margins(self) -> dict:
        return self.margins_response

    def holdings(self) -> list:
        return self.holdings_response


# ---------------------------------------------------------------------------
# Capability + paper-mode defaults
# ---------------------------------------------------------------------------


def test_kite_capabilities_require_static_ip(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    assert adapter.BROKER_ID == "kite"
    assert adapter.CAPABILITIES.requires_static_ip is True
    assert adapter.CAPABILITIES.supports_equity is True


def test_kite_paper_mode_is_default(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    assert adapter.mode == "paper"
    assert adapter.configured_static_ip() is None


# ---------------------------------------------------------------------------
# Paper-mode order flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kite_paper_place_returns_synthetic_fill(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    proposal = adapter.propose_order(
        symbol="INFY", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "filled"
    assert result.broker == "kite"
    assert result.broker_order_id.startswith("paper-kite-")
    assert adapter._client is None


@pytest.mark.asyncio
async def test_kite_paper_account_info(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    summary = await adapter.account_info()
    assert isinstance(summary, AccountSummary)
    assert summary.broker == "kite"
    assert summary.currency == "INR"


# ---------------------------------------------------------------------------
# Live-mode SDK dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kite_live_place_calls_sdk(temp_data_dir: object, monkeypatch) -> None:
    adapter = KiteAdapter()
    fake = _FakeKiteClient()
    adapter._client = fake
    adapter._account_id = "KITE-USER-001"

    # Patch static-ip detector so set_mode("live") does not hit the network.
    async def _fake_status(configured, *args, **kwargs):
        return StaticIpStatus(
            detectedIp=configured,
            configuredIp=configured,
            matches=True,
            message="ok",
            detectedAt=1000,
        )

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _fake_status)
    await adapter.set_mode("live")

    proposal = adapter.propose_order(
        symbol="INFY", side="buy", order_type="limit", quantity=5, limit_price=100.0
    )
    result = await adapter.confirm_and_place(proposal, human_confirmed=True)
    assert result.status == "open"
    assert result.broker_order_id == "KITE-001"
    assert len(fake.place_calls) == 1
    assert fake.place_calls[0]["transaction_type"] == "BUY"


@pytest.mark.asyncio
async def test_kite_live_account_info_reads_margins(temp_data_dir: object, monkeypatch) -> None:
    adapter = KiteAdapter()
    fake = _FakeKiteClient()
    fake.holdings_response = [
        {
            "tradingsymbol": "INFY",
            "quantity": 10,
            "average_price": 90.0,
            "last_price": 105.0,
            "pnl": 150.0,
        }
    ]
    adapter._client = fake
    adapter._account_id = "KITE-USER-001"

    async def _fake_status(configured, *args, **kwargs):
        return StaticIpStatus(
            detectedIp=None, configuredIp=None, matches=False, message="x", detectedAt=1
        )

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _fake_status)
    await adapter.set_mode("live")

    summary = await adapter.account_info()
    assert summary.equity == 300_000.0
    assert len(summary.positions) == 1
    assert summary.positions[0].symbol == "INFY"
    assert summary.positions[0].unrealized_pnl == 150.0


# ---------------------------------------------------------------------------
# Static-IP UX flow
# ---------------------------------------------------------------------------


def test_kite_set_configured_static_ip_round_trip(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    adapter.set_configured_static_ip(" 203.0.113.5 ")
    assert adapter.configured_static_ip() == "203.0.113.5"
    adapter.set_configured_static_ip(None)
    assert adapter.configured_static_ip() is None
    adapter.set_configured_static_ip("")
    assert adapter.configured_static_ip() is None


@pytest.mark.asyncio
async def test_kite_live_toggle_audit_logs_static_ip_match(
    temp_data_dir: object, monkeypatch
) -> None:
    adapter = KiteAdapter()
    adapter.set_configured_static_ip("203.0.113.5")

    captured = {}

    async def _fake_status(configured, *args, **kwargs):
        captured["configured"] = configured
        return StaticIpStatus(
            detectedIp="203.0.113.5",
            configuredIp=configured,
            matches=True,
            message="match",
            detectedAt=1000,
        )

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _fake_status)

    await adapter.set_mode("live")

    assert captured["configured"] == "203.0.113.5"
    rows = audit_log.tail(limit=10)
    # Two mode-changed rows expected: the base ABC's row + the Kite override's
    # static-ip annotation row.
    mode_rows = [r for r in rows if r.action == "mode-changed"]
    assert len(mode_rows) >= 2
    static_ip_row = next((r for r in mode_rows if "staticIpStatus" in r.payload), None)
    assert static_ip_row is not None
    assert static_ip_row.payload["staticIpStatus"]["matches"] is True
    assert static_ip_row.outcome == "ok"


@pytest.mark.asyncio
async def test_kite_live_toggle_audit_logs_static_ip_mismatch(
    temp_data_dir: object, monkeypatch
) -> None:
    adapter = KiteAdapter()
    adapter.set_configured_static_ip("203.0.113.5")

    async def _fake_status(configured, *args, **kwargs):
        return StaticIpStatus(
            detectedIp="198.51.100.42",
            configuredIp=configured,
            matches=False,
            message="mismatch",
            detectedAt=1000,
        )

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _fake_status)

    await adapter.set_mode("live")
    rows = audit_log.tail(limit=10)
    static_ip_row = next(
        (r for r in rows if r.action == "mode-changed" and "staticIpStatus" in r.payload),
        None,
    )
    assert static_ip_row is not None
    assert static_ip_row.payload["staticIpStatus"]["matches"] is False
    assert static_ip_row.outcome == "static-ip-mismatch"


@pytest.mark.asyncio
async def test_kite_paper_toggle_does_not_run_static_ip_detection(
    temp_data_dir: object, monkeypatch
) -> None:
    """Toggling back to paper mode must not trigger the static-IP detector.

    The detector is only relevant for live placement; calling it on a paper
    toggle would still leak a network request via the public IP-echo URL.
    """
    adapter = KiteAdapter()
    adapter.set_configured_static_ip("203.0.113.5")

    invocations: list[str | None] = []

    async def _fake_status(configured, *args, **kwargs):
        invocations.append(configured)
        return StaticIpStatus(
            detectedIp=None, configuredIp=None, matches=False, message="x", detectedAt=1
        )

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _fake_status)

    await adapter.set_mode("paper")
    assert invocations == []


@pytest.mark.asyncio
async def test_kite_live_toggle_swallows_detector_errors(
    temp_data_dir: object, monkeypatch
) -> None:
    """The detector raising must not break the live toggle path."""
    adapter = KiteAdapter()
    adapter.set_configured_static_ip("203.0.113.5")

    async def _boom(configured, *args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(kite_module.static_ip_detector, "static_ip_status", _boom)

    # The override must catch the exception and still leave the adapter live.
    await adapter.set_mode("live")
    assert adapter.mode == "live"


# ---------------------------------------------------------------------------
# Foundation safety gates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kite_kill_switch_propagates(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    await kill_switch.get_bus().fire(reason="emergency", fired_by="user-keyboard")
    assert adapter.read_only is True
    with pytest.raises(BrokerError, match="kill switch fired"):
        adapter.propose_order(
            symbol="INFY", side="buy", order_type="limit", quantity=1, limit_price=10.0
        )


def test_kite_position_limits_raise(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    with pytest.raises(BrokerError, match="per-symbol cap"):
        adapter.propose_order(
            symbol="INFY", side="buy", order_type="limit", quantity=1500, limit_price=1.0
        )


@pytest.mark.asyncio
async def test_kite_connect_rejects_missing_credentials(temp_data_dir: object) -> None:
    adapter = KiteAdapter()
    with pytest.raises(BrokerError, match="credentials"):
        await adapter.connect({"api_key": "x"})
