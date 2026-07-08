"""Tests for the bundled fundamentals seed pack (R11, D52) — the shipped
pack's integrity, the loader's degrade path, the store's NULL-fill seeding
semantics, and the EOD (bhavcopy-lane) upsert tier."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from models.fundamentals import Fundamentals
from services import fundamentals_seed, fundamentals_store

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path) -> None:
    fundamentals_store.reset_for_tests(tmp_path / "seed_test.db")
    fundamentals_seed.reset_for_tests()
    yield
    fundamentals_store.reset_for_tests(None)
    fundamentals_seed.reset_for_tests()


# ---------------------------------------------------------------------------
# Shipped pack integrity — the bundled artifact must be the real census.
# ---------------------------------------------------------------------------


async def test_shipped_pack_loads_with_honest_header() -> None:
    rows = fundamentals_seed.load_seed_rows()
    info = fundamentals_seed.pack_info()
    assert len(rows) > 4000, "the shipped pack must cover most of india-all"
    assert info.get("_rows") == len(rows), "header count must match the actual census"
    assert info.get("_generated"), "pack must carry its generation date"
    # Every row is dated and keyed on a quote-form India symbol.
    sample = rows[:200]
    assert all(r["symbol"].endswith((".NS", ".BO")) for r in sample)
    assert all(isinstance(r.get("seed_as_of"), (int, float)) for r in sample)
    # The pack is fundamentals, never prices: no quote columns ride it.
    assert all("quote_price" not in r for r in sample)


async def test_shipped_pack_has_screener_grade_coverage() -> None:
    rows = fundamentals_seed.load_seed_rows()
    mcap = sum(1 for r in rows if r.get("market_cap") is not None)
    roe = sum(1 for r in rows if r.get("roe") is not None)
    sector = sum(1 for r in rows if r.get("sector") is not None)
    assert mcap > 3500, f"market_cap coverage too thin: {mcap}"
    assert roe > 3000, f"roe coverage too thin: {roe}"
    assert sector > 3500, f"sector coverage too thin: {sector}"


# ---------------------------------------------------------------------------
# seed_fundamentals — NULL-fill only, seed stamp only.
# ---------------------------------------------------------------------------


async def test_seed_fills_nulls_and_stamps_seed_tier_only() -> None:
    as_of = time.time() - 20 * 24 * 3600
    touched = await fundamentals_store.seed_fundamentals(
        [
            {
                "symbol": "SEEDCO.NS",
                "name": "Seed Co",
                "currency": "INR",
                "sector": "Technology",
                "sector_source": "seed-pack",
                "seed_as_of": as_of,
                "market_cap": 5e9,
                "pe_ratio": 12.0,
                "roe": 0.21,
            }
        ]
    )
    assert touched == 1
    row = (await fundamentals_store.fetch_rows(["SEEDCO.NS"]))["SEEDCO.NS"]
    assert row["market_cap"] == 5e9
    assert row["roe"] == 0.21
    assert row["seed_updated_at"] == pytest.approx(as_of)
    # The seed NEVER masquerades as a live tier.
    assert row["v7_updated_at"] is None
    assert row["info_updated_at"] is None
    assert row["quote_updated_at"] is None


async def test_seed_never_clobbers_a_fetched_value() -> None:
    await fundamentals_store.upsert_v7(
        "LIVECO.NS",
        Fundamentals(symbol="LIVECO.NS", market_cap=9e9, pe_ratio=30.0, provider="t"),
        None,
    )
    await fundamentals_store.seed_fundamentals(
        [
            {
                "symbol": "LIVECO.NS",
                "seed_as_of": time.time() - 1e6,
                "market_cap": 1e9,  # stale pack value — must not win
                "roe": 0.15,  # info-tier gap — fills
            }
        ]
    )
    row = (await fundamentals_store.fetch_rows(["LIVECO.NS"]))["LIVECO.NS"]
    assert row["market_cap"] == 9e9  # live v7 value kept
    assert row["roe"] == 0.15  # NULL gap filled from seed
    assert row["v7_updated_at"] is not None


async def test_loader_degrades_to_empty_on_missing_pack(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(fundamentals_seed, "_PACK_FILENAME", "no-such-pack.json.gz")
    fundamentals_seed.reset_for_tests()
    assert fundamentals_seed.load_seed_rows() == []
    assert fundamentals_seed.pack_info() == {}


# ---------------------------------------------------------------------------
# upsert_eod_batch — the bhavcopy lane's store tier (D54).
# ---------------------------------------------------------------------------


async def test_upsert_eod_writes_quote_and_mcap_without_v7_stamp() -> None:
    await fundamentals_store.upsert_eod_batch(
        [
            {
                "symbol": "RELIANCE.NS",
                "price": 1275.9,
                "prev_close": 1308.4,
                "volume": 19_960_000,
                "market_cap": 1275.9 * 6_766_000_000,
                "trade_date_iso": "2026-07-08",
            }
        ],
        provider="nse-bhavcopy",
    )
    row = (await fundamentals_store.fetch_rows(["RELIANCE.NS"]))["RELIANCE.NS"]
    assert row["quote_price"] == pytest.approx(1275.9)
    assert row["quote_change"] == pytest.approx(1275.9 - 1308.4)
    assert row["quote_market_state"] == "CLOSED"
    assert row["quote_timestamp"] == "2026-07-08"
    assert row["quote_currency"] == "INR"
    assert row["market_cap"] == pytest.approx(1275.9 * 6_766_000_000)
    assert row["eod_updated_at"] is not None
    assert row["quote_updated_at"] is not None
    assert row["provider"] == "nse-bhavcopy"
    # The EOD lane must never fake the v7 valuation tier (stale P/E would
    # ride a fresh stamp otherwise).
    assert row["v7_updated_at"] is None


async def test_upsert_eod_priceless_row_is_dropped() -> None:
    await fundamentals_store.upsert_eod_batch(
        [{"symbol": "NOPRICE.NS", "price": None, "trade_date_iso": "2026-07-08"}],
        provider="nse-bhavcopy",
    )
    assert await fundamentals_store.fetch_rows(["NOPRICE.NS"]) == {}
