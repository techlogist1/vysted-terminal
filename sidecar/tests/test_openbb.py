"""Tests for the ``/openbb`` router — proxy endpoints, status, graceful 503.

The provider is patched directly so the router's wiring is exercised without a
live OpenBB SDK. The patch toggles ``is_available`` to verify both the live
path (200, payload returned) and the disabled path (503, machine-readable
detail) the plugin distinguishes between.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from models.fundamentals import (
    AnalystRating,
    BalanceSheet,
    CashFlowStatement,
    Fundamentals,
    IncomeStatement,
    StatementLine,
)
from models.market import (
    MacroObservation,
    MacroSeries,
    OHLCVBar,
    OHLCVSeries,
    Quote,
)
from services import openbb_provider

# ---------------------------------------------------------------------------
# Status endpoint
# ---------------------------------------------------------------------------


def test_status_reports_availability(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    body = client.get("/openbb/status").json()
    assert body == {"available": True, "provider": "openbb"}

    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", False)
    body = client.get("/openbb/status").json()
    assert body == {"available": False, "provider": "openbb"}


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


def test_quote_endpoint_returns_provider_payload(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    canned = Quote(
        symbol="AAPL",
        price=192.5,
        change=2.5,
        change_percent=1.32,
        volume=1_000_000,
        currency="USD",
        timestamp=datetime(2026, 5, 15, 15, 30, tzinfo=UTC),
        provider="openbb",
    )
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(openbb_provider, "get_quote", lambda symbol: canned)
    response = client.get("/openbb/quotes/AAPL")
    assert response.status_code == 200
    assert response.json()["symbol"] == "AAPL"
    assert response.json()["provider"] == "openbb"


def test_quote_endpoint_503_when_openbb_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", False)
    response = client.get("/openbb/quotes/AAPL")
    assert response.status_code == 503
    assert "not bundled" in response.json()["detail"]


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------


def test_history_endpoint_passes_timeframe_and_range(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str | None] = {}

    def _fake_history(symbol: str, timeframe: str, range_: str | None = None) -> OHLCVSeries:
        captured["symbol"] = symbol
        captured["timeframe"] = timeframe
        captured["range_"] = range_
        return OHLCVSeries(
            symbol=symbol.upper(),
            timeframe=timeframe,
            bars=[
                OHLCVBar(
                    timestamp=datetime(2026, 5, 15, tzinfo=UTC),
                    open=190.0,
                    high=193.0,
                    low=189.0,
                    close=192.5,
                    volume=51_000_000,
                )
            ],
            provider="openbb",
        )

    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(openbb_provider, "get_history", _fake_history)
    response = client.get("/openbb/history/AAPL", params={"timeframe": "1h", "range": "2025-01-01"})
    assert response.status_code == 200
    body = response.json()
    assert body["timeframe"] == "1h"
    assert captured == {"symbol": "AAPL", "timeframe": "1h", "range_": "2025-01-01"}


# ---------------------------------------------------------------------------
# Fundamentals + statements + ratings
# ---------------------------------------------------------------------------


def test_fundamentals_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(
        openbb_provider,
        "get_fundamentals",
        lambda symbol: Fundamentals(
            symbol=symbol.upper(), name="Apple Inc.", pe_ratio=31.2, provider="openbb"
        ),
    )
    body = client.get("/openbb/fundamentals/AAPL").json()
    assert body["pe_ratio"] == 31.2
    assert body["provider"] == "openbb"


def test_income_statement_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(
        openbb_provider,
        "get_income_statement",
        lambda symbol: IncomeStatement(
            symbol=symbol.upper(),
            periods=["2025-09-30"],
            lines=[StatementLine(label="revenue", values={"2025-09-30": 400000.0})],
            provider="openbb",
        ),
    )
    body = client.get("/openbb/fundamentals/AAPL/income").json()
    assert body["periods"] == ["2025-09-30"]


def test_balance_sheet_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(
        openbb_provider,
        "get_balance_sheet",
        lambda symbol: BalanceSheet(
            symbol=symbol.upper(),
            periods=["2025-09-30"],
            lines=[StatementLine(label="total_assets", values={"2025-09-30": 500000.0})],
            provider="openbb",
        ),
    )
    body = client.get("/openbb/fundamentals/AAPL/balance").json()
    assert body["lines"][0]["label"] == "total_assets"


def test_cash_flow_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(
        openbb_provider,
        "get_cash_flow",
        lambda symbol: CashFlowStatement(
            symbol=symbol.upper(),
            periods=["2025-09-30"],
            lines=[StatementLine(label="operating_cash_flow", values={"2025-09-30": 120000.0})],
            provider="openbb",
        ),
    )
    body = client.get("/openbb/fundamentals/AAPL/cashflow").json()
    assert body["lines"][0]["values"]["2025-09-30"] == 120000.0


def test_analyst_rating_endpoint(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(
        openbb_provider,
        "get_analyst_rating",
        lambda symbol: AnalystRating(
            symbol=symbol.upper(),
            consensus="buy",
            target_mean=225.0,
            strong_buy=12,
            buy=20,
            hold=8,
            provider="openbb",
        ),
    )
    body = client.get("/openbb/fundamentals/AAPL/ratings").json()
    assert body["consensus"] == "buy"
    assert body["strong_buy"] == 12


# ---------------------------------------------------------------------------
# Macro
# ---------------------------------------------------------------------------


def test_macro_endpoint_passes_provider_override(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, str | None] = {}

    def _fake_macro(series_id: str, provider: str | None = None) -> MacroSeries:
        captured["series_id"] = series_id
        captured["provider"] = provider
        return MacroSeries(
            series_id=series_id,
            title="10-Year Treasury",
            observations=[MacroObservation(date=datetime(2025, 1, 1, tzinfo=UTC), value=5.5)],
            provider="openbb",
        )

    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", True)
    monkeypatch.setattr(openbb_provider, "get_macro_series", _fake_macro)
    response = client.get("/openbb/macro/DGS10", params={"provider": "econdb"})
    assert response.status_code == 200
    assert captured == {"series_id": "DGS10", "provider": "econdb"}


def test_macro_endpoint_503_when_openbb_unavailable(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(openbb_provider, "_OPENBB_AVAILABLE", False)
    response = client.get("/openbb/macro/DGS10")
    assert response.status_code == 503
