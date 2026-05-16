"""Tests for the earnings provider — calendar / history / surprises / estimates.

The provider's only external dependency is ``yfinance.Ticker``; tests
swap that out with a deterministic fake so every assertion exercises
the provider's mapping code rather than the upstream network.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

import pandas as pd
import pytest

from services import earnings_provider
from services.errors import ProviderError


class _FakeEarningsTicker:
    """Stand-in for ``yfinance.Ticker`` covering the earnings surface."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol

    @property
    def calendar(self) -> dict[str, Any]:
        return {
            "Earnings Date": [date(2026, 5, 20)],
            "Earnings Average": 1.50,
            "Earnings High": 1.60,
            "Earnings Low": 1.40,
            "Revenue Average": 100_000_000.0,
            "Revenue High": 105_000_000.0,
            "Revenue Low": 95_000_000.0,
        }

    @property
    def earnings_dates(self) -> pd.DataFrame:
        return pd.DataFrame(
            {"EPS Estimate": [1.45, 1.30], "Reported EPS": [None, 1.32]},
            index=pd.to_datetime(["2026-05-20", "2026-02-20"]),
        )

    @property
    def earnings_estimate(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"period": "0q", "avg": 1.50, "low": 1.40, "high": 1.60, "numberOfAnalysts": 21}
            ]
        )

    @property
    def earnings_history(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {"epsActual": 1.32, "epsEstimate": 1.30, "revenueActual": 99_000_000.0, "revenueEstimate": 98_000_000.0},
                {"epsActual": 1.27, "epsEstimate": 1.20, "revenueActual": 96_000_000.0, "revenueEstimate": 95_000_000.0},
            ],
            index=pd.to_datetime(["2026-02-20", "2025-11-20"]),
        )

    @property
    def info(self) -> dict:
        return {"longName": "Apple Inc.", "currency": "USD"}


class _NoCalendarTicker(_FakeEarningsTicker):
    """Ticker whose calendar is empty — used to exercise the no-event path."""

    @property
    def calendar(self) -> dict[str, Any]:  # type: ignore[override]
        return {"Earnings Date": []}


class _FarFutureTicker(_FakeEarningsTicker):
    """Ticker whose next event falls outside the requested window."""

    @property
    def calendar(self) -> dict[str, Any]:  # type: ignore[override]
        return {
            "Earnings Date": [date.today() + timedelta(days=365)],
            "Earnings Average": 1.50,
            "Earnings High": 1.55,
            "Earnings Low": 1.45,
        }


@pytest.fixture
def mock_yf_earnings(monkeypatch: pytest.MonkeyPatch) -> type[_FakeEarningsTicker]:
    """Patch ``earnings_provider._yf_ticker`` with the canned fake."""
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _FakeEarningsTicker)
    return _FakeEarningsTicker


@pytest.mark.asyncio
async def test_get_upcoming_default_window(mock_yf_earnings: type[_FakeEarningsTicker]) -> None:
    response = await earnings_provider.get_upcoming(
        date(2026, 5, 19), date(2026, 5, 21), ["AAPL"]
    )
    assert response.start_date == date(2026, 5, 19)
    assert response.end_date == date(2026, 5, 21)
    assert len(response.events) == 1
    event = response.events[0]
    assert event.symbol == "AAPL"
    assert event.scheduled_date == date(2026, 5, 20)
    assert event.eps_estimate_mean == 1.50
    assert event.fiscal_period.year == 2026


@pytest.mark.asyncio
async def test_get_upcoming_filters_outside_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _FarFutureTicker)
    response = await earnings_provider.get_upcoming(
        date.today(), date.today() + timedelta(days=7), ["AAPL"]
    )
    assert response.events == []


@pytest.mark.asyncio
async def test_get_upcoming_rejects_inverted_window(
    mock_yf_earnings: type[_FakeEarningsTicker],
) -> None:
    with pytest.raises(ProviderError):
        await earnings_provider.get_upcoming(date(2026, 5, 21), date(2026, 5, 20), ["AAPL"])


@pytest.mark.asyncio
async def test_get_history(mock_yf_earnings: type[_FakeEarningsTicker]) -> None:
    response = await earnings_provider.get_history("AAPL")
    assert response.symbol == "AAPL"
    assert len(response.history) == 2
    # Sorted newest-first.
    assert response.history[0].reported_date >= response.history[1].reported_date
    assert response.history[0].eps_actual == 1.32
    assert response.history[0].eps_estimate_mean == 1.30


@pytest.mark.asyncio
async def test_get_surprises(mock_yf_earnings: type[_FakeEarningsTicker]) -> None:
    response = await earnings_provider.get_surprises("AAPL")
    assert response.symbol == "AAPL"
    assert len(response.surprises) == 2
    first = response.surprises[0]
    assert first.eps_actual == 1.32
    assert first.eps_estimate_mean == 1.30
    assert first.eps_surprise == pytest.approx(0.02)
    assert first.eps_surprise_pct == pytest.approx(0.02 / 1.30)
    assert first.revenue_surprise_pct == pytest.approx(1_000_000.0 / 98_000_000.0)


@pytest.mark.asyncio
async def test_get_estimate_detail(mock_yf_earnings: type[_FakeEarningsTicker]) -> None:
    detail = await earnings_provider.get_estimate_detail("AAPL")
    assert detail.symbol == "AAPL"
    assert detail.eps_estimate_mean == 1.50
    assert detail.eps_estimate_high == 1.60
    assert detail.eps_estimate_low == 1.40
    assert detail.estimate_analyst_count == 21
    # Stddev fallback approximation: high-low / 4.
    assert detail.eps_estimate_stddev == pytest.approx(0.05)
    assert isinstance(detail.as_of, datetime)


@pytest.mark.asyncio
async def test_get_estimate_detail_no_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _NoCalendarTicker)
    with pytest.raises(ProviderError):
        await earnings_provider.get_estimate_detail("AAPL")
