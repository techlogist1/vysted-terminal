"""Shared QuantLib helpers for the Phase 6 pricing modules.

Centralises the "build a Black-Scholes-Merton process from request inputs"
machinery so the option / Greeks / MC modules don't each re-derive the
``Date``/``YieldTermStructureHandle``/``BlackVolTermStructureHandle`` plumbing.

Day count convention: ``Actual365Fixed`` (matches v0.6.0 plan).
Calendar:             ``NullCalendar`` (region-specific calendars deferred to v0.7+).
"""

from __future__ import annotations

from datetime import date

import QuantLib as ql

#: Single QuantLib day-counter used by every option pricing path.
DAY_COUNT = ql.Actual365Fixed()

#: Single QuantLib calendar used by every option pricing path.
CALENDAR = ql.NullCalendar()


def to_ql_date(d: date) -> ql.Date:
    """Convert a Python ``date`` to a QuantLib ``Date``."""
    return ql.Date(d.day, d.month, d.year)


def from_ql_date(d: ql.Date) -> date:
    """Convert a QuantLib ``Date`` back to a Python ``date``."""
    return date(d.year(), d.month(), d.dayOfMonth())


def set_evaluation_date(valuation_date: date) -> ql.Date:
    """Pin the QuantLib global evaluation date.

    Returns the QL date so the caller can reuse it without re-converting.
    """
    qd = to_ql_date(valuation_date)
    ql.Settings.instance().evaluationDate = qd
    return qd


def build_bsm_process(
    spot: float,
    risk_free_rate: float,
    dividend_yield: float,
    volatility: float,
    valuation_date: date,
) -> ql.BlackScholesMertonProcess:
    """Build a Black-Scholes-Merton process from primitive inputs.

    The four term structures are all flat (constant rate / vol) — the
    Pydantic request surface deliberately keeps the wire minimal in
    v0.6.0; surface curves are a v0.7+ enhancement.
    """
    qd = set_evaluation_date(valuation_date)
    spot_handle = ql.QuoteHandle(ql.SimpleQuote(spot))
    r_handle = ql.YieldTermStructureHandle(ql.FlatForward(qd, risk_free_rate, DAY_COUNT))
    q_handle = ql.YieldTermStructureHandle(ql.FlatForward(qd, dividend_yield, DAY_COUNT))
    vol_handle = ql.BlackVolTermStructureHandle(
        ql.BlackConstantVol(qd, CALENDAR, volatility, DAY_COUNT)
    )
    return ql.BlackScholesMertonProcess(spot_handle, q_handle, r_handle, vol_handle)


def ql_option_type(payoff: str) -> int:
    """Translate the wire payoff string to a QuantLib option-type enum."""
    if payoff == "call":
        return ql.Option.Call
    if payoff == "put":
        return ql.Option.Put
    raise ValueError(f"unknown payoff {payoff!r} (expected 'call' or 'put')")


__all__ = [
    "CALENDAR",
    "DAY_COUNT",
    "build_bsm_process",
    "from_ql_date",
    "ql_option_type",
    "set_evaluation_date",
    "to_ql_date",
]
