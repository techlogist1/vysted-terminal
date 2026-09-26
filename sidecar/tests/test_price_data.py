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


def test_30m_timeframe_default_range_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-064 acceptance: a 30m request with no explicit range (the
    default 6mo, past Yahoo's 60-day sub-hour cap) reaches the REAL provider
    chain and still succeeds — the provider clamps the range rather than
    coming back with an empty, gate-rejected series."""
    import pandas as pd

    from services import yfinance_provider

    class _FastInfo:
        last_price = 100.0
        previous_close = 99.0
        last_volume = 1_000.0
        currency = "USD"

    class _Ticker:
        def __init__(self, symbol: str) -> None:  # noqa: ARG002
            pass

        @property
        def fast_info(self) -> _FastInfo:
            return _FastInfo()

        def get_history_metadata(self) -> dict:
            return {"regularMarketTime": int(datetime.now(tz=UTC).timestamp())}

        def history(self, period: str, interval: str) -> pd.DataFrame:  # noqa: ARG002
            index = pd.to_datetime(["2026-05-12", "2026-05-13"])
            return pd.DataFrame(
                {
                    "Open": [100.0, 101.0],
                    "High": [101.0, 102.0],
                    "Low": [99.0, 100.0],
                    "Close": [100.5, 101.5],
                    "Volume": [1_000.0, 1_100.0],
                },
                index=index,
            )

    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _Ticker)
    result = asyncio.run(price_data._price_data({"symbol": "AAPL", "timeframe": "30m"}))
    assert result["ok"] is True
    assert result["bars_returned"] > 0
