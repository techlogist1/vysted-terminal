"""FR-042 (SC-012) — genuine granular Kite reads.

Today ``/positions``, ``/holdings``, ``/margins`` aliased ``account_info()`` →
one ``AccountSummary``. These tests assert the NET-NEW granular reads return the
DISTINCT real shapes (positions ≠ holdings ≠ margins), carry per-position P&L,
and that paper / disconnected mode returns a clearly-labelled synthetic result
(FR-041) rather than a fabricated real holding. Mirrors
``test_kite_account_readonly.py``: a ``_FakeKiteClient`` returns distinct
positions/holdings/margins shapes; no live SDK call.
"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import create_app
from config import DATA_DIR_ENV
from routers import brokers as brokers_router
from services import kill_switch
from services.brokers import registry as brokers_registry
from services.brokers.kite import KiteAdapter


class _FakeKiteClient:
    """Returns three DISTINCT shapes — one per real kiteconnect read call."""

    def positions(self) -> dict:
        return {
            "net": [
                {
                    "tradingsymbol": "NIFTY24FUT",
                    "quantity": 50,
                    "average_price": 22_000.0,
                    "last_price": 22_100.0,
                    "pnl": 5000.0,
                    "unrealised": 5000.0,
                    "realised": 250.0,
                    "product": "NRML",
                }
            ],
            "day": [
                {
                    "tradingsymbol": "BANKNIFTY24FUT",
                    "quantity": 25,
                    "average_price": 48_000.0,
                    "last_price": 47_800.0,
                    "pnl": -5000.0,
                    "product": "MIS",
                }
            ],
        }

    def holdings(self) -> list[dict]:
        return [
            {
                "tradingsymbol": "INFY",
                "quantity": 10,
                "average_price": 1400.0,
                "last_price": 1500.0,
                "pnl": 1000.0,
            }
        ]

    def margins(self) -> dict:
        return {
            "equity": {
                "net": 150_000.0,
                "available": {"cash": 50_000.0, "collateral": 20_000.0},
                "utilised": {"debits": 30_000.0},
            },
            "commodity": {
                "net": 10_000.0,
                "available": {"cash": 10_000.0},
                "utilised": {},
            },
        }


def _live_adapter() -> KiteAdapter:
    adapter = KiteAdapter()
    adapter._client = _FakeKiteClient()
    adapter._mode = "live"
    adapter._account_id = "U123"
    return adapter


def test_granular_reads_are_distinct_real_shapes() -> None:
    adapter = _live_adapter()
    positions = asyncio.run(adapter.positions_info())
    holdings = asyncio.run(adapter.holdings_info())
    margins = asyncio.run(adapter.margins_info())

    # positions ≠ holdings ≠ margins — distinct, real, unmerged.
    pos_symbols = {p.symbol for p in positions.net} | {p.symbol for p in positions.day}
    hold_symbols = {h.symbol for h in holdings.holdings}
    margin_segments = {m.segment for m in margins.segments}

    assert pos_symbols == {"NIFTY24FUT", "BANKNIFTY24FUT"}
    assert hold_symbols == {"INFY"}
    assert margin_segments == {"equity", "commodity"}
    # No overlap — these are genuinely different reads, not the same merged list.
    assert pos_symbols.isdisjoint(hold_symbols)


def test_positions_carry_per_leg_pnl() -> None:
    positions = asyncio.run(_live_adapter().positions_info())
    net_leg = positions.net[0]
    assert net_leg.unrealized_pnl == 5000.0
    assert net_leg.realized_pnl == 250.0
    assert net_leg.last_price == 22_100.0
    # Realized P&L is a genuine new field the merged AccountSummary never had.
    assert net_leg.product == "NRML"


def test_holdings_carry_market_value_and_pnl() -> None:
    holdings = asyncio.run(_live_adapter().holdings_info())
    h = holdings.holdings[0]
    assert h.symbol == "INFY"
    assert h.market_value == 10 * 1500.0
    assert h.unrealized_pnl == 1000.0


def test_margins_have_per_segment_available_used_net() -> None:
    margins = asyncio.run(_live_adapter().margins_info())
    equity = next(m for m in margins.segments if m.segment == "equity")
    # available sums the available sub-map; used sums utilised; net read directly.
    assert equity.available == 70_000.0  # 50k cash + 20k collateral
    assert equity.used == 30_000.0
    assert equity.net == 150_000.0


def test_live_reads_are_labeled_real() -> None:
    for result in (
        asyncio.run(_live_adapter().positions_info()),
        asyncio.run(_live_adapter().holdings_info()),
        asyncio.run(_live_adapter().margins_info()),
    ):
        assert result.synthetic is False
        assert result.mode == "live"
        assert result.provider == "kite"
        assert result.broker == "kite"


def test_paper_mode_returns_labeled_synthetic_not_fabricated_data() -> None:
    adapter = KiteAdapter()  # paper by default, no client
    positions = asyncio.run(adapter.positions_info())
    holdings = asyncio.run(adapter.holdings_info())
    margins = asyncio.run(adapter.margins_info())

    for result in (positions, holdings, margins):
        assert result.synthetic is True
        assert result.mode == "paper"
        assert result.provider == "kite"
    # Synthetic results do NOT fabricate real-looking holdings.
    assert positions.net == [] and positions.day == []
    assert holdings.holdings == []
    assert margins.segments == []


# ---------------------------------------------------------------------------
# Route layer — GET-only + granular payloads surfaced over HTTP.
# ---------------------------------------------------------------------------


@pytest.fixture
def client(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    kill_switch.reset_bus_for_tests()
    brokers_registry.reset_for_tests()
    brokers_router._reset_pending_proposals_for_tests()
    c = TestClient(create_app())
    brokers_registry.ensure_registered("kite")
    yield c
    brokers_registry.reset_for_tests()
    kill_switch.reset_bus_for_tests()


def test_granular_routes_are_get_only() -> None:
    # §6.5 read-only-by-construction — never a body, never a mutation.
    for route in brokers_router.router.routes:
        path = getattr(route, "path", "")
        methods = getattr(route, "methods", set()) or set()
        if path.endswith(("/positions", "/holdings", "/margins")):
            assert methods == {"GET"}, f"{path} should be GET-only, got {methods}"


def test_live_positions_route_returns_granular_payload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    adapter = brokers_registry.get("kite")
    adapter._client = _FakeKiteClient()
    adapter._mode = "live"
    adapter._account_id = "U123"

    body = client.get("/brokers/kite/positions").json()
    assert body["synthetic"] is False
    assert body["mode"] == "live"
    # Granular shape, not the AccountSummary 'positions' key.
    assert "net" in body and "day" in body
    assert {leg["symbol"] for leg in body["net"]} == {"NIFTY24FUT"}
