"""``price_data``: the 90-bar prompt cap is visible in the payload, never a silent
cut of the requested range (R15-AGENT-062)."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from models.market import OHLCVBar, OHLCVSeries, Quote
from services import provider_registry
from services.agent_tools import price_data

_BARS_BY_RANGE = {"6mo": 126, "1mo": 21}


def _stub(monkeypatch: pytest.MonkeyPatch) -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)

    def fake_history(symbol: str, timeframe: str, range_: str, asset_class: str) -> OHLCVSeries:
        bars = [
            OHLCVBar(
                timestamp=start + timedelta(days=i),
                open=1.0,
                high=1.0,
                low=1.0,
                close=1.0,
                volume=1.0,
            )
            for i in range(_BARS_BY_RANGE[range_])
        ]
        return OHLCVSeries(symbol=symbol, timeframe=timeframe, bars=bars, provider="yfinance")

    def fake_quote(symbol: str, asset_class: str) -> Any:
        return Quote.model_validate(
            {
                "symbol": symbol,
                "price": 1.0,
                "change": 0.0,
                "change_percent": 0.0,
                "timestamp": start.isoformat(),
                "provider": "yfinance",
            }
        )

    monkeypatch.setattr(provider_registry, "get_history", fake_history)
    monkeypatch.setattr(provider_registry, "get_quote", fake_quote)


def test_six_month_range_reports_the_cut_window(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch)
    result = asyncio.run(price_data._price_data({"symbol": "AAPL", "range": "6mo"}))

    assert result["bars_returned"] == 90
    assert result["bars_available"] == 126
    expected_start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=126 - 90)
    assert result["window_start"] == expected_start.isoformat()
    assert result["bars"][0]["timestamp"] == result["window_start"]


def test_range_under_the_cap_returns_every_bar(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub(monkeypatch)
    result = asyncio.run(price_data._price_data({"symbol": "AAPL", "range": "1mo"}))

    assert result["bars_returned"] == result["bars_available"] == 21
    assert result["window_start"] == datetime(2026, 1, 1, tzinfo=UTC).isoformat()
