"""Trailing-12-month dividend cross-check (R11 / D56).

Yahoo's ``dividendRate`` (the source of ``Fundamentals.dividend_per_share``) is
a single opaque scalar that can OMIT a special dividend — ABBOTINDIA reported
Rs 525 (final only) against a true Rs 656 (525 final + 131 special). The
corporate-action history cannot omit a payment, so summing the trailing-12-month
dividends actually paid gives a deterministic completeness check the arithmetic
unit-reconciliation in :mod:`services.research.semantics` cannot.

:func:`get_dividend_ttm` is the ONLY entry point. It never raises into the
research path: every yfinance failure becomes ``None`` (the caller then simply
emits no cross-check card). A detected throttle is reported to the shared
Yahoo-family circuit breaker so a dividend-history 429 backs the same cooldown
as a quote/``.info`` 429 (one IP reputation, one breaker) — a healthy
round-trip resets it.
"""

from __future__ import annotations

import asyncio
import logging

import pandas as pd
import yfinance as yf

from services import provider_health

logger = logging.getLogger(__name__)

#: Trailing window summed for the "actually paid" figure — twelve months back
#: from now, matching Yahoo's own "trailing annual dividend rate" horizon so the
#: two are like-for-like (a divergence is then a COMPLETENESS gap, not a window
#: mismatch).
_TRAILING_DAYS = 365


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


def _sum_trailing_dividends(symbol: str) -> float | None:
    """Sum per-share dividends paid in the trailing 12 months (BLOCKING).

    Returns ``None`` when the ticker has paid no dividend in the window (a valid,
    healthy result — the caller still records the round-trip as a success). Runs
    under :func:`asyncio.to_thread`; may raise on a network/throttle failure,
    which the async wrapper classifies and swallows.
    """
    series = yf.Ticker(symbol).dividends
    if series is None or len(series) == 0:
        return None
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=_TRAILING_DAYS)
    total = 0.0
    found = False
    for raw_ts, amount in series.items():
        ts = pd.Timestamp(raw_ts)
        # yfinance indexes dividends in the exchange timezone (tz-aware for most
        # listings, occasionally tz-naive) — normalise to UTC either way so the
        # window comparison never raises on a tz mismatch.
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        if ts < cutoff:
            continue
        if amount is None or pd.isna(amount):
            continue
        total += float(amount)
        found = True
    return total if found else None


async def get_dividend_ttm(symbol: str) -> float | None:
    """Trailing-12-month per-share dividends actually paid for ``symbol``.

    ``None`` on any failure OR when no dividend was paid in the window — never
    raises into the research snapshot. ``symbol`` must already be the listing the
    fundamentals leg resolved to (the caller passes the Yahoo-form symbol) so the
    paid history reconciles against the SAME ``dividendRate``.
    """
    if not isinstance(symbol, str) or not symbol:
        return None
    try:
        total = await asyncio.to_thread(_sum_trailing_dividends, symbol)
    except Exception as exc:  # noqa: BLE001 — a cross-check must never break research
        if _is_rate_limited(exc):
            provider_health.record_rate_limited()
        else:
            logger.debug("dividend history unavailable for %s: %s", symbol, exc)
        return None
    provider_health.record_success()
    return total


__all__ = ["get_dividend_ttm"]
