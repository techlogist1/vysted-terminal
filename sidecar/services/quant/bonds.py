"""Fixed-rate bond pricing — clean / dirty / accrued / duration / convexity.

Built around :class:`ql.FixedRateBond` + :class:`ql.BondFunctions`. Day
count is ``Thirty360`` per the US Treasury convention; compounding is
``Compounded`` and frequency follows the bond's coupon frequency.
The face value sits on the wire (default 1000.0) and is honoured here —
QuantLib's clean / dirty figures are quoted per-100, so we scale by
``face / 100`` so the panel sees dollar-denominated prices.
"""

from __future__ import annotations

import time

import QuantLib as ql

from models.quant import BondPricingRequest, BondPricingResult

from ._common import to_ql_date

_FREQUENCY_MAP: dict[int, int] = {
    1: ql.Annual,
    2: ql.Semiannual,
    4: ql.Quarterly,
}


def price_bond(req: BondPricingRequest) -> BondPricingResult:
    """Price a fixed-rate bond at the given yield-to-maturity.

    The schedule is built from issue → maturity at the requested coupon
    frequency. Day-count is ``Thirty360 (US)``. Compounding is
    ``Compounded`` at the coupon frequency, which is the standard US
    Treasury convention.

    Returns clean / dirty as **dollar amounts** scaled to face value
    (QuantLib quotes per-100 by default; we rescale by ``face / 100`` so
    the panel doesn't have to know the conversion).
    """
    started = time.perf_counter()

    if req.coupons_per_year not in _FREQUENCY_MAP:
        raise ValueError(f"coupons_per_year must be one of 1, 2, 4 — got {req.coupons_per_year}")
    if req.maturity_date <= req.issue_date:
        raise ValueError("maturity_date must be strictly after issue_date")
    if req.settlement_date < req.issue_date or req.settlement_date >= req.maturity_date:
        raise ValueError(
            "settlement_date must be on or after issue_date and strictly before maturity_date"
        )

    ql.Settings.instance().evaluationDate = to_ql_date(req.settlement_date)

    day_count = ql.Thirty360(ql.Thirty360.USA)
    freq = _FREQUENCY_MAP[req.coupons_per_year]
    schedule = ql.Schedule(
        to_ql_date(req.issue_date),
        to_ql_date(req.maturity_date),
        ql.Period(freq),
        ql.NullCalendar(),
        ql.Unadjusted,
        ql.Unadjusted,
        ql.DateGeneration.Backward,
        False,
    )

    bond = ql.FixedRateBond(
        0,  # settlement days — 0 because we set the evaluation date explicitly above
        req.face_value,
        schedule,
        [req.coupon_rate],
        day_count,
    )

    yield_rate = req.yield_to_maturity
    # Per-100 QuantLib quotes, scaled to face.
    scale = req.face_value / 100.0
    clean_pct = bond.cleanPrice(yield_rate, day_count, ql.Compounded, freq)
    dirty_pct = bond.dirtyPrice(yield_rate, day_count, ql.Compounded, freq)
    accrued_pct = bond.accruedAmount()

    clean = clean_pct * scale
    dirty = dirty_pct * scale
    accrued = accrued_pct * scale

    ytm_ir = ql.InterestRate(yield_rate, day_count, ql.Compounded, freq)
    macaulay = ql.BondFunctions.duration(bond, ytm_ir, ql.Duration.Macaulay)
    modified = ql.BondFunctions.duration(bond, ytm_ir, ql.Duration.Modified)
    convexity = ql.BondFunctions.convexity(bond, ytm_ir)

    return BondPricingResult(
        clean_price=clean,
        dirty_price=dirty,
        accrued_interest=accrued,
        duration=macaulay,
        modified_duration=modified,
        convexity=convexity,
        duration_ms=(time.perf_counter() - started) * 1000.0,
    )


__all__ = ["price_bond"]
