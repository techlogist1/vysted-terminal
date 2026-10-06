"""Trailing-12-month dividend cross-check (R11 / D56).

Yahoo's ``dividendRate`` (the source of ``Fundamentals.dividend_per_share``) is
a single opaque scalar that can OMIT a special dividend — ABBOTINDIA reported
Rs 525 (final only) against a true Rs 656 (525 final + 131 special). The
corporate-action history cannot omit a payment, so summing the trailing-12-month
dividends actually paid gives a deterministic completeness check the arithmetic
unit-reconciliation in :mod:`services.research.semantics` cannot.

:func:`get_dividend_ttm` is the ONLY fetching entry point. It returns a
:class:`DividendTTM` carrying the null-vs-AFFIRMED-ZERO distinction (a company
with real history depth that paid nothing in the trailing window affirms ``0.0``,
never an unknown null). :func:`apply_dividend_ttm` threads that result onto a
fundamentals payload — the ONE paid-TTM leg shared by ``GET /fundamentals``
(:func:`services.correctness_gate.apply_witnesses`) and the research snapshot
(R15-DATA-047/049). It never raises into the research path: every yfinance
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
from typing import Any

import pandas as pd
import yfinance as yf

from services import provider_health
from services.research.semantics import _DIVIDEND_TTM_DIVERGENCE

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
#: The provider the paid history comes from (Yahoo's corporate-action series).
PROVIDER = "yfinance"


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


def _utc(raw_ts: Any) -> pd.Timestamp:
    """yfinance indexes in the exchange timezone (tz-aware for most listings,
    occasionally tz-naive) — normalise to UTC either way so a window comparison
    never raises on a tz mismatch."""
    ts = pd.Timestamp(raw_ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")


def _sum_trailing_dividends(symbol: str) -> DividendTTM:
    """Sum per-share dividends paid in the trailing 12 months (BLOCKING).

    Distinguishes an AFFIRMED trailing-12m zero (the series has real depth — at
    least one dividend older than the window — but paid nothing inside it) from an
    UNAVAILABLE null (empty series / no depth to affirm anything). Runs under
    :func:`asyncio.to_thread`; may raise on a network/throttle failure, which the
    async wrapper classifies and swallows.
    """
    ticker = yf.Ticker(symbol)
    series = ticker.dividends
    cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=_TRAILING_DAYS)
    if series is None or len(series) == 0:
        # No dividend ever recorded: a zero is affirmed only when the listing's
        # price history reaches back past the window (a year of trading with no
        # dividend event), never for a listing too young to say (R15-DATA-049).
        prices = ticker.history(period="2y", interval="1mo")
        if len(prices) and _utc(prices.index[0]) <= cutoff:
            return DividendTTM(0.0, "affirmed_zero", AFFIRMED_ZERO_LABEL)
        return DividendTTM(None, "unavailable", INSUFFICIENT_DEPTH_REASON)
    total = 0.0
    found_in_window = False
    has_depth = False  # a real dividend OLDER than the window → ≥12 months covered
    for raw_ts, amount in series.items():
        ts = _utc(raw_ts)
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
        if provider_health.is_rate_limit(exc):
            provider_health.record_rate_limited()
        else:
            logger.debug("dividend history unavailable for %s: %s", symbol, exc)
        return DividendTTM(None, "unavailable", UNAVAILABLE_REASON)
    provider_health.record_success()
    return result


def apply_dividend_ttm(fund: dict[str, Any], ttm: DividendTTM | None) -> None:
    """Thread the trailing-12m PAID result onto a fundamentals wire dict, in place.

    * ``paid`` sets ``dividend_per_share_ttm``; a ``dividend_yield`` the
      provider did not publish is served as paid / the ratio price.
    * ``affirmed_zero`` sets ``dividend_per_share_ttm`` and an unpublished
      ``dividend_yield`` to ``0.0``, both labelled :data:`AFFIRMED_ZERO_LABEL`.
    * ``unavailable`` (or ``None``) leaves the field null with the reason.
    * A ``dividend_per_share`` (Yahoo ``dividendRate``) that diverges from the
      paid figure past the D56 tolerance is flagged, never replaced (an
      omitted special dividend, or an anticipated unpaid one).
    """
    if ttm is None:
        ttm = DividendTTM(None, "unavailable", UNAVAILABLE_REASON)
    meta = fund.get("field_meta") or {}
    fund["field_meta"] = meta
    if ttm.value is None:
        meta["dividend_per_share_ttm"] = {
            "status": "unavailable",
            "provider": PROVIDER,
            "reason": ttm.reason,
        }
        return
    paid, affirmed = ttm.value, ttm.is_affirmed_zero
    label = AFFIRMED_ZERO_LABEL if affirmed else None
    fund["dividend_per_share_ttm"] = paid
    meta["dividend_per_share_ttm"] = {
        "status": "ok",
        "provider": PROVIDER,
        "reason": ttm.reason,
        "label": label,
    }

    price = fund.get("ratio_price")
    yield_meta = meta.get("dividend_yield") or {}
    if fund.get("dividend_yield") is None and yield_meta.get("status") != "withheld":
        reason = None
        if affirmed:
            fund["dividend_yield"], reason = 0.0, AFFIRMED_ZERO_LABEL
        elif isinstance(price, (int, float)) and price > 0:
            fund["dividend_yield"] = paid / price
            reason = f"trailing-12m dividends paid ({paid:g}) / price ({price:g})"
        if reason is not None:
            meta["dividend_yield"] = {
                "status": "ok",
                "provider": PROVIDER,
                "reason": reason,
                "label": label,
            }

    dps = fund.get("dividend_per_share")
    if isinstance(dps, (int, float)) and max(abs(dps), paid) > 0:
        gap = abs(dps - paid) / max(abs(dps), paid)
        if gap > _DIVIDEND_TTM_DIVERGENCE:
            direction = "exceeds" if dps > paid else "is below"
            reason = (
                f"dividend per share {dps:g} (Yahoo dividendRate) {direction} the "
                f"{paid:g} actually paid in the trailing 12 months by {gap:.0%} — the "
                "rate can omit a special dividend or anticipate an unpaid one; kept, flagged"
            )
            prev = meta.get("dividend_per_share") or {"provider": PROVIDER}
            if prev.get("status") == "flagged" and prev.get("reason"):
                reason = f"{prev['reason']}; {reason}"
            meta["dividend_per_share"] = {**prev, "status": "flagged", "reason": reason}


__all__ = [
    "AFFIRMED_ZERO_LABEL",
    "INSUFFICIENT_DEPTH_REASON",
    "DividendTTM",
    "apply_dividend_ttm",
    "get_dividend_ttm",
]
