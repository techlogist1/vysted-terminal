"""Tests for the columnar SQLite fundamentals store (R10, D40).

Covers the write tiers (seed / v7 / info) and their freshness stamps, the
TTL-gated ``query``/``stale_symbols`` reads, the ``info_priority`` crawl
ordering, the ``freshness`` block, and — the load-bearing one — PREFILTER
SOUNDNESS: pruning may only WIDEN, never narrow, the true match set (a
symbol is removed only on a FRESH NON-NULL value that definitively fails an
AND-ed cheap criterion; NULL and stale values keep the symbol).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import (
    NumericBetweenCriterion,
    NumericRange,
    NumericThresholdCriterion,
    SetInCriterion,
    StringEqCriterion,
)
from services import fundamentals_store as store


@pytest.fixture(autouse=True)
def _isolated_store(tmp_path: Path) -> None:
    store.reset_for_tests(tmp_path / "fundamentals_test.db")
    yield
    store.reset_for_tests(None)


def _fund(symbol: str, **overrides: Any) -> Fundamentals:
    payload: dict[str, Any] = {"symbol": symbol, "provider": "test"}
    payload.update(overrides)
    return Fundamentals(**payload)


def _quote(symbol: str, price: float = 100.0) -> Quote:
    return Quote(
        symbol=symbol,
        price=price,
        change=1.0,
        change_percent=1.0,
        volume=1_000_000.0,
        currency="USD",
        market_state="open",
        timestamp=datetime.now(tz=UTC),
        provider="test",
    )


async def _age_tier(symbol: str, column: str, age_seconds: float) -> None:
    """Backdate one tier stamp directly (TTL tests can't sleep for hours)."""
    import contextlib
    import sqlite3

    with contextlib.closing(sqlite3.connect(store._db_path())) as conn:
        conn.execute(
            f"UPDATE fundamentals SET {column} = ? WHERE symbol = ?",
            (time.time() - age_seconds, symbol),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Writes + stamps
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upsert_v7_stamps_tiers_and_quote_columns() -> None:
    await store.upsert_v7("AAA", _fund("AAA", market_cap=1e12, pe_ratio=20.0), _quote("AAA"))
    rows = await store.fetch_rows(["AAA"])
    row = rows["AAA"]
    assert row["market_cap"] == 1e12
    assert row["pe_ratio"] == 20.0
    assert row["quote_price"] == 100.0
    assert row["v7_updated_at"] is not None
    assert row["quote_updated_at"] is not None
    assert row["info_updated_at"] is None


@pytest.mark.asyncio
async def test_upsert_info_writes_full_vocabulary_and_sector_source() -> None:
    await store.upsert_v7("AAA", _fund("AAA", market_cap=1e12), _quote("AAA"))
    await store.upsert_info(
        "AAA",
        _fund("AAA", sector="Technology", industry="Software", roe=0.31, provider="yf"),
    )
    row = (await store.fetch_rows(["AAA"]))["AAA"]
    assert row["sector"] == "Technology"
    assert row["sector_source"] == "yf"
    assert row["roe"] == 0.31
    # The info write is a v7 superset — both stamps land.
    assert row["info_updated_at"] is not None
    assert row["v7_updated_at"] is not None
    # The earlier v7 numerics survive (info wrote only non-None fields).
    assert row["market_cap"] == 1e12


@pytest.mark.asyncio
async def test_seed_fills_only_null_columns() -> None:
    await store.upsert_info("RELIANCE.NS", _fund("RELIANCE.NS", sector="Energy", provider="yf"))
    touched = await store.seed_universe(
        [
            {
                "symbol": "RELIANCE.NS",
                "exchange": "NSE",
                "isin": "INE002A01018",
                "sector": "Utilities",  # must NOT clobber the fetched sector
                "sector_source": "seed",
            },
            {
                "symbol": "TCS.NS",
                "exchange": "NSE",
                "sector": "Technology",
                "sector_source": "seed",
                "shares_outstanding": 3.6e9,
            },
        ]
    )
    assert touched == 2
    rows = await store.fetch_rows(["RELIANCE.NS", "TCS.NS"])
    rel = rows["RELIANCE.NS"]
    assert rel["sector"] == "Energy"  # fetched value wins
    assert rel["sector_source"] == "yf"
    assert rel["exchange"] == "NSE"  # NULL identity column filled
    assert rel["isin"] == "INE002A01018"
    tcs = rows["TCS.NS"]
    assert tcs["sector"] == "Technology"
    assert tcs["sector_source"] == "seed"
    assert tcs["shares_outstanding"] == 3.6e9
    # A seed row alone carries no tier stamps — it is identity, not data.
    assert tcs["v7_updated_at"] is None


# ---------------------------------------------------------------------------
# TTL-gated reads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_serves_fresh_and_drops_stale_v7() -> None:
    await store.upsert_v7("AAA", _fund("AAA", market_cap=1e12), _quote("AAA"))
    await store.upsert_v7("OLD", _fund("OLD", market_cap=1e11), _quote("OLD"))
    await _age_tier("OLD", "v7_updated_at", store.TTL_V7_SECONDS + 60)
    fresh = await store.query(["AAA", "OLD"])
    assert "AAA" in fresh
    assert "OLD" not in fresh


@pytest.mark.asyncio
async def test_query_require_fields_gates_on_info_tier() -> None:
    await store.upsert_v7("AAA", _fund("AAA"), _quote("AAA"))
    await store.upsert_info("AAA", _fund("AAA", roe=0.2))
    await store.upsert_v7("BBB", _fund("BBB"), _quote("BBB"))
    fresh = await store.query(["AAA", "BBB"], require_fields={"roe"})
    assert "AAA" in fresh
    assert "BBB" not in fresh  # roe NULL
    # A stale info tier disqualifies even a non-NULL value.
    await _age_tier("AAA", "info_updated_at", store.TTL_INFO_SECONDS + 60)
    fresh = await store.query(["AAA"], require_fields={"roe"})
    assert fresh == {}


@pytest.mark.asyncio
async def test_stale_symbols_orders_and_detects_tiers() -> None:
    await store.upsert_v7("FRESH", _fund("FRESH"), _quote("FRESH"))
    await store.upsert_v7("QSTALE", _fund("QSTALE"), _quote("QSTALE"))
    await _age_tier("QSTALE", "quote_updated_at", store.TTL_QUOTE_FULL_SECONDS + 60)
    stale = await store.stale_symbols(["NEVER", "FRESH", "QSTALE"])
    assert stale == ["NEVER", "QSTALE"]


# ---------------------------------------------------------------------------
# Prefilter SOUNDNESS — prune may only widen, never narrow.
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prefilter_removes_only_fresh_failing_values() -> None:
    # FAIL: fresh value definitively failing market_cap > 1e9.
    await store.upsert_v7("FAIL", _fund("FAIL", market_cap=1e6), _quote("FAIL"))
    # PASS: fresh value passing.
    await store.upsert_v7("PASS", _fund("PASS", market_cap=1e12), _quote("PASS"))
    # NULLV: row exists, market_cap NULL — must be KEPT (sweep may fill it).
    await store.upsert_v7("NULLV", _fund("NULLV"), _quote("NULLV"))
    # STALE: failing value but the v7 tier is stale — must be KEPT.
    await store.upsert_v7("STALE", _fund("STALE", market_cap=1e6), _quote("STALE"))
    await _age_tier("STALE", "v7_updated_at", store.TTL_V7_SECONDS + 60)
    # MISSING: no row at all — must be KEPT.
    symbols = ["FAIL", "PASS", "NULLV", "STALE", "MISSING"]
    kept = await store.prefilter(
        symbols,
        [NumericThresholdCriterion(field="market_cap", operator="gt", value=1e9)],
    )
    assert kept == ["PASS", "NULLV", "STALE", "MISSING"]


@pytest.mark.asyncio
async def test_prefilter_string_and_set_criteria() -> None:
    await store.seed_universe(
        [
            {"symbol": "TECH", "sector": "Technology", "sector_source": "seed"},
            {"symbol": "BANK", "sector": "Financial Services", "sector_source": "seed"},
            {"symbol": "UNKNOWN"},  # sector NULL — kept
        ]
    )
    kept = await store.prefilter(
        ["TECH", "BANK", "UNKNOWN"],
        [StringEqCriterion(field="sector", operator="eq", value="technology")],
    )
    assert kept == ["TECH", "UNKNOWN"]
    kept = await store.prefilter(
        ["TECH", "BANK", "UNKNOWN"],
        [SetInCriterion(field="sector", operator="in", value=["Financial Services"])],
    )
    assert kept == ["BANK", "UNKNOWN"]
    # symbol-set prune: definitively not in the set — droppable even rowless.
    kept = await store.prefilter(
        ["TECH", "BANK", "UNKNOWN"],
        [SetInCriterion(field="symbol", operator="in", value=["tech"])],
    )
    assert kept == ["TECH"]


@pytest.mark.asyncio
async def test_prefilter_between_and_empty_criteria() -> None:
    await store.upsert_v7("LOW", _fund("LOW", pe_ratio=5.0), _quote("LOW"))
    await store.upsert_v7("MID", _fund("MID", pe_ratio=15.0), _quote("MID"))
    await store.upsert_v7("HIGH", _fund("HIGH", pe_ratio=50.0), _quote("HIGH"))
    crit = NumericBetweenCriterion(
        field="pe_ratio", operator="between", value=NumericRange(min=10.0, max=20.0)
    )
    kept = await store.prefilter(["LOW", "MID", "HIGH"], [crit])
    assert kept == ["MID"]
    assert await store.prefilter(["LOW", "MID"], []) == ["LOW", "MID"]


# ---------------------------------------------------------------------------
# Crawl priority + freshness block
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_info_priority_never_fetched_first_then_mcap_then_stalest() -> None:
    # Never-fetched, big cap.
    await store.upsert_v7("BIGNEW", _fund("BIGNEW", market_cap=1e12), _quote("BIGNEW"))
    # Never-fetched, small cap.
    await store.upsert_v7("SMALLNEW", _fund("SMALLNEW", market_cap=1e9), _quote("SMALLNEW"))
    # Fetched long ago.
    await store.upsert_info("OLDINFO", _fund("OLDINFO", market_cap=5e12, roe=0.1))
    await _age_tier("OLDINFO", "info_updated_at", 6 * 24 * 3600)
    # Fetched recently.
    await store.upsert_info("FRESHINFO", _fund("FRESHINFO", market_cap=4e12, roe=0.1))
    order = await store.info_priority(["FRESHINFO", "OLDINFO", "SMALLNEW", "BIGNEW"], 3)
    assert order == ["BIGNEW", "SMALLNEW", "OLDINFO"]


@pytest.mark.asyncio
async def test_freshness_reports_oldest_stamp_per_tier() -> None:
    await store.upsert_v7("AAA", _fund("AAA"), _quote("AAA"))
    await store.upsert_v7("BBB", _fund("BBB"), _quote("BBB"))
    await _age_tier("BBB", "quote_updated_at", 300)
    block = await store.freshness(["AAA", "BBB"])
    assert set(block) == {"quotes_as_of", "valuation_as_of"}
    assert block["quotes_as_of"] <= time.time() - 290


@pytest.mark.asyncio
async def test_row_to_pair_roundtrip_and_priceless_quote() -> None:
    await store.upsert_v7("AAA", _fund("AAA", market_cap=2e12, pe_ratio=30.0), _quote("AAA"))
    row = (await store.fetch_rows(["AAA"]))["AAA"]
    fundamentals, quote = store.row_to_pair(row)
    assert fundamentals.market_cap == 2e12
    assert quote is not None and quote.price == 100.0
    # A seed-only row has no quote columns — quote comes back None.
    await store.seed_universe([{"symbol": "SEEDED", "sector": "Energy"}])
    seeded_row = (await store.fetch_rows(["SEEDED"]))["SEEDED"]
    seeded_fund, seeded_quote = store.row_to_pair(seeded_row)
    assert seeded_fund.sector == "Energy"
    assert seeded_quote is None
