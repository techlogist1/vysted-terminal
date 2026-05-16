"""Yield-curve bootstrapping from depo + swap instruments.

Builds a :class:`ql.PiecewiseLinearZero` curve from a heterogeneous mix of
``DepositRateHelper`` (money-market rates) and ``SwapRateHelper`` (vanilla
interest-rate swaps). Samples the curve at evenly-spaced dates and returns
per-point zero rates + discount factors.

Convention choices for v0.6.0:

* Day-count       — ``Actual365Fixed``.
* Calendar        — ``NullCalendar``.
* Swap-index     — synthetic ``IborIndex`` ("VYSTED-IBOR") at 3-month tenor.
  This is sufficient for retail-side curve inspection — region-specific
  index choices (LIBOR-replacement SOFR / ESTR) are an enhancement we'll
  surface as user-facing options in v0.7+.
* Zero-rate convention — continuously compounded.
"""

from __future__ import annotations

import time
from datetime import date, timedelta

import QuantLib as ql

from models.quant import (
    YieldCurvePoint,
    YieldCurveRequest,
    YieldCurveResult,
)

from ._common import DAY_COUNT, from_ql_date, set_evaluation_date


def _tenor_to_period(tenor: int, unit: str) -> ql.Period:
    """Convert a (tenor, unit) pair to a QuantLib ``Period``."""
    if unit == "months":
        return ql.Period(tenor, ql.Months)
    if unit == "years":
        return ql.Period(tenor, ql.Years)
    raise ValueError(f"unknown tenor unit {unit!r} (expected 'months' or 'years')")


def _tenor_to_years(tenor: int, unit: str) -> float:
    """Approximate the tenor in fractional years (used to size sample grid)."""
    if unit == "months":
        return tenor / 12.0
    return float(tenor)


def bootstrap_curve(req: YieldCurveRequest) -> YieldCurveResult:
    """Bootstrap a zero-rate curve from depo + swap helpers.

    Workflow:

    1. Convert each :class:`YieldCurveInstrument` to a QuantLib rate
       helper (depo or swap).
    2. Build the curve via :class:`ql.PiecewiseLinearZero`.
    3. Sample at ``req.sample_count`` evenly-spaced dates spanning the
       valuation date to the longest tenor.
    """
    started = time.perf_counter()

    if not req.instruments:
        raise ValueError("yield-curve bootstrap requires at least one instrument")
    if req.sample_count < 2:
        raise ValueError("sample_count must be at least 2")

    qd = set_evaluation_date(req.valuation_date)
    calendar = ql.NullCalendar()

    helpers: list[ql.RateHelper] = []
    max_tenor_years = 0.0

    # Build a synthetic IborIndex once and reuse it for all swap helpers.
    ibor = ql.IborIndex(
        "VYSTED-IBOR",
        ql.Period(3, ql.Months),
        2,
        ql.USDCurrency(),
        calendar,
        ql.ModifiedFollowing,
        False,
        DAY_COUNT,
    )

    for inst in req.instruments:
        quote = ql.QuoteHandle(ql.SimpleQuote(inst.rate))
        period = _tenor_to_period(inst.tenor, inst.tenor_unit)
        max_tenor_years = max(max_tenor_years, _tenor_to_years(inst.tenor, inst.tenor_unit))

        if inst.type == "deposit":
            helper = ql.DepositRateHelper(
                quote,
                period,
                2,  # fixing days
                calendar,
                ql.ModifiedFollowing,
                False,
                DAY_COUNT,
            )
        elif inst.type == "swap":
            helper = ql.SwapRateHelper(
                quote,
                period,
                calendar,
                ql.Annual,
                ql.ModifiedFollowing,
                DAY_COUNT,
                ibor,
            )
        else:
            raise ValueError(f"unknown instrument type {inst.type!r}")

        helpers.append(helper)

    curve = ql.PiecewiseLinearZero(qd, helpers, DAY_COUNT)
    curve.enableExtrapolation()

    # Sample the curve. We use a date-based sample grid spanning
    # valuation_date → valuation_date + max_tenor_years to keep the
    # interpolation honest at the long end.
    total_days = max(1, int(round(max_tenor_years * 365.0)))
    step_days = max(1, total_days // (req.sample_count - 1))
    sample_dates: list[date] = []
    for i in range(req.sample_count):
        d = req.valuation_date + timedelta(days=i * step_days)
        sample_dates.append(d)

    points: list[YieldCurvePoint] = []
    for d in sample_dates:
        qld = ql.Date(d.day, d.month, d.year)
        # Skip the valuation date itself — the curve doesn't define a
        # zero rate at t=0. Substitute the shortest-tenor zero rate for
        # the first point so the panel doesn't show a NaN.
        if qld <= qd:
            qld = qd + 1
        zero_rate = curve.zeroRate(qld, DAY_COUNT, ql.Continuous).rate()
        discount = curve.discount(qld)
        tenor_years = DAY_COUNT.yearFraction(qd, qld)
        points.append(
            YieldCurvePoint(
                date=from_ql_date(qld),
                tenor_years=tenor_years,
                zero_rate=zero_rate,
                discount_factor=discount,
            )
        )

    return YieldCurveResult(
        valuation_date=req.valuation_date,
        curve=points,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )


__all__ = ["bootstrap_curve"]
