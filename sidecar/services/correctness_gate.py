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
from datetime import date
from typing import Any

from models.fundamentals import FieldMeta, Fundamentals, IncomeStatement
from models.market import OHLCVSeries, Quote
from services import locale, ownership_check, yfinance_provider
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
    """True if ``returned`` is the same instrument the caller asked for."""
    return _match_key(requested) == _match_key(returned)


def validate_quote(quote: Quote, requested_symbol: str, region: str) -> Quote:
    """Reject a quote that is empty-priced, mis-symboled, or broken-feed stale.

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
    if not exchange_dated and locale.is_rejectably_stale(region, as_of):
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
        filed_pct = (
            exchange.promoter_percent
            if field_name == "held_percent_insiders"
            else exchange.institutions_percent
        )
        provider_pct = value * 100.0
        exchange_pct = filed_pct if filed_pct is not None else 0.0
        zero_mismatch = (provider_pct == 0.0) != (exchange_pct == 0.0)
        if not zero_mismatch and abs(provider_pct - exchange_pct) <= _OWNERSHIP_BAND_PP:
            continue
        shown = f"{filed_pct:.2f}%" if filed_pct is not None else f"no {category} reported"
        flagged[field_name] = (
            f"{f.provider} {label} {provider_pct:.2f}% disagrees with the {exchange.source} "
            f"shareholding filing for the quarter ended {exchange.as_of_quarter} "
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


def reconcile_revenue(
    f: Fundamentals,
    annual: IncomeStatement | None,
    quarter_ends: list[date] | None,
) -> Fundamentals:
    """Flag a ``revenue_ttm`` its own provider's statements do not bear out
    (R15-DATA-014), never substituting one.

      * against the latest annual Total Revenue, beyond
        :data:`_REVENUE_STATEMENT_DIVERGENCE`;
      * net income / revenue against the provider's own ``profit_margin``,
        beyond :data:`_MARGIN_GAP`;
      * fewer than four filed quarters in the trailing year (a half-yearly filer)
        → the trailing sizes are labelled "annual, not trailing-4Q".

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
                f"latest annual Total Revenue ({annual_revenue:,.0f}, FY {period}) — the "
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
    if quarter_ends:  # an empty frame says nothing about the filing cadence
        newest = max(quarter_ends)
        filed = [d for d in quarter_ends if (newest - d).days < _TTM_WINDOW_DAYS]
        if len(filed) < 4:
            basis = (
                f"TTM basis: only {len(filed)} filed quarter(s) in the trailing year "
                "(e.g. a half-yearly filer) — annual, not trailing-4Q; kept, flagged"
            )
            for field_name in ("revenue_ttm", "net_income_ttm"):
                if getattr(f, field_name) is not None:
                    prior = flagged.get(field_name)
                    flagged[field_name] = f"{prior}; {basis}" if prior else basis
    return _merge_meta(f, {}, flagged)


async def _statement_witnesses(
    f: Fundamentals,
) -> tuple[IncomeStatement | None, list[date] | None]:
    """The serving provider's own annual income statement and quarterly period
    ends for the same listing. Only a yfinance-served payload has a same-provider
    statement to check against; any fetch failure attaches nothing."""

    async def fetch(fn: Any) -> Any:
        try:
            return await asyncio.to_thread(fn, f.symbol)
        except Exception as exc:  # noqa: BLE001 — a witness must never break the payload
            logger.debug("statement witness unavailable for %s: %s", f.symbol, exc)
            return None

    return await asyncio.gather(
        fetch(yfinance_provider.get_income_statement),
        fetch(yfinance_provider.get_quarterly_period_ends),
    )


async def apply_witnesses(f: Fundamentals) -> Fundamentals:
    """Run the witnesses that need a network fetch over served fundamentals.

    Shared by ``GET /fundamentals`` and the company narrative so both surfaces
    carry the same flags, fetched concurrently:

      * for an Indian listing with a served ownership fraction, the exchange
        shareholding pattern (``get_exchange_ownership`` never raises and
        respects its circuit) → :func:`reconcile_ownership`;
      * for a yfinance-served ``revenue_ttm``, the same provider's annual income
        statement and quarterly period ends → :func:`reconcile_revenue`.
    """
    has_ownership = f.held_percent_insiders is not None or f.held_percent_institutions is not None
    check_ownership = has_ownership and ownership_check.is_applicable(f.symbol)
    check_revenue = f.revenue_ttm is not None and f.provider == yfinance_provider.PROVIDER

    async def ownership() -> ownership_check.ExchangeOwnership | None:
        return await ownership_check.get_exchange_ownership(f.symbol) if check_ownership else None

    async def statements() -> tuple[IncomeStatement | None, list[date] | None]:
        return await _statement_witnesses(f) if check_revenue else (None, None)

    exchange, (annual, quarter_ends) = await asyncio.gather(ownership(), statements())
    if check_ownership:
        f = reconcile_ownership(f, exchange)
    if check_revenue:
        f = reconcile_revenue(f, annual, quarter_ends)
    return f


__all__ = [
    "CorrectnessError",
    "apply_witnesses",
    "reconcile_ownership",
    "reconcile_revenue",
    "symbols_match",
    "validate_fundamentals",
    "validate_quote",
    "validate_series",
]
