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

from models.fundamentals import Fundamentals
from models.market import OHLCVSeries, Quote
from services import locale
from services.errors import ProviderError

logger = logging.getLogger(__name__)

_SUFFIX_RE = re.compile(r"[.\-](NS|BO|BSE)$", re.IGNORECASE)


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
    """Reject fundamentals for the wrong instrument (symbol mismatch only).

    Fundamentals are sparse by nature (many ``None`` fields are legitimate), so
    the gate only enforces instrument identity here — it does not reject on a
    missing ratio.
    """
    if fundamentals.symbol and not symbols_match(requested_symbol, fundamentals.symbol):
        raise CorrectnessError(
            f"correctness gate: provider {fundamentals.provider!r} returned fundamentals for "
            f"{fundamentals.symbol!r}, requested {requested_symbol!r} (symbol mismatch)"
        )
    return fundamentals


__all__ = [
    "CorrectnessError",
    "symbols_match",
    "validate_fundamentals",
    "validate_quote",
    "validate_series",
]
