"""R10 (E8) — ``services.research.semantics``: the metric discipline layer.

Pins the BriefDerivedMetrics contract (types/brief.ts): drawdown-from-high is
computed (never confused with the Yahoo 52-week change), the dividend yield is
reconciled against dividend-per-share/price with the unit chaos resolved
EXPLICITLY (>25% divergence → a conflict and NO single dividend value), growth
figures carry their basis, the market-cap cross-check flags >5% disagreement,
and missing inputs yield null values — never a fabricated number. Also pins
the prompt block rendering and the snapshot hook that carries the derived leg
into every research path.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from services.research.semantics import derive_semantics, prompt_block


def _structured(
    *,
    price: float | None = 80.0,
    fund: dict[str, Any] | None = None,
    fund_ok: bool = True,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if price is not None:
        out["price"] = {"ok": True, "provider": "yfinance", "data": {"price": price}}
    base = {"fifty_two_week_high": 100.0}
    base.update(fund or {})
    out["fundamentals"] = {
        "ok": fund_ok,
        "provider": "yfinance",
        "data": base if fund_ok else None,
    }
    return out


def _derived(structured: dict[str, Any]) -> dict[str, Any]:
    leg = derive_semantics(structured, "IN")
    assert leg["ok"] is True
    assert leg["provider"] == "derived"
    return leg["data"]


def test_drawdown_from_high_is_computed_with_label_and_formula() -> None:
    data = _derived(_structured(price=80.0))
    dd = data["drawdown_from_high"]
    assert dd["value"] == 0.2  # (100 - 80) / 100
    assert dd["label"] == "Below 52-week high"
    assert dd["formula"] == "(52w high - price) / 52w high"
    assert dd["unit"] == "percent"


def test_fifty_two_week_change_keeps_its_own_label_never_drawdown() -> None:
    data = _derived(_structured(fund={"fifty_two_week_change": -0.35}))
    chg = data["fifty_two_week_change"]
    assert chg["value"] == -0.35
    assert chg["label"] == "52-week price change (Yahoo)"
    assert chg["label"] != data["drawdown_from_high"]["label"]


def test_missing_inputs_yield_null_never_fabricated() -> None:
    data = _derived(_structured(price=None, fund={"fifty_two_week_high": None}))
    assert data["drawdown_from_high"]["value"] is None
    assert data["fifty_two_week_change"]["value"] is None
    assert data["dividend_yield"]["value"] is None
    assert data["conflicts"] == []


# --- R13 JARVIS 2a: field_meta reasons on null derived metrics ----------------


def test_withheld_field_surfaces_reason_on_null_metric_and_prompt_block() -> None:
    """A field the correctness gate WITHHELD (nulled as implausible) carries its
    reason onto the derived null value AND into the synthesis prompt — never a
    silent absence the prose can round up to a world-absence claim."""
    structured = _structured(
        fund={
            "dividend_yield": None,
            "field_meta": {
                "dividend_yield": {
                    "status": "withheld",
                    "provider": "yfinance",
                    "reason": "dividend yield 55% implausible as a fraction of price",
                }
            },
        }
    )
    dy = _derived(structured)["dividend_yield"]
    assert dy["value"] is None
    assert dy["reason"] == "dividend yield 55% implausible as a fraction of price"
    block = prompt_block(derive_semantics(structured, "IN"))
    assert "not available — dividend yield 55% implausible" in block


def test_withheld_growth_states_reason_on_null() -> None:
    data = _derived(
        _structured(
            fund={
                "revenue_growth": None,
                "field_meta": {
                    "revenue_growth": {"status": "withheld", "reason": "growth 3286x implausible"}
                },
            }
        )
    )
    assert data["revenue_growth"]["value"] is None
    assert data["revenue_growth"]["reason"] == "growth 3286x implausible"


def test_withheld_without_reason_text_gets_default_withheld_phrase() -> None:
    data = _derived(
        _structured(
            fund={
                "fifty_two_week_change": None,
                "field_meta": {"fifty_two_week_change": {"status": "withheld"}},
            }
        )
    )
    assert data["fifty_two_week_change"]["reason"] == "provider value withheld as implausible"


def test_unavailable_field_states_a_gap_reason() -> None:
    data = _derived(
        _structured(
            fund={
                "earnings_growth": None,
                "field_meta": {"earnings_growth": {"status": "unavailable"}},
            }
        )
    )
    assert data["earnings_growth"]["reason"] == "the provider did not carry this field"


def test_real_value_carries_no_reason() -> None:
    data = _derived(_structured(fund={"fifty_two_week_change": -0.35}))
    assert "reason" not in data["fifty_two_week_change"]


def test_dividend_yield_reconciles_fraction_form() -> None:
    data = _derived(_structured(fund={"dividend_yield": 0.0125, "dividend_per_share": 1.0}))
    dy = data["dividend_yield"]
    assert dy["value"] == 1.0 / 80.0
    assert dy["basis"] == "fraction of price"
    assert data["dividend_per_share"]["value"] == 1.0
    assert data["conflicts"] == []


def test_dividend_yield_reconciles_percent_form_unit_chaos() -> None:
    # yfinance sometimes ships 1.25 meaning 1.25% — the percent reading agrees
    # with dps/price (1/80 = 1.25%), so it reconciles instead of conflicting.
    data = _derived(_structured(fund={"dividend_yield": 1.25, "dividend_per_share": 1.0}))
    assert data["dividend_yield"]["value"] == 1.0 / 80.0
    assert data["conflicts"] == []


def test_dividend_divergence_flags_conflict_and_emits_no_single_value() -> None:
    # The live E8 defect shape: a 55% yield next to a Rs 1 dividend on an
    # Rs 80 stock — no unit reading reconciles; flag, never pick.
    data = _derived(_structured(fund={"dividend_yield": 55.0, "dividend_per_share": 1.0}))
    assert data["dividend_yield"]["value"] is None
    assert data["dividend_per_share"]["value"] is None
    conflicts = data["conflicts"]
    assert len(conflicts) == 1
    assert conflicts[0]["field"] == "dividend_yield"
    assert len(conflicts[0]["sources"]) == 2
    assert conflicts[0]["note"]


def test_unverifiable_lone_yield_is_withheld_when_unit_ambiguous() -> None:
    # A lone 0.55 with no dps to verify: plausible as a fraction? 0.55 = 55%
    # of price — implausible; withheld (null), never guessed into a unit.
    data = _derived(_structured(fund={"dividend_yield": 0.55}))
    assert data["dividend_yield"]["value"] is None
    # A plausible fraction (1.2%) passes through.
    data2 = _derived(_structured(fund={"dividend_yield": 0.012}))
    assert data2["dividend_yield"]["value"] == 0.012


def test_growth_metrics_carry_quarterly_mrq_yoy_basis() -> None:
    # D55: yfinance revenueGrowth/earningsGrowth are MOST-RECENT-QUARTER vs the
    # same quarter a year ago — the basis must say so, not a bare "yoy" that
    # reads as annual.
    data = _derived(_structured(fund={"revenue_growth": 0.18, "earnings_growth": -0.05}))
    assert data["revenue_growth"] == {
        "value": 0.18,
        "label": "Revenue growth",
        "basis": "quarterly YoY (MRQ)",
        "unit": "percent",
    }
    assert data["earnings_growth"]["value"] == -0.05
    assert data["earnings_growth"]["basis"] == "quarterly YoY (MRQ)"


def test_dividend_ttm_divergence_flags_conflict_and_carries_paid_figure() -> None:
    # D56, the ABBOTINDIA shape: dividendRate reports Rs 525 (final only) while
    # the trailing-12m paid history sums to Rs 656 (525 final + 131 special).
    # >10% divergence flags a conflict AND surfaces the 656 paid figure.
    data = _derived(
        _structured(fund={"dividend_per_share": 525.0, "dividend_per_share_ttm": 656.0})
    )
    ttm = data["dividend_per_share_ttm"]
    assert ttm["value"] == 656.0
    assert ttm["label"] == "Dividend/share (trailing 12m paid)"
    assert ttm["basis"] == "corporate-action history"
    conflict_fields = [c["field"] for c in data["conflicts"]]
    assert "dividend_per_share" in conflict_fields
    div_conflict = next(c for c in data["conflicts"] if c["field"] == "dividend_per_share")
    assert {s["value"] for s in div_conflict["sources"]} == {525.0, 656.0}


def test_dividend_ttm_agreeing_emits_no_extra_card() -> None:
    # dividendRate and the paid history agree (525 == 525) → no conflict, no
    # extra fact.
    data = _derived(
        _structured(fund={"dividend_per_share": 525.0, "dividend_per_share_ttm": 525.0})
    )
    assert "dividend_per_share_ttm" not in data
    assert all(c["field"] != "dividend_per_share" for c in data["conflicts"])


def test_dividend_ttm_within_tolerance_emits_no_extra_card() -> None:
    # A <=10% gap (rounding / timing, not an omitted special) does not flag.
    data = _derived(
        _structured(fund={"dividend_per_share": 525.0, "dividend_per_share_ttm": 550.0})
    )
    assert "dividend_per_share_ttm" not in data
    assert all(c["field"] != "dividend_per_share" for c in data["conflicts"])


def test_dividend_ttm_absent_scalar_emits_no_card() -> None:
    # Paid history present but no dividendRate to diverge from → nothing to flag.
    data = _derived(_structured(fund={"dividend_per_share_ttm": 656.0}))
    assert "dividend_per_share_ttm" not in data
    assert all(c["field"] != "dividend_per_share" for c in data["conflicts"])


def test_growth_divergence_flags_conflict_and_never_replaces_provider_value() -> None:
    # D66, the ICICIBANK shape: yfinance revenueGrowth claims +66.9% MRQ YoY
    # while the quarterly income statements compute +2.0% on the same basis.
    # Beyond tolerance → a conflict carrying both values, bases, and the
    # quarter labels — and the provider value stays UNCHANGED (disclosure,
    # never substitution).
    data = _derived(
        _structured(
            fund={
                "revenue_growth": 0.669,
                "revenue_growth_computed": 0.02,
                "growth_computed_quarters": {"mrq": "2026-03-31", "prior": "2025-03-31"},
            }
        )
    )
    assert data["revenue_growth"]["value"] == 0.669  # provider value never replaced
    computed = data["revenue_growth_computed"]
    assert computed["value"] == 0.02
    assert computed["label"] == "Revenue growth (computed from quarterly statements)"
    assert computed["basis"] == "quarterly YoY (MRQ)"
    conflict = next(c for c in data["conflicts"] if c["field"] == "revenue_growth")
    assert {s["value"] for s in conflict["sources"]} == {0.669, 0.02}
    bases = {s["provider"]: s["basis"] for s in conflict["sources"]}
    assert bases["yfinance (revenueGrowth)"] == "mrq_yoy (provider-claimed)"
    assert bases["derived (quarterly income statement)"] == "quarterly YoY (MRQ)"
    assert conflict["quarters"] == {"mrq": "2026-03-31", "prior": "2025-03-31"}
    assert "2026-03-31 vs 2025-03-31" in conflict["note"]


def test_growth_sign_flip_flags_earnings_conflict() -> None:
    # D66, the SBIN shape: provider says earnings shrank (-3.1%) while the
    # statements compute +5.6% — an 8.7pp gap past the 2pp floor.
    data = _derived(
        _structured(fund={"earnings_growth": -0.031, "earnings_growth_computed": 0.056})
    )
    assert data["earnings_growth"]["value"] == -0.031
    conflict = next(c for c in data["conflicts"] if c["field"] == "earnings_growth")
    assert {s["value"] for s in conflict["sources"]} == {-0.031, 0.056}
    # No quarter labels attached upstream → none fabricated in the payload.
    assert "quarters" not in conflict


def test_growth_within_relative_tolerance_emits_nothing_extra() -> None:
    # 0.50 vs 0.46: Δ = 4pp but ≤ 10% of the larger magnitude (5pp) → agree.
    data = _derived(_structured(fund={"revenue_growth": 0.50, "revenue_growth_computed": 0.46}))
    assert "revenue_growth_computed" not in data
    assert all(c["field"] != "revenue_growth" for c in data["conflicts"])


def test_growth_within_absolute_floor_emits_nothing_extra() -> None:
    # 1.0% vs 2.5%: relative gap is 60% but Δ = 1.5pp ≤ the 2pp absolute floor
    # ("whichever is larger") — small-base noise never flags.
    data = _derived(_structured(fund={"earnings_growth": 0.010, "earnings_growth_computed": 0.025}))
    assert "earnings_growth_computed" not in data
    assert all(c["field"] != "earnings_growth" for c in data["conflicts"])


def test_growth_missing_either_leg_is_a_no_op() -> None:
    # No computed figure → nothing to check; no provider scalar → nothing to
    # check either. Absence is honest — no conflict is fabricated.
    data = _derived(_structured(fund={"revenue_growth": 0.18}))
    assert "revenue_growth_computed" not in data
    assert data["conflicts"] == []
    data2 = _derived(_structured(fund={"revenue_growth_computed": 0.02}))
    assert "revenue_growth_computed" not in data2
    assert data2["conflicts"] == []


def test_growth_conflict_reaches_the_prompt_block() -> None:
    leg = derive_semantics(
        _structured(
            fund={
                "revenue_growth": 0.669,
                "revenue_growth_computed": 0.02,
                "growth_computed_quarters": {"mrq": "2026-03-31", "prior": "2025-03-31"},
            }
        ),
        "IN",
    )
    block = prompt_block(leg)
    # Growth renders as a SIGNED percent (D67) so an extreme fraction can never be
    # misread as an already-percent number.
    assert "Revenue growth: +66.9%" in block  # the provider value, unreplaced, signed
    assert "Revenue growth (computed from quarterly statements): +2.0%" in block
    assert "CONFLICT (revenue_growth):" in block


def test_prompt_block_renders_extreme_growth_fraction_signed_with_caution() -> None:
    """D67: SIMPLXREA revenue_growth=32.863 is a FRACTION (+3286.3%) that the
    narration halved to "+32.9%", reading the raw number as an already-percent.
    The prompt block must render growth as a formatted SIGNED percent ("+3286.3%")
    and, for an extreme magnitude, append a tiny-prior-year-base caution — never
    the bare "32.863"."""
    leg = derive_semantics(_structured(fund={"revenue_growth": 32.863}), "IN")
    block = prompt_block(leg)
    assert "+3286.3%" in block
    assert "extreme figure" in block
    assert "verify before quoting" in block
    assert "32.863" not in block  # the raw fraction never leaks
    # A normal-magnitude growth stays signed but carries NO extreme caution.
    normal = prompt_block(derive_semantics(_structured(fund={"revenue_growth": 0.18}), "IN"))
    assert "Revenue growth: +18.0%" in normal
    assert "extreme figure" not in normal


def test_market_cap_cross_check_flags_beyond_five_percent() -> None:
    # price 80 x 1e9 shares = 8e10; provider says 1e11 → >5% out → conflict.
    data = _derived(_structured(fund={"market_cap": 1e11, "shares_outstanding": 1e9}))
    fields = [c["field"] for c in data["conflicts"]]
    assert "market_cap" in fields
    # Within tolerance → no conflict.
    data2 = _derived(_structured(fund={"market_cap": 8.2e10, "shares_outstanding": 1e9}))
    assert all(c["field"] != "market_cap" for c in data2["conflicts"])


def test_failed_legs_yield_all_null_data_never_a_crash() -> None:
    data = _derived(_structured(price=None, fund_ok=False))
    assert all(
        data[key]["value"] is None
        for key in (
            "drawdown_from_high",
            "fifty_two_week_change",
            "dividend_yield",
            "dividend_per_share",
            "revenue_growth",
            "earnings_growth",
        )
    )
    # Tolerates entirely empty/garbled structured maps too.
    assert derive_semantics({}, None)["ok"] is True
    assert derive_semantics({"price": "garbage"}, None)["ok"] is True


def test_wire_string_numbers_are_tolerated() -> None:
    # Arbitrary-precision numbers cross the wire as strings (CLAUDE.md).
    structured = _structured(fund={"fifty_two_week_high": "100.0"})
    structured["price"]["data"]["price"] = "80"
    data = _derived(structured)
    assert data["drawdown_from_high"]["value"] == 0.2


# --- prompt_block -------------------------------------------------------------


def test_prompt_block_renders_labels_bases_and_conflicts_verbatim() -> None:
    leg = derive_semantics(
        _structured(fund={"dividend_yield": 55.0, "dividend_per_share": 1.0}), "IN"
    )
    block = prompt_block(leg)
    assert block.startswith("METRIC FACTS — use these labels and bases verbatim")
    assert "Below 52-week high: 20.00%" in block
    assert "(basis: vs 52w high)" in block
    assert "CONFLICT (dividend_yield):" in block


def test_prompt_block_is_empty_for_absent_or_all_null_leg() -> None:
    assert prompt_block(None) == ""
    assert prompt_block({"ok": False}) == ""
    empty = derive_semantics({}, None)
    assert prompt_block(empty) == ""


# --- the ONE hook: snapshot_structured carries the derived leg -----------------


def test_snapshot_structured_attaches_the_derived_leg() -> None:
    from services.research.fast import snapshot_structured

    async def tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        if name == "price_data":
            return {"ok": True, "provider": "yfinance", "quote": {"symbol": "X", "price": 80.0}}
        if name == "fundamentals":
            return {
                "ok": True,
                "fundamentals": {
                    "symbol": "X",
                    "provider": "yfinance",
                    "fifty_two_week_high": 100.0,
                },
            }
        raise AssertionError(f"unexpected tool {name}")

    snap = asyncio.run(snapshot_structured(tool, "X", region="IN"))
    assert set(snap) == {"price", "fundamentals", "derived"}
    assert snap["derived"]["provider"] == "derived"
    assert snap["derived"]["data"]["drawdown_from_high"]["value"] == 0.2


def test_identity_conflict_rides_derived_conflicts() -> None:
    """D67 wire-up: a materially different provider name vs the resolver's
    canonical name surfaces as an identity conflict in derived.conflicts."""
    structured = {
        "price": {"ok": True, "provider": "nse", "data": {"price": 100.0}},
        "fundamentals": {
            "ok": True,
            "provider": "yfinance",
            "data": {"name": "Gujarat Energy Limited"},
        },
    }
    derived = derive_semantics(
        structured, "IN", canonical_name="Gujarat Gas Limited", symbol="GUJGASLTD.NS"
    )
    kinds = [c.get("kind") for c in derived["data"]["conflicts"]]
    assert "identity_conflict" in kinds
    conflict = next(c for c in derived["data"]["conflicts"] if c.get("kind") == "identity_conflict")
    assert conflict["symbol"] == "GUJGASLTD.NS"
    assert any("Gujarat Energy Limited" in str(s["value"]) for s in conflict["sources"])


def test_identity_agreement_stays_silent() -> None:
    structured = {
        "price": {"ok": True, "provider": "nse", "data": {"price": 100.0}},
        "fundamentals": {
            "ok": True,
            "provider": "yfinance",
            "data": {"name": "Deepak Nitrite Ltd"},
        },
    }
    derived = derive_semantics(
        structured, "IN", canonical_name="Deepak Nitrite Limited", symbol="DEEPAKNTR.NS"
    )
    assert all(c.get("kind") != "identity_conflict" for c in derived["data"]["conflicts"])


# --- ownership cross-check (R13 / D68) --------------------------------------
#
# yfinance heldPercentInsiders/heldPercentInstitutions vs the exchange
# shareholding pattern attached upstream as ``ownership_exchange``. The R13
# probe: institutions ~141x overstated (yf 8.455% vs BSE 0.06%) and insiders
# overstating the promoter group by 2.5-5.4pp on NSE/BSE names.


def _ownership_fund(*, insiders=None, institutions=None, exchange=None) -> dict[str, Any]:
    fund: dict[str, Any] = {}
    if insiders is not None:
        fund["held_percent_insiders"] = insiders
    if institutions is not None:
        fund["held_percent_institutions"] = institutions
    if exchange is not None:
        fund["ownership_exchange"] = exchange
    return fund


def test_ownership_institutions_141x_and_promoter_drift_both_fire() -> None:
    data = _derived(
        _structured(
            fund=_ownership_fund(
                insiders=0.75806,
                institutions=0.08455,
                exchange={
                    "promoter_percent": 73.29,
                    "institutions_percent": 0.06,
                    "public_percent": 26.71,
                    "as_of_quarter": "2026-06-30",
                    "source": "BSE",
                },
            )
        )
    )
    # separately-labeled exchange facts, with the as-of quarter in the basis
    assert data["promoter_percent_exchange"]["value"] == 0.7329
    assert data["promoter_percent_exchange"]["label"] == "Promoter group (exchange filing)"
    assert "2026-06-30" in data["promoter_percent_exchange"]["basis"]
    assert data["institutions_percent_exchange"]["value"] == 0.0006
    # institutions 141x → data_conflict carrying BOTH values + BOTH definitions
    inst = next(c for c in data["conflicts"] if c["field"] == "held_percent_institutions")
    assert inst["conflict_kind"] == "data_conflict"
    assert inst["kind"] == "ownership_conflict"
    values = {s["value"] for s in inst["sources"]}
    assert 8.455 in values and 0.06 in values
    assert len({s["basis"] for s in inst["sources"]}) == 2
    # promoter 2.5pp drift (insiders superset, small gap) → definitional_expected
    prom = next(c for c in data["conflicts"] if c["field"] == "held_percent_insiders")
    assert prom["conflict_kind"] == "definitional_expected"
    assert "2026-06-30" in prom["note"]
    assert {s["value"] for s in prom["sources"]} == {75.806, 73.29}


def test_ownership_kiriindus_promoter_5pp_fires_data_conflict() -> None:
    # insiders 41.714% vs the strict quarter-end promoter 36.72% → ~5pp gap:
    # too wide to be pure definitional drift, so a data_conflict.
    data = _derived(
        _structured(
            fund=_ownership_fund(
                insiders=0.41714,
                exchange={
                    "promoter_percent": 36.72,
                    "as_of_quarter": "2026-03-31",
                    "source": "NSE",
                },
            )
        )
    )
    prom = next(c for c in data["conflicts"] if c["field"] == "held_percent_insiders")
    assert prom["conflict_kind"] == "data_conflict"
    assert prom["sources"][0]["value"] == 41.714
    assert prom["sources"][1]["value"] == 36.72
    # the filing carried no institutions category → no institutions fact/conflict
    assert "institutions_percent_exchange" not in data
    assert all(c["field"] != "held_percent_institutions" for c in data["conflicts"])


def test_ownership_unseen_shape_institutions_3x_off_fires() -> None:
    # A case the fix was NOT written against: promoter agrees, institutions 3x off.
    data = _derived(
        _structured(
            fund=_ownership_fund(
                insiders=0.401,
                institutions=0.03,
                exchange={
                    "promoter_percent": 39.5,
                    "institutions_percent": 1.0,
                    "as_of_quarter": "2026-06-30",
                    "source": "NSE",
                },
            )
        )
    )
    assert all(c["field"] != "held_percent_insiders" for c in data["conflicts"])  # 0.6pp: agrees
    inst = next(c for c in data["conflicts"] if c["field"] == "held_percent_institutions")
    assert inst["conflict_kind"] == "data_conflict"
    assert {s["value"] for s in inst["sources"]} == {3.0, 1.0}


def test_ownership_agreeing_emits_facts_but_no_conflict() -> None:
    data = _derived(
        _structured(
            fund=_ownership_fund(
                insiders=0.501,
                institutions=0.205,
                exchange={
                    "promoter_percent": 50.0,
                    "institutions_percent": 20.55,
                    "as_of_quarter": "2026-03-31",
                    "source": "BSE",
                },
            )
        )
    )
    assert data["promoter_percent_exchange"]["value"] == 0.5
    assert data["institutions_percent_exchange"]["value"] == 0.2055
    assert all(
        c["field"] not in ("held_percent_insiders", "held_percent_institutions")
        for c in data["conflicts"]
    )


def test_ownership_absent_exchange_leg_is_a_noop() -> None:
    data = _derived(_structured(fund=_ownership_fund(insiders=0.5, institutions=0.2)))
    assert "promoter_percent_exchange" not in data
    assert "institutions_percent_exchange" not in data
    assert data["conflicts"] == []


def test_ownership_facts_and_conflict_reach_the_prompt_block() -> None:
    structured = _structured(
        fund=_ownership_fund(
            insiders=0.75806,
            institutions=0.08455,
            exchange={
                "promoter_percent": 73.29,
                "institutions_percent": 0.06,
                "as_of_quarter": "2026-06-30",
                "source": "BSE",
            },
        )
    )
    block = prompt_block(derive_semantics(structured, "IN"))
    assert "Promoter group (exchange filing)" in block
    assert "73.29%" in block
    assert "CONFLICT (held_percent_institutions)" in block


# --- dividend: direction + declared-not-yet-paid (R11 D56 / R13 D57) --------


def test_dividend_scalar_above_paid_uses_inflation_not_omission_wording() -> None:
    # dividendRate (20.0) INFLATED above the trailing paid (14.6) by >10%: the
    # note must NOT say "omit a special dividend" (backwards) — it says the
    # scalar anticipates / rides a forward basis.
    data = _derived(
        _structured(price=400.0, fund={"dividend_per_share": 20.0, "dividend_per_share_ttm": 14.6})
    )
    div = next(c for c in data["conflicts"] if c["field"] == "dividend_per_share")
    assert div["conflict_kind"] == "data_conflict"
    assert "EXCEEDS" in div["note"] and "anticipate" in div["note"]
    assert "omit a special dividend" not in div["note"]


def test_dividend_pfc_declared_unpaid_surfaced_and_reconciled() -> None:
    # PFC: dividendRate 15.8 ≈ trailing PAID 14.6 (7.6% < 10% → NO D56 conflict),
    # but a declared FINAL dividend of ₹3.95 (record 2026-07-31, future) is unpaid.
    data = _derived(
        _structured(
            price=400.0,
            fund={
                "dividend_per_share": 15.8,
                "dividend_per_share_ttm": 14.6,
                "dividend_declared": {
                    "amount": 3.95,
                    "record_date": "2026-07-31",
                    "subject": "Dividend - Rs 3.95 Per Share",
                },
            },
        )
    )
    # the declared-not-yet-paid dividend is its own labeled fact
    declared = data["dividend_declared"]
    assert declared["value"] == 3.95
    assert "2026-07-31" in declared["label"]
    # the trailing figure is relabeled PAID so it never reads as the full figure
    assert data["dividend_per_share_ttm"]["label"] == "Dividend/share (trailing 12m PAID)"
    # no scalar-vs-paid conflict fires (7.6% is below the 10% band)
    assert all(c["field"] != "dividend_per_share" for c in data["conflicts"])
    # the PFC arithmetic is reconciled explicitly (14.6 + 3.95 = 18.55)
    recon = next(c for c in data["conflicts"] if c.get("kind") == "dividend_reconciliation")
    assert recon["conflict_kind"] == "definitional_expected"
    assert "18.55" in recon["note"] and "3.95" in recon["note"] and "14.6" in recon["note"]


def test_dividend_ioc_omission_direction_plus_declared_fact() -> None:
    # IOC: dividendRate 8.25 is BELOW the trailing PAID 10.0 (17.5% > 10% → D56
    # fires, OMISSION wording) AND a declared final dividend ₹1.25 (future).
    data = _derived(
        _structured(
            price=140.0,
            fund={
                "dividend_per_share": 8.25,
                "dividend_per_share_ttm": 10.0,
                "dividend_declared": {
                    "amount": 1.25,
                    "record_date": "2026-08-14",
                    "subject": "Dividend - Rs 1.25 Per Share",
                },
            },
        )
    )
    div = next(c for c in data["conflicts"] if c["field"] == "dividend_per_share")
    assert div["conflict_kind"] == "data_conflict"
    assert "BELOW" in div["note"] and "omit a special dividend" in div["note"]
    assert data["dividend_per_share_ttm"]["label"] == "Dividend/share (trailing 12m PAID)"
    assert data["dividend_declared"]["value"] == 1.25


def test_dividend_declared_absent_leaves_ttm_label_lowercase() -> None:
    # No declared dividend attached → the diverging paid fact keeps its plain label.
    data = _derived(
        _structured(fund={"dividend_per_share": 525.0, "dividend_per_share_ttm": 656.0})
    )
    assert data["dividend_per_share_ttm"]["label"] == "Dividend/share (trailing 12m paid)"
    assert not any(c.get("kind") == "dividend_reconciliation" for c in data["conflicts"])


# --- conflict kinds: definitional vs data (R13 / D69) -----------------------


def test_bank_revenue_growth_divergence_is_definitional_expected() -> None:
    # A financial-sector (bank) revenue-growth divergence rides different revenue
    # lines (interest income vs total income) — a DEFINITIONAL mismatch.
    data = _derived(
        _structured(
            fund={
                "sector": "Financial Services",
                "revenue_growth": 0.669,
                "revenue_growth_computed": 0.02,
            }
        )
    )
    conflict = next(c for c in data["conflicts"] if c["field"] == "revenue_growth")
    assert conflict["conflict_kind"] == "definitional_expected"
    assert conflict["kind"] == "growth_conflict"


def test_bank_earnings_growth_divergence_stays_data_conflict() -> None:
    # Earnings (net income) is not definitionally ambiguous the way bank revenue
    # is — even for a financial, an earnings divergence stays a data_conflict.
    data = _derived(
        _structured(
            fund={
                "sector": "Financial Services",
                "earnings_growth": -0.031,
                "earnings_growth_computed": 0.056,
            }
        )
    )
    conflict = next(c for c in data["conflicts"] if c["field"] == "earnings_growth")
    assert conflict["conflict_kind"] == "data_conflict"


def test_non_bank_revenue_growth_divergence_is_data_conflict() -> None:
    data = _derived(
        _structured(
            fund={
                "sector": "Technology",
                "revenue_growth": 0.669,
                "revenue_growth_computed": 0.02,
            }
        )
    )
    conflict = next(c for c in data["conflicts"] if c["field"] == "revenue_growth")
    assert conflict["conflict_kind"] == "data_conflict"


def test_market_cap_conflict_defaults_to_data_conflict() -> None:
    # price 80 x shares 10 = 800 implied vs provider market_cap 2000 → >5% gap.
    data = _derived(
        _structured(price=80.0, fund={"market_cap": 2000.0, "shares_outstanding": 10.0})
    )
    conflict = next(c for c in data["conflicts"] if c["field"] == "market_cap")
    assert conflict["conflict_kind"] == "data_conflict"


def test_identity_conflict_keeps_its_type_and_defaults_nature_to_data() -> None:
    leg = derive_semantics(
        _structured(fund={"name": "Gujarat Energy Limited"}),
        "IN",
        canonical_name="Gujarat Gas Limited",
        symbol="GUJGASLTD",
    )
    identity = next(c for c in leg["data"]["conflicts"] if c["field"] == "identity")
    assert identity["kind"] == "identity_conflict"  # TYPE discriminator preserved
    assert identity["conflict_kind"] == "data_conflict"  # NATURE default (orthogonal)


# --- attach-key parity: the literal keys track their module constants ----------


def test_semantics_attach_keys_match_the_module_constants() -> None:
    # ``semantics`` reads the R13 cross-check wires by LITERAL key (to stay free
    # of pandas/provider imports); this pins those literals against the source-of-
    # truth module constants so the linkage can never silently drift.
    from services import earnings_quality, market_cap_witness
    from services.research import range_check, semantics

    assert semantics._EARNINGS_KEY == earnings_quality.EARNINGS_KEY
    assert semantics._RANGE_KEY == range_check.RANGE_KEY
    assert semantics._MCAP_WITNESS_KEY == market_cap_witness.MCAP_WITNESS_KEY


# --- reported-vs-adjusted earnings (R13 / D70) ---------------------------------
#
# The TI trap: yfinance PE ~460 / ROE ~1.08% on REPORTED earnings (₹20.9 Cr,
# crushed by Imperial-Blue one-offs) vs the world's ~43.9 / ~13.1% on the
# ADJUSTED basis (~₹232 Cr). Both correct on different bases — flag, never pick.

_TI_EARNINGS = {
    "reported_net_income": 2.087e8,
    "normalized_income": 2.32e9,
    "unusual_items": -2.11e9,
    "tax_effect": None,
    "one_off_net": 2.087e8 - 2.32e9,
    "distortion_fraction": abs(2.087e8 - 2.32e9) / 2.087e8,
    "period": "2026-03-31",
}


def test_ti_shape_one_off_distortion_fires_definitional_conflict() -> None:
    data = _derived(
        _structured(
            fund={
                "currency": "INR",
                "pe_ratio": 460.0,
                "roe": 0.0108,
                "earnings_quality": dict(_TI_EARNINGS),
            }
        )
    )
    # both net-income bases surfaced as separately-labeled facts
    assert data["reported_net_income"]["value"] == pytest.approx(2.087e8)
    assert data["reported_net_income"]["label"] == "Net income (reported, incl. one-offs)"
    assert data["normalized_net_income"]["value"] == pytest.approx(2.32e9)
    # the conflict names the PE/ROE/EPS basis seam — definitional, both correct
    eq = next(c for c in data["conflicts"] if c["field"] == "earnings_quality")
    assert eq["kind"] == "earnings_quality_conflict"
    assert eq["conflict_kind"] == "definitional_expected"
    assert {round(s["value"], 2) for s in eq["sources"]} == {round(2.087e8, 2), round(2.32e9, 2)}
    # the note carries real numbers (compact ₹Cr), the % and the direction
    assert "₹20.9 Cr" in eq["note"]
    assert "₹232.0 Cr" in eq["note"]
    assert "DEPRESSED" in eq["note"]  # one-off CHARGES depressed reported earnings
    assert "PE/ROE/EPS" in eq["note"]


def test_ti_shape_one_off_gain_uses_inflation_wording() -> None:
    # The PML shape: a one-off GAIN inflates reported earnings (reported > adjusted).
    fund = {
        "currency": "INR",
        "pe_ratio": 0.59,
        "earnings_quality": {
            "reported_net_income": 3.0e9,
            "normalized_income": 4.0e8,
            "one_off_net": 3.0e9 - 4.0e8,  # positive → gains
            "distortion_fraction": abs(3.0e9 - 4.0e8) / 3.0e9,
            "period": "2026-03-31",
        },
    }
    data = _derived(_structured(fund=fund))
    eq = next(c for c in data["conflicts"] if c["field"] == "earnings_quality")
    assert "INFLATED" in eq["note"]
    assert "DEPRESSED" not in eq["note"]


def test_clean_earnings_stay_silent() -> None:
    fund = {
        "pe_ratio": 20.0,
        "earnings_quality": {
            "reported_net_income": 1.0e9,
            "normalized_income": 9.8e8,
            "one_off_net": 2.0e7,
            "distortion_fraction": 0.02,
            "period": "2026-03-31",
        },
    }
    data = _derived(_structured(fund=fund))
    assert "reported_net_income" not in data
    assert "normalized_net_income" not in data
    assert all(c["field"] != "earnings_quality" for c in data["conflicts"])


def test_earnings_quality_absent_leg_is_a_noop() -> None:
    data = _derived(_structured(fund={"pe_ratio": 30.0}))
    assert "reported_net_income" not in data
    assert all(c["field"] != "earnings_quality" for c in data["conflicts"])


def test_earnings_quality_conflict_reaches_the_prompt_block() -> None:
    leg = derive_semantics(
        _structured(
            fund={"currency": "INR", "pe_ratio": 460.0, "earnings_quality": dict(_TI_EARNINGS)}
        ),
        "IN",
    )
    block = prompt_block(leg)
    assert "CONFLICT (earnings_quality)" in block
    assert "Net income (reported, incl. one-offs)" in block


# --- 52-week range cross-check (R13 / D71) -------------------------------------
#
# BI: provider 52w high ~75 while the exchange series the chart renders shows
# ~116. Recompute from the app's own history and flag the wrong provider bound.


def test_bi_shape_range_high_divergence_fires() -> None:
    data = _derived(
        _structured(
            fund={
                "fifty_two_week_high": 75.0,
                "fifty_two_week_low": 50.0,
                "range_52w_exchange": {
                    "high": 116.0,
                    "low": 50.0,
                    "coverage_days": 359,
                    "bars": 360,
                    "source": "nse_direct",
                },
            }
        )
    )
    # the exchange high is surfaced beside the provider scalar (never replaced)
    assert data["fifty_two_week_high_exchange"]["value"] == 116.0
    assert data["fifty_two_week_high_exchange"]["label"] == "52-week high (exchange series)"
    # the low agrees (50 vs 50) → no low fact, no low conflict
    assert "fifty_two_week_low_exchange" not in data
    rc = next(c for c in data["conflicts"] if c["field"] == "fifty_two_week_high")
    assert rc["kind"] == "range_conflict"
    assert rc["conflict_kind"] == "data_conflict"
    assert {s["value"] for s in rc["sources"]} == {75.0, 116.0}
    assert "nse_direct" in rc["note"]
    assert all(c["field"] != "fifty_two_week_low" for c in data["conflicts"])


def test_pml_shape_both_bounds_diverge() -> None:
    # PML-shaped: provider high 645 vs exchange 823 (21.6%) and provider low 451
    # vs exchange 380 (15.7%) — both bounds clearly past the 10% band.
    data = _derived(
        _structured(
            fund={
                "fifty_two_week_high": 645.0,
                "fifty_two_week_low": 451.0,
                "range_52w_exchange": {"high": 823.0, "low": 380.0, "source": "bse"},
            }
        )
    )
    assert data["fifty_two_week_high_exchange"]["value"] == 823.0
    assert data["fifty_two_week_low_exchange"]["value"] == 380.0
    fields = {c["field"] for c in data["conflicts"] if c.get("kind") == "range_conflict"}
    assert fields == {"fifty_two_week_high", "fifty_two_week_low"}


def test_agreeing_range_stays_silent() -> None:
    data = _derived(
        _structured(
            fund={
                "fifty_two_week_high": 114.0,  # 1.7% off 116 → within tolerance
                "fifty_two_week_low": 50.5,  # 1% off 50 → within tolerance
                "range_52w_exchange": {"high": 116.0, "low": 50.0, "source": "bse"},
            }
        )
    )
    assert "fifty_two_week_high_exchange" not in data
    assert "fifty_two_week_low_exchange" not in data
    assert all(c.get("kind") != "range_conflict" for c in data["conflicts"])


def test_range_absent_leg_is_a_noop() -> None:
    data = _derived(_structured(fund={"fifty_two_week_high": 75.0, "fifty_two_week_low": 50.0}))
    assert "fifty_two_week_high_exchange" not in data
    assert all(c.get("kind") != "range_conflict" for c in data["conflicts"])


# --- market-cap share-count witness (R13 / D72) --------------------------------
#
# RBA: provider mcap ~₹5,233 Cr vs price × the BSE-derived share count ~₹4,236 Cr
# (23% high, live promoter-stake churn). Breaks the circularity of the provider-
# share-count check.

_RBA_WITNESS = {
    "shares_outstanding": 582876028,
    "source": "BSE ListOfScripData (bundled India master)",
    "scrip_code": "543248",
}


def test_rba_shape_market_cap_witness_fires() -> None:
    data = _derived(
        _structured(
            price=72.7, fund={"market_cap": 5.233e10, "market_cap_witness": dict(_RBA_WITNESS)}
        )
    )
    implied = 72.7 * 582876028
    assert data["market_cap_witness"]["value"] == pytest.approx(round(implied, 2))
    mcw = next(c for c in data["conflicts"] if c.get("kind") == "market_cap_witness_conflict")
    assert mcw["field"] == "market_cap"
    assert mcw["conflict_kind"] == "data_conflict"
    assert mcw["sources"][0]["value"] == pytest.approx(round(5.233e10, 2))
    assert mcw["sources"][1]["value"] == pytest.approx(round(implied, 2))
    assert "circular" in mcw["note"]


def test_agreeing_market_cap_witness_stays_silent() -> None:
    # provider mcap ≈ price × witness shares → no witness conflict.
    data = _derived(
        _structured(
            price=72.7, fund={"market_cap": 4.24e10, "market_cap_witness": dict(_RBA_WITNESS)}
        )
    )
    assert "market_cap_witness" not in data
    assert all(c.get("kind") != "market_cap_witness_conflict" for c in data["conflicts"])


def test_market_cap_witness_needs_price_and_witness() -> None:
    # No price → cannot form the witness product; no witness leg → nothing.
    no_price = _derived(
        _structured(
            price=None, fund={"market_cap": 5.233e10, "market_cap_witness": dict(_RBA_WITNESS)}
        )
    )
    assert all(c.get("kind") != "market_cap_witness_conflict" for c in no_price["conflicts"])
    no_witness = _derived(_structured(price=72.7, fund={"market_cap": 5.233e10}))
    assert all(c.get("kind") != "market_cap_witness_conflict" for c in no_witness["conflicts"])
