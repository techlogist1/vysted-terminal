"""Tests for the Phase 6 screener filter engine.

The engine has three surfaces under test:

  - ``resolve_universe`` — universe resolution from shipped JSON
    snapshots + cache-backed crypto-top50 path + custom universe
    coming off the request body.
  - ``apply_criteria`` — pure filter; AND-combined discriminated-union
    operator dispatch + market-cap-desc sort + missing-value handling.
  - ``run_screener`` — top-level orchestration; mocks the provider
    registry so we can drive deterministic fundamentals + quote data
    through the fan-out path.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    CriterionGroup,
    NumericBetweenCriterion,
    NumericRange,
    NumericThresholdCriterion,
    ScreenerRequest,
    SetInCriterion,
    StringEqCriterion,
)
from services import data_cache, screener
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Point the data cache at a tmp file per test."""
    data_cache.reset_for_tests(tmp_path / "screener_test_cache.db")
    yield
    data_cache.reset_for_tests(None)


# ---------------------------------------------------------------------------
# Fixture helpers — fundamentals + quote stand-ins
# ---------------------------------------------------------------------------


def _make_fundamentals(
    symbol: str,
    *,
    sector: str = "Technology",
    industry: str | None = "Software",
    market_cap: float | None = 200_000_000_000.0,
    pe_ratio: float | None = 15.0,
    name: str | None = None,
    **overrides: Any,
) -> Fundamentals:
    payload: dict[str, Any] = {
        "symbol": symbol,
        "name": name or f"{symbol} Inc.",
        "sector": sector,
        "industry": industry,
        "market_cap": market_cap,
        "pe_ratio": pe_ratio,
        "provider": "test",
    }
    payload.update(overrides)
    return Fundamentals(**payload)


def _make_quote(symbol: str, price: float = 100.0, change_percent: float = 1.5) -> Quote:
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
# Universe resolution
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_universe_sp500_loads_snapshot() -> None:
    universe = await screener.resolve_universe("sp500")
    assert universe.id == "sp500"
    assert universe.asset_class == "equity"
    # Full-index snapshot now (003 rebuild) — honest "S&P 500", not a Top-100 subset.
    assert universe.label == "S&P 500"
    # Snapshot ships the full ~500-name index; assert ≥ 400 to guard against a
    # corrupted/truncated JSON without coupling to the exact (drift-prone) list.
    assert len(universe.symbols) >= 400
    assert "AAPL" in universe.symbols
    assert "MSFT" in universe.symbols
    # No dupes — multi-class issuers (GOOGL/GOOG) are distinct symbols, but the
    # same ticker must never appear twice.
    assert len(universe.symbols) == len(set(universe.symbols))


@pytest.mark.asyncio
async def test_resolve_universe_custom_symbols_override_named_universe() -> None:
    """Non-empty custom_symbols take precedence even over a named universe
    (Phase 9.5 nit: custom_symbols was ignored unless universe=='custom')."""
    universe = await screener.resolve_universe("sp500", ["tsla", " amd ", "NFLX"])
    assert universe.id == "custom"
    assert universe.symbols == ["TSLA", "AMD", "NFLX"]
    # The named sp500 snapshot must NOT leak in.
    assert "AAPL" not in universe.symbols


@pytest.mark.asyncio
async def test_resolve_universe_nifty50_loads_snapshot() -> None:
    universe = await screener.resolve_universe("nifty50")
    assert universe.id == "nifty50"
    assert universe.asset_class == "equity"
    assert len(universe.symbols) == 50
    assert "RELIANCE.NS" in universe.symbols


@pytest.mark.asyncio
async def test_resolve_universe_crypto_top50_uses_seed_then_caches() -> None:
    # First call: cache miss → seed used + cache populated.
    first = await screener.resolve_universe("crypto-top50")
    assert first.id == "crypto-top50"
    assert first.asset_class == "crypto"
    assert "BTC/USDT" in first.symbols
    assert "ETH/USDT" in first.symbols

    # Second call: cache hit → same payload.
    second = await screener.resolve_universe("crypto-top50")
    assert second.symbols == first.symbols


@pytest.mark.asyncio
async def test_resolve_universe_custom_uses_payload_symbols() -> None:
    universe = await screener.resolve_universe("custom", ["aapl", " msft ", "", "NVDA"])
    assert universe.id == "custom"
    assert universe.asset_class == "equity"
    # Whitespace-stripped, upper-cased, empties dropped.
    assert universe.symbols == ["AAPL", "MSFT", "NVDA"]


@pytest.mark.asyncio
async def test_resolve_universe_custom_empty_list_rejected() -> None:
    with pytest.raises(ProviderError):
        await screener.resolve_universe("custom", [])
    with pytest.raises(ProviderError):
        await screener.resolve_universe("custom", None)


@pytest.mark.asyncio
async def test_resolve_universe_unknown_id_raises() -> None:
    with pytest.raises(ProviderError):
        await screener.resolve_universe("does-not-exist")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# apply_criteria — discriminated-union operator dispatch
# ---------------------------------------------------------------------------


def test_apply_criteria_numeric_gt_matches_only_above_threshold() -> None:
    rows = [
        (_make_fundamentals("AAA", market_cap=500e9), _make_quote("AAA")),
        (_make_fundamentals("BBB", market_cap=50e9), _make_quote("BBB")),
        (_make_fundamentals("CCC", market_cap=200e9), _make_quote("CCC")),
    ]
    criterion = NumericThresholdCriterion(field="market_cap", operator="gt", value=100e9)
    result = screener.apply_criteria(rows, [criterion])
    assert [r.symbol for r in result] == ["AAA", "CCC"]


def test_apply_criteria_numeric_lt_lte_gte_dispatch() -> None:
    rows = [
        (_make_fundamentals("X", pe_ratio=15.0), _make_quote("X")),
        (_make_fundamentals("Y", pe_ratio=20.0), _make_quote("Y")),
        (_make_fundamentals("Z", pe_ratio=25.0), _make_quote("Z")),
    ]
    lt = NumericThresholdCriterion(field="pe_ratio", operator="lt", value=20.0)
    lte = NumericThresholdCriterion(field="pe_ratio", operator="lte", value=20.0)
    gte = NumericThresholdCriterion(field="pe_ratio", operator="gte", value=20.0)

    assert {r.symbol for r in screener.apply_criteria(rows, [lt])} == {"X"}
    assert {r.symbol for r in screener.apply_criteria(rows, [lte])} == {"X", "Y"}
    assert {r.symbol for r in screener.apply_criteria(rows, [gte])} == {"Y", "Z"}


def test_apply_criteria_numeric_between_inclusive_range() -> None:
    rows = [
        (_make_fundamentals("A", pe_ratio=10.0), _make_quote("A")),
        (_make_fundamentals("B", pe_ratio=15.0), _make_quote("B")),
        (_make_fundamentals("C", pe_ratio=20.0), _make_quote("C")),
        (_make_fundamentals("D", pe_ratio=30.0), _make_quote("D")),
    ]
    criterion = NumericBetweenCriterion(
        field="pe_ratio",
        operator="between",
        value=NumericRange(min=15.0, max=20.0),
    )
    result = screener.apply_criteria(rows, [criterion])
    assert {r.symbol for r in result} == {"B", "C"}


def test_apply_criteria_string_eq_is_case_insensitive() -> None:
    rows = [
        (_make_fundamentals("A", sector="Technology"), _make_quote("A")),
        (_make_fundamentals("B", sector="Healthcare"), _make_quote("B")),
        (_make_fundamentals("C", sector="technology"), _make_quote("C")),
    ]
    criterion = StringEqCriterion(field="sector", operator="eq", value="TECHNOLOGY")
    result = screener.apply_criteria(rows, [criterion])
    assert {r.symbol for r in result} == {"A", "C"}


def test_apply_criteria_set_in_symbol_path() -> None:
    rows = [
        (_make_fundamentals("AAPL"), _make_quote("AAPL")),
        (_make_fundamentals("MSFT"), _make_quote("MSFT")),
        (_make_fundamentals("NVDA"), _make_quote("NVDA")),
    ]
    criterion = SetInCriterion(field="symbol", operator="in", value=["AAPL", "NVDA"])
    result = screener.apply_criteria(rows, [criterion])
    assert {r.symbol for r in result} == {"AAPL", "NVDA"}


def test_apply_criteria_and_combines_multiple_criteria() -> None:
    rows = [
        (
            _make_fundamentals("A", sector="Technology", market_cap=500e9, pe_ratio=15.0),
            _make_quote("A"),
        ),
        (
            _make_fundamentals("B", sector="Technology", market_cap=50e9, pe_ratio=15.0),
            _make_quote("B"),
        ),
        (
            _make_fundamentals("C", sector="Healthcare", market_cap=500e9, pe_ratio=15.0),
            _make_quote("C"),
        ),
        (
            _make_fundamentals("D", sector="Technology", market_cap=500e9, pe_ratio=40.0),
            _make_quote("D"),
        ),
    ]
    criteria = [
        StringEqCriterion(field="sector", operator="eq", value="Technology"),
        NumericThresholdCriterion(field="market_cap", operator="gt", value=100e9),
        NumericThresholdCriterion(field="pe_ratio", operator="lt", value=20.0),
    ]
    result = screener.apply_criteria(rows, criteria)
    assert [r.symbol for r in result] == ["A"]
    # matched_criteria records every index since AND-all passes.
    assert result[0].matched_criteria == [0, 1, 2]


def test_apply_criteria_missing_value_fails_numeric_threshold() -> None:
    """A None ``market_cap`` should not be treated as matching '> 100B'."""
    rows = [
        (_make_fundamentals("A", market_cap=None), _make_quote("A")),
        (_make_fundamentals("B", market_cap=200e9), _make_quote("B")),
    ]
    criterion = NumericThresholdCriterion(field="market_cap", operator="gt", value=100e9)
    result = screener.apply_criteria(rows, [criterion])
    assert {r.symbol for r in result} == {"B"}


def test_apply_criteria_price_derived_fields_resolve_from_quote() -> None:
    rows = [
        (_make_fundamentals("A"), _make_quote("A", price=50.0)),
        (_make_fundamentals("B"), _make_quote("B", price=150.0)),
    ]
    criterion = NumericThresholdCriterion(field="price", operator="gt", value=100.0)
    result = screener.apply_criteria(rows, [criterion])
    assert {r.symbol for r in result} == {"B"}


def test_apply_criteria_sorted_by_market_cap_desc_with_none_last() -> None:
    rows = [
        (_make_fundamentals("A", market_cap=100e9), _make_quote("A")),
        (_make_fundamentals("B", market_cap=None), _make_quote("B")),
        (_make_fundamentals("C", market_cap=500e9), _make_quote("C")),
        (_make_fundamentals("D", market_cap=300e9), _make_quote("D")),
    ]
    # No criteria — every row passes; check ordering.
    result = screener.apply_criteria(rows, [])
    assert [r.symbol for r in result] == ["C", "D", "A", "B"]


# ---------------------------------------------------------------------------
# CriterionGroup — AND/OR boolean tree (003 rebuild OR-grammar)
# ---------------------------------------------------------------------------


def test_apply_criteria_or_group_matches_either_branch() -> None:
    """An OR group matches a row satisfying ANY one leaf (cheap OR high-yield)."""
    rows = [
        (
            _make_fundamentals("CHEAP", market_cap=300e9, pe_ratio=10.0, dividend_yield=0.0),
            _make_quote("CHEAP"),
        ),
        (
            _make_fundamentals("YIELD", market_cap=200e9, pe_ratio=40.0, dividend_yield=0.06),
            _make_quote("YIELD"),
        ),
        (
            _make_fundamentals("MEH", market_cap=100e9, pe_ratio=40.0, dividend_yield=0.0),
            _make_quote("MEH"),
        ),
    ]
    group = CriterionGroup(
        combinator="or",
        criteria=[
            NumericThresholdCriterion(field="pe_ratio", operator="lt", value=15.0),
            NumericThresholdCriterion(field="dividend_yield", operator="gt", value=0.04),
        ],
    )
    result = screener.apply_criteria(rows, [], group=group)
    assert {r.symbol for r in result} == {"CHEAP", "YIELD"}


def test_apply_criteria_nested_group_and_within_or() -> None:
    """(P/E < 15 AND ROE > 0.2) OR dividend_yield > 0.04 — nested combinators."""
    rows = [
        # passes the AND branch
        (
            _make_fundamentals("A", pe_ratio=10.0, roe=0.30, dividend_yield=0.0, market_cap=300e9),
            _make_quote("A"),
        ),
        # fails AND (low ROE) and has no yield → dropped
        (
            _make_fundamentals("B", pe_ratio=10.0, roe=0.05, dividend_yield=0.0, market_cap=200e9),
            _make_quote("B"),
        ),
        # passes the OR via dividend yield
        (
            _make_fundamentals("C", pe_ratio=40.0, roe=0.05, dividend_yield=0.06, market_cap=100e9),
            _make_quote("C"),
        ),
    ]
    group = CriterionGroup(
        combinator="or",
        criteria=[
            CriterionGroup(
                combinator="and",
                criteria=[
                    NumericThresholdCriterion(field="pe_ratio", operator="lt", value=15.0),
                    NumericThresholdCriterion(field="roe", operator="gt", value=0.20),
                ],
            ),
            NumericThresholdCriterion(field="dividend_yield", operator="gt", value=0.04),
        ],
    )
    result = screener.apply_criteria(rows, [], group=group)
    assert {r.symbol for r in result} == {"A", "C"}


def test_apply_criteria_empty_group_matches_all() -> None:
    """An empty group is a no-op filter regardless of combinator (mirrors flat path)."""
    rows = [
        (_make_fundamentals("A", market_cap=200e9), _make_quote("A")),
        (_make_fundamentals("B", market_cap=100e9), _make_quote("B")),
    ]
    group = CriterionGroup(combinator="or", criteria=[])
    result = screener.apply_criteria(rows, [], group=group)
    assert {r.symbol for r in result} == {"A", "B"}


@pytest.mark.asyncio
async def test_run_screener_or_group_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_screener honours ``req.group`` (OR) over the flat criteria."""

    fake = {
        "CHEAP": _make_fundamentals("CHEAP", market_cap=300e9, pe_ratio=10.0, dividend_yield=0.0),
        "YIELD": _make_fundamentals("YIELD", market_cap=200e9, pe_ratio=40.0, dividend_yield=0.06),
        "MEH": _make_fundamentals("MEH", market_cap=100e9, pe_ratio=40.0, dividend_yield=0.0),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["CHEAP", "YIELD", "MEH"],
        criteria=[],
        group=CriterionGroup(
            combinator="or",
            criteria=[
                NumericThresholdCriterion(field="pe_ratio", operator="lt", value=15.0),
                NumericThresholdCriterion(field="dividend_yield", operator="gt", value=0.04),
            ],
        ),
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"CHEAP", "YIELD"}


@pytest.mark.asyncio
async def test_run_screener_caches_pairs_across_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """The batching layer caches each symbol's pair — a second run hits the cache
    and does NOT re-call the provider (key prerequisite for the full-500 universe)."""

    calls: dict[str, int] = {}

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        calls[symbol] = calls.get(symbol, 0) + 1
        return _make_fundamentals(symbol, sector="Technology", market_cap=200e9)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["AAA", "BBB"],
        criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
        limit=10,
    )
    first = await screener.run_screener(request)
    assert {r.symbol for r in first.rows} == {"AAA", "BBB"}
    assert calls == {"AAA": 1, "BBB": 1}

    # Second identical run resolves entirely from the per-symbol cache.
    second = await screener.run_screener(request)
    assert {r.symbol for r in second.rows} == {"AAA", "BBB"}
    assert calls == {"AAA": 1, "BBB": 1}, "expected cache hit, provider re-called"


# ---------------------------------------------------------------------------
# run_screener — top-level orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_screener_custom_universe_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    """A small custom universe routed through the engine."""

    fake_fundamentals = {
        "AAA": _make_fundamentals("AAA", sector="Technology", market_cap=500e9, pe_ratio=15.0),
        "BBB": _make_fundamentals("BBB", sector="Technology", market_cap=50e9, pe_ratio=15.0),
        "CCC": _make_fundamentals("CCC", sector="Healthcare", market_cap=500e9, pe_ratio=15.0),
        "DDD": _make_fundamentals("DDD", sector="Technology", market_cap=500e9, pe_ratio=40.0),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake_fundamentals[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["AAA", "BBB", "CCC", "DDD"],
        criteria=[
            StringEqCriterion(field="sector", operator="eq", value="Technology"),
            NumericThresholdCriterion(field="market_cap", operator="gt", value=100e9),
            NumericThresholdCriterion(field="pe_ratio", operator="lt", value=20.0),
        ],
        limit=10,
    )
    result = await screener.run_screener(request)

    assert result.universe == "custom"
    assert result.evaluated_count == 4
    assert result.result_count == 1
    assert [row.symbol for row in result.rows] == ["AAA"]
    assert result.duration_ms >= 0.0


@pytest.mark.asyncio
async def test_run_screener_per_symbol_failure_does_not_poison_run(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """One failing fundamentals call drops that symbol; others survive."""

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        if symbol == "BAD":
            raise ProviderError("upstream down")
        return _make_fundamentals(symbol, sector="Technology", market_cap=200e9)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["GOOD1", "BAD", "GOOD2"],
        criteria=[
            StringEqCriterion(field="sector", operator="eq", value="Technology"),
        ],
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"GOOD1", "GOOD2"}
    assert result.evaluated_count == 2


@pytest.mark.asyncio
async def test_run_screener_limit_clamps_result_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Limit caps the row count after the criteria filter."""

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        # Market cap embedded in symbol order so sort is deterministic.
        index = int(symbol[1:])
        return _make_fundamentals(symbol, sector="Technology", market_cap=(100 - index) * 1e9)

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    symbols = [f"S{i:02d}" for i in range(20)]
    request = ScreenerRequest(
        universe="custom",
        custom_symbols=symbols,
        criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
        limit=5,
    )
    result = await screener.run_screener(request)
    assert result.result_count == 5
    # Sorted by market_cap desc — S00 has the highest market cap.
    assert result.rows[0].symbol == "S00"
