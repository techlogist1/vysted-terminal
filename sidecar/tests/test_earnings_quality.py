"""R13 (D70) — ``services.earnings_quality``: the reported-vs-adjusted seam.

The one-off-distortion check that catches the TI trap (yfinance PE ~460 / ROE
~1.08% on REPORTED earnings crushed by exceptional items vs the world's ~43.9 /
~13.1% on the ADJUSTED basis — both correct, no flag). Never hits the network
(``yf.Ticker`` is patched), never raises into the research path (every failure
is ``None``), reports throttles to the shared Yahoo circuit breaker, and only
DISCLOSES — the distortion measure rides beside the provider ratios, never over
them.
"""

from __future__ import annotations

import asyncio

import pandas as pd
import pytest

from services import earnings_quality, provider_health
from services.earnings_quality import (
    EarningsQuality,
    compute_earnings_quality,
    should_cross_check,
)


class YFRateLimitError(Exception):
    """Stand-in matched by TYPE NAME (the module never imports the real one)."""


def _frame(columns: list[str], rows: dict[str, list[float | None]]) -> pd.DataFrame:
    """An annual income-statement frame shaped like yfinance's (rows = line
    labels, columns = fiscal-year-end Timestamps, most recent first)."""
    return pd.DataFrame(
        {
            pd.Timestamp(col): [rows[label][idx] for label in rows]
            for idx, col in enumerate(columns)
        },
        index=list(rows),
    )


class _FakeTicker:
    def __init__(self, frame: pd.DataFrame | None) -> None:
        self._frame = frame

    @property
    def income_stmt(self) -> pd.DataFrame | None:
        return self._frame


def _patch_ticker(monkeypatch: pytest.MonkeyPatch, frame_or_exc: object) -> None:
    def factory(symbol: str) -> _FakeTicker:  # noqa: ARG001
        if isinstance(frame_or_exc, BaseException):
            raise frame_or_exc
        return _FakeTicker(frame_or_exc)  # type: ignore[arg-type]

    monkeypatch.setattr(earnings_quality.yf, "Ticker", factory)


@pytest.fixture(autouse=True)
def _reset_health() -> None:
    provider_health.reset_for_tests()


# --- compute_earnings_quality: the pinned arithmetic ----------------------------


def test_ti_shape_measures_large_distortion() -> None:
    # TI FY26: reported PAT ₹20.87 Cr (2.087e8), adjusted/normalized ~₹232 Cr
    # (2.32e9) — one-off CHARGES depress reported earnings by ~₹211 Cr, a >10x
    # distortion. The measure is |one_off| / |reported|.
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {
            "Total Revenue": [3.5e10, 3.0e10],
            "Net Income": [2.087e8, 2.0e9],
            "Normalized Income": [2.32e9, 2.05e9],
            "Total Unusual Items": [-2.11e9, -5.0e7],
        },
    )
    eq = compute_earnings_quality(frame)
    assert eq is not None
    assert eq.reported_net_income == pytest.approx(2.087e8)
    assert eq.normalized_income == pytest.approx(2.32e9)
    assert eq.one_off_net == pytest.approx(2.087e8 - 2.32e9)  # negative → charges
    assert eq.one_off_net < 0
    assert eq.distortion_fraction == pytest.approx(abs(2.087e8 - 2.32e9) / 2.087e8)
    assert eq.distortion_fraction > 1.0
    assert eq.period == "2026-03-31"


def test_clean_earnings_measure_is_near_zero() -> None:
    # Normalized ≈ reported → the one-off component is a rounding wisp.
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {
            "Net Income": [1.00e9, 9.0e8],
            "Normalized Income": [9.8e8, 8.9e8],
            "Total Unusual Items": [2.0e7, 1.0e7],
        },
    )
    eq = compute_earnings_quality(frame)
    assert eq is not None
    assert eq.distortion_fraction == pytest.approx(0.02)


def test_unusual_items_path_when_normalized_absent() -> None:
    # No Normalized Income row → fall back to the tax-netted unusual line.
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {
            "Net Income": [1.0e8, 5.0e8],
            "Total Unusual Items": [-6.0e8, 0.0],
            "Tax Effect Of Unusual Items": [-1.0e8, 0.0],
        },
    )
    eq = compute_earnings_quality(frame)
    assert eq is not None
    assert eq.normalized_income is None
    # net one-off = unusual - tax_effect = -6e8 - (-1e8) = -5e8
    assert eq.one_off_net == pytest.approx(-5.0e8)
    assert eq.distortion_fraction == pytest.approx(5.0e8 / 1.0e8)


def test_no_reported_row_is_none() -> None:
    frame = _frame(["2026-03-31"], {"Total Revenue": [1.0e9]})
    assert compute_earnings_quality(frame) is None


def test_no_one_off_lines_is_none() -> None:
    # A reported figure but neither Normalized Income nor Unusual Items → nothing
    # to measure a one-off against; absence is honest.
    frame = _frame(["2026-03-31"], {"Net Income": [1.0e9]})
    assert compute_earnings_quality(frame) is None


def test_zero_reported_yields_no_distortion_fraction() -> None:
    frame = _frame(
        ["2026-03-31"],
        {"Net Income": [0.0], "Normalized Income": [5.0e8]},
    )
    eq = compute_earnings_quality(frame)
    assert eq is not None
    assert eq.distortion_fraction is None  # cannot form a ratio on zero reported


def test_empty_or_none_frame_is_none() -> None:
    assert compute_earnings_quality(None) is None
    assert compute_earnings_quality(pd.DataFrame()) is None


def test_latest_column_is_read_regardless_of_order() -> None:
    # Columns out of order — the most-recent fiscal year still wins.
    frame = _frame(
        ["2024-03-31", "2026-03-31", "2025-03-31"],
        {
            "Net Income": [1.0e9, 2.087e8, 1.5e9],
            "Normalized Income": [1.0e9, 2.32e9, 1.5e9],
        },
    )
    eq = compute_earnings_quality(frame)
    assert eq is not None
    assert eq.period == "2026-03-31"
    assert eq.reported_net_income == pytest.approx(2.087e8)


# --- should_cross_check: the applicability gate ---------------------------------


def test_gate_requires_a_ratio_to_caveat() -> None:
    assert should_cross_check({"pe_ratio": 460.0}) is True
    assert should_cross_check({"roe": 0.0108}) is True
    assert should_cross_check({"eps": 0.5}) is True
    assert should_cross_check({"net_income_ttm": 2.0e8}) is True
    assert should_cross_check({}) is False
    assert should_cross_check({"pe_ratio": None, "roe": None}) is False
    assert should_cross_check({"pe_ratio": True}) is False


def test_is_applicable_is_universal_for_nonempty_symbols() -> None:
    assert earnings_quality.is_applicable("TI.NS")
    assert earnings_quality.is_applicable("AAPL")
    assert not earnings_quality.is_applicable("")


# --- get_earnings_quality: the fetching wrapper ---------------------------------


def test_fetch_computes_from_patched_statements(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame(
        ["2026-03-31", "2025-03-31"],
        {"Net Income": [2.087e8, 2.0e9], "Normalized Income": [2.32e9, 2.05e9]},
    )
    _patch_ticker(monkeypatch, frame)
    eq = asyncio.run(earnings_quality.get_earnings_quality("TI.NS"))
    assert isinstance(eq, EarningsQuality)
    assert eq.distortion_fraction is not None and eq.distortion_fraction > 1.0
    assert eq.as_wire()["period"] == "2026-03-31"


def test_rate_limit_records_breaker_and_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_ticker(monkeypatch, YFRateLimitError("Too Many Requests"))
    assert asyncio.run(earnings_quality.get_earnings_quality("THROTTLED.NS")) is None
    assert provider_health.status()["throttles_total"] == pytest.approx(1.0)


def test_generic_failure_returns_none_without_recording_a_throttle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_ticker(monkeypatch, RuntimeError("socket reset"))
    assert asyncio.run(earnings_quality.get_earnings_quality("BROKEN.NS")) is None
    assert provider_health.status()["throttles_total"] == pytest.approx(0.0)


def test_open_circuit_skips_the_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    provider_health.record_rate_limited(weight=5)
    assert provider_health.is_open()

    def explode(symbol: str) -> _FakeTicker:  # noqa: ARG001
        raise AssertionError("open circuit must skip the yfinance fetch")

    monkeypatch.setattr(earnings_quality.yf, "Ticker", explode)
    assert asyncio.run(earnings_quality.get_earnings_quality("TI.NS")) is None


def test_empty_symbol_is_rejected_without_touching_yfinance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode(symbol: str) -> _FakeTicker:  # noqa: ARG001
        raise AssertionError("yfinance must not be touched for an empty symbol")

    monkeypatch.setattr(earnings_quality.yf, "Ticker", explode)
    assert asyncio.run(earnings_quality.get_earnings_quality("")) is None
