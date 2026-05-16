"""Yield-curve bootstrap tests."""

from __future__ import annotations

from datetime import date

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
