"""Tests for the screener formula expression layer (R7 hackability Pillar 3).

Four surfaces:

  - ``compile_formula`` / ``validate_formula`` — the restricted recursive-descent
    grammar: fields + aliases, arithmetic, comparisons, and/or/not, abs/min/max,
    positioned errors (caret column), hostile-input caps.
  - ``evaluate_formula`` — per-row semantics: truth, div-by-zero → no-match,
    missing field → honest skip signal, quote-derived fields without a quote.
  - ``run_screener`` integration — the formula AND-combines with criteria; a row
    missing a referenced field lands in the skip ledger as ``missing_field:<f>``
    with ``skipped_count == len(skip_details)`` intact.
  - Request/router boundary — ScreenerRequest rejects an unparseable formula
    with the caret column in the message; ``POST /screener/formula/validate``
    returns ``ok``/``error``/``position``/``fields`` and never a 4xx.

NOTE: the grammar is hand-mirrored in ``src/lib/screener-expr.ts``; the parity
vectors in ``src/lib/screener-expr.test.ts`` track the cases asserted here.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import ScreenerRequest
from services import data_cache, fundamentals_store, screener
from services.screener_formula import (
    MAX_NESTING_DEPTH,
    MAX_TOKENS,
    NUMERIC_FIELDS,
    FormulaError,
    compile_formula,
    evaluate_formula,
    validate_formula,
)


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Point the data cache at a tmp file per test (run_screener tests hit it)."""
    data_cache.reset_for_tests(tmp_path / "screener_formula_test_cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)


def _fundamentals(symbol: str = "AAA", **overrides: Any) -> Fundamentals:
    payload: dict[str, Any] = {
        "symbol": symbol,
        "name": f"{symbol} Inc.",
        "sector": "Technology",
        "market_cap": 200e9,
        "pe_ratio": 12.0,
        "roe": 0.25,
        "roa": 0.10,
        "dividend_yield": 0.02,
        "debt_to_equity": 0.5,
        "provider": "test",
    }
    payload.update(overrides)
    return Fundamentals(**payload)


def _quote(symbol: str = "AAA", price: float = 100.0, change_percent: float = 1.5) -> Quote:
    return Quote(
        symbol=symbol,
        price=price,
        change=price * change_percent / 100.0,
        change_percent=change_percent,
        volume=1_000_000.0,
        currency="USD",
        market_state="open",
        timestamp=datetime.now(tz=UTC),
        provider="test",
    )


# ---------------------------------------------------------------------------
# Grammar — happy paths
# ---------------------------------------------------------------------------


class TestCompile:
    def test_simple_comparison(self) -> None:
        compiled = compile_formula("pe_ratio < 15")
        assert compiled.fields == frozenset({"pe_ratio"})

    def test_aliases_resolve_to_canonical_fields(self) -> None:
        compiled = compile_formula("pe < 15 and marketCap > 1e9 and pb < 2")
        assert compiled.fields == frozenset({"pe_ratio", "market_cap", "price_to_book"})

    def test_field_match_is_case_insensitive(self) -> None:
        assert compile_formula("PE_RATIO < 15").fields == frozenset({"pe_ratio"})

    def test_every_canonical_numeric_field_parses(self) -> None:
        for field in NUMERIC_FIELDS:
            assert compile_formula(f"{field} > 0").fields == frozenset({field})

    def test_arithmetic_boolean_and_functions(self) -> None:
        compiled = compile_formula(
            "(market_cap / volume > 1e6 or not (pe < 10)) "
            "and max(roe, roa) > 0.15 and abs(change_percent_1d) < 2 "
            "and min(pe_ratio, forward_pe) > 0"
        )
        assert "volume" in compiled.fields
        assert "roa" in compiled.fields

    def test_scientific_notation_and_precedence(self) -> None:
        # 1 + 2 * 3 == 7 (not 9) — term binds tighter than sum.
        compiled = compile_formula("market_cap > 1 + 2 * 3e0")
        assert compiled.fields == frozenset({"market_cap"})

    def test_validate_formula_ok_shape(self) -> None:
        report = validate_formula("roe > 0.2 and pe < 15")
        assert report == {
            "ok": True,
            "error": None,
            "position": None,
            "fields": ["pe_ratio", "roe"],
        }


# ---------------------------------------------------------------------------
# Grammar — positioned errors (the caret contract)
# ---------------------------------------------------------------------------


class TestErrors:
    def test_unknown_field_position_points_at_the_identifier(self) -> None:
        src = "pe < 15 and bogus > 1"
        with pytest.raises(FormulaError) as exc_info:
            compile_formula(src)
        assert exc_info.value.position == src.index("bogus")
        assert "unknown field 'bogus'" in str(exc_info.value)

    def test_unexpected_character_position(self) -> None:
        with pytest.raises(FormulaError) as exc_info:
            compile_formula("pe < 15 $ roe > 1")
        assert exc_info.value.position == 8

    def test_unclosed_paren_positions_at_end(self) -> None:
        src = "(pe < 15"
        with pytest.raises(FormulaError) as exc_info:
            compile_formula(src)
        assert exc_info.value.position == len(src)

    def test_empty_formula(self) -> None:
        with pytest.raises(FormulaError, match="empty formula"):
            compile_formula("   ")

    def test_top_level_must_be_boolean(self) -> None:
        with pytest.raises(FormulaError, match="comparison or boolean"):
            compile_formula("pe_ratio + 1")

    def test_chained_comparison_rejected(self) -> None:
        src = "1 < pe < 15"
        with pytest.raises(FormulaError) as exc_info:
            compile_formula(src)
        assert "combine with 'and'" in str(exc_info.value)
        assert exc_info.value.position == src.rindex("<")

    def test_abs_arity(self) -> None:
        with pytest.raises(FormulaError, match="abs\\(\\) takes exactly 1"):
            compile_formula("abs(pe, roe) > 1")

    def test_min_needs_two_args(self) -> None:
        with pytest.raises(FormulaError, match="min\\(\\) takes at least 2"):
            compile_formula("min(pe) > 1")

    def test_max_arg_cap(self) -> None:
        args = ", ".join(["1"] * 9)
        with pytest.raises(FormulaError, match="at most 8"):
            compile_formula(f"max({args}) > 1")

    def test_paren_bomb_is_positioned_error_not_recursion(self) -> None:
        bomb = "(" * 5000 + "pe < 1" + ")" * 5000
        with pytest.raises(FormulaError) as exc_info:
            compile_formula(bomb)
        # Token cap or nesting cap — both are positioned FormulaErrors.
        message = str(exc_info.value)
        assert "too long" in message or "too deeply nested" in message
        assert exc_info.value.position is not None

    def test_token_flood_capped(self) -> None:
        flood = "pe > 1" + " and pe > 1" * MAX_TOKENS
        with pytest.raises(FormulaError, match=f"max {MAX_TOKENS} tokens"):
            compile_formula(flood)

    def test_nesting_cap(self) -> None:
        depth = MAX_NESTING_DEPTH + 1
        with pytest.raises(FormulaError, match="too deeply nested"):
            compile_formula("(" * depth + "pe < 1" + ")" * depth)

    def test_huge_literal_rejected(self) -> None:
        with pytest.raises(FormulaError, match="number literal too large"):
            compile_formula("pe < 1e999")

    def test_validate_formula_error_shape(self) -> None:
        report = validate_formula("pe <")
        assert report["ok"] is False
        assert report["position"] == 4  # end of input
        assert report["fields"] == []


# ---------------------------------------------------------------------------
# Evaluation semantics
# ---------------------------------------------------------------------------


class TestEvaluate:
    def test_match_and_reject(self) -> None:
        compiled = compile_formula("pe < 15 and roe > 0.2")
        assert evaluate_formula(compiled, _fundamentals(), _quote()) == (True, None)
        assert evaluate_formula(compiled, _fundamentals(pe_ratio=40.0), _quote()) == (False, None)

    def test_alias_reads_same_value_as_canonical(self) -> None:
        fundamentals = _fundamentals(pe_ratio=12.0)
        for src in ("pe < 15", "pe_ratio < 15"):
            assert evaluate_formula(compile_formula(src), fundamentals, _quote()) == (True, None)

    def test_functions_evaluate(self) -> None:
        compiled = compile_formula("max(roe, roa) > 0.2 and abs(change_percent_1d) < 2")
        assert evaluate_formula(compiled, _fundamentals(), _quote(change_percent=-1.5)) == (
            True,
            None,
        )
        assert evaluate_formula(compiled, _fundamentals(), _quote(change_percent=-3.0)) == (
            False,
            None,
        )

    def test_quote_derived_fields(self) -> None:
        compiled = compile_formula("price > 50 and volume > 1000")
        assert evaluate_formula(compiled, _fundamentals(), _quote(price=100.0)) == (True, None)

    def test_division_by_zero_is_no_match_not_skip(self) -> None:
        compiled = compile_formula("market_cap / debt_to_equity > 1")
        verdict, missing = evaluate_formula(compiled, _fundamentals(debt_to_equity=0.0), _quote())
        assert verdict is False
        assert missing is None

    def test_missing_field_is_skip_signal(self) -> None:
        compiled = compile_formula("roe > 0.2")
        verdict, missing = evaluate_formula(compiled, _fundamentals(roe=None), _quote())
        assert verdict is False
        assert missing == "roe"

    def test_missing_field_wins_even_when_an_or_branch_matches(self) -> None:
        # Strict, deterministic semantics (mirrors the criteria enrichment gate):
        # a row missing ANY referenced field is skipped — no short-circuit.
        compiled = compile_formula("pe < 15 or roe > 0.2")
        verdict, missing = evaluate_formula(compiled, _fundamentals(roe=None), _quote())
        assert verdict is False
        assert missing == "roe"

    def test_quote_fields_missing_without_a_quote(self) -> None:
        compiled = compile_formula("price > 50")
        verdict, missing = evaluate_formula(compiled, _fundamentals(), None)
        assert verdict is False
        assert missing == "price"

    def test_not_and_unary_minus(self) -> None:
        compiled = compile_formula("not (change_percent_1d < -2)")
        assert evaluate_formula(compiled, _fundamentals(), _quote(change_percent=1.0)) == (
            True,
            None,
        )
        assert evaluate_formula(compiled, _fundamentals(), _quote(change_percent=-3.0)) == (
            False,
            None,
        )


# ---------------------------------------------------------------------------
# run_screener integration — formula + honest skip ledger
# ---------------------------------------------------------------------------


def _mock_registry(monkeypatch: pytest.MonkeyPatch, fundamentals: dict[str, Fundamentals]) -> None:
    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fundamentals[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)


@pytest.mark.asyncio
async def test_run_screener_formula_filters_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """The formula AND-combines with the flat criteria."""
    _mock_registry(
        monkeypatch,
        {
            "GOOD": _fundamentals("GOOD", pe_ratio=10.0, roe=0.30),
            "PRICY": _fundamentals("PRICY", pe_ratio=40.0, roe=0.30),
            "WEAK": _fundamentals("WEAK", pe_ratio=10.0, roe=0.05),
        },
    )
    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["GOOD", "PRICY", "WEAK"],
        criteria=[{"field": "market_cap", "operator": "gt", "value": 1e9}],
        formula="pe < 15 and roe > 0.2",
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"GOOD"}
    # Formula-rejected rows were still EVALUATED (they are not skips).
    assert result.evaluated_count == 3
    assert result.skipped_count == 0
    assert result.skip_details == []


@pytest.mark.asyncio
async def test_run_screener_formula_missing_field_skips_honestly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A row missing a formula-referenced field is itemized ``missing_field:<f>``
    — and the ledger invariant ``skipped_count == len(skip_details)`` holds."""
    _mock_registry(
        monkeypatch,
        {
            "FULL": _fundamentals("FULL", pe_ratio=10.0, roe=0.30),
            "NOROE": _fundamentals("NOROE", pe_ratio=10.0, roe=None),
        },
    )
    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["FULL", "NOROE"],
        criteria=[],
        formula="roe > 0.2",
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"FULL"}
    assert result.evaluated_count == 1
    assert result.skipped_count == 1
    assert result.skipped_count == len(result.skip_details)
    assert result.skip_details[0].symbol == "NOROE"
    assert result.skip_details[0].reason == "missing_field:roe"


@pytest.mark.asyncio
async def test_run_screener_formula_div_by_zero_row_stays_evaluated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _mock_registry(
        monkeypatch,
        {
            "ZERO": _fundamentals("ZERO", debt_to_equity=0.0),
            "OK": _fundamentals("OK", debt_to_equity=0.5),
        },
    )
    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["ZERO", "OK"],
        criteria=[],
        formula="market_cap / debt_to_equity > 1",
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"OK"}
    # ZERO was evaluable (no missing field) — it just didn't match.
    assert result.evaluated_count == 2
    assert result.skipped_count == 0


# ---------------------------------------------------------------------------
# Request boundary + router validate endpoint
# ---------------------------------------------------------------------------


class TestRequestBoundary:
    def test_request_rejects_unparseable_formula_with_column(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            ScreenerRequest(
                universe="sp500",
                criteria=[],
                formula="pe << 15",
                limit=10,
            )
        message = str(exc_info.value)
        assert "invalid formula" in message
        assert "col" in message

    def test_request_normalizes_blank_formula_to_none(self) -> None:
        request = ScreenerRequest(universe="sp500", criteria=[], formula="   ", limit=10)
        assert request.formula is None

    def test_request_accepts_valid_formula(self) -> None:
        request = ScreenerRequest(
            universe="sp500", criteria=[], formula="pe < 15 and roe > 0.2", limit=10
        )
        assert request.formula == "pe < 15 and roe > 0.2"


class TestValidateEndpoint:
    @pytest.fixture()
    def client(self) -> TestClient:
        from app import app

        return TestClient(app)

    def test_validate_ok(self, client: TestClient) -> None:
        response = client.post(
            "/screener/formula/validate", json={"formula": "pe < 15 and roe > 0.2"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is True
        assert body["fields"] == ["pe_ratio", "roe"]
        assert body["error"] is None

    def test_validate_error_carries_caret_position_not_a_4xx(self, client: TestClient) -> None:
        src = "pe < 15 and bogus > 1"
        response = client.post("/screener/formula/validate", json={"formula": src})
        assert response.status_code == 200
        body = response.json()
        assert body["ok"] is False
        assert body["position"] == src.index("bogus")
        assert "unknown field" in body["error"]

    def test_run_route_422_on_bad_formula(self, client: TestClient) -> None:
        response = client.post(
            "/screener/run",
            json={"universe": "sp500", "criteria": [], "formula": "pe <", "limit": 10},
        )
        assert response.status_code == 422
        assert "invalid formula" in response.text
