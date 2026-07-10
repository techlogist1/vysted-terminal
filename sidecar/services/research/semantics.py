"""Metric semantics — the discipline layer between raw provider fields and
every rendered/stated number (R10, E8 / D37).

Pure module, no IO. The live E8 defects: drawdown-from-high stated under the
"52-week change" label, a 55% dividend yield co-existing with a Rs 1/share
dividend (yfinance unit chaos absorbed by a magic guard), growth figures with
no named basis. :func:`derive_semantics` computes the ``derived`` leg of the
brief's structured bundle per the ``BriefDerivedMetrics`` contract
(``types/brief.ts``): every value carries its exact display label, its basis,
and (when computed) its formula; cross-source disagreements land in
``conflicts[]`` instead of being silently resolved; missing inputs yield
``null`` values — never a fabricated number.

:func:`prompt_block` renders the same facts as a synthesis-prompt block so the
prose layer states figures under the SAME labels and bases the metric cards
render — one truth, two surfaces.
"""

from __future__ import annotations

from typing import Any

from services import identity_crosscheck, ownership_check

#: Relative divergence above which the provider dividend yield and the implied
#: yield (dividend per share / price) are a CONFLICT — flagged, and no single
#: dividend value is emitted (the 55%-yield-next-to-Rs-1 defect).
_DIVIDEND_DIVERGENCE = 0.25

#: Relative divergence above which the provider dividend-per-share (Yahoo
#: ``dividendRate``) and the trailing-12-month dividends actually paid disagree
#: enough to flag (R11 / D56) — dividendRate can omit a special dividend, so the
#: paid history is surfaced as a separate, more-complete fact. Tighter than the
#: unit-chaos band above: this is a COMPLETENESS gap, not a units question.
_DIVIDEND_TTM_DIVERGENCE = 0.10

#: The MRQ-YoY truth (R11 / D55): yfinance's ``revenueGrowth``/``earningsGrowth``
#: are most-recent-quarter vs the same quarter a year ago — NOT annual/TTM. The
#: basis string says so at every surface that renders these figures.
_GROWTH_BASIS_MRQ_YOY = "quarterly YoY (MRQ)"

#: Growth cross-check tolerance (R12 / D66): the provider scalar and the value
#: computed from the quarterly income statements AGREE when their gap is within
#: 10% relative OR 2 percentage points absolute, whichever band is LARGER (the
#: absolute floor keeps small-base growth from flagging on noise; the relative
#: band keeps large growth honest). Beyond it the disagreement is a conflict —
#: disclosed, never resolved by replacing the provider value.
_GROWTH_RELATIVE_TOLERANCE = 0.10
_GROWTH_ABSOLUTE_TOLERANCE = 0.02

#: (provider field, computed field, provider scalar name, computed fact label).
_GROWTH_CHECKS = (
    (
        "revenue_growth",
        "revenue_growth_computed",
        "revenueGrowth",
        "Revenue growth (computed from quarterly statements)",
    ),
    (
        "earnings_growth",
        "earnings_growth_computed",
        "earningsGrowth",
        "Net-profit growth (computed from quarterly statements)",
    ),
)

#: Relative tolerance for the market-cap cross-check against
#: price x shares outstanding; beyond it the disagreement is flagged.
_MARKET_CAP_TOLERANCE = 0.05

#: A dividend yield reported without a verifiable dividend-per-share companion
#: is emitted only when plausible AS A FRACTION of price (< this bound) — an
#: ambiguous-unit figure (0.55? 55?) is withheld rather than guessed.
_PLAUSIBLE_YIELD_FRACTION = 0.25

#: Ownership cross-check tolerances (R13 / D68). The provider's
#: ``heldPercentInsiders`` and the exchange promoter-group percentage AGREE
#: within this absolute pp band; beyond it a conflict is flagged.
_OWNERSHIP_PROMOTER_PP = 2.0
#: A promoter-vs-insiders gap at or under this pp band, in the EXPECTED direction
#: (insiders ≥ promoter — insiders is a superset), is a DEFINITIONAL divergence
#: (insiders ≠ promoter-group), not a data contradiction; a wider gap is data.
_OWNERSHIP_DEFINITIONAL_PP = 3.0
#: ``heldPercentInstitutions`` vs the exchange institutional holding are a
#: CONFLICT when the larger exceeds this factor of the smaller (a >2x gap) —
#: institutional definitions are close enough that a gap this wide is a data
#: contradiction, never merely definitional.
_OWNERSHIP_INSTITUTIONS_RATIO = 2.0
#: The zero-vs-nonzero floor (pp): a category the exchange reports as ~0 that the
#: provider reports above this is a real divergence (not a rounding wisp).
_OWNERSHIP_ZERO_FLOOR_PP = 0.5

#: Conflict-NATURE discriminator (R13 / D69) — additive, ORTHOGONAL to the
#: conflict-TYPE ``kind`` (e.g. "identity_conflict"/"ownership_conflict"):
#: "definitional_expected" = the divergence is explained by a known
#: definition/basis difference (insiders vs promoter-group; bank revenue line);
#: "data_conflict" = a genuine cross-source contradiction. Consumers default to
#: ``data_conflict`` when the field is absent, so existing readers are unchanged.
_CONFLICT_DATA = "data_conflict"
_CONFLICT_DEFINITIONAL = "definitional_expected"


def _leg_data(structured: dict[str, Any], leg: str) -> dict[str, Any]:
    """The ``data`` dict of an ok leg, or ``{}`` — never raises on thin shapes."""
    value = structured.get(leg)
    if isinstance(value, dict) and value.get("ok"):
        data = value.get("data")
        if isinstance(data, dict):
            return data
    return {}


def _num(data: dict[str, Any], key: str) -> float | None:
    """A numeric field as float, tolerating wire-string numbers; else ``None``."""
    value = data.get(key)
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _value(
    value: float | None,
    label: str,
    *,
    basis: str | None = None,
    formula: str | None = None,
    unit: str | None = None,
) -> dict[str, Any]:
    """One ``BriefDerivedValue`` wire dict — ``value`` may honestly be null."""
    out: dict[str, Any] = {"value": value, "label": label}
    if basis:
        out["basis"] = basis
    if formula:
        out["formula"] = formula
    if unit:
        out["unit"] = unit
    return out


def _relative_divergence(a: float, b: float) -> float:
    """Relative divergence of ``a`` from ``b`` (symmetric enough for gating)."""
    denominator = max(abs(a), abs(b))
    if denominator == 0:
        return 0.0
    return abs(a - b) / denominator


def _dividend_ttm_leg(
    fund: dict[str, Any], dps: float | None, provider: str, currency: str | None
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Cross-check ``dividend_per_share`` against the trailing-12m paid history.

    Returns ``(ttm_fact_or_None, conflicts)``. Both the scalar
    (``dividendRate``) and the paid-history sum (``dividend_per_share_ttm``,
    attached upstream by :func:`services.research.fast.snapshot_structured`)
    must be present; a divergence past :data:`_DIVIDEND_TTM_DIVERGENCE` flags a
    conflict AND surfaces the paid figure as its own labeled fact (R11 / D56).
    When they agree — or either is absent — nothing extra is emitted.
    """
    ttm = _num(fund, "dividend_per_share_ttm")
    if dps is None or ttm is None:
        return None, []
    if _relative_divergence(ttm, dps) <= _DIVIDEND_TTM_DIVERGENCE:
        return None, []
    unit = "currency"
    ttm_basis = "corporate-action history"
    fact = _value(
        ttm,
        "Dividend/share (trailing 12m paid)",
        basis=ttm_basis,
        formula="sum of dividends paid in the trailing 12 months",
        unit=unit,
    )
    conflict = {
        "field": "dividend_per_share",
        "sources": [
            {"provider": f"{provider} (dividendRate)", "value": dps},
            {"provider": "derived (trailing-12m paid history)", "value": round(ttm, 4)},
        ],
        "note": (
            "The provider's dividend per share (Yahoo dividendRate) differs from "
            "the trailing-12-month dividends actually paid by more than 10% — "
            "dividendRate can omit a special dividend, so the paid history is the "
            "complete figure."
        ),
    }
    _ = currency  # currency rides the dps fact's basis; noted here for symmetry
    return fact, [conflict]


def _growth_agrees(provider_value: float, computed: float) -> bool:
    """The D66 tolerance gate: |Δ| within max(10% relative, 2pp absolute)."""
    band = max(
        _GROWTH_RELATIVE_TOLERANCE * max(abs(provider_value), abs(computed)),
        _GROWTH_ABSOLUTE_TOLERANCE,
    )
    return abs(provider_value - computed) <= band


def _growth_leg(fund: dict[str, Any], provider: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Cross-check the provider growth scalars against the quarterly-statement
    computation (R12 / D66).

    Returns ``(facts, conflicts)``. Both the provider scalar and the computed
    figure (``*_growth_computed``, attached upstream by
    :func:`services.research.fast.snapshot_structured`) must be present; a gap
    past the :func:`_growth_agrees` band flags a conflict AND surfaces the
    computed figure as its own labeled fact — the provider value is NEVER
    replaced (its ``data`` entry is emitted unchanged elsewhere; this is
    disclosure, not substitution). Agreement — or an absent leg — emits
    nothing extra: absence is honest.
    """
    quarters = fund.get("growth_computed_quarters")
    quarters = quarters if isinstance(quarters, dict) else None
    facts: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []
    for provider_key, computed_key, scalar_name, label in _GROWTH_CHECKS:
        provider_value = _num(fund, provider_key)
        computed = _num(fund, computed_key)
        if provider_value is None or computed is None:
            continue
        if _growth_agrees(provider_value, computed):
            continue
        facts[computed_key] = _value(
            computed,
            label,
            basis=_GROWTH_BASIS_MRQ_YOY,
            formula="(MRQ - same quarter prior year) / |same quarter prior year|",
            unit="percent",
        )
        quarter_note = (
            f" ({quarters.get('mrq')} vs {quarters.get('prior')})"
            if quarters and quarters.get("mrq") and quarters.get("prior")
            else ""
        )
        conflict: dict[str, Any] = {
            "field": provider_key,
            "sources": [
                {
                    "provider": f"{provider} ({scalar_name})",
                    "value": provider_value,
                    "basis": "mrq_yoy (provider-claimed)",
                },
                {
                    "provider": "derived (quarterly income statement)",
                    "value": round(computed, 4),
                    "basis": _GROWTH_BASIS_MRQ_YOY,
                },
            ],
            "note": (
                f"The provider's {provider_key.replace('_', ' ')} scalar claims "
                "MRQ YoY but disagrees with the figure computed from its own "
                f"quarterly income statements{quarter_note} beyond tolerance — "
                "the statement-derived figure reconciles against reported "
                "quarterly results; the scalar may ride a different line "
                "definition (bank revenue) or a restated base quarter. The "
                "provider value is shown unchanged."
            ),
        }
        if quarters:
            conflict["quarters"] = dict(quarters)
        conflicts.append(conflict)
    return facts, conflicts


def _diverges_by_factor(a: float, b: float, factor: float) -> bool:
    """True when the larger of ``|a|``/``|b|`` exceeds ``factor``× the smaller.

    A zero-vs-nonzero pair diverges when the nonzero side clears
    :data:`_OWNERSHIP_ZERO_FLOOR_PP` — so 0.06% vs 8.455% fires while 0 vs a
    rounding wisp does not.
    """
    hi, lo = max(abs(a), abs(b)), min(abs(a), abs(b))
    if lo == 0:
        return hi > _OWNERSHIP_ZERO_FLOOR_PP
    return hi / lo > factor


def _ownership_promoter_conflict(
    provider: str, yf_pct: float, promoter_pct: float, source: str, as_of: str | None
) -> dict[str, Any]:
    """The insiders-vs-promoter conflict — direction/definition/as-of aware."""
    gap = abs(yf_pct - promoter_pct)
    # insiders is a SUPERSET of promoter-group; a small over-count in that
    # direction is definitional, a large gap (or the wrong direction) is data.
    definitional = gap <= _OWNERSHIP_DEFINITIONAL_PP and yf_pct >= promoter_pct
    as_of_note = f" as of {as_of}" if as_of else ""
    return {
        "field": "held_percent_insiders",
        "kind": "ownership_conflict",
        "conflict_kind": _CONFLICT_DEFINITIONAL if definitional else _CONFLICT_DATA,
        "sources": [
            {
                "provider": f"{provider} (heldPercentInsiders)",
                "value": round(yf_pct, 3),
                "basis": "insiders (provider roster; mixed as-of)",
            },
            {
                "provider": f"{source} shareholding filing",
                "value": round(promoter_pct, 3),
                "basis": f"promoter group{as_of_note}",
            },
        ],
        "note": (
            f"The provider's heldPercentInsiders ({yf_pct:.2f}%) counts INSIDERS — "
            "a superset that mixes promoter-group holders with other insider rows "
            "and can carry stale, individually-dated as-of dates — while the "
            f"{source} shareholding filing reports the strict PROMOTER GROUP at "
            f"{promoter_pct:.2f}%{as_of_note}. Insiders and promoter-group are "
            "different by definition; both figures are shown, neither replaced."
        ),
    }


def _ownership_institutions_conflict(
    provider: str, yf_pct: float, institutions_pct: float, source: str, as_of: str | None
) -> dict[str, Any]:
    """The institutions divergence conflict (always a data contradiction)."""
    as_of_note = f" as of {as_of}" if as_of else ""
    return {
        "field": "held_percent_institutions",
        "kind": "ownership_conflict",
        "conflict_kind": _CONFLICT_DATA,
        "sources": [
            {
                "provider": f"{provider} (heldPercentInstitutions)",
                "value": round(yf_pct, 3),
                "basis": "institutions (provider snapshot)",
            },
            {
                "provider": f"{source} shareholding filing",
                "value": round(institutions_pct, 3),
                "basis": f"institutional holding{as_of_note}",
            },
        ],
        "note": (
            f"The provider's heldPercentInstitutions ({yf_pct:.2f}%) diverges from "
            f"the {source} exchange filing's institutional holding "
            f"({institutions_pct:.2f}%{as_of_note}) by more than "
            f"{_OWNERSHIP_INSTITUTIONS_RATIO:g}x — the provider scalar is "
            "unreliable for this listing; both are shown, neither replaced."
        ),
    }


def _ownership_leg(
    fund: dict[str, Any], provider: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Cross-check yfinance insider/institution % against the exchange SHP
    (R13 / D68).

    Returns ``(facts, conflicts)``. The exchange promoter (and institutions,
    where the filing carried them) are surfaced as SEPARATELY-LABELED facts;
    a divergence past tolerance flags a conflict carrying BOTH values, BOTH
    definitions, and BOTH as-of dates. The provider ownership scalars are NEVER
    replaced — disclosure, not substitution. The exchange pattern rides
    ``fund[ownership_check.OWNERSHIP_KEY]`` (attached upstream by the snapshot
    builder, mirroring D66); an absent leg emits nothing (absence is honest).
    """
    exchange = fund.get(ownership_check.OWNERSHIP_KEY)
    if not isinstance(exchange, dict):
        return {}, []
    source = exchange.get("source") if isinstance(exchange.get("source"), str) else "exchange"
    raw_as_of = exchange.get("as_of_quarter")
    as_of = raw_as_of if isinstance(raw_as_of, str) and raw_as_of else None
    promoter_pct = _num(exchange, "promoter_percent")
    institutions_pct = _num(exchange, "institutions_percent")
    basis = f"{source} shareholding filing" + (f", {as_of}" if as_of else "")

    facts: dict[str, Any] = {}
    conflicts: list[dict[str, Any]] = []

    if promoter_pct is not None:
        facts["promoter_percent_exchange"] = _value(
            round(promoter_pct / 100.0, 6),
            "Promoter group (exchange filing)",
            basis=basis,
            unit="percent",
        )
        yf_insiders = _num(fund, "held_percent_insiders")  # a fraction (0-1)
        if yf_insiders is not None:
            yf_pct = yf_insiders * 100.0
            if abs(yf_pct - promoter_pct) > _OWNERSHIP_PROMOTER_PP:
                conflicts.append(
                    _ownership_promoter_conflict(provider, yf_pct, promoter_pct, source, as_of)
                )

    if institutions_pct is not None:
        facts["institutions_percent_exchange"] = _value(
            round(institutions_pct / 100.0, 6),
            "Institutional holding (exchange filing)",
            basis=basis,
            unit="percent",
        )
        yf_inst = _num(fund, "held_percent_institutions")  # a fraction (0-1)
        if yf_inst is not None:
            yf_pct = yf_inst * 100.0
            if _diverges_by_factor(yf_pct, institutions_pct, _OWNERSHIP_INSTITUTIONS_RATIO):
                conflicts.append(
                    _ownership_institutions_conflict(
                        provider, yf_pct, institutions_pct, source, as_of
                    )
                )

    return facts, conflicts


def _dividend_leg(
    fund: dict[str, Any], price: float | None, provider: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None, list[dict[str, Any]]]:
    """Reconcile dividend_yield against dividend_per_share / price, and the
    dividend-per-share scalar against the trailing-12m paid history.

    Returns ``(dividend_yield_value, dividend_per_share_value,
    dividend_ttm_fact_or_None, conflicts)``. The provider yield's unit is
    reconciled EXPLICITLY (yfinance ships both fraction and percent forms): the
    interpretation closest to the implied yield wins; past
    :data:`_DIVIDEND_DIVERGENCE` the disagreement is a conflict and NO single
    dividend value is emitted. Separately, a trailing-12m-paid figure that
    diverges from ``dividendRate`` past :data:`_DIVIDEND_TTM_DIVERGENCE` is
    surfaced as its own fact with a conflict (R11 / D56).
    """
    reported = _num(fund, "dividend_yield")
    dps = _num(fund, "dividend_per_share")
    implied = dps / price if dps is not None and price else None
    currency = fund.get("currency") if isinstance(fund.get("currency"), str) else None
    dps_basis = f"per share, {currency}" if currency else "per share, listing currency"
    ttm_fact, ttm_conflicts = _dividend_ttm_leg(fund, dps, provider, currency)

    yield_kwargs: dict[str, Any] = {
        "basis": "fraction of price",
        "unit": "percent",
    }
    dps_kwargs: dict[str, Any] = {"basis": dps_basis, "unit": "currency"}

    if implied is not None and reported is not None:
        # Pick the provider-unit interpretation (fraction vs percent) closest
        # to the implied yield — the unit chaos is resolved, not absorbed.
        interpretations = [("fraction", reported), ("percent", reported / 100.0)]
        unit_name, closest = min(
            interpretations, key=lambda pair: _relative_divergence(pair[1], implied)
        )
        if _relative_divergence(closest, implied) <= _DIVIDEND_DIVERGENCE:
            return (
                _value(
                    implied,
                    "Dividend yield",
                    formula="dividend per share / price",
                    **yield_kwargs,
                ),
                _value(dps, "Dividend per share", **dps_kwargs),
                ttm_fact,
                list(ttm_conflicts),
            )
        conflict = {
            "field": "dividend_yield",
            "sources": [
                {"provider": f"{provider} (as {unit_name})", "value": reported},
                {"provider": "derived (dividend per share / price)", "value": round(implied, 6)},
            ],
            "note": (
                "The provider's dividend yield disagrees with dividend-per-share "
                "/ price by more than 25% under every unit reading — state no "
                "single dividend figure; a primary-source dividend history would "
                "reconcile it."
            ),
        }
        return (
            _value(None, "Dividend yield", **yield_kwargs),
            _value(None, "Dividend per share", **dps_kwargs),
            ttm_fact,
            [conflict, *ttm_conflicts],
        )

    if implied is not None:
        return (
            _value(implied, "Dividend yield", formula="dividend per share / price", **yield_kwargs),
            _value(dps, "Dividend per share", **dps_kwargs),
            ttm_fact,
            list(ttm_conflicts),
        )

    if reported is not None:
        # No dividend-per-share to verify against: emit only when the figure is
        # plausible as a fraction of price; an ambiguous-unit number is withheld
        # (null), never guessed into a unit.
        plausible = 0 <= reported < _PLAUSIBLE_YIELD_FRACTION
        return (
            _value(reported if plausible else None, "Dividend yield", **yield_kwargs),
            _value(None, "Dividend per share", **dps_kwargs),
            ttm_fact,
            list(ttm_conflicts),
        )

    return (
        _value(None, "Dividend yield", **yield_kwargs),
        _value(None, "Dividend per share", **dps_kwargs),
        ttm_fact,
        list(ttm_conflicts),
    )


def derive_semantics(
    structured: dict[str, Any],
    region: str | None,
    *,
    canonical_name: str | None = None,
    symbol: str | None = None,
) -> dict[str, Any]:
    """Compute the ``derived`` structured leg from the price/fundamentals legs.

    Returns ``{"ok": True, "provider": "derived", "data": {...}}`` per the
    ``BriefDerivedMetrics`` contract. Values are ``null`` when inputs are
    missing — never fabricated; ``region`` rides only as context (currency
    labels come from the fundamentals leg itself when present).
    """
    del region  # context only — no value is region-fabricated
    price_data = _leg_data(structured, "price")
    fund = _leg_data(structured, "fundamentals")
    provider = "unknown"
    fund_leg = structured.get("fundamentals")
    if isinstance(fund_leg, dict) and isinstance(fund_leg.get("provider"), str):
        provider = fund_leg["provider"]

    price = _num(price_data, "price")
    high = _num(fund, "fifty_two_week_high")
    conflicts: list[dict[str, Any]] = []

    drawdown = None
    if price is not None and high is not None and high > 0:
        drawdown = (high - price) / high
    data: dict[str, Any] = {
        "drawdown_from_high": _value(
            drawdown,
            "Below 52-week high",
            basis="vs 52w high",
            formula="(52w high - price) / 52w high",
            unit="percent",
        ),
        "fifty_two_week_change": _value(
            _num(fund, "fifty_two_week_change"),
            "52-week price change (Yahoo)",
            basis="trailing 52 weeks",
            unit="percent",
        ),
    }

    dividend_yield, dividend_per_share, dividend_ttm_fact, dividend_conflicts = _dividend_leg(
        fund, price, provider
    )
    data["dividend_yield"] = dividend_yield
    data["dividend_per_share"] = dividend_per_share
    # D56: only present when the paid history diverges from dividendRate — an
    # agreeing figure emits no extra card.
    if dividend_ttm_fact is not None:
        data["dividend_per_share_ttm"] = dividend_ttm_fact
    conflicts.extend(dividend_conflicts)

    # D55: yfinance's growth is MRQ-YoY, not annual — label the basis so no
    # surface narrates a single strong quarter as full-year growth.
    data["revenue_growth"] = _value(
        _num(fund, "revenue_growth"),
        "Revenue growth",
        basis=_GROWTH_BASIS_MRQ_YOY,
        unit="percent",
    )
    data["earnings_growth"] = _value(
        _num(fund, "earnings_growth"),
        "Earnings growth",
        basis=_GROWTH_BASIS_MRQ_YOY,
        unit="percent",
    )

    # D66: only present when the quarterly-statement computation diverges from
    # the provider scalar — an agreeing figure emits no extra card, and the
    # provider values above are NEVER replaced (disclosure, not substitution).
    growth_facts, growth_conflicts = _growth_leg(fund, provider)
    data.update(growth_facts)
    conflicts.extend(growth_conflicts)

    # D68: cross-check yfinance insider/institution % against the exchange
    # shareholding pattern (attached upstream as ``ownership_exchange``). The
    # exchange promoter/institutions are surfaced as separately-labeled facts,
    # and a divergence flags a conflict carrying BOTH definitions + as-of dates.
    ownership_facts, ownership_conflicts = _ownership_leg(fund, provider)
    data.update(ownership_facts)
    conflicts.extend(ownership_conflicts)

    market_cap = _num(fund, "market_cap")
    shares = _num(fund, "shares_outstanding")
    if market_cap is not None and shares is not None and price is not None:
        implied_cap = price * shares
        if (
            implied_cap > 0
            and _relative_divergence(market_cap, implied_cap) > _MARKET_CAP_TOLERANCE
        ):
            conflicts.append(
                {
                    "field": "market_cap",
                    "sources": [
                        {"provider": provider, "value": market_cap},
                        {
                            "provider": "derived (price x shares outstanding)",
                            "value": round(implied_cap, 2),
                        },
                    ],
                    "note": (
                        "The provider market cap diverges more than 5% from "
                        "price x shares outstanding — the figures may be from "
                        "different sessions or share classes."
                    ),
                }
            )

    # R12 (D67): the resolver's canonical name vs the provider's company name —
    # a material disagreement (rename/mis-resolution) is FLAGGED, never picked.
    identity = identity_crosscheck.identity_conflict(
        canonical_name, fund.get("name"), provider=provider, symbol=symbol
    )
    if identity is not None:
        conflicts.append(identity)

    data["conflicts"] = conflicts
    return {"ok": True, "provider": "derived", "data": data}


#: The keys rendered into the synthesis prompt block, in display order.
_PROMPT_KEYS = (
    "drawdown_from_high",
    "fifty_two_week_change",
    "dividend_yield",
    "dividend_per_share",
    "dividend_per_share_ttm",
    "revenue_growth",
    "earnings_growth",
    "revenue_growth_computed",
    "earnings_growth_computed",
    "promoter_percent_exchange",
    "institutions_percent_exchange",
)

#: Growth keys rendered as a SIGNED percent in the prompt block (D67): a raw
#: fraction like ``32.863`` means +3286.3% (a tiny prior-year base), and the
#: narration leg halved it to "+32.9%" reading the number as an already-percent.
#: A signed, formatted percent ("+3286.3%") plus a small-base caution makes an
#: extreme figure unmistakable so the prose never mis-states it.
_GROWTH_PROMPT_KEYS = frozenset(
    {"revenue_growth", "earnings_growth", "revenue_growth_computed", "earnings_growth_computed"}
)

#: |growth fraction| above which the figure rides a tiny prior-year base — a
#: +3286% is arithmetically real but misleading quoted without the caveat.
_EXTREME_GROWTH_FRACTION = 5.0
_EXTREME_GROWTH_CAUTION = "extreme figure — tiny prior-year base; verify before quoting"


def _render(item: dict[str, Any], *, growth: bool = False) -> str | None:
    """One prompt line for a derived value, or ``None`` when the value is null.

    Growth values (``growth=True``) render as a SIGNED percent so an extreme
    fraction reads unmistakably as growth (``32.863`` → ``+3286.3%``, never the
    bare ``32.863`` the narration halved to ``+32.9%``); when the fraction's
    magnitude is extreme a small-base caution is appended.
    """
    value = item.get("value")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    unit = item.get("unit")
    if unit == "percent":
        rendered = f"{value * 100:+.1f}%" if growth else f"{value * 100:.2f}%"
    else:
        rendered = f"{value:,.2f}"
    line = f"- {item.get('label')}: {rendered}"
    if item.get("basis"):
        line += f" (basis: {item['basis']})"
    if item.get("formula"):
        line += f" [= {item['formula']}]"
    if growth and abs(value) > _EXTREME_GROWTH_FRACTION:
        line += f" — {_EXTREME_GROWTH_CAUTION}"
    return line


def prompt_block(derived: dict[str, Any] | None) -> str:
    """Render the derived leg as the METRIC FACTS block for synthesis prompts.

    Empty string when there is nothing to state (no leg / all values null) —
    callers append it conditionally and the prompt stays unchanged for runs
    with no structured coverage.
    """
    if not isinstance(derived, dict) or not derived.get("ok"):
        return ""
    data = derived.get("data")
    if not isinstance(data, dict):
        return ""
    lines: list[str] = []
    for key in _PROMPT_KEYS:
        item = data.get(key)
        if isinstance(item, dict):
            line = _render(item, growth=key in _GROWTH_PROMPT_KEYS)
            if line:
                lines.append(line)
    for conflict in data.get("conflicts") or []:
        if isinstance(conflict, dict) and conflict.get("note"):
            lines.append(f"- CONFLICT ({conflict.get('field')}): {conflict['note']}")
    if not lines:
        return ""
    return (
        "METRIC FACTS — use these labels and bases verbatim; figures not "
        "listed here must be cited to a source:\n" + "\n".join(lines)
    )


__all__ = ["derive_semantics", "prompt_block"]
