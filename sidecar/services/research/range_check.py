"""52-week range cross-check against the app's own exchange-direct history
(R13 / D71).

The R13 battery found the provider's 52-week high/low pair can be plainly WRONG
while the correct series is already in the app: BI (Bilcare) shows a provider 52w
high near 75 vs a real ~116; PML shows 645/451 vs the real 823/407. The chart
panel renders the RIGHT series — it pulls exchange-direct EOD history through
:func:`services.provider_registry.get_history` (the nse_direct → jugaad → bse
lane) — so the brief can recompute the 52-week high/low from that same series and
flag a provider pair that disagrees.

D56/D66/D68 taught the app to FLAG, never silently pick, two sources that
disagree; this applies that discipline to the 52-WEEK RANGE. The cross-check
DISCLOSES, never substitutes: the provider ``fifty_two_week_high`` /
``fifty_two_week_low`` are left untouched everywhere; a divergence surfaces as
separately-labeled facts + a conflict in the derived semantics leg
(:func:`services.research.semantics.derive_semantics`).

:func:`get_52w_range` is the fetching entry point. It never raises into the
research path: every provider failure becomes ``None`` (the caller then attaches
nothing — absence is honest). It is APPLICABILITY-GATED twice: only for NSE/BSE
listings (the exchange-direct lane exists only there), and only when the returned
series actually spans ~52 weeks (a thin/cold cache that covers a few weeks cannot
witness a 52-week range, so it stays silent rather than emit a false low high).

Wiring contract (mirrors D66)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The snapshot builder attaches this module's result onto the fundamentals leg's
``data`` dict under :data:`RANGE_KEY` — a plain dict
``{high, low, coverage_days, bars, source}``. ``derive_semantics`` reads it
alongside the provider's ``fifty_two_week_high`` / ``fifty_two_week_low`` and
applies the divergence tolerance (which lives THERE, next to the other
cross-check tolerances).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from services import locale, provider_health, symbol_resolver

logger = logging.getLogger(__name__)

#: The provider-health FAMILY for the exchange-direct HISTORY lane. Distinct from
#: the ``exchange`` shareholding family (a different endpoint / block semantics)
#: and from the Yahoo family — a throttle on one exchange endpoint must not open
#: the others' circuits.
EXCHANGE_HISTORY = "exchange_history"

#: The fundamentals-leg key the snapshot builder attaches this result under, and
#: that :func:`services.research.semantics.derive_semantics` reads.
RANGE_KEY = "range_52w_exchange"

#: The 52-week window in calendar days (the reduction is taken over bars within
#: this trailing window of the latest bar).
_WINDOW_DAYS = 365

#: Coverage floors: the windowed series must span at least this many calendar
#: days AND carry at least this many bars to honestly witness a "52-week" range.
#: ~300 days (≈ 43 weeks) tolerates a young listing / holiday gaps while still
#: covering most of the year; 180 trading bars is ~9 months of sessions. A
#: thinner series (a cold BSE cache, a fresh IPO) returns ``None`` — absence is
#: honest, never a low high computed from three weeks of data.
_COVERAGE_MIN_DAYS = 300
_COVERAGE_MIN_BARS = 180


@dataclass(frozen=True)
class Range52w:
    """The 52-week high/low recomputed from the app's exchange-direct history.

    ``high``/``low`` are the max intraday high / min intraday low over the
    trailing 52-week window; ``coverage_days`` and ``bars`` back the
    applicability gate and are carried as evidence; ``source`` is the provider
    lane that actually served the series (``nse_direct`` / ``nse`` / ``bse`` /
    ``yfinance``), so a disagreement names which exchange series it came from.
    """

    high: float
    low: float
    coverage_days: int
    bars: int
    source: str

    def as_wire(self) -> dict[str, Any]:
        """The plain dict attached under :data:`RANGE_KEY`."""
        return asdict(self)


def should_cross_check(fund: dict[str, Any]) -> bool:
    """Whether the fundamentals payload carries a 52-week bound to reconcile.

    True only when the provider actually ships a numeric ``fifty_two_week_high``
    or ``fifty_two_week_low`` — there is nothing to cross-check otherwise, and
    fetching a year of history would spend budget for no comparison.
    """
    return any(
        isinstance(fund.get(key), (int, float)) and not isinstance(fund.get(key), bool)
        for key in ("fifty_two_week_high", "fifty_two_week_low")
    )


def is_applicable(symbol: str) -> bool:
    """True when ``symbol`` is an Indian exchange listing (NSE or BSE).

    The exchange-direct history lane exists only for NSE/BSE names; a US/other
    listing routes to the same provider the 52-week scalar came from, so
    recomputing from it would not be an independent witness.
    """
    if not isinstance(symbol, str) or not symbol:
        return False
    bare = locale.strip_exchange_suffix(symbol.strip().upper())
    return symbol_resolver.is_nse_symbol(bare) or symbol_resolver.is_bse_symbol(bare)


def _bar_timestamp(bar: Any) -> datetime | None:
    """The bar's timestamp as an aware UTC datetime, or ``None`` if unusable."""
    ts = getattr(bar, "timestamp", None)
    if not isinstance(ts, datetime):
        return None
    return ts if ts.tzinfo is not None else ts.replace(tzinfo=UTC)


def compute_range(bars: list[Any] | None, source: str) -> Range52w | None:
    """The trailing-52-week high/low from an ascending OHLCV bar list.

    Pure and synchronous so tests pin the reduction on fixture bars. The window
    is the 365 days ending at the LATEST bar; the reduction is
    ``max(b.high)`` / ``min(b.low)`` over the windowed bars. Returns ``None``
    when there are no bars, or the windowed series fails the coverage floors
    (:data:`_COVERAGE_MIN_DAYS` / :data:`_COVERAGE_MIN_BARS`) — a series too thin
    to witness a full year cannot honestly emit a 52-week range.
    """
    if not bars:
        return None
    stamped = [(ts, bar) for bar in bars if (ts := _bar_timestamp(bar)) is not None]
    if not stamped:
        return None
    latest = max(ts for ts, _ in stamped)
    window_start = latest - timedelta(days=_WINDOW_DAYS)
    windowed = [bar for ts, bar in stamped if ts >= window_start]
    windowed_ts = [ts for ts, _ in stamped if ts >= window_start]
    if not windowed:
        return None
    coverage_days = (latest - min(windowed_ts)).days
    if coverage_days < _COVERAGE_MIN_DAYS or len(windowed) < _COVERAGE_MIN_BARS:
        return None
    highs = [float(b.high) for b in windowed if b.high is not None]
    lows = [float(b.low) for b in windowed if b.low is not None]
    if not highs or not lows:
        return None
    return Range52w(
        high=max(highs),
        low=min(lows),
        coverage_days=coverage_days,
        bars=len(windowed),
        source=source,
    )


def _is_blocked(exc: BaseException) -> bool:
    """True when ``exc`` looks like an exchange block/throttle (vs a plain miss)."""
    text = str(exc).lower()
    return "blocked" in text or any(code in text for code in ("http 401", "http 403", "http 429"))


def _fetch_history(symbol: str) -> Any:
    """A year of daily exchange-direct history (BLOCKING; runs under
    ``to_thread``). The SAME lane the chart panel uses —
    :func:`services.provider_registry.get_history` — so the witness reconciles
    against exactly what the user sees rendered."""
    from services import provider_registry

    return provider_registry.get_history(symbol, "1d", "1y", "equity")


async def get_52w_range(symbol: str) -> Range52w | None:
    """The 52-week high/low recomputed from the app's exchange-direct history.

    ``None`` when the listing is not an Indian exchange name, the exchange-history
    circuit is open, the series is unreachable, or the returned series does not
    span ~52 weeks — never raises into the research snapshot. ``symbol`` should be
    the listing the fundamentals leg resolved to (its exchange suffix is stripped
    internally by the provider lane).
    """
    if not is_applicable(symbol):
        return None
    if provider_health.is_open(EXCHANGE_HISTORY):
        return None  # circuit open — serve no exchange history this round (D52)
    try:
        series = await asyncio.to_thread(_fetch_history, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_blocked(exc):
            provider_health.record_rate_limited(EXCHANGE_HISTORY)
        else:
            logger.debug("exchange history unavailable for %s: %s", symbol, exc)
        return None
    provider_health.record_success(EXCHANGE_HISTORY)
    bars = getattr(series, "bars", None)
    source = getattr(series, "provider", None) or "exchange"
    return compute_range(bars, source)


__all__ = [
    "EXCHANGE_HISTORY",
    "RANGE_KEY",
    "Range52w",
    "compute_range",
    "get_52w_range",
    "is_applicable",
    "should_cross_check",
]
