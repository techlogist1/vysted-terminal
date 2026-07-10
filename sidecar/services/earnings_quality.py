"""Reported-vs-adjusted earnings cross-check (R13 / D70).

The R13 battery's subtlest trap (TI / Tilaknagar Industries): yfinance reports a
PE of ~460 and an ROE of ~1.08% while the world quotes PE ~43.9 / ROE ~13.1% —
and BOTH are "correct". yfinance computes its ratios on the REPORTED net income
(FY26 PAT ~Rs 20.9 Cr), which was crushed by one-off exceptional items (the
Imperial Blue acquisition costs + a Labour Code gratuity charge); the world
quotes them on the ADJUSTED/normalized basis (~Rs 232 Cr). No source is lying —
they are on different bases, and nothing flags the seam. The same shape drives
PML's 0.59x-51x PE spread (a one-off gold-loan-sale GAIN inflating reported
earnings the other way).

D56 (dividend), D66 (growth) and D68 (ownership) taught the app to FLAG, never
silently pick, two sources that disagree. This applies that discipline to the
EARNINGS BASIS. yfinance's annual income statement carries the exact evidence:
``Normalized Income`` (net income excluding unusual items) alongside the reported
``Net Income`` and the ``Total Unusual Items`` line. When the one-off component is
a large fraction of reported net income, every ratio built on the reported basis
(PE / ROE / EPS) is materially off the adjusted basis — so the derived semantics
leg attaches a basis note + a ``definitional_expected`` conflict. It NEVER
replaces a number: reported PE stays reported PE, the adjusted basis is disclosed
beside it.

:func:`get_earnings_quality` is the fetching entry point. It never raises into
the research path: every yfinance failure becomes ``None`` (the caller then
attaches nothing — absence is honest). A detected throttle is reported to the
shared Yahoo-family circuit breaker, mirroring :mod:`services.growth_check`.

Wiring contract (mirrors D66)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The snapshot builder attaches this module's result onto the fundamentals leg's
``data`` dict under :data:`EARNINGS_KEY` — a plain dict
``{reported_net_income, normalized_income, unusual_items, tax_effect,
one_off_net, distortion_fraction, period}`` (currency amounts in the listing
currency, ``distortion_fraction`` a ratio, ``period`` the ISO fiscal year-end).
:func:`services.research.semantics.derive_semantics` reads it and applies the
materiality gate — the threshold lives THERE, next to the other cross-check
tolerances, so this module only measures the distortion.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from typing import Any

import pandas as pd
import yfinance as yf

from services import provider_health

logger = logging.getLogger(__name__)

#: The fundamentals-leg key the snapshot builder attaches this result under, and
#: that :func:`services.research.semantics.derive_semantics` reads.
EARNINGS_KEY = "earnings_quality"

#: Reported-net-income row labels, in preference order (yfinance labels drift
#: across listings; the first present row wins). Same matching discipline as
#: :func:`services.growth_check._row_value`.
_REPORTED_ROWS = (
    "Net Income",
    "Net Income Common Stockholders",
    "Net Income From Continuing Operation Net Minority Interest",
    "Net Income Continuous Operations",
)

#: Normalized (ex-unusual-items) net-income row — yfinance's own adjusted figure.
_NORMALIZED_ROWS = ("Normalized Income",)

#: Unusual/exceptional-items row (pre-tax), the fallback when Normalized Income
#: is absent.
_UNUSUAL_ROWS = ("Total Unusual Items", "Total Unusual Items Excluding Goodwill")

#: The tax impact of the unusual items, to net the pre-tax unusual figure.
_TAX_EFFECT_ROWS = ("Tax Effect Of Unusual Items",)


@dataclass(frozen=True)
class EarningsQuality:
    """One-off-distortion evidence from the latest annual income statement.

    ``reported_net_income`` includes the one-offs; ``normalized_income`` excludes
    them (yfinance's own adjusted figure). ``one_off_net`` is the after-tax
    one-off contribution to reported earnings (``reported - normalized`` when
    normalized is present, else the tax-netted unusual line); its SIGN says the
    direction (negative = charges DEPRESSED reported earnings, so reported PE is
    overstated; positive = gains INFLATED them). ``distortion_fraction`` is
    ``|one_off_net| / |reported|`` — ``None`` when reported earnings were zero or
    the line items were missing (never fabricated). ``period`` is the ISO fiscal
    year-end actually read, carried into the conflict payload as evidence.
    """

    reported_net_income: float | None
    normalized_income: float | None
    unusual_items: float | None
    tax_effect: float | None
    one_off_net: float | None
    distortion_fraction: float | None
    period: str

    def as_wire(self) -> dict[str, Any]:
        """The plain dict attached under :data:`EARNINGS_KEY`."""
        return asdict(self)


def should_cross_check(fund: dict[str, Any]) -> bool:
    """Whether the fundamentals payload carries a ratio the one-off distortion
    would bias.

    True only when the provider actually ships a numeric ``pe_ratio``, ``roe``,
    ``eps`` or ``net_income_ttm`` — the surfaces a reported-vs-adjusted earnings
    gap distorts. Nothing to caveat otherwise, and fetching the income statement
    would spend budget for no comparison.
    """
    return any(
        isinstance(fund.get(key), (int, float)) and not isinstance(fund.get(key), bool)
        for key in ("pe_ratio", "roe", "eps", "net_income_ttm")
    )


def is_applicable(symbol: str) -> bool:
    """True for any non-empty symbol — one-off distortion is universal.

    Unlike the exchange-shareholding cross-check, reported-vs-adjusted earnings
    is not India-specific: US and other listings carry the same yfinance income
    statement rows. The real gate is :func:`should_cross_check` (a ratio to
    caveat) plus the presence of the statement line items.
    """
    return isinstance(symbol, str) and bool(symbol)


def _row_value(frame: pd.DataFrame, labels: tuple[str, ...], column: Any) -> float | None:
    """The first present row's value at ``column``, as float; NaN/missing → None.

    Mirrors :func:`services.growth_check._row_value` (case-insensitive label
    match, duplicate-row tolerant) so the two Yahoo statement readers behave
    identically.
    """
    lowered = {str(label).strip().lower(): label for label in frame.index}
    for candidate in labels:
        actual = lowered.get(candidate.lower())
        if actual is None:
            continue
        value = frame.loc[actual, column]
        if isinstance(value, pd.Series):
            value = value.iloc[0]
        if value is None or pd.isna(value):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def compute_earnings_quality(frame: pd.DataFrame | None) -> EarningsQuality | None:
    """One-off-distortion evidence from an annual income-statement frame.

    The latest annual column is read for reported net income, normalized income,
    unusual items and their tax effect. Pure and synchronous so tests pin the
    arithmetic on fixture frames. Returns ``None`` when the frame is empty, no
    reported-net-income row was present, or NEITHER a normalized-income nor an
    unusual-items line existed to measure a one-off against — absence is honest,
    nothing is interpolated.
    """
    if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
        return None
    try:
        columns = [pd.Timestamp(col) for col in frame.columns]
    except (TypeError, ValueError):
        return None
    latest_ts = max(columns)
    col = frame.columns[columns.index(latest_ts)]

    reported = _row_value(frame, _REPORTED_ROWS, col)
    normalized = _row_value(frame, _NORMALIZED_ROWS, col)
    unusual = _row_value(frame, _UNUSUAL_ROWS, col)
    tax_effect = _row_value(frame, _TAX_EFFECT_ROWS, col)

    # After-tax one-off contribution to reported earnings. Prefer the direct
    # gap against Normalized Income (yfinance's own adjusted figure, already net
    # of tax); fall back to the tax-netted unusual line when it is absent.
    one_off_net: float | None
    if reported is not None and normalized is not None:
        one_off_net = reported - normalized
    elif unusual is not None:
        one_off_net = unusual - (tax_effect or 0.0)
    else:
        one_off_net = None

    distortion: float | None = None
    if one_off_net is not None and reported is not None and reported != 0:
        distortion = abs(one_off_net) / abs(reported)

    if reported is None or (normalized is None and unusual is None):
        return None
    return EarningsQuality(
        reported_net_income=reported,
        normalized_income=normalized,
        unusual_items=unusual,
        tax_effect=tax_effect,
        one_off_net=one_off_net,
        distortion_fraction=distortion,
        period=latest_ts.date().isoformat(),
    )


def _is_rate_limited(exc: BaseException) -> bool:
    """True when ``exc`` (or a chained cause) is a yfinance rate-limit.

    Matched by type NAME — same rationale as
    :func:`services.growth_check._is_rate_limited`: importing
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


def _fetch_income_stmt(symbol: str) -> pd.DataFrame | None:
    """The ANNUAL income statement (BLOCKING; runs under ``to_thread``)."""
    return yf.Ticker(symbol).income_stmt


async def get_earnings_quality(symbol: str) -> EarningsQuality | None:
    """One-off-distortion evidence for ``symbol`` from the annual income statement.

    ``None`` on any failure OR when the statement cannot support the measurement
    — never raises into the research snapshot. ``symbol`` must already be the
    listing the fundamentals leg resolved to (the Yahoo form) so the statement
    reconciles against the SAME ratios.
    """
    if not is_applicable(symbol):
        return None
    if provider_health.is_open():
        return None  # Yahoo circuit open — spend no budget this round (D53)
    try:
        frame = await asyncio.to_thread(_fetch_income_stmt, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_rate_limited(exc):
            provider_health.record_rate_limited()
        else:
            logger.debug("annual income statement unavailable for %s: %s", symbol, exc)
        return None
    provider_health.record_success()
    return compute_earnings_quality(frame)


__all__ = [
    "EARNINGS_KEY",
    "EarningsQuality",
    "compute_earnings_quality",
    "get_earnings_quality",
    "is_applicable",
    "should_cross_check",
]
