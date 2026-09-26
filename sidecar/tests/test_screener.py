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

import config
from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    CriterionGroup,
    NumericBetweenCriterion,
    NumericRange,
    NumericThresholdCriterion,
    ScreenerRequest,
    ScreenerResultRow,
    SetInCriterion,
    StringEqCriterion,
)
from services import data_cache, fundamentals_store, screener
from services.errors import ProviderError


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Point the data cache at a tmp file per test."""
    data_cache.reset_for_tests(tmp_path / "screener_test_cache.db")
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)


@pytest.fixture(autouse=True)
def _default_region_us(monkeypatch: pytest.MonkeyPatch) -> None:
    """R15-DATA-093: custom_symbols now canonicalise through the region-aware
    ``yfinance_provider._yahoo_symbol``, which appends ``.NS`` to any bare
    ticker under the ambient default region (IN, R10/E1) that isn't a known
    US name. This file's fixtures use synthetic symbols ("AAA", "S00", ...)
    that are not real tickers and must round-trip unchanged — pin US here;
    the India-specific tests below set the region back explicitly."""
    monkeypatch.setattr(config, "get_region", lambda: "US")


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


def test_apply_criteria_groups_by_currency_before_market_cap() -> None:
    """R15-DATA-043: a mixed-currency universe is grouped by currency first —
    RELIANCE.NS's raw INR market cap (~1.95e13) must never rank above AAPL's
    raw USD one (~3.5e12) as though they were the same unit."""
    rows = [
        (_make_fundamentals("AAPL", market_cap=3.5e12, currency="USD"), _make_quote("AAPL")),
        (
            _make_fundamentals("RELIANCE.NS", market_cap=1.95e13, currency="INR"),
            _make_quote("RELIANCE.NS"),
        ),
        (_make_fundamentals("MSFT", market_cap=3.0e12, currency="USD"), _make_quote("MSFT")),
    ]
    result = screener.apply_criteria(rows, [])
    # Currency groups stay contiguous (never interleaved), and each group is
    # independently market_cap-desc.
    currencies = [r.currency for r in result]
    assert currencies == sorted(currencies)
    usd_symbols = [r.symbol for r in result if r.currency == "USD"]
    assert usd_symbols == ["AAPL", "MSFT"]


def test_apply_criteria_sort_by_field_with_none_last() -> None:
    """R15-UI-006: sort_by applied BEFORE any limit cut — a lowest-P/E screen
    must rank the lowest P/E first, not whatever market_cap put first."""
    rows = [
        (_make_fundamentals("A", market_cap=500e9, pe_ratio=30.0), _make_quote("A")),
        (_make_fundamentals("B", market_cap=50e9, pe_ratio=10.0), _make_quote("B")),
        (_make_fundamentals("C", market_cap=200e9, pe_ratio=None), _make_quote("C")),
    ]
    asc = screener.apply_criteria(rows, [], sort_by="pe_ratio", sort_dir="asc")
    assert [r.symbol for r in asc] == ["B", "A", "C"]  # None (C) always last
    desc = screener.apply_criteria(rows, [], sort_by="pe_ratio", sort_dir="desc")
    # Case not written against: `desc` on a field with NULLs still keeps the
    # NULL row last, not first.
    assert [r.symbol for r in desc] == ["A", "B", "C"]


def test_apply_criteria_sorts_by_a_field_the_result_row_does_not_carry() -> None:
    """R15-UI-006: ``sort_by`` accepts any screener numeric field; ``beta`` is
    not a results-table column, and the rows still rank by it."""
    rows = [
        (_make_fundamentals("HI", beta=1.8), _make_quote("HI")),
        (_make_fundamentals("LO", beta=0.4), _make_quote("LO")),
        (_make_fundamentals("MID", beta=1.1), _make_quote("MID")),
    ]
    ranked = screener.apply_criteria(rows, [], sort_by="beta", sort_dir="asc")
    assert [r.symbol for r in ranked] == ["LO", "MID", "HI"]


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


def test_result_row_has_no_matched_criteria() -> None:
    """R15-CODE-DATA-019: ``matched_criteria`` was a dead wire field — empty on
    every group run, ``[0..n-1]`` on every flat run, read by nothing. It is gone
    from the row model and from both engine paths' serialised rows."""
    assert "matched_criteria" not in ScreenerResultRow.model_fields
    rows = [(_make_fundamentals("A", pe_ratio=10.0), _make_quote("A"))]
    flat = screener.apply_criteria(
        rows, [NumericThresholdCriterion(field="pe_ratio", operator="lt", value=15.0)]
    )
    grouped = screener.apply_criteria(
        rows,
        [],
        group=CriterionGroup(
            combinator="or",
            criteria=[NumericThresholdCriterion(field="pe_ratio", operator="lt", value=15.0)],
        ),
    )
    for result in (flat, grouped):
        assert [r.symbol for r in result] == ["A"]
        assert "matched_criteria" not in result[0].model_dump()


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
async def test_run_screener_mixed_currency_universe_ranked_within_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-043: custom=[AAPL, RELIANCE.NS] must not rank RELIANCE.NS's
    raw INR market cap (~1.95e13) above AAPL's raw USD one (~3.5e12) as one
    number, and the coverage line discloses the currency-grouped basis."""

    fake_fundamentals = {
        "AAPL": _make_fundamentals("AAPL", market_cap=3.5e12, currency="USD"),
        "RELIANCE.NS": _make_fundamentals("RELIANCE.NS", market_cap=1.95e13, currency="INR"),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake_fundamentals[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["AAPL", "RELIANCE.NS"],
        criteria=[],
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {r.symbol for r in result.rows} == {"AAPL", "RELIANCE.NS"}
    assert result.coverage is not None
    assert "ranked within each currency" in result.coverage


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


@pytest.mark.asyncio
async def test_run_screener_sort_by_applies_before_limit_cut(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-UI-006: `sort_by`/`sort_dir` apply BEFORE the `limit` cut — a
    lowest-P/E screen must surface the lowest-P/E stock even though it is
    the smallest cap (the old market-cap-desc-only cut would drop it first).
    `matched_count` reports the true pre-cut count."""
    fake = {
        "BIG": _make_fundamentals("BIG", sector="Technology", market_cap=900e9, pe_ratio=30.0),
        "SMALL": _make_fundamentals("SMALL", sector="Technology", market_cap=10e9, pe_ratio=5.0),
        "MID": _make_fundamentals("MID", sector="Technology", market_cap=200e9, pe_ratio=15.0),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["BIG", "SMALL", "MID"],
        criteria=[StringEqCriterion(field="sector", operator="eq", value="Technology")],
        limit=2,
        sort_by="pe_ratio",
        sort_dir="asc",
    )
    result = await screener.run_screener(request)
    assert [row.symbol for row in result.rows] == ["SMALL", "MID"]
    assert result.result_count == 2
    assert result.matched_count == 3


@pytest.mark.asyncio
async def test_run_screener_itemizes_null_non_enrichment_field(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-044: a NULL value for a field the v7 batch row ALREADY
    carries (pe_ratio needs no further enrichment) previously failed
    `_evaluate_criterion` silently instead of itemizing missing_field:<f>."""
    fake = {
        "HASPE": _make_fundamentals("HASPE", market_cap=200e9, pe_ratio=15.0),
        "NOPE": _make_fundamentals("NOPE", market_cap=200e9, pe_ratio=None),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["HASPE", "NOPE"],
        criteria=[NumericThresholdCriterion(field="pe_ratio", operator="lt", value=20.0)],
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"HASPE"}
    itemized = {d.symbol: d.reason for d in result.skip_details}
    assert itemized.get("NOPE") == "missing_field:pe_ratio"


@pytest.mark.asyncio
async def test_run_screener_itemizes_null_field_under_nested_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case not written against: the same itemization holds for a field
    referenced only inside a nested ``group`` tree, not the flat criteria."""
    fake = {
        "HASPB": _make_fundamentals("HASPB", market_cap=200e9, price_to_book=1.2),
        "NOPB": _make_fundamentals("NOPB", market_cap=200e9, price_to_book=None),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["HASPB", "NOPB"],
        criteria=[],
        group=CriterionGroup(
            combinator="and",
            criteria=[
                NumericThresholdCriterion(field="price_to_book", operator="lt", value=3.0),
            ],
        ),
        limit=10,
    )
    result = await screener.run_screener(request)
    assert {row.symbol for row in result.rows} == {"HASPB"}
    itemized = {d.symbol: d.reason for d in result.skip_details}
    assert itemized.get("NOPB") == "missing_field:price_to_book"


@pytest.mark.asyncio
async def test_resolve_universe_custom_symbols_canonicalise_india_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-093: a bare India custom symbol canonicalises through the same
    ``_yahoo_symbol`` mapping the rest of the app uses (C3), so it hits the
    same warm store row a quote/history lookup already keyed under `.NS`."""
    monkeypatch.setattr(config, "get_region", lambda: "IN")
    universe = await screener.resolve_universe("custom", ["reliance"])
    assert universe.symbols == ["RELIANCE.NS"]


@pytest.mark.asyncio
async def test_resolve_universe_custom_symbols_bo_suffix_passes_through(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Case not written against: an already-suffixed .BO code is left alone."""
    monkeypatch.setattr(config, "get_region", lambda: "IN")
    universe = await screener.resolve_universe("custom", ["532540.bo"])
    assert universe.symbols == ["532540.BO"]


# ---------------------------------------------------------------------------
# R15-DATA-048: a derived debt_to_equity of 0.0 (a debt-free name) is a real
# value the formula engine can screen on, never an itemized missing_field.
# ---------------------------------------------------------------------------


def test_debt_free_zero_debt_to_equity_passes_a_threshold_screen() -> None:
    """A debt-free row's ``debt_to_equity`` is a served 0.0 (yfinance_provider's
    derived leg — R15-DATA-048), not ``None`` — ``evaluate_formula`` must treat
    it as a real value and match ``debt_to_equity < 0.5``, never skip the row
    as ``missing_field:debt_to_equity``."""
    from services.screener_formula import compile_formula, evaluate_formula

    fund = _make_fundamentals("DEBTFREE", debt_to_equity=0.0)
    compiled = compile_formula("debt_to_equity < 0.5")
    matched, missing = evaluate_formula(compiled, fund, None)
    assert missing is None
    assert matched is True


# ---------------------------------------------------------------------------
# R15-DATA-112: a missing listing currency must sort LAST, not first.
# ---------------------------------------------------------------------------


def test_apply_criteria_missing_currency_sorts_last_desc() -> None:
    """MANIKA.NS has no fundamentals currency (None) — it must never form its
    own leading group ahead of every real currency code."""
    rows = [
        (_make_fundamentals("MANIKA.NS", market_cap=None, currency=None), _make_quote("MANIKA.NS")),
        (
            _make_fundamentals("RELIANCE.NS", market_cap=1.655e13, currency="INR"),
            _make_quote("RELIANCE.NS"),
        ),
        (_make_fundamentals("TCS.NS", market_cap=7.55e12, currency="INR"), _make_quote("TCS.NS")),
    ]
    result = screener.apply_criteria(rows, [], sort_by="market_cap", sort_dir="desc")
    assert [r.symbol for r in result] == ["RELIANCE.NS", "TCS.NS", "MANIKA.NS"]


def test_apply_criteria_missing_currency_sorts_last_asc() -> None:
    """Same rule holds ascending — the missing-currency group stays last
    regardless of sort_dir (it is not scaled by the value's sign)."""
    rows = [
        (_make_fundamentals("MANIKA.NS", market_cap=None, currency=None), _make_quote("MANIKA.NS")),
        (
            _make_fundamentals("RELIANCE.NS", market_cap=1.655e13, currency="INR"),
            _make_quote("RELIANCE.NS"),
        ),
        (_make_fundamentals("TCS.NS", market_cap=7.55e12, currency="INR"), _make_quote("TCS.NS")),
    ]
    result = screener.apply_criteria(rows, [], sort_by="market_cap", sort_dir="asc")
    assert [r.symbol for r in result] == ["TCS.NS", "RELIANCE.NS", "MANIKA.NS"]


# ---------------------------------------------------------------------------
# R15-DATA-043: the top-K cut is round-robin per currency, and the disclosure
# is computed over the full matched set, not the served page.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_screener_top_k_cut_is_round_robin_per_currency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A mixed-currency universe cut to a top-K smaller than the matched set
    must not silently keep only the alphabetically-first currency group
    (INR before USD) — each currency is represented, and the 'ranked within
    each currency' disclosure survives the cut."""
    fake_fundamentals = {
        "AAPL": _make_fundamentals("AAPL", market_cap=3.5e12, currency="USD"),
        "RELIANCE.NS": _make_fundamentals("RELIANCE.NS", market_cap=1.95e13, currency="INR"),
        "MSFT": _make_fundamentals("MSFT", market_cap=3.0e12, currency="USD"),
        "TCS.NS": _make_fundamentals("TCS.NS", market_cap=7.5e12, currency="INR"),
    }

    async def fake_get_fundamentals(symbol: str) -> Fundamentals:
        return fake_fundamentals[symbol]

    def fake_get_quote(symbol: str, _asset_class: str = "equity") -> Quote:
        return _make_quote(symbol)

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_get_fundamentals)
    monkeypatch.setattr("services.provider_registry.get_quote", fake_get_quote)

    request = ScreenerRequest(
        universe="custom",
        custom_symbols=["AAPL", "RELIANCE.NS", "MSFT", "TCS.NS"],
        criteria=[],
        sort_by="market_cap",
        sort_dir="desc",
        limit=2,
    )
    result = await screener.run_screener(request)
    assert result.matched_count == 4
    assert result.result_count == 2
    assert "ranked within each currency" in result.coverage
    assert any(row.currency == "USD" for row in result.rows)
