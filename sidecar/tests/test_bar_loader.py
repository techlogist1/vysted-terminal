"""Tests for the production bar loader (Teammate K v0.5.0).

The loader wraps Phase-1's ``provider_registry.get_history`` per symbol
and normalises provider ``OHLCVBar``s into engine ``Bar``s. Provider
calls are mocked here — no test makes a live network request.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from models.market import OHLCVBar, OHLCVSeries
from services import bar_loader
from services.errors import ProviderError


def _series(symbol: str) -> OHLCVSeries:
    bars = [
        OHLCVBar(
            timestamp=datetime(2025, 6, 2, tzinfo=UTC),
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=1_000.0,
        ),
        OHLCVBar(
            timestamp=datetime(2025, 6, 3, tzinfo=UTC),
            open=101.0,
            high=104.0,
            low=100.0,
            close=103.0,
            volume=1_200.0,
        ),
        OHLCVBar(
            timestamp=datetime(2025, 12, 30, tzinfo=UTC),
            open=110.0,
            high=112.0,
            low=109.0,
            close=111.0,
            volume=1_500.0,
        ),
    ]
    return OHLCVSeries(symbol=symbol, timeframe="1d", bars=bars, provider="yfinance")


@pytest.mark.asyncio
async def test_load_bars_pulls_one_symbol_and_normalises_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_get_history(symbol: str, timeframe: str, range_: str, asset_class: str):
        captured["symbol"] = symbol
        captured["timeframe"] = timeframe
        captured["range_"] = range_
        captured["asset_class"] = asset_class
        return _series(symbol)

    monkeypatch.setattr(bar_loader.provider_registry, "get_history", fake_get_history)

    bars = await bar_loader.load_bars(["AAPL"], "2025-06-01", "2025-12-31")
    timestamps = [b.timestamp for b in bars]
    # All three sample bars fall inside the window.
    assert timestamps == ["2025-06-02", "2025-06-03", "2025-12-30"]
    assert captured["asset_class"] == "equity"
    assert captured["timeframe"] == "1d"


@pytest.mark.asyncio
async def test_load_bars_filters_to_date_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bar_loader.provider_registry,
        "get_history",
        lambda *_a, **_k: _series("AAPL"),
    )
    bars = await bar_loader.load_bars(["AAPL"], "2025-06-01", "2025-06-15")
    timestamps = [b.timestamp for b in bars]
    assert timestamps == ["2025-06-02", "2025-06-03"]


@pytest.mark.asyncio
async def test_load_bars_returns_empty_on_provider_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_provider_error(*_a, **_k):
        raise ProviderError("yfinance is sad")

    monkeypatch.setattr(bar_loader.provider_registry, "get_history", raise_provider_error)
    bars = await bar_loader.load_bars(["AAPL"], "2025-01-01", "2025-12-31")
    assert bars == []


@pytest.mark.asyncio
async def test_load_bars_dispatches_crypto_for_slash_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict = {}

    def fake_get_history(symbol: str, timeframe: str, range_: str, asset_class: str):
        captured["asset_class"] = asset_class
        return _series(symbol)

    monkeypatch.setattr(bar_loader.provider_registry, "get_history", fake_get_history)
    await bar_loader.load_bars(["BTC/USDT"], "2025-06-01", "2025-12-31")
    assert captured["asset_class"] == "crypto"


@pytest.mark.asyncio
async def test_load_bars_concatenates_multiple_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: list[str] = []

    def fake_get_history(symbol: str, timeframe: str, range_: str, asset_class: str):
        seen.append(symbol)
        return _series(symbol)

    monkeypatch.setattr(bar_loader.provider_registry, "get_history", fake_get_history)

    bars = await bar_loader.load_bars(["AAPL", "MSFT"], "2025-06-01", "2025-12-31")
    symbols_in_bars = {bar.symbol for bar in bars}
    assert symbols_in_bars == {"AAPL", "MSFT"}
    assert set(seen) == {"AAPL", "MSFT"}


@pytest.mark.asyncio
async def test_load_bars_empty_symbol_list_returns_empty() -> None:
    bars = await bar_loader.load_bars([], "2025-01-01", "2025-12-31")
    assert bars == []


@pytest.mark.parametrize(
    "start,end,expected",
    [
        ("2025-06-01", "2025-06-15", "3mo"),  # 14 days
        ("2025-04-01", "2025-06-20", "6mo"),  # 80 days
        ("2025-01-01", "2025-12-31", "2y"),  # 364 days
        ("2020-01-01", "2025-12-31", "max"),  # >2000 days
        ("2025-06-01", "2025-06-01", "1mo"),  # same-day → 0 days
        ("not-a-date", "2025-12-31", "1y"),  # invalid input
    ],
)
def test_provider_range_picks_a_safe_overfetch(start: str, end: str, expected: str) -> None:
    assert bar_loader._provider_range(start, end) == expected
