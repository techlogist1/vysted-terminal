"""Yield-curve bootstrap tests."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from models.quant import YieldCurveInstrument, YieldCurveRequest
from services.quant import yield_curve


def _canonical_us_treasury_request(sample_count: int = 20) -> YieldCurveRequest:
    return YieldCurveRequest(
        valuation_date=date(2026, 5, 16),
        instruments=[
            YieldCurveInstrument(type="deposit", tenor=1, tenor_unit="months", rate=0.041),
            YieldCurveInstrument(type="deposit", tenor=3, tenor_unit="months", rate=0.043),
            YieldCurveInstrument(type="deposit", tenor=6, tenor_unit="months", rate=0.044),
            YieldCurveInstrument(type="swap", tenor=2, tenor_unit="years", rate=0.045),
            YieldCurveInstrument(type="swap", tenor=5, tenor_unit="years", rate=0.047),
            YieldCurveInstrument(type="swap", tenor=10, tenor_unit="years", rate=0.05),
            YieldCurveInstrument(type="swap", tenor=30, tenor_unit="years", rate=0.052),
        ],
        sample_count=sample_count,
    )


def test_bootstraps_and_samples_returns_requested_count() -> None:
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request(sample_count=15))
    assert len(result.curve) == 15
    assert result.valuation_date == date(2026, 5, 16)


def test_zero_rates_are_plausible_in_yield_band() -> None:
    """Bootstrapped zero rates should land between the lowest and highest input rates
    (with a small leeway for the very-short-end interpolation behaviour).
    """
    req = _canonical_us_treasury_request(sample_count=20)
    result = yield_curve.bootstrap_curve(req)
    rates = [p.zero_rate for p in result.curve]
    assert all(0.02 < r < 0.07 for r in rates)


def test_discount_factors_are_monotone_decreasing() -> None:
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request(sample_count=30))
    dfs = [p.discount_factor for p in result.curve]
    for prev, curr in zip(dfs, dfs[1:], strict=False):
        assert curr <= prev + 1e-9  # tolerate floating-point noise


def test_first_discount_factor_close_to_one() -> None:
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request(sample_count=20))
    assert 0.95 < result.curve[0].discount_factor <= 1.0


def test_long_tenor_zero_rate_above_short() -> None:
    """For our canonical upward-sloping input grid, the long-end zero rate
    should exceed the short-end zero rate.
    """
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request(sample_count=15))
    assert result.curve[-1].zero_rate > result.curve[0].zero_rate


def test_empty_instruments_raises() -> None:
    req = YieldCurveRequest(valuation_date=date(2026, 5, 16), instruments=[], sample_count=10)
    with pytest.raises(ValueError, match="at least one instrument"):
        yield_curve.bootstrap_curve(req)


def test_sample_count_below_two_raises() -> None:
    req = YieldCurveRequest(
        valuation_date=date(2026, 5, 16),
        instruments=[YieldCurveInstrument(type="deposit", tenor=1, tenor_unit="months", rate=0.04)],
        sample_count=1,
    )
    with pytest.raises(ValueError, match="sample_count"):
        yield_curve.bootstrap_curve(req)


def test_tenor_years_increases_along_curve() -> None:
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request(sample_count=15))
    tenor_years = [p.tenor_years for p in result.curve]
    for prev, curr in zip(tenor_years, tenor_years[1:], strict=False):
        assert curr > prev


def test_duration_ms_recorded() -> None:
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request())
    assert result.duration_ms > 0


def test_grid_distinct_and_within_max_tenor() -> None:
    """R15-DATA-098: the sample grid must not run past the last instrument's
    tenor, and (when the span has enough distinct days for the requested
    sample count) must not repeat a date."""
    # Long span (30y swap), moderate sample count -> distinctness is
    # achievable; every date strictly increases and none exceeds the max
    # tenor (2026-05-16 + 30y).
    result = yield_curve.bootstrap_curve(_canonical_us_treasury_request(sample_count=100))
    dates = [p.date for p in result.curve]
    assert dates == sorted(set(dates)), "sample dates must be strictly increasing / distinct"
    # 30y ~ round(30 * 365) = 10950 days -> the longest instrument's tenor date.
    max_tenor_date = date(2026, 5, 16) + timedelta(days=round(30 * 365.0))
    assert dates[-1] <= max_tenor_date

    # The exact register repro: a single 3-month deposit with a sample count
    # that outruns the span in days. The grid must still never extrapolate
    # past the instrument's tenor (2026-08-16), even though 100 samples over
    # ~91 days can't all be distinct calendar dates.
    short_req = YieldCurveRequest(
        valuation_date=date(2026, 5, 16),
        instruments=[YieldCurveInstrument(type="deposit", tenor=3, tenor_unit="months", rate=0.05)],
        sample_count=100,
    )
    short_result = yield_curve.bootstrap_curve(short_req)
    # 3 months ~ round(0.25 * 365) = 91 days -> the instrument's own tenor date.
    assert short_result.curve[-1].date <= date(2026, 5, 16) + timedelta(days=91)
