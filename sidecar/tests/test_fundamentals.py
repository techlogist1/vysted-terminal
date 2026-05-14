"""Tests for the /fundamentals router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_fundamentals(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/fundamentals/AAPL").json()
    assert body["symbol"] == "AAPL"
    assert body["name"] == "Apple Inc."
    assert body["sector"] == "Technology"
    assert body["pe_ratio"] == 31.2
    assert body["beta"] == 1.25
    assert body["provider"] == "yfinance"


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
