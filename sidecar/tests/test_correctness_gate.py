"""Pass B (B1) — the correctness gate (FR-063): reject wrong/empty/mismatched data."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from models.market import OHLCVBar, OHLCVSeries, Quote
from services import correctness_gate
from services.correctness_gate import CorrectnessError


def _quote(symbol: str, price: float, *, days_old: int = 0) -> Quote:
    return Quote(
        symbol=symbol,
        price=price,
        change=0.0,
        change_percent=0.0,
        currency="INR",
        timestamp=datetime.now(tz=UTC) - timedelta(days=days_old),
        provider="nse",
    )


def _series(symbol: str, last_close: float, n: int = 3) -> OHLCVSeries:
    bars = [
        OHLCVBar(
            timestamp=datetime.now(tz=UTC) - timedelta(days=n - i),
            open=last_close,
            high=last_close,
            low=last_close,
            close=last_close,
            volume=1000.0,
        )
        for i in range(n)
    ]
    return OHLCVSeries(symbol=symbol, timeframe="1d", bars=bars, provider="nse")


def test_symbols_match_normalises_suffix_and_dash() -> None:
    assert correctness_gate.symbols_match("GOLDBEES", "GOLDBEES.NS")
    assert correctness_gate.symbols_match("GOLDBEES", "GOLDBEES-NS")  # yfinance dash form
    assert correctness_gate.symbols_match("BRK.B", "BRK-B")
    assert correctness_gate.symbols_match("aapl", "AAPL")
    assert not correctness_gate.symbols_match("AAPL", "MSFT")
    assert not correctness_gate.symbols_match("CNS", "C")  # does not over-strip "NS"


def test_validate_quote_accepts_good() -> None:
    q = _quote("GOLDBEES", 128.5)
    assert correctness_gate.validate_quote(q, "GOLDBEES", "IN") is q
    # Matches across the .NS form the resolver may have requested.
    assert correctness_gate.validate_quote(q, "GOLDBEES.NS", "IN") is q


def test_validate_quote_rejects_non_positive() -> None:
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("GOLDBEES", 0.0), "GOLDBEES", "IN")
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("GOLDBEES", -5.0), "GOLDBEES", "IN")


def test_validate_quote_rejects_symbol_mismatch() -> None:
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("WRONG", 100.0), "GOLDBEES", "IN")


def test_validate_quote_rejects_broken_feed_staleness() -> None:
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_quote(_quote("GOLDBEES", 100.0, days_old=40), "GOLDBEES", "IN")


def test_validate_series_rejects_empty_and_mismatch() -> None:
    empty = OHLCVSeries(symbol="GOLDBEES", timeframe="1d", bars=[], provider="nse")
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_series(empty, "GOLDBEES", "IN")
    with pytest.raises(CorrectnessError):
        correctness_gate.validate_series(_series("WRONG", 100.0), "GOLDBEES", "IN")


def test_validate_series_accepts_old_but_valid() -> None:
    # Staleness is a label on a series, not a rejection — an old-but-valid series passes.
    old = _series("GOLDBEES", 100.0)
    old.bars[-1] = OHLCVBar(
        timestamp=datetime(2024, 1, 2, tzinfo=UTC),
        open=100,
        high=100,
        low=100,
        close=100,
        volume=1,
    )
    assert correctness_gate.validate_series(old, "GOLDBEES", "IN") is old
