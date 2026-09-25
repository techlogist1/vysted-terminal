"""Correctness gate — never present wrong, stale, or glitchy data (FR-063).

Constitution VIII: "wrong data is fatal" for a research product. After a
provider returns, the registry runs the served value through this gate; a
rejection is raised as :class:`CorrectnessError` (a :class:`ProviderError`
subclass) so the registry's existing preference-ordered fall-through advances to
the next provider — and, if every provider is rejected, surfaces an honest
"unavailable" rather than the bad value.

What the gate rejects (→ advance to next provider):

  * an empty / null series, or a quote/last-bar with a non-positive or
    non-finite (NaN/inf) price;
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

import asyncio
import logging
import math
import re
import statistics
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import Any

from models.fundamentals import FieldMeta, Fundamentals, IncomeStatement
from models.market import OHLCVSeries, Quote
from services import (
    dividend_history,
    exchange_financials,
    fundamentals_store,
    locale,
    ownership_check,
    symbol_resolver,
    yfinance_provider,
)
from services.errors import ProviderError
from services.research import range_check
from services.research.semantics import (
    _GROWTH_ABSOLUTE_TOLERANCE,
    _GROWTH_RELATIVE_TOLERANCE,
    _RANGE_TOLERANCE,
)

logger = logging.getLogger(__name__)

_SUFFIX_RE = re.compile(r"[.\-](NS|BO|BSE)$", re.IGNORECASE)

# --- numeric plausibility bounds for fundamentals (R13, deliverable 4) ---------
# Aligned with services.research.semantics._PLAUSIBLE_YIELD_FRACTION (0.25): a
# dividend yield expressed as a FRACTION above this is an ambiguous-unit figure
# (0.55 read as 55%?) — withheld rather than served as fact. The only yield bound
# on a served path (R15-DATA-034): the providers map the raw value and the gate
# judges it, together with a negative yield.
_PLAUSIBLE_YIELD_FRACTION = 0.25
# A current-price proxy (pe_ratio x eps) outside this band around the 52-week
# range is implausible — the low is scaled down / the high scaled up to tolerate
# a normal move past the trailing window before the pair is flagged.
_PRICE_BAND_LOW_FACTOR = 0.7
_PRICE_BAND_HIGH_FACTOR = 1.3
# Relative divergence of market cap from price x shares above which market cap is
# flagged (kept, not withheld).
_MARKET_CAP_DIVERGENCE = 0.25
# Relative gap between shares outstanding and the shares implied by market cap /
# price above which the share basis is flagged (R15-DATA-005). Tight on purpose:
# both figures come from ONE snapshot, so anything past rounding and a few
# percent of intra-day drift means two share counts (VERTEX: 74.0M vs 148.0M).
_SHARE_BASIS_DIVERGENCE = 0.05
# Relative gap between trailing EPS and the payload's net income / shares above
# which EPS and P/E are flagged (R15-DATA-013). A weighted-average EPS differs
# from net income over period-end shares only by the TTM share-count drift, a
# few percent; past this it is a different fiscal period (DAL 8.9 vs 2.04).
_EPS_DIVERGENCE = 0.05


# The exchange-direct India quote lanes that date a quote by the exchange's own
# last-trade record (the BSE scrip header's Ason / bhavcopy day, NSE's
# historicalOR rows). The jugaad ``nse`` lane is not here: it reads through an
# on-disk cache, so an old date there can be a stale cache, which the rejection
# rightly routes past.
_EXCHANGE_DATED_PROVIDERS = frozenset({"bse", "nse_direct"})


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
    """True if ``returned`` is the same instrument the caller asked for.

    A request addressed by a bare BSE scrip code (``506597.BO``) also matches the
    code's canonical ticker (``AMAL``), the symbol the BSE lane labels its
    result with (R15-LEAD-028)."""
    key, got = _match_key(requested), _match_key(returned)
    if key == got:
        return True
    canonical = symbol_resolver.bse_symbol_for_code(key) if key.isdigit() else None
    return canonical is not None and _match_key(canonical) == got


def validate_quote(
    quote: Quote, requested_symbol: str, region: str, *, check_staleness: bool = True
) -> Quote:
    """Reject a quote that is empty-priced, mis-symboled, or broken-feed stale.

    ``check_staleness=False`` skips the session-calendar staleness leg only (a
    crypto quote trades off any exchange calendar).

    An exchange lane's quote (:data:`_EXCHANGE_DATED_PROVIDERS`) is dated by the
    exchange's own last-trade record, so an old date there is the truth about an
    illiquid scrip, not a broken feed: it is served with that date and labelled
    stale by the quotes router (R15-DATA-006), never rejected into a lane that
    would present the same print as fresh.

    Returns the quote unchanged on success so callers can use it inline.
    """
    if quote.price is None or not math.isfinite(quote.price) or quote.price <= 0:
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
    exchange_dated = quote.provider in _EXCHANGE_DATED_PROVIDERS
    if check_staleness and not exchange_dated and locale.is_rejectably_stale(region, as_of):
        raise CorrectnessError(
            f"correctness gate: quote for {requested_symbol!r} from "
            f"{quote.provider!r} is dated {as_of} — too stale for the {region} calendar"
        )
    return quote


def validate_series(series: OHLCVSeries, requested_symbol: str, region: str) -> OHLCVSeries:
    """Reject an empty series, a non-positive last close, a mis-symboled one, or
    one in which every bar is flat (open = high = low = close) with zero volume —
    that shape is a parser filling missing fields, or no trade at all, never a
    traded price history (R15-LIFECYCLE-004).

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
    if last.close is None or not math.isfinite(last.close) or last.close <= 0:
        raise CorrectnessError(
            f"correctness gate: non-positive last close {last.close!r} for "
            f"{requested_symbol!r} from {series.provider!r}"
        )
    if not symbols_match(requested_symbol, series.symbol):
        raise CorrectnessError(
            f"correctness gate: provider {series.provider!r} returned series for "
            f"{series.symbol!r}, requested {requested_symbol!r} (symbol mismatch)"
        )
    if all(b.volume == 0 and b.open == b.high == b.low == b.close for b in series.bars):
        raise CorrectnessError(
            f"correctness gate: every bar for {requested_symbol!r} from "
            f"{series.provider!r} is flat with zero volume — not a traded series"
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
      * ``dividend_yield`` as a fraction above the plausible bound (ambiguous unit)
        or below zero;
      * ``fifty_two_week_high`` below ``fifty_two_week_low`` (the pair is internally
        inconsistent — both withheld).

    FLAGGED (value kept, reason recorded) — a cross-check disagreement that a
    single field cannot arbitrate:
      * the implied current price (pe x eps) sitting far outside the 52-week band
        → the 52-week pair is flagged (kept);
      * ``market_cap`` diverging from price x shares outstanding beyond tolerance
        → market cap is flagged (kept);
      * shares outstanding disagreeing with market cap / price (the ratio price,
        pe x eps only as fallback) → shares outstanding, book value and P/B are
        flagged (kept) — the per-share fields are on a different share basis;
      * trailing EPS disagreeing with net income / shares outstanding → EPS and
        P/E are flagged (kept), naming the payload-implied EPS and its P/E.

    Returns the SAME object when nothing tripped (callers use it inline); else a
    ``model_copy`` with the nulled fields + a merged ``field_meta`` (the provider's
    ``ok`` provenance is preserved for untouched fields, overwritten to
    ``withheld`` for nulled ones, and set to ``flagged`` with the reason for
    kept-but-disputed ones).
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

    # Dividend yield (a fraction) above the plausible bound is ambiguous-unit;
    # a negative one is not a yield at all.
    dy = f.dividend_yield
    if dy is not None and dy > _PLAUSIBLE_YIELD_FRACTION:
        withheld["dividend_yield"] = (
            f"a dividend yield of {dy:.2%} exceeds the plausible fraction bound of "
            f"{_PLAUSIBLE_YIELD_FRACTION:.0%} — an ambiguous-unit value; withheld"
        )
    elif dy is not None and dy < 0:
        withheld["dividend_yield"] = (
            f"a negative dividend yield ({dy:.2%}) is not a yield; withheld"
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

    # The cross-field passes below price through the provider's own ratio price
    # (the price its market cap and ratios were computed at), so a loss-maker with
    # no trailing P/E is still covered; pe x eps is only the fallback.
    ratio_price = f.ratio_price if f.ratio_price is not None and f.ratio_price > 0 else None
    cap_price = ratio_price if ratio_price is not None else price
    price_source = "the ratio price" if ratio_price is not None else "pe x eps"

    # Market cap vs price x shares outstanding → flag the (kept) market cap.
    market_cap = f.market_cap
    shares = f.shares_outstanding
    if market_cap is not None and shares is not None and cap_price is not None and shares > 0:
        implied_cap = cap_price * shares
        if (
            implied_cap > 0
            and _relative_divergence(market_cap, implied_cap) > _MARKET_CAP_DIVERGENCE
        ):
            flagged["market_cap"] = (
                f"market cap {market_cap:,.0f} diverges more than "
                f"{_MARKET_CAP_DIVERGENCE:.0%} from price x shares outstanding "
                f"({implied_cap:,.0f}, price from {price_source}) — the figures may be "
                "from different sessions or share classes; kept, flagged"
            )

    # Share basis (R15-DATA-005): the shares implied by market cap / price must
    # match shares outstanding. A gap means the per-share fields sit on a
    # different (typically stale, pre-rights/pre-IPO) share count than the market
    # cap, so shares outstanding, book value per share and P/B are flagged.
    if (
        market_cap is not None
        and market_cap > 0
        and shares is not None
        and shares > 0
        and cap_price is not None
    ):
        implied_shares = market_cap / cap_price
        gap = _relative_divergence(shares, implied_shares)
        if gap > _SHARE_BASIS_DIVERGENCE:
            reason = (
                f"shares outstanding {shares:,.0f} disagrees by {gap:.0%} with the "
                f"{implied_shares:,.0f} shares implied by market cap / price "
                f"({market_cap:,.0f} / {cap_price:,.4g}, price from {price_source}) — "
                "the per-share figures may sit on a stale share count (e.g. before a "
                "rights issue or IPO); kept, flagged"
            )
            for field_name in ("shares_outstanding", "book_value", "price_to_book"):
                if getattr(f, field_name) is not None:
                    flagged[field_name] = reason

    # EPS vs the payload's own net income / shares (R15-DATA-013): Yahoo's
    # trailingEps can lag a fiscal year behind netIncomeToCommon (DAL 8.9 vs
    # 2.04). Skipped when the share count is itself disputed (the implied EPS
    # would sit on the stale count) and for a foreign reporter (net income is in
    # the reporting currency, EPS in the trading currency).
    eps, net_income = f.eps, f.net_income_ttm
    if (
        eps is not None
        and net_income is not None
        and shares is not None
        and shares > 0
        and "shares_outstanding" not in flagged
        and f.financial_currency is None
    ):
        implied_eps = net_income / shares
        gap = _relative_divergence(eps, implied_eps)
        if gap > _EPS_DIVERGENCE:
            if ratio_price is not None and implied_eps > 0:
                implied_pe = f"{ratio_price / implied_eps:,.1f}"
                pe_note = (
                    f"the P/E it implies at the ratio price {ratio_price:,.4g} is {implied_pe}"
                )
            else:
                pe_note = "it implies no positive trailing P/E"
            reason = (
                f"trailing EPS {eps:,.4g} disagrees by {gap:.0%} with the payload's net "
                f"income / shares outstanding ({net_income:,.0f} / {shares:,.0f} = "
                f"{implied_eps:,.2f}); {pe_note} — the EPS may be from a stale fiscal "
                "period; kept, flagged"
            )
            flagged["eps"] = reason
            if f.pe_ratio is not None:
                flagged["pe_ratio"] = reason

    return _merge_meta(f, withheld, flagged)


def _merge_meta(f: Fundamentals, withheld: dict[str, str], flagged: dict[str, str]) -> Fundamentals:
    """Apply withheld (nulled) and flagged (kept) fields onto ``f``'s ``field_meta``.

    Returns the SAME object when there is nothing to record, else a ``model_copy``.
    A field already flagged by an earlier pass keeps that reason and gains the new
    one, so two disagreements on one value are both disclosed.
    """
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
        if prev is None:
            meta[field_name] = FieldMeta(status="flagged", provider=f.provider, reason=reason)
            continue
        if prev.status == "flagged" and prev.reason:
            reason = f"{prev.reason}; {reason}"
        meta[field_name] = prev.model_copy(update={"status": "flagged", "reason": reason})
    updates["field_meta"] = meta
    return f.model_copy(update=updates)


# --- exchange + statement witnesses (R15, D-B2-2: disclose, never substitute) --

#: The ownership band (pp): Yahoo's ``heldPercentInsiders`` vs the exchange
#: promoter group (and ``heldPercentInstitutions`` vs the exchange institutional
#: holding) beyond this gap is flagged. The same 3pp band as the research leg's
#: definitional insiders-vs-promoter tolerance (``semantics``, D68).
_OWNERSHIP_BAND_PP = 3.0


def reconcile_ownership(
    f: Fundamentals, exchange: ownership_check.ExchangeOwnership | None
) -> Fundamentals:
    """Flag Yahoo's ownership fractions that the exchange shareholding filing
    does not bear out (R15-DATA-004).

    Each served ``held_percent_*`` is compared with its exchange counterpart
    (percent, 0-100): a gap over :data:`_OWNERSHIP_BAND_PP`, or one side zero
    while the other is not, flags the provider value with the filing's figure
    and quarter. A filing category the exchange does not report (a promoter-less
    bank) counts as zero. When no filing figure is available at all, a served
    value is flagged as unreconciled. Never substituted.
    """
    pairs = (
        ("held_percent_insiders", "insiders", "promoter group", "insiders ≠ promoter group"),
        (
            "held_percent_institutions",
            "institutions",
            "institutional holding",
            "provider institutions ≠ exchange institutional holding",
        ),
    )
    filed = exchange is not None and any(
        v is not None
        for v in (
            exchange.promoter_percent,
            exchange.institutions_percent,
            exchange.public_percent,
        )
    )
    flagged: dict[str, str] = {}
    for field_name, label, category, definition in pairs:
        value = getattr(f, field_name)
        if value is None:
            continue
        if not filed or exchange is None:
            flagged[field_name] = f"unreconciled: exchange shareholding unavailable ({definition})"
            continue
        if field_name == "held_percent_insiders":
            filed_pct, source, as_of = (
                exchange.promoter_percent,
                exchange.source,
                exchange.as_of_quarter,
            )
        else:  # the institutions split may come from another lane and quarter
            filed_pct = exchange.institutions_percent
            source = exchange.institutions_source or exchange.source
            as_of = exchange.institutions_as_of or exchange.as_of_quarter
        provider_pct = value * 100.0
        exchange_pct = filed_pct if filed_pct is not None else 0.0
        zero_mismatch = (provider_pct == 0.0) != (exchange_pct == 0.0)
        if not zero_mismatch and abs(provider_pct - exchange_pct) <= _OWNERSHIP_BAND_PP:
            continue
        shown = f"{filed_pct:.2f}%" if filed_pct is not None else f"no {category} reported"
        flagged[field_name] = (
            f"{f.provider} {label} {provider_pct:.2f}% disagrees with the {source} "
            f"shareholding filing for the quarter ended {as_of} "
            f"({category}: {shown}) beyond {_OWNERSHIP_BAND_PP:g}pp ({definition}); "
            "kept, flagged"
        )
    return _merge_meta(f, {}, flagged)


#: Relative gap between ``revenue_ttm`` and the provider's own latest annual
#: Total Revenue above which the TTM is flagged (R15-DATA-014). Wide enough for a
#: fast grower's TTM to run ahead of its last fiscal year (JNPR: 8.49B TTM vs
#: 7.09B FY, 17%); FUSION's 858cr TTM against a 1,513cr fiscal year (43%) is not
#: growth but a mis-scoped figure.
_REVENUE_STATEMENT_DIVERGENCE = 0.30
#: Absolute gap (fraction) between net income / revenue and the provider's own
#: ``profit_margin`` above which the revenue is flagged: the two sizes and the
#: margin come from different periods.
_MARGIN_GAP = 0.02
#: A trailing-12-month size needs four filed quarters inside a year; a period end
#: less than this many days before the latest one falls inside that year.
_TTM_WINDOW_DAYS = 330
#: A median gap between Yahoo's period ends above this many days is a
#: half-yearly cadence (a quarterly one sits near 91, a half-yearly near 182).
_HALF_YEAR_GAP_DAYS = 135
_HALF_YEARLY_BASIS = "annual, not trailing-4Q; kept, flagged"


def _latest_annual(statement: IncomeStatement, label: str) -> tuple[str, float] | None:
    """The newest period's value for ``label`` in an annual statement, if any."""
    for line in statement.lines:
        if line.label != label:
            continue
        for period in statement.periods:
            value = line.values.get(period)
            if value is not None:
                return period, value
    return None


def _ttm_basis(quarter_ends: list[date] | None, cadence: str | None) -> str | None:
    """The TTM-basis label for the trailing sizes, or ``None`` when four
    quarters back them (R15-LEAD-004, D-B7-2).

    The cadence comes from the exchange-filed periods when that lane answered,
    else from the median gap between Yahoo's period ends — never from a count
    of Yahoo's columns, whose Indian frames skip quarters: a quarterly filer
    with a missing Yahoo column spans a provider gap, it is not half-yearly.
    """
    if cadence == "half-yearly":
        return (
            "TTM basis: the exchange filings do not cover the trailing year in four "
            f"quarters (a half-yearly filer) — {_HALF_YEARLY_BASIS}"
        )
    if not quarter_ends:  # an empty frame says nothing about the filing cadence
        return None
    ends = sorted(set(quarter_ends), reverse=True)
    filed = [d for d in ends if (ends[0] - d).days < _TTM_WINDOW_DAYS]
    if len(filed) >= 4:
        return None
    gaps = [(newer - older).days for newer, older in zip(ends, ends[1:], strict=False)]
    if cadence is None and gaps and statistics.median(gaps) > _HALF_YEAR_GAP_DAYS:
        return (
            f"TTM basis: only {len(filed)} filed period(s) in the trailing year "
            f"(a half-yearly filer) — {_HALF_YEARLY_BASIS}"
        )
    return (
        f"TTM basis: the provider's quarterly statements show only {len(filed)} "
        "quarter(s) in the trailing year — the trailing figure spans a provider gap; "
        "kept, flagged"
    )


def reconcile_revenue(
    f: Fundamentals,
    annual: IncomeStatement | None,
    quarter_ends: list[date] | None,
    cadence: str | None = None,
) -> Fundamentals:
    """Flag a ``revenue_ttm`` its own provider's statements do not bear out
    (R15-DATA-014), never substituting one.

      * against the latest annual Total Revenue, beyond
        :data:`_REVENUE_STATEMENT_DIVERGENCE`;
      * net income / revenue against the provider's own ``profit_margin``,
        beyond :data:`_MARGIN_GAP`;
      * a trailing year not backed by four quarters → the trailing sizes carry
        the :func:`_ttm_basis` label (``cadence`` is the exchange-filed cadence,
        ``None`` when that lane did not answer).

    A witness that could not be fetched (``None``, or an empty quarterly
    frame) contributes nothing.
    """
    revenue = f.revenue_ttm
    if revenue is None or revenue <= 0:
        return f
    reasons: list[str] = []
    latest = _latest_annual(annual, "Total Revenue") if annual is not None else None
    if latest is not None and latest[1] > 0:
        period, annual_revenue = latest
        gap = _relative_divergence(revenue, annual_revenue)
        if gap > _REVENUE_STATEMENT_DIVERGENCE:
            reasons.append(
                f"revenue_ttm {revenue:,.0f} diverges {gap:.0%} from the provider's own "
                f"latest annual Total Revenue ({annual_revenue:,.0f}, FY ending {period}) — the "
                "trailing figure may be mis-scoped"
            )
    margin, net_income = f.profit_margin, f.net_income_ttm
    if margin is not None and net_income is not None:
        implied_margin = net_income / revenue
        if abs(implied_margin - margin) > _MARGIN_GAP:
            reasons.append(
                f"net income / revenue ({implied_margin:.1%}) disagrees with the "
                f"provider's own profit margin ({margin:.1%}) — revenue and net income "
                "may be from different periods"
            )
    flagged: dict[str, str] = {}
    if reasons:
        flagged["revenue_ttm"] = "; ".join(reasons) + "; kept, flagged"
    basis = _ttm_basis(quarter_ends, cadence)
    if basis is not None:
        for field_name in ("revenue_ttm", "net_income_ttm"):
            if getattr(f, field_name) is not None:
                prior = flagged.get(field_name)
                flagged[field_name] = f"{prior}; {basis}" if prior else basis
    return _merge_meta(f, {}, flagged)


#: The filed-period sums the exchange overlay serves: (field, period attribute).
_FILED_SIZES = (("revenue_ttm", "revenue"), ("net_income_ttm", "net_profit"), ("eps", "eps"))
_FILED_GROWTH = (("revenue_growth", "revenue"), ("earnings_growth", "net_profit"))


def _growth_disagrees(served: float, filed: float) -> bool:
    """The research leg's growth tolerance (relative, with an absolute floor)."""
    band = max(
        _GROWTH_RELATIVE_TOLERANCE * max(abs(served), abs(filed)), _GROWTH_ABSOLUTE_TOLERANCE
    )
    return abs(served - filed) > band


def overlay_filed_periods(f: Fundamentals, filed: exchange_financials.FiledPeriods) -> Fundamentals:
    """Serve the exchange-filed figures over the provider's (D-B7-1).

      * ``revenue_ttm`` / ``net_income_ttm`` / ``eps`` — the sum of the filed
        periods covering the trailing 12 months (four quarters, or two halves);
        nothing when the filings leave a hole in that year;
      * ``revenue_growth`` / ``earnings_growth`` — the newest filed period
        against the same-length period a year earlier (MRQ-YoY), when filed.

    ``field_meta`` names the venue, the basis and the latest period end; a
    provider figure beyond the witness band (30% for sizes, the research
    growth tolerance for growth) is disclosed in the reason. Every other field
    stays the provider's.
    """
    latest = filed.periods[0]
    as_of = latest.end.isoformat()
    meta = dict(f.field_meta or {})
    updates: dict[str, Any] = {}

    def serve(name: str, value: float, label: str, disagrees: bool) -> None:
        served = getattr(f, name)
        reason = None
        if served is not None and disagrees:
            shown = (
                f"{served:.1%}"
                if name.endswith("_growth")
                else f"{served:,.2f}"
                if name == "eps"
                else f"{served:,.0f}"
            )
            reason = (
                f"exchange-filed ({filed.venue.upper()}) figure served; the provider's "
                f"{shown} disagrees with it — not served"
            )
        updates[name] = value
        meta[name] = FieldMeta(
            status="ok", provider=filed.venue, as_of=as_of, reason=reason, label=label
        )

    trail = filed.trailing()
    if trail is not None:
        kind = "quarters" if all(p.months == 3 for p in trail) else "half-years"
        label = f"{filed.basis}, sum of {len(trail)} filed {kind} to {as_of}"
        for name, attr in _FILED_SIZES:
            values = [getattr(p, attr) for p in trail]
            if any(v is None for v in values):
                continue
            total = sum(values)
            served = getattr(f, name)
            off = served is not None and (
                _relative_divergence(served, total) > _REVENUE_STATEMENT_DIVERGENCE
            )
            serve(name, total, label, off)
    prior = filed.year_ago(latest)
    if prior is not None and f.growth_basis == "mrq_yoy":
        label = f"{filed.basis}, period to {as_of} vs the same period to {prior.end.isoformat()}"
        for name, attr in _FILED_GROWTH:
            now, then = getattr(latest, attr), getattr(prior, attr)
            if now is None or not then:
                continue
            growth = (now - then) / abs(then)
            served = getattr(f, name)
            serve(name, growth, label, served is not None and _growth_disagrees(served, growth))
    if not updates:
        return f
    updates["field_meta"] = meta
    return f.model_copy(update=updates)


async def apply_exchange_financials(f: Fundamentals) -> Fundamentals:
    """The exchange-filed overlay for one Indian listing's fundamentals
    (:func:`overlay_filed_periods`). A non-Indian listing, or a lane that
    returns nothing, leaves ``f`` unchanged; never raises. Called by the agent
    ``fundamentals`` tool; :func:`apply_witnesses` runs the same overlay."""
    filed = await exchange_financials.get_filed_periods(f.symbol)
    return overlay_filed_periods(f, filed) if filed is not None else f


#: Relative gap between a served per-share book field and the same figure
#: rebuilt from the newest filed equity above which the field is flagged
#: (R15-DATA-005, D-B3-8). JUMBO's 54.361 against its own 57.01 is 4.6%.
_BOOK_BASIS_DIVERGENCE = 0.03


def reconcile_book_value(f: Fundamentals, equity: tuple[date, float] | None) -> Fundamentals:
    """Flag ``book_value`` and ``price_to_book`` the provider's own newest filed
    stockholders' equity does not bear out (R15-DATA-005), never substituting.

      * ``book_value`` against equity / ``shares_outstanding``;
      * ``price_to_book`` against ``market_cap`` / equity.

    A per-share figure computed on a stale share count (JNPR's pre-IPO shares)
    passes the market-cap share-basis pass, because the share count itself is
    current; only the balance sheet shows the stale denominator. A foreign
    reporter is skipped (its statements are in another currency than its
    per-share fields), as is a witness that could not be fetched.
    """
    if equity is None or f.financial_currency is not None:
        return f
    period_end, equity_value = equity
    shares, market_cap = f.shares_outstanding, f.market_cap
    flagged: dict[str, str] = {}
    if f.book_value is not None and shares is not None and shares > 0:
        implied = equity_value / shares
        gap = _relative_divergence(f.book_value, implied)
        if gap > _BOOK_BASIS_DIVERGENCE:
            flagged["book_value"] = (
                f"book value per share {f.book_value:,.4g} disagrees by {gap:.1%} with the "
                f"provider's newest filed stockholders' equity / shares outstanding "
                f"({equity_value:,.0f} as of {period_end} / {shares:,.0f} = {implied:,.2f}) — "
                "it may sit on a stale share count; kept, flagged"
            )
    if f.price_to_book is not None and market_cap is not None and equity_value > 0:
        implied = market_cap / equity_value
        gap = _relative_divergence(f.price_to_book, implied)
        if gap > _BOOK_BASIS_DIVERGENCE:
            flagged["price_to_book"] = (
                f"P/B {f.price_to_book:,.4g} disagrees by {gap:.1%} with market cap / the "
                f"provider's newest filed stockholders' equity ({market_cap:,.0f} / "
                f"{equity_value:,.0f} as of {period_end} = {implied:,.2f}) — the book value "
                "behind it may sit on a stale share count; kept, flagged"
            )
    return _merge_meta(f, {}, flagged)


#: How long a fetched witness input is reused (R15-LEAD-002, D-B3-9): the
#: fundamentals valuation-tier row TTL, so a witness is never older than the row
#: it checks. Filings and statements change quarterly; without this every
#: /fundamentals load re-fetched them (Indian median 2-3 s rising to 4-8.5 s).
_WITNESS_TTL_SECONDS = fundamentals_store.TTL_V7_SECONDS
#: ``(witness, listing)`` → ``(fetched at, input)``. In-process only, so a
#: restart (or a fix) starts clean; flags are always recomputed from the inputs.
_witness_cache: dict[tuple[str, str], tuple[float, Any]] = {}


def reset_witness_cache_for_tests() -> None:
    """Drop every cached witness input (test isolation)."""
    _witness_cache.clear()


async def _cached_witness(kind: str, symbol: str, fetch: Callable[[], Awaitable[Any]]) -> Any:
    """The ``kind`` witness input for ``symbol``, fetched at most once per
    :data:`_WITNESS_TTL_SECONDS`. A failed or empty fetch (``None``) is not
    cached, so the next request tries again."""
    key = (kind, symbol.upper())
    now = time.monotonic()
    hit = _witness_cache.get(key)
    if hit is not None and now - hit[0] < _WITNESS_TTL_SECONDS:
        return hit[1]
    value = await fetch()
    if value is not None:
        _witness_cache[key] = (now, value)
    return value


async def _statement_witness(fn: Any, symbol: str) -> Any:
    """One same-provider statement fetch for ``symbol``; any failure attaches
    nothing (``None``) — a witness must never break the payload."""
    try:
        return await asyncio.to_thread(fn, symbol)
    except Exception as exc:  # noqa: BLE001 — a witness must never break the payload
        logger.debug("statement witness unavailable for %s: %s", symbol, exc)
        return None


def reconcile_52w_range(
    f: Fundamentals,
    history: tuple[list[Any], list[str]] | None,
    today: date | None = None,
) -> Fundamentals:
    """Witness the provider's 52-week high/low against both Indian venues' bars.

    ``history`` is :func:`services.research.range_check.get_venue_history`'s
    ``(bars, venues)``. The last trade is the newer of the last exchange bar and
    the provider's own trade time (``ratio_price`` as-of):

      * no trade in 52 weeks → both bounds are withheld; a range over forward-
        filled untraded days describes nothing (DAL: last trade 2025-03-12);
      * a full year of exchange bars → a bound off the exchange extreme by more
        than the research leg's 10% tolerance is flagged, either direction;
      * a shorter series → only an exchange extreme OUTSIDE the provider range
        by more than the tolerance is flagged, and the reason says "since" the
        first bar, since the missing months could hold the provider's extreme.

    Both bounds come from one provider window, so when either is flagged the
    other is flagged too. Disclose, never substitute: flagged bounds keep the
    provider value.
    """
    names = [n for n in ("fifty_two_week_high", "fifty_two_week_low") if getattr(f, n) is not None]
    if not names:
        return f
    bars, venues = history or ([], [])
    trades = [ts.date() for b in bars if isinstance(ts := getattr(b, "timestamp", None), datetime)]
    price_meta = (f.field_meta or {}).get("ratio_price")
    if price_meta is not None and price_meta.as_of:
        trades.append(datetime.fromisoformat(price_meta.as_of).date())
    if not trades:
        return f
    last_trade = max(trades)
    today = today or datetime.now(UTC).date()
    if (today - last_trade).days > 365:
        reason = f"no trades in 52 weeks (last trade {last_trade.isoformat()}); withheld"
        return _merge_meta(f, dict.fromkeys(names, reason), {})
    if not bars:
        return f

    full = range_check.compute_range(bars, "+".join(venues))
    ex_high = max(float(b.high) for b in bars)
    ex_low = min(float(b.low) for b in bars)
    first = min(
        ts.date() for b in bars if isinstance(ts := getattr(b, "timestamp", None), datetime)
    )
    exchange = {"fifty_two_week_high": ex_high, "fifty_two_week_low": ex_low}
    flagged: dict[str, str] = {}
    for name in names:
        provider_value = float(getattr(f, name))
        gap = _relative_divergence(provider_value, exchange[name])
        if gap <= _RANGE_TOLERANCE:
            continue
        outside = ex_high > provider_value if name.endswith("high") else ex_low < provider_value
        if full is None and not outside:
            continue  # a short series cannot say the provider's extreme did not print
        label = "high" if name.endswith("high") else "low"
        flagged[name] = (
            f"52-week {label} {provider_value:,.2f} is {gap:.0%} off the {' + '.join(venues)} "
            f"exchange range {ex_low:,.2f}-{ex_high:,.2f} since {first.isoformat()}; kept, flagged"
        )
    # Both bounds come from ONE provider window: a flagged bound shows that window
    # is off the exchange range, so its partner is not ok either (R15-DATA-015).
    for name in names:
        other = next((n for n in flagged if n != name), None)
        if name in flagged or other is None:
            continue
        label = "high" if name.endswith("high") else "low"
        other_label = "high" if other.endswith("high") else "low"
        flagged[name] = (
            f"52-week {label} {float(getattr(f, name)):,.2f} comes from the same provider "
            f"52-week window as the flagged {other_label}, and that window disagrees with the "
            f"{' + '.join(venues)} exchange range {ex_low:,.2f}-{ex_high:,.2f} since "
            f"{first.isoformat()}; kept, flagged"
        )
    return _merge_meta(f, {}, flagged)


async def _dividend_witness(symbol: str) -> dividend_history.DividendTTM | None:
    """The paid-TTM dividend history for ``symbol``; a failed round-trip is
    ``None`` so :func:`_cached_witness` does not keep it."""
    ttm = await dividend_history.get_dividend_ttm(symbol)
    if ttm is None or ttm.reason == dividend_history.UNAVAILABLE_REASON:
        return None
    return ttm


async def apply_witnesses(f: Fundamentals) -> Fundamentals:
    """Run the witnesses that need a network fetch over served fundamentals.

    Shared by ``GET /fundamentals`` and the company narrative so both surfaces
    carry the same flags, fetched concurrently:

      * for an Indian listing with a served ownership fraction, the exchange
        shareholding pattern (``get_exchange_ownership`` never raises and
        respects its circuit) → :func:`reconcile_ownership`;
      * for a yfinance-served ``revenue_ttm``, the same provider's annual income
        statement and quarterly period ends → :func:`reconcile_revenue`;
      * for a yfinance-served ``book_value``/``price_to_book``, the same
        provider's newest filed stockholders' equity → :func:`reconcile_book_value`;
      * for yfinance-served fundamentals, the trailing-12m dividends actually
        paid → :func:`services.dividend_history.apply_dividend_ttm`, the same leg
        the research snapshot runs (R15-DATA-047/049);
      * for a yfinance-served 52-week range on an Indian listing, a year of
        NSE + BSE daily bars → :func:`reconcile_52w_range` (R15-DATA-015/016);
      * for an Indian listing, the exchange-filed results →
        :func:`overlay_filed_periods` (D-B7-1). A trailing revenue served from
        the filings is not reconciled against Yahoo's statements; one left as
        Yahoo's takes its cadence label from the filings (R15-LEAD-004).

    Each fetched input is reused per listing for :data:`_WITNESS_TTL_SECONDS`
    (the filed results for a day); the reconcile functions run on every call.
    """
    yfinance_served = f.provider == yfinance_provider.PROVIDER
    has_ownership = f.held_percent_insiders is not None or f.held_percent_institutions is not None
    check_ownership = has_ownership and ownership_check.is_applicable(f.symbol)
    check_revenue = f.revenue_ttm is not None and yfinance_served
    check_book = yfinance_served and (f.book_value is not None or f.price_to_book is not None)
    has_range = f.fifty_two_week_high is not None or f.fifty_two_week_low is not None
    check_range = yfinance_served and has_range and range_check.is_applicable(f.symbol)

    async def ownership() -> ownership_check.ExchangeOwnership | None:
        if not check_ownership:
            return None
        return await _cached_witness(
            "ownership", f.symbol, lambda: ownership_check.get_exchange_ownership(f.symbol)
        )

    async def statement(kind: str, fn: Any, wanted: bool) -> Any:
        if not wanted:
            return None
        return await _cached_witness(kind, f.symbol, lambda: _statement_witness(fn, f.symbol))

    async def dividends() -> dividend_history.DividendTTM | None:
        if not yfinance_served:
            return None
        return await _cached_witness("dividends", f.symbol, lambda: _dividend_witness(f.symbol))

    async def venue_history() -> tuple[list[Any], list[str]] | None:
        if not check_range:
            return None
        return await _cached_witness(
            "range52w", f.symbol, lambda: range_check.get_venue_history(f.symbol)
        )

    exchange, annual, quarter_ends, equity, paid, venues, filed = await asyncio.gather(
        ownership(),
        statement("income", yfinance_provider.get_income_statement, check_revenue),
        statement("quarters", yfinance_provider.get_quarterly_period_ends, check_revenue),
        statement("equity", yfinance_provider.get_newest_equity, check_book),
        dividends(),
        venue_history(),
        exchange_financials.get_filed_periods(f.symbol),
    )
    if check_ownership:
        f = reconcile_ownership(f, exchange)
    if filed is not None:
        f = overlay_filed_periods(f, filed)
    revenue_meta = (f.field_meta or {}).get("revenue_ttm")
    exchange_revenue = filed is not None and revenue_meta is not None
    exchange_revenue = exchange_revenue and revenue_meta.provider == filed.venue
    if check_revenue and not exchange_revenue:
        f = reconcile_revenue(f, annual, quarter_ends, filed.cadence() if filed else None)
    if check_book:
        f = reconcile_book_value(f, equity)
    if yfinance_served:
        data = f.model_dump()
        dividend_history.apply_dividend_ttm(data, paid)
        f = Fundamentals.model_validate(data)
    if check_range:
        f = reconcile_52w_range(f, venues)
    return f


__all__ = [
    "CorrectnessError",
    "apply_exchange_financials",
    "apply_witnesses",
    "overlay_filed_periods",
    "reconcile_52w_range",
    "reconcile_book_value",
    "reconcile_ownership",
    "reconcile_revenue",
    "symbols_match",
    "validate_fundamentals",
    "validate_quote",
    "validate_series",
]
