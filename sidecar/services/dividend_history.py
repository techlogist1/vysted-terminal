"""Trailing-12-month dividend cross-check (R11 / D56).

Yahoo's ``dividendRate`` (the source of ``Fundamentals.dividend_per_share``) is
a single opaque scalar that can OMIT a special dividend — ABBOTINDIA reported
Rs 525 (final only) against a true Rs 656 (525 final + 131 special). The
corporate-action history cannot omit a payment, so summing the trailing-12-month
dividends actually paid gives a deterministic completeness check the arithmetic
unit-reconciliation in :mod:`services.research.semantics` cannot.

:func:`get_dividend_ttm` is the ONLY entry point. It returns a
:class:`DividendTTM` carrying the null-vs-AFFIRMED-ZERO distinction (a company
with real history depth that paid nothing in the trailing window affirms ``0.0``,
never an unknown null). It never raises into the research path: every yfinance
failure becomes an ``"unavailable"`` result (the caller then emits no paid figure,
only an honest reason). A detected throttle is reported to the shared
Yahoo-family circuit breaker so a dividend-history 429 backs the same cooldown
as a quote/``.info`` 429 (one IP reputation, one breaker) — a healthy
round-trip resets it.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

from services import provider_health

logger = logging.getLogger(__name__)

#: Trailing window summed for the "actually paid" figure — twelve months back
#: from now, matching Yahoo's own "trailing annual dividend rate" horizon so the
#: two are like-for-like (a divergence is then a COMPLETENESS gap, not a window
#: mismatch).
_TRAILING_DAYS = 365

#: The label carried on an AFFIRMED trailing-12m zero (a company with real
#: dividend-history depth that paid nothing in the window) — distinct from an
#: unknown null so a consumer can state "0.00% (nothing paid)" as a fact.
AFFIRMED_ZERO_LABEL = "no dividends paid (trailing 12m)"
#: The reason carried when history depth is INSUFFICIENT to affirm a zero (the
#: dividends series is empty / does not reach back a full year), so the field
#: stays null rather than a fabricated affirmed zero.
INSUFFICIENT_DEPTH_REASON = "insufficient dividend-history depth to affirm a trailing-12m zero"
#: The reason carried when the history round-trip itself failed (throttle / error).
UNAVAILABLE_REASON = "dividend history unavailable"


@dataclass(frozen=True)
class DividendTTM:
    """The trailing-12m PAID result, carrying the null-vs-affirmed-zero distinction.

    ``status`` is one of:
      * ``"paid"`` — ``value`` is the (>0) sum of dividends paid in the window.
      * ``"affirmed_zero"`` — the series has real depth (≥12 months) and paid
        NOTHING in the trailing window: ``value`` is ``0.0`` and ``reason`` is
        :data:`AFFIRMED_ZERO_LABEL`. An honest, stateable zero — not a null.
      * ``"unavailable"`` — no value AND no depth to affirm a zero (empty history,
        a throttle, or a fetch error): ``value`` is ``None`` and ``reason`` says why.
    """

    value: float | None
    status: str
    reason: str | None = None

    @property
    def is_affirmed_zero(self) -> bool:
        return self.status == "affirmed_zero"


def _is_rate_limited(exc: BaseException) -> bool:
    """True when ``exc`` (or a chained cause) is a yfinance rate-limit.

    Matched by type NAME (``YFRateLimitError``) so the module never imports
    ``yfinance.exceptions`` — that submodule drifts across yfinance releases and
    a hard import would make this module un-importable on an older/newer pin.
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


def _sum_trailing_dividends(symbol: str) -> DividendTTM:
    """Sum per-share dividends paid in the trailing 12 months (BLOCKING).

    Distinguishes an AFFIRMED trailing-12m zero (the series has real depth — at
    least one dividend older than the window — but paid nothing inside it) from an
    UNAVAILABLE null (empty series / no depth to affirm anything). Runs under
    :func:`asyncio.to_thread`; may raise on a network/throttle failure, which the
    async wrapper classifies and swallows.
    """
    series = yf.Ticker(symbol).dividends
    if series is None or len(series) == 0:
        # No history at all — cannot affirm a zero (never paid vs data missing are
        # indistinguishable from an empty series alone).
        return DividendTTM(None, "unavailable", INSUFFICIENT_DEPTH_REASON)
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=_TRAILING_DAYS)
    total = 0.0
    found_in_window = False
    has_depth = False  # a real dividend OLDER than the window → ≥12 months covered
    for raw_ts, amount in series.items():
        ts = pd.Timestamp(raw_ts)
        # yfinance indexes dividends in the exchange timezone (tz-aware for most
        # listings, occasionally tz-naive) — normalise to UTC either way so the
        # window comparison never raises on a tz mismatch.
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        if amount is None or pd.isna(amount):
            continue
        if ts < cutoff:
            has_depth = True
            continue
        total += float(amount)
        found_in_window = True
    if found_in_window:
        return DividendTTM(total, "paid")
    if has_depth:
        # Real depth (≥12 months of history) with nothing paid in the window — an
        # honest, stateable zero, not a null.
        return DividendTTM(0.0, "affirmed_zero", AFFIRMED_ZERO_LABEL)
    return DividendTTM(None, "unavailable", INSUFFICIENT_DEPTH_REASON)


async def get_dividend_ttm(symbol: str) -> DividendTTM:
    """Trailing-12-month per-share dividends actually paid for ``symbol``.

    Returns a :class:`DividendTTM` — ``"paid"`` with the summed value,
    ``"affirmed_zero"`` (value ``0.0``) when real history depth paid nothing in the
    window, or ``"unavailable"`` (value ``None``) on any failure or when depth is
    insufficient to affirm a zero. Never raises into the research snapshot.
    ``symbol`` must already be the listing the fundamentals leg resolved to (the
    caller passes the Yahoo-form symbol) so the paid history reconciles against the
    SAME ``dividendRate``.
    """
    if not isinstance(symbol, str) or not symbol:
        return DividendTTM(None, "unavailable", UNAVAILABLE_REASON)
    try:
        result = await asyncio.to_thread(_sum_trailing_dividends, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_rate_limited(exc):
            provider_health.record_rate_limited()
        else:
            logger.debug("dividend history unavailable for %s: %s", symbol, exc)
        return DividendTTM(None, "unavailable", UNAVAILABLE_REASON)
    provider_health.record_success()
    return result


__all__ = [
    "AFFIRMED_ZERO_LABEL",
    "INSUFFICIENT_DEPTH_REASON",
    "DividendTTM",
    "get_dividend_ttm",
]
