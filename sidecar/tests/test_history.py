"""Tests for the /history router."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_get_history(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body["symbol"] == "AAPL"
    assert body["timeframe"] == "1d"
    assert body["provider"] == "yfinance"
    assert len(body["bars"]) == 3
    first = body["bars"][0]
    assert first["open"] == 188.0
    assert first["close"] == 190.0
    assert first["volume"] == 48_000_000.0


def test_get_history_default_timeframe(client: TestClient, mock_yfinance: object) -> None:
    body = client.get("/history/AAPL").json()
    assert body["timeframe"] == "1d"
    assert len(body["bars"]) == 3


def test_get_history_carries_freshness(client: TestClient, mock_yfinance: object) -> None:
    """The series carries a calendar-aware freshness label for its last bar so the
    chart never shows a stale series as current (SC-019)."""
    body = client.get("/history/AAPL", params={"timeframe": "1d"}).json()
    assert body["freshness"] in {"live", "eod", "stale"}
