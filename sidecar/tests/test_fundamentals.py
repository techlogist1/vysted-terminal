"""Tests for the /fundamentals router."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_get_fundamentals(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL").json()
    assert body["symbol"] == "AAPL"
    assert body["name"] == "Apple Inc."
    assert body["sector"] == "Technology"
    assert body["pe_ratio"] == 31.2
    assert body["beta"] == 1.25
    # yfinance 1.3.0 returns ``dividendYield`` as a percentage number
    # (the fake supplies ``0.44``); the provider divides by 100 so the
    # ``dividend_yield`` field carries a true fraction.
    assert body["dividend_yield"] == pytest.approx(0.0044)
    assert body["provider"] == "yfinance"


def test_get_fundamentals_dividend_yield_missing(
    client: TestClient,
    mock_yfinance: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing ``dividendYield`` stays ``None`` — no divide-by-100 crash."""
    from services import yfinance_provider

    class _NoYieldTicker(mock_yfinance):  # type: ignore[misc, valid-type]
        @property
        def info(self) -> dict:
            data = super().info.copy()
            data.pop("dividendYield", None)
            return data

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _NoYieldTicker)
    body = client.get("/fundamentals/AAPL").json()
    assert body["dividend_yield"] is None


def test_get_income_statement(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/income").json()
    assert body["symbol"] == "AAPL"
    assert body["periods"] == ["2025", "2024"]
    labels = {line["label"] for line in body["lines"]}
    assert "Total Revenue" in labels
    assert "Net Income" in labels


def test_get_balance_sheet(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/balance").json()
    assert body["periods"] == ["2025", "2024"]
    assert len(body["lines"]) == 2


def test_get_cash_flow(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/cashflow").json()
    assert len(body["lines"]) == 2


def test_get_analyst_rating(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL/ratings").json()
    assert body["symbol"] == "AAPL"
    assert body["strong_buy"] == 12
    assert body["buy"] == 20
    assert body["hold"] == 8
    assert body["consensus"] == "buy"
    assert body["target_mean"] == 225.0
