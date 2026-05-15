"""Tests for ``services.yfinance_provider`` — focus on symbol normalisation.

yfinance returns 502 / "no data" for dot-tickers (``BRK.B``, ``BF.B``,
``RDS.A``) — its API expects the dash form (``BRK-B``). This module's
``_normalize_symbol`` helper translates dots to dashes at every public entry
point so callers can ask for the natural ``BRK.B`` and get a working response.
"""

from __future__ import annotations

import pytest

from services import yfinance_provider


class _RecordingTicker:
    """Capture the symbol every constructed Ticker was passed.

    The tests below patch ``yfinance_provider.yf.Ticker`` with this recorder, so
    the test can assert what the provider actually sent upstream — independent
    of whatever the call returned.
    """

    instances: list[str] = []

    def __init__(self, symbol: str) -> None:
        type(self).instances.append(symbol)
        self.symbol = symbol

    @property
    def fast_info(self) -> object:
        class _Info:
            last_price = 100.0
            previous_close = 99.0
            last_volume = 1_000.0
            currency = "USD"

        return _Info()

    def history(self, period: str, interval: str) -> object:  # noqa: ARG002
        import pandas as pd

        index = pd.to_datetime(["2026-05-14"])
        return pd.DataFrame(
            {
                "Open": [99.0],
                "High": [101.0],
                "Low": [98.0],
                "Close": [100.0],
                "Volume": [1_000.0],
            },
            index=index,
        )

    @property
    def info(self) -> dict:
        return {
            "longName": "Berkshire Hathaway Inc.",
            "sector": "Financial Services",
            "industry": "Insurance—Diversified",
            "marketCap": 1_000_000_000_000,
            "trailingPE": 12.0,
            "forwardPE": 11.0,
            "trailingPegRatio": 1.5,
            "priceToBook": 1.6,
            "dividendYield": 0.0,
            "trailingEps": 30.0,
            "beta": 0.85,
            "fiftyTwoWeekHigh": 500.0,
            "fiftyTwoWeekLow": 380.0,
        }

    @property
    def income_stmt(self) -> object:
        import pandas as pd

        columns = pd.to_datetime(["2025-12-31"])
        return pd.DataFrame({columns[0]: [100.0]}, index=["Total Revenue"])

    balance_sheet = income_stmt
    cashflow = income_stmt

    @property
    def recommendations(self) -> object:
        import pandas as pd

        return pd.DataFrame([{"strongBuy": 1, "buy": 2, "hold": 3, "sell": 0, "strongSell": 0}])

    @property
    def analyst_price_targets(self) -> dict:
        return {"low": 380.0, "high": 600.0, "mean": 500.0}


@pytest.fixture
def recording_ticker(monkeypatch: pytest.MonkeyPatch) -> type[_RecordingTicker]:
    _RecordingTicker.instances = []
    monkeypatch.setattr(yfinance_provider.yf, "Ticker", _RecordingTicker)
    return _RecordingTicker


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("BRK.B", "BRK-B"),
        ("BF.B", "BF-B"),
        ("RDS.A", "RDS-A"),
        ("brk.b", "brk-b"),  # case preservation; yfinance is case-insensitive
        ("AAPL", "AAPL"),  # no-op for symbols without dots
        ("MSFT", "MSFT"),
    ],
)
def test_normalize_symbol(raw: str, expected: str) -> None:
    assert yfinance_provider._normalize_symbol(raw) == expected


def test_get_quote_normalises_dot_ticker(recording_ticker: type[_RecordingTicker]) -> None:
    quote = yfinance_provider.get_quote("BRK.B")
    assert recording_ticker.instances == ["BRK-B"], (
        "yfinance must receive the dash form, not the dot form"
    )
    assert quote.symbol == "BRK-B"
    assert quote.price == 100.0


def test_get_history_normalises_dot_ticker(recording_ticker: type[_RecordingTicker]) -> None:
    series = yfinance_provider.get_history("BRK.B", "1d")
    assert recording_ticker.instances == ["BRK-B"]
    assert series.symbol == "BRK-B"
    assert len(series.bars) == 1


def test_get_fundamentals_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    fundamentals = yfinance_provider.get_fundamentals("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert fundamentals.symbol == "BRK-B"


def test_get_income_statement_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    statement = yfinance_provider.get_income_statement("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert statement.symbol == "BRK-B"


def test_get_balance_sheet_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    sheet = yfinance_provider.get_balance_sheet("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert sheet.symbol == "BRK-B"


def test_get_cash_flow_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    flow = yfinance_provider.get_cash_flow("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert flow.symbol == "BRK-B"


def test_get_analyst_rating_normalises_dot_ticker(
    recording_ticker: type[_RecordingTicker],
) -> None:
    rating = yfinance_provider.get_analyst_rating("BRK.B")
    assert recording_ticker.instances == ["BRK-B"]
    assert rating.symbol == "BRK-B"


def test_aapl_unchanged(recording_ticker: type[_RecordingTicker]) -> None:
    """Sanity: dotless symbols are not transformed."""
    yfinance_provider.get_quote("AAPL")
    assert recording_ticker.instances == ["AAPL"]
