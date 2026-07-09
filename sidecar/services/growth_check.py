"""Quarterly-YoY growth cross-check (R12 / D66).

Yahoo's ``revenueGrowth``/``earningsGrowth`` (the source of
``Fundamentals.revenue_growth``/``earnings_growth``, honestly labeled
``growth_basis: mrq_yoy`` since D55) are opaque scalars that can be materially
WRONG on their own claimed basis — an R12 ten-stock battery measured ICICIBANK
at +66.9% provider vs +2.0/+2.5% computed from the exchange statements, SBIN
earnings at -3.1% vs +5.6% (a sign flip), and RADICO off on both legs. The
QUARTERLY income statements are the more primary source and cannot restate a
scalar silently, so recomputing MRQ-vs-same-quarter-prior-year from them gives
a deterministic consistency check — the exact D56 pattern (dividendRate vs the
paid corporate-action history), applied to growth.

:func:`get_quarterly_yoy` is the fetching entry point. It never raises into the
research path: every yfinance failure becomes ``None`` (the caller then simply
attaches no computed figure — absence is honest). A detected throttle is
reported to the shared Yahoo-family circuit breaker, mirroring
:mod:`services.dividend_history`. The cross-check DISCLOSES, never substitutes:
the provider values are left untouched everywhere; a divergence surfaces as a
conflict in the derived semantics leg (:mod:`services.research.semantics`).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf

from services import provider_health

logger = logging.getLogger(__name__)

#: Income-statement row labels accepted for the revenue leg, in preference
#: order (yfinance labels drift across listings; the first present row wins).
_REVENUE_ROWS = ("Total Revenue", "Operating Revenue")

#: Row labels accepted for the net-profit leg, in preference order.
_EARNINGS_ROWS = ("Net Income", "Net Income Common Stockholders")

#: The prior-year quarter is the column closest to 365 days before the MRQ,
#: within this window. Neighbouring quarters sit ~91 days off the 365-day mark,
#: so ±45 days identifies the same fiscal quarter uniquely while tolerating
#: quarter-end drift (Feb 28/29, fiscal-calendar shifts).
_PRIOR_YEAR_WINDOW_DAYS = 45


@dataclass(frozen=True)
class QuarterlyYoY:
    """MRQ-vs-same-quarter-prior-year growth computed from quarterly statements.

    Per-metric ``None`` when that line was missing/NaN in either quarter or the
    prior-year base was zero — never fabricated. ``mrq``/``prior`` are the ISO
    quarter-end dates actually compared, carried into the conflict payload so a
    disagreement names its evidence.
    """

    revenue_growth: float | None
    earnings_growth: float | None
    mrq: str
    prior: str


def should_cross_check(fund: dict[str, Any]) -> bool:
    """Whether the fundamentals payload warrants the quarterly cross-check.

    True only when the provider actually carries a numeric growth scalar to
    reconcile AND its claimed basis is MRQ-YoY (``growth_basis`` absent means
    the D55 default, which is ``mrq_yoy``). A provider on a different basis is
    never compared against quarterly YoY — that would manufacture false
    conflicts out of a basis mismatch.
    """
    basis = fund.get("growth_basis")
    if basis is not None and basis != "mrq_yoy":
        return False
    return any(
        isinstance(fund.get(key), (int, float)) and not isinstance(fund.get(key), bool)
        for key in ("revenue_growth", "earnings_growth")
    )


def _row_value(frame: pd.DataFrame, labels: tuple[str, ...], column: Any) -> float | None:
    """The first present row's value at ``column``, as float; NaN/missing → None."""
    lowered = {str(label).strip().lower(): label for label in frame.index}
    for candidate in labels:
        actual = lowered.get(candidate.lower())
        if actual is None:
            continue
        value = frame.loc[actual, column]
        # Duplicate row labels make .loc return a Series — take the first.
        if isinstance(value, pd.Series):
            value = value.iloc[0]
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def _yoy(current: float | None, prior: float | None) -> float | None:
    """Sign-aware YoY fraction ``(current - prior) / |prior|``; None when
    either leg is missing or the base is zero (never a division blow-up)."""
    if current is None or prior is None or prior == 0:
        return None
    return (current - prior) / abs(prior)


def compute_quarterly_yoy(frame: pd.DataFrame | None) -> QuarterlyYoY | None:
    """Deterministic MRQ-YoY growth from a quarterly income-statement frame.

    The MRQ is the LATEST quarter column; the base is the column closest to 365
    days earlier (within :data:`_PRIOR_YEAR_WINDOW_DAYS`). Pure and synchronous
    so tests pin the arithmetic on fixture frames. Returns ``None`` when the
    frame is empty, the prior-year quarter is absent (e.g. only four quarters
    served), or neither metric could be computed — absence is honest, nothing
    is interpolated from mismatched quarters.
    """
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    try:
        columns = [pd.Timestamp(col) for col in frame.columns]
    except (TypeError, ValueError):
        return None
    mrq_ts = max(columns)
    mrq_col = frame.columns[columns.index(mrq_ts)]

    prior_col = None
    best_off = _PRIOR_YEAR_WINDOW_DAYS + 1
    for ts, col in zip(columns, frame.columns, strict=True):
        offset = abs((mrq_ts - ts).days - 365)
        if offset < best_off:
            best_off = offset
            prior_col = col
    if prior_col is None:
        return None

    revenue = _yoy(
        _row_value(frame, _REVENUE_ROWS, mrq_col),
        _row_value(frame, _REVENUE_ROWS, prior_col),
    )
    earnings = _yoy(
        _row_value(frame, _EARNINGS_ROWS, mrq_col),
        _row_value(frame, _EARNINGS_ROWS, prior_col),
    )
    if revenue is None and earnings is None:
        return None
    return QuarterlyYoY(
        revenue_growth=revenue,
        earnings_growth=earnings,
        mrq=mrq_ts.date().isoformat(),
        prior=pd.Timestamp(prior_col).date().isoformat(),
    )


def _is_rate_limited(exc: BaseException) -> bool:
    """True when ``exc`` (or a chained cause) is a yfinance rate-limit.

    Matched by type NAME — same rationale as
    ``services.dividend_history._is_rate_limited``: importing
    ``yfinance.exceptions`` would couple this module to a drifting submodule.
    """
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        name = type(cur).__name__
        if name == "YFRateLimitError" or "ratelimit" in name.lower():
            return True
        cur = cur.__cause__ or cur.__context__
    return False


def _fetch_quarterly_income(symbol: str) -> pd.DataFrame | None:
    """The quarterly income statement (BLOCKING; runs under ``to_thread``)."""
    return yf.Ticker(symbol).quarterly_income_stmt


async def get_quarterly_yoy(symbol: str) -> QuarterlyYoY | None:
    """MRQ-YoY revenue/net-profit growth computed from quarterly statements.

    ``None`` on any failure OR when the statements cannot support the
    computation — never raises into the research snapshot. ``symbol`` must
    already be the listing the fundamentals leg resolved to (the Yahoo form)
    so the statements reconcile against the SAME growth scalars.
    """
    if not isinstance(symbol, str) or not symbol:
        return None
    try:
        frame = await asyncio.to_thread(_fetch_quarterly_income, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_rate_limited(exc):
            provider_health.record_rate_limited()
        else:
            logger.debug("quarterly income statement unavailable for %s: %s", symbol, exc)
        return None
    provider_health.record_success()
    return compute_quarterly_yoy(frame)


__all__ = ["QuarterlyYoY", "compute_quarterly_yoy", "get_quarterly_yoy", "should_cross_check"]
