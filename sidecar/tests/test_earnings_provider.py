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
            [{"period": "0q", "avg": 1.50, "low": 1.40, "high": 1.60, "numberOfAnalysts": 21}]
        )

    @property
    def earnings_history(self) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "epsActual": 1.32,
                    "epsEstimate": 1.30,
                    "revenueActual": 99_000_000.0,
                    "revenueEstimate": 98_000_000.0,
                },
                {
                    "epsActual": 1.27,
                    "epsEstimate": 1.20,
                    "revenueActual": 96_000_000.0,
                    "revenueEstimate": 95_000_000.0,
                },
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
    response = await earnings_provider.get_upcoming(date(2026, 5, 19), date(2026, 5, 21), ["AAPL"])
    assert response.start_date == date(2026, 5, 19)
    assert response.end_date == date(2026, 5, 21)
    assert len(response.events) == 1
    event = response.events[0]
    assert event.symbol == "AAPL"
    assert event.scheduled_date == date(2026, 5, 20)
    assert event.eps_estimate_mean == 1.50
    # R15-DATA-067: yfinance names no fiscal period — none is inferred from the
    # report month (this assertion used to pin the inferred label).
    assert event.fiscal_period is None


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
    # R15-DATA-032: yfinance measures no dispersion — no (high-low)/4 proxy.
    assert detail.eps_estimate_stddev is None
    assert isinstance(detail.as_of, datetime)


@pytest.mark.asyncio
async def test_get_estimate_detail_no_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _NoCalendarTicker)
    with pytest.raises(ProviderError):
        await earnings_provider.get_estimate_detail("AAPL")


# ---------------------------------------------------------------------------
# India symbols resolve through _yahoo_symbol (R15-DATA-029)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_earnings_lane_resolves_india_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    import config

    asked: list[str] = []

    def _recording(symbol: str) -> _FakeEarningsTicker:
        asked.append(symbol)
        return _FakeEarningsTicker(symbol)

    monkeypatch.setattr(earnings_provider, "_yf_ticker", _recording)
    detail = await earnings_provider.get_estimate_detail("RELIANCE.NS")
    token = config.set_request_region("IN")
    try:
        history = await earnings_provider.get_history("INFY")
    finally:
        config.reset_request_region(token)
    assert asked == ["RELIANCE.NS", "INFY.NS"]  # never RELIANCE-NS, never the INFY ADR
    assert (detail.symbol, history.symbol) == ("RELIANCE.NS", "INFY.NS")


# ---------------------------------------------------------------------------
# R15-DATA-032 — no proxy statistics on typed estimate fields
# ---------------------------------------------------------------------------


class _InfyShapedTicker(_FakeEarningsTicker):
    """The batch-4 live INFY shape: mean/high/low, an EPS frame with its own
    analyst count and a revenue frame with a different one."""

    @property
    def calendar(self) -> dict[str, Any]:  # type: ignore[override]
        return {
            "Earnings Date": [date(2026, 10, 23)],
            "Earnings Average": 19.58006,
            "Earnings High": 20.33,
            "Earnings Low": 19.20,
            "Revenue Average": 4.9e11,
            "Revenue High": 5.0e11,
            "Revenue Low": 4.8e11,
        }

    @property
    def earnings_estimate(self) -> pd.DataFrame:
        return pd.DataFrame([{"avg": 19.58006, "low": 19.2, "high": 20.33, "numberOfAnalysts": 31}])

    @property
    def revenue_estimate(self) -> pd.DataFrame:
        return pd.DataFrame(
            [{"avg": 4.9e11, "low": 4.8e11, "high": 5.0e11, "numberOfAnalysts": 27}]
        )


@pytest.mark.asyncio
async def test_estimate_detail_carries_no_proxy_statistics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _InfyShapedTicker)
    detail = await earnings_provider.get_estimate_detail("INFY.NS")
    assert detail.eps_estimate_median is None  # was == mean (19.58006)
    assert detail.eps_estimate_stddev is None  # was (20.33 - 19.20) / 4 = 0.2825
    assert detail.revenue_estimate_median is None
    assert detail.estimate_analyst_count == 31
    assert detail.revenue_analyst_count == 27  # the revenue frame's own count


@pytest.mark.asyncio
async def test_calendar_event_without_a_count_reports_none(monkeypatch: pytest.MonkeyPatch) -> None:
    class _NoCount(_InfyShapedTicker):
        @property
        def earnings_estimate(self) -> pd.DataFrame:  # type: ignore[override]
            return pd.DataFrame([{"avg": 19.58006, "low": 19.2, "high": 20.33}])

    monkeypatch.setattr(earnings_provider, "_yf_ticker", _NoCount)
    response = await earnings_provider.get_upcoming(
        date(2026, 10, 20), date(2026, 10, 25), ["INFY.NS"]
    )
    event = response.events[0]
    assert event.eps_estimate_stddev is None
    assert event.estimate_analyst_count is None  # never a 0 standing in for unknown


# ---------------------------------------------------------------------------
# R15-DATA-067 — no fiscal quarter inferred from the report month
# ---------------------------------------------------------------------------


class _JpmOctoberTicker(_FakeEarningsTicker):
    """JPM reports its fiscal Q3 in mid-October (the report month says Q4)."""

    @property
    def calendar(self) -> dict[str, Any]:  # type: ignore[override]
        return {
            "Earnings Date": [date(2026, 10, 13)],
            "Earnings Average": 5.0,
            "Earnings High": 5.2,
            "Earnings Low": 4.8,
        }


@pytest.mark.asyncio
async def test_events_and_estimates_carry_no_inferred_fiscal_period(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _JpmOctoberTicker)
    upcoming = await earnings_provider.get_upcoming(date(2026, 10, 10), date(2026, 10, 25), ["JPM"])
    assert upcoming.events[0].fiscal_period is None  # was {Q4, 2026}
    monkeypatch.setattr(earnings_provider, "_yf_ticker", _InfyShapedTicker)
    assert (await earnings_provider.get_estimate_detail("INFY.NS")).fiscal_period is None


@pytest.mark.asyncio
async def test_history_rows_carry_no_inferred_fiscal_period(
    mock_yf_earnings: type[_FakeEarningsTicker],
) -> None:
    history = await earnings_provider.get_history("AAPL")
    assert history.history and all(row.fiscal_period is None for row in history.history)
    surprises = await earnings_provider.get_surprises("AAPL")
    assert all(row.fiscal_period is None for row in surprises.surprises)


# ---------------------------------------------------------------------------
# R15-DATA-028 — the IN default is NSE's market-wide event calendar
# ---------------------------------------------------------------------------

#: Market-wide ``/api/event-calendar`` rows (the live shape, 24-Sep-2026).
_NSE_EVENT_CALENDAR_FIXTURE = [
    {
        "symbol": "ESDS",
        "company": "ESDS Software Solution Limited",
        "purpose": "Financial Results",
        "bm_desc": "To consider and approve the financial results for the period ended Jun 30",
        "date": "24-Sep-2026",
    },
    {
        "symbol": "INFY",
        "company": "Infosys Limited",
        "purpose": "Financial Results/Dividend",
        "bm_desc": "To consider and approve the financial results and interim dividend",
        "date": "26-Sep-2026",
    },
    {
        "symbol": "AIFL",
        "company": "Ashapura Intimates Fashion Limited",
        "purpose": "Fund Raising/Other business matters",
        "bm_desc": "To consider Fund Raising and other business matters",
        "date": "25-Sep-2026",
    },
    {
        "symbol": "GATECH",
        "company": "GACM Technologies Limited",
        "purpose": "Dividend",
        "bm_desc": "To consider an interim dividend",
        "date": "28-Sep-2026",
    },
]


@pytest.mark.asyncio
async def test_in_default_reads_the_nse_market_wide_event_calendar(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import config

    calls: list[tuple[str, dict[str, str]]] = []

    def fake_get_json(path: str, params: dict[str, str], referer: str) -> object:
        calls.append((path, params))
        return _NSE_EVENT_CALENDAR_FIXTURE

    def no_yahoo(symbol: str) -> _FakeEarningsTicker:
        raise AssertionError(f"the IN default must not walk a per-symbol universe ({symbol})")

    monkeypatch.setattr(earnings_provider, "_get_json", fake_get_json)
    monkeypatch.setattr(earnings_provider, "_yf_ticker", no_yahoo)
    token = config.set_request_region("IN")
    try:
        response = await earnings_provider.get_upcoming(date(2026, 9, 24), date(2026, 10, 1))
    finally:
        config.reset_request_region(token)

    assert calls == [
        (
            "/api/event-calendar",
            {"index": "equities", "from_date": "24-09-2026", "to_date": "01-10-2026"},
        )
    ]
    assert [(e.symbol, e.scheduled_date) for e in response.events] == [
        ("ESDS.NS", date(2026, 9, 24)),
        ("INFY.NS", date(2026, 9, 26)),
    ]
    infy = response.events[1]
    assert (infy.company_name, infy.currency, infy.provider) == ("Infosys Limited", "INR", "nse")
    assert infy.eps_estimate_mean is None and infy.estimate_analyst_count is None


@pytest.mark.asyncio
async def test_non_in_default_keeps_the_us_universe(monkeypatch: pytest.MonkeyPatch) -> None:
    import config

    asked: list[str] = []

    def recording(symbol: str) -> _FakeEarningsTicker:
        asked.append(symbol)
        return _FakeEarningsTicker(symbol)

    def no_nse(*_args: object) -> object:
        raise AssertionError("the US default must not read the NSE calendar")

    monkeypatch.setattr(earnings_provider, "_yf_ticker", recording)
    monkeypatch.setattr(earnings_provider, "_get_json", no_nse)
    token = config.set_request_region("US")
    try:
        response = await earnings_provider.get_upcoming(date(2026, 5, 19), date(2026, 5, 21))
    finally:
        config.reset_request_region(token)
    assert sorted(asked) == sorted(earnings_provider._DEFAULT_UNIVERSE)
    assert {e.symbol for e in response.events} == set(earnings_provider._DEFAULT_UNIVERSE)
