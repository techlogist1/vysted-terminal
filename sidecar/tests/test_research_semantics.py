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


def test_growth_metrics_carry_yoy_basis() -> None:
    data = _derived(_structured(fund={"revenue_growth": 0.18, "earnings_growth": -0.05}))
    assert data["revenue_growth"] == {
        "value": 0.18,
        "label": "Revenue growth",
        "basis": "yoy",
        "unit": "percent",
    }
    assert data["earnings_growth"]["value"] == -0.05
    assert data["earnings_growth"]["basis"] == "yoy"


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
