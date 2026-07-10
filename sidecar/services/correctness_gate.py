"""Correctness gate — never present wrong, stale, or glitchy data (FR-063).

Constitution VIII: "wrong data is fatal" for a research product. After a
provider returns, the registry runs the served value through this gate; a
rejection is raised as :class:`CorrectnessError` (a :class:`ProviderError`
subclass) so the registry's existing preference-ordered fall-through advances to
the next provider — and, if every provider is rejected, surfaces an honest
"unavailable" rather than the bad value.

What the gate rejects (→ advance to next provider):

  * an empty / null series, or a quote/last-bar with a non-positive price;
  * a returned symbol that does not match the requested instrument
    (normalised across ``.NS``/``.BO`` and dot/dash quirks);
  * a value dated far enough behind the exchange's most-recent session that the
    feed is clearly broken (calendar-aware, generous T+1 tolerance — a normal
    EOD lag is *labelled* stale via :mod:`services.locale`, not rejected here).

What it does NOT do: invent a reference price to catch a *plausible-but-wrong*
value (e.g. yfinance's silent-wrong NSE OHLC, issue #2055). That failure mode is
handled by **ranking** — the locale-correct source (NSE/jugaad) is preferred and
yfinance is the gated last resort for ``.NS``/``.BO`` — not by this gate.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from models.fundamentals import FieldMeta, Fundamentals
from models.market import OHLCVSeries, Quote
from services import locale
from services.errors import ProviderError

logger = logging.getLogger(__name__)

_SUFFIX_RE = re.compile(r"[.\-](NS|BO|BSE)$", re.IGNORECASE)

# --- numeric plausibility bounds for fundamentals (R13, deliverable 4) ---------
# Aligned with services.research.semantics._PLAUSIBLE_YIELD_FRACTION (0.25): a
# dividend yield expressed as a FRACTION above this is an ambiguous-unit figure
# (0.55 read as 55%?) — withheld rather than served as fact.
_PLAUSIBLE_YIELD_FRACTION = 0.25
# A current-price proxy (pe_ratio x eps) outside this band around the 52-week
# range is implausible — the low is scaled down / the high scaled up to tolerate
# a normal move past the trailing window before the pair is flagged.
_PRICE_BAND_LOW_FACTOR = 0.7
_PRICE_BAND_HIGH_FACTOR = 1.3
# Relative divergence of market cap from price x shares above which market cap is
# flagged (kept, not withheld).
_MARKET_CAP_DIVERGENCE = 0.25


class CorrectnessError(ProviderError):
    """A provider response was rejected by the correctness gate (FR-063).

    Subclasses :class:`ProviderError` so the registry's preference-ordered
    fall-through treats a correctness rejection exactly like a provider failure.
    """


class EmptySeriesError(CorrectnessError):
    """A history series came back with zero bars (Bug-2).

    Distinguished from the other correctness rejections (non-positive close,
    symbol mismatch) so the ``/history`` router can downgrade an
    all-providers-empty history to a clean ``200`` "no price data" response
    instead of a scary ``502``, while a genuine data-integrity failure still
    surfaces as ``502``. Still a :class:`CorrectnessError` (→
    :class:`ProviderError`) so provider preference-ordered fall-through is
    unchanged — an empty result from provider A still advances to provider B.
    """


def _match_key(symbol: str) -> str:
    """Normalise a symbol for cross-provider identity comparison.

    Strips a recognised exchange suffix (``.NS``/``.BO``) then removes dot/dash
    quirks, so ``GOLDBEES.NS`` (resolved), ``GOLDBEES-NS`` (yfinance's dash
    form), and ``GOLDBEES`` (NSE) all compare equal — while a genuine ticker
    like ``BRK.B``/``BRK-B`` still collapses to ``BRKB`` without losing identity.
    """
    upper = symbol.strip().upper()
    upper = _SUFFIX_RE.sub("", upper)
    return upper.replace(".", "").replace("-", "")


def symbols_match(requested: str, returned: str) -> bool:
    """True if ``returned`` is the same instrument the caller asked for."""
    return _match_key(requested) == _match_key(returned)


def validate_quote(quote: Quote, requested_symbol: str, region: str) -> Quote:
    """Reject a quote that is empty-priced, mis-symboled, or broken-feed stale.

    Returns the quote unchanged on success so callers can use it inline.
    """
    if quote.price is None or quote.price <= 0:
        raise CorrectnessError(
            f"correctness gate: non-positive price {quote.price!r} for "
            f"{requested_symbol!r} from {quote.provider!r}"
        )
    if not symbols_match(requested_symbol, quote.symbol):
        raise CorrectnessError(
            f"correctness gate: provider {quote.provider!r} returned "
            f"{quote.symbol!r} for requested {requested_symbol!r} (symbol mismatch)"
        )
    as_of = quote.timestamp.date() if quote.timestamp else None
    if locale.is_rejectably_stale(region, as_of):
        raise CorrectnessError(
            f"correctness gate: quote for {requested_symbol!r} from "
            f"{quote.provider!r} is dated {as_of} — too stale for the {region} calendar"
        )
    return quote


def validate_series(series: OHLCVSeries, requested_symbol: str, region: str) -> OHLCVSeries:
    """Reject an empty series, a non-positive last close, or a mis-symboled one.

    Staleness is NOT a rejection here (unlike :func:`validate_quote`): a history
    series legitimately ends at an old date (a delisted name, a market that has
    been closed, a deep-history request) and hard-rejecting it would dead-end
    valid data. Its recency is surfaced as a freshness *label*
    (:func:`services.locale.freshness_for`) instead — the hard staleness gate
    applies to the *quote*, which claims to be current.
    """
    if not series.bars:
        raise EmptySeriesError(
            f"correctness gate: empty series for {requested_symbol!r} from {series.provider!r}"
        )
    last = series.bars[-1]
    if last.close is None or last.close <= 0:
        raise CorrectnessError(
            f"correctness gate: non-positive last close {last.close!r} for "
            f"{requested_symbol!r} from {series.provider!r}"
        )
    if not symbols_match(requested_symbol, series.symbol):
        raise CorrectnessError(
            f"correctness gate: provider {series.provider!r} returned series for "
            f"{series.symbol!r}, requested {requested_symbol!r} (symbol mismatch)"
        )
    return series


def validate_fundamentals(
    fundamentals: Fundamentals, requested_symbol: str, region: str
) -> Fundamentals:
    """Reject fundamentals for the wrong instrument, then withhold/flag any field
    whose VALUE is numerically implausible (R13, deliverable 4).

    Two stages, both preserving the "wrong data is fatal, missing data is honest"
    stance:

      * INSTRUMENT IDENTITY — a symbol mismatch rejects the whole result (advance
        to the next provider), exactly as before.
      * PER-FIELD PLAUSIBILITY — an out-of-bounds VALUE never rejects the whole
        (mostly-good) result; it is WITHHELD (nulled, with a recorded reason) or
        FLAGGED (kept, with a recorded reason). The record rides ``field_meta`` so
        the reason travels with the payload. Fundamentals stay sparse by nature —
        a *missing* ratio is still legitimate and is left untouched.
    """
    if fundamentals.symbol and not symbols_match(requested_symbol, fundamentals.symbol):
        raise CorrectnessError(
            f"correctness gate: provider {fundamentals.provider!r} returned fundamentals for "
            f"{fundamentals.symbol!r}, requested {requested_symbol!r} (symbol mismatch)"
        )
    return _apply_plausibility_bounds(fundamentals)


def _relative_divergence(a: float, b: float) -> float:
    """Relative divergence of ``a`` from ``b`` (symmetric enough for gating)."""
    denominator = max(abs(a), abs(b))
    if denominator == 0:
        return 0.0
    return abs(a - b) / denominator


def _implied_price(f: Fundamentals) -> float | None:
    """A current-price proxy from the valuation identity ``trailing PE = price /
    trailing EPS`` → ``price = pe_ratio x eps``.

    Both inputs come from the SAME provider info snapshot, so the product
    reconstructs the price the ratios were computed against — the only "current
    price" the gate can see without a separate quote. ``None`` unless both are
    present and the product is positive (a negative-EPS loss-maker has no usable
    trailing PE, so the product is not a price)."""
    if f.pe_ratio is not None and f.eps is not None:
        price = f.pe_ratio * f.eps
        return price if price > 0 else None
    return None


def _apply_plausibility_bounds(f: Fundamentals) -> Fundamentals:
    """Withhold implausible field values, flag suspicious-but-kept ones (R13).

    WITHHELD (value nulled) — a value that cannot be right under any reading:
      * ``held_percent_insiders`` / ``held_percent_institutions`` outside [0, 1]
        (a fraction contract; 8455% is a percent served as a fraction or garbage);
      * ``dividend_yield`` as a fraction above the plausible bound (ambiguous unit);
      * ``fifty_two_week_high`` below ``fifty_two_week_low`` (the pair is internally
        inconsistent — both withheld).

    FLAGGED (value kept, reason recorded) — a cross-check disagreement that a
    single field cannot arbitrate:
      * the implied current price (pe x eps) sitting far outside the 52-week band
        → the 52-week pair is flagged (kept);
      * ``market_cap`` diverging from price x shares outstanding beyond tolerance
        → market cap is flagged (kept).

    Returns the SAME object when nothing tripped (callers use it inline); else a
    ``model_copy`` with the nulled fields + a merged ``field_meta`` (the provider's
    ``ok`` provenance is preserved for untouched fields, overwritten to
    ``withheld`` for nulled ones, and reason-annotated for flagged ones).
    """
    withheld: dict[str, str] = {}
    flagged: dict[str, str] = {}

    # Ownership fractions must live in [0, 1].
    for field_name in ("held_percent_insiders", "held_percent_institutions"):
        value = getattr(f, field_name)
        if value is not None and not (0.0 <= value <= 1.0):
            withheld[field_name] = (
                f"{value:g} is outside the valid ownership fraction range [0, 1] "
                f"({value * 100:g}% — likely a percent served as a fraction or a "
                "bad source value); withheld"
            )

    # Dividend yield (a fraction) above the plausible bound is ambiguous-unit.
    dy = f.dividend_yield
    if dy is not None and dy > _PLAUSIBLE_YIELD_FRACTION:
        withheld["dividend_yield"] = (
            f"a dividend yield of {dy:.2%} exceeds the plausible fraction bound of "
            f"{_PLAUSIBLE_YIELD_FRACTION:.0%} — an ambiguous-unit value; withheld"
        )

    # 52-week high below low is internally inconsistent — withhold both.
    hi, lo = f.fifty_two_week_high, f.fifty_two_week_low
    pair_withheld = False
    if hi is not None and lo is not None and hi < lo:
        reason = (
            f"52-week high {hi:g} is below 52-week low {lo:g} — the pair is "
            "internally inconsistent; withheld"
        )
        withheld["fifty_two_week_high"] = reason
        withheld["fifty_two_week_low"] = reason
        pair_withheld = True

    price = _implied_price(f)

    # Implied price far outside the 52-week band → flag the (kept) 52-week pair.
    # Skipped when the pair was already withheld above (nothing to flag).
    if price is not None and hi is not None and lo is not None and not pair_withheld and hi >= lo:
        band_low = lo * _PRICE_BAND_LOW_FACTOR
        band_high = hi * _PRICE_BAND_HIGH_FACTOR
        if not (band_low <= price <= band_high):
            reason = (
                f"the price implied by pe x eps ({price:,.2f}) sits far outside the "
                f"52-week band [{band_low:,.2f}, {band_high:,.2f}] — the 52-week pair "
                "or the valuation ratios may be from a different session/instrument; "
                "kept, flagged"
            )
            flagged["fifty_two_week_high"] = reason
            flagged["fifty_two_week_low"] = reason

    # Market cap vs implied price x shares outstanding → flag the (kept) market cap.
    market_cap = f.market_cap
    shares = f.shares_outstanding
    if market_cap is not None and shares is not None and price is not None and shares > 0:
        implied_cap = price * shares
        if (
            implied_cap > 0
            and _relative_divergence(market_cap, implied_cap) > _MARKET_CAP_DIVERGENCE
        ):
            flagged["market_cap"] = (
                f"market cap {market_cap:,.0f} diverges more than "
                f"{_MARKET_CAP_DIVERGENCE:.0%} from price x shares outstanding "
                f"({implied_cap:,.0f}, price from pe x eps) — the figures may be from "
                "different sessions or share classes; kept, flagged"
            )

    if not withheld and not flagged:
        return f

    updates: dict[str, Any] = {}
    meta: dict[str, FieldMeta] = dict(f.field_meta or {})
    for field_name, reason in withheld.items():
        updates[field_name] = None
        prev = meta.get(field_name)
        meta[field_name] = FieldMeta(
            status="withheld",
            provider=prev.provider if prev else f.provider,
            as_of=prev.as_of if prev else None,
            reason=reason,
        )
    for field_name, reason in flagged.items():
        if field_name in withheld:
            continue  # a withheld field is never also flagged
        prev = meta.get(field_name)
        if prev is not None:
            meta[field_name] = prev.model_copy(update={"reason": reason})
        else:
            meta[field_name] = FieldMeta(status="ok", provider=f.provider, reason=reason)
    updates["field_meta"] = meta
    return f.model_copy(update=updates)


__all__ = [
    "CorrectnessError",
    "symbols_match",
    "validate_fundamentals",
    "validate_quote",
    "validate_series",
]
