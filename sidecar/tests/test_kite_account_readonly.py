"""Phase 10 — Kite read-only account fixes + the real OAuth login exchange.

Covers the gaps the integrations track closed: equity = ``net`` (not
``available.cash``), F&O/intraday positions merged with long-term holdings, the
daily ``TokenException`` mapped to a typed "session expired" error, and the
``request_token -> access_token`` exchange (the genuine OAuth dance, not a
static pasted token).
"""

from __future__ import annotations

import asyncio

import pytest

from services.broker_base import BrokerError
from services.brokers.kite import (
    KiteAdapter,
    _raise_kite_read_error,
    exchange_request_token,
)


class _FakeKiteClient:
    def margins(self) -> dict:
        # net (equity/buying power) differs from available cash — the old code
        # collapsed all three to cash, hiding used/F&O margin.
        return {"equity": {"net": 150_000.0, "available": {"cash": 50_000.0}}}

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

    def positions(self) -> dict:
        return {
            "net": [
                {
                    "tradingsymbol": "NIFTY24FUT",
                    "quantity": 50,
                    "average_price": 22_000.0,
                    "last_price": 22_100.0,
                    "pnl": 5000.0,
                }
            ]
        }


def _live_adapter() -> KiteAdapter:
    adapter = KiteAdapter()
    adapter._client = _FakeKiteClient()
    adapter._mode = "live"
    adapter._account_id = "U123"
    return adapter


def test_account_info_uses_net_and_merges_positions() -> None:
    summary = asyncio.run(_live_adapter()._account_info())
    assert summary.equity == 150_000.0  # net, not available.cash
    assert summary.cash == 50_000.0
    symbols = {p.symbol for p in summary.positions}
    # long-term holding AND the intraday/F&O net position both appear.
    assert "INFY" in symbols
    assert "NIFTY24FUT" in symbols


def test_token_exception_maps_to_session_expired() -> None:
    class TokenException(Exception):
        pass

    with pytest.raises(BrokerError, match="session expired"):
        _raise_kite_read_error(TokenException("403 token"))


def test_other_read_error_stays_generic() -> None:
    with pytest.raises(BrokerError, match="account fetch failed"):
        _raise_kite_read_error(ValueError("boom"))


def test_exchange_request_token_runs_the_real_flow(monkeypatch) -> None:
    captured: dict = {}

    class _FakeKC:
        def __init__(self, api_key: str) -> None:
            captured["api_key"] = api_key

        def generate_session(self, request_token: str, api_secret: str) -> dict:
            captured["request_token"] = request_token
            captured["api_secret"] = api_secret
            return {
                "access_token": "atok",
                "user_id": "U123",
                "login_time": "2026-05-30 09:00:00",
            }

    import kiteconnect

    monkeypatch.setattr(kiteconnect, "KiteConnect", _FakeKC)
    data = asyncio.run(exchange_request_token("ak", "secret", "rt"))
    assert data["access_token"] == "atok"
    assert data["user_id"] == "U123"
    # the SDK computed the checksum from these — api_secret used here only.
    assert captured == {
        "api_key": "ak",
        "request_token": "rt",
        "api_secret": "secret",
    }


def test_exchange_requires_all_fields() -> None:
    with pytest.raises(BrokerError, match="required"):
        asyncio.run(exchange_request_token("", "secret", "rt"))
