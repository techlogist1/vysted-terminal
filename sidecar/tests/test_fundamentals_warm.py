"""Tests for the region-aware India fundamentals warming (R10, D40).

The warm workers must: seed identity+sector rows locally (<1 s, no network),
sweep only STALE symbols through the v7 batch into the store, pause the deep
``.info`` crawler while a foreground screen runs, respect the
``info_priority`` ordering, and start/stop cleanly from the lifespan without
leaking tasks. No live network — the v7 endpoint rides the MockTransport
seam and the registry is monkeypatched.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from models.fundamentals import Fundamentals
from models.market import Quote
from models.screener import ScreenerUniverse
from services import fundamentals_store, fundamentals_warm
from services import yahoo_batch_provider as yb


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path) -> None:
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    fundamentals_warm.reset_for_tests()
    yb.reset_for_tests()
    yield
    fundamentals_store.reset_for_tests(None)
    fundamentals_warm.reset_for_tests()
    yb.reset_for_tests()


def _tiny_universe(symbols: list[str]):
    def _load(universe_id: str) -> ScreenerUniverse:  # noqa: ARG001
        return ScreenerUniverse(
            id="india-all", label="India (NSE + BSE)", symbols=symbols, asset_class="equity"
        )

    return _load


def _v7_row(symbol: str) -> dict[str, object]:
    return {
        "symbol": symbol,
        "longName": f"{symbol} Ltd",
        "regularMarketPrice": 1250.0,
        "regularMarketVolume": 100_000,
        "currency": "INR",
        "marketCap": 5e12,
        "trailingPE": 25.0,
        "sharesOutstanding": 4e9,
    }


def _install_v7(rows: dict[str, dict[str, object]]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            requested = (request.url.params.get("symbols") or "").split(",")
            result = [rows[s] for s in requested if s in rows]
            return httpx.Response(200, json={"quoteResponse": {"result": result}})
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))


# ---------------------------------------------------------------------------
# Pause gate
# ---------------------------------------------------------------------------


def test_screen_bracket_refcounts_overlapping_runs() -> None:
    assert not fundamentals_warm.foreground_screen_running()
    fundamentals_warm.screen_started()
    fundamentals_warm.screen_started()
    assert fundamentals_warm.foreground_screen_running()
    fundamentals_warm.screen_finished()
    # One run still in flight — the crawler must stay paused.
    assert fundamentals_warm.foreground_screen_running()
    fundamentals_warm.screen_finished()
    assert not fundamentals_warm.foreground_screen_running()
    # Over-release never goes negative.
    fundamentals_warm.screen_finished()
    assert not fundamentals_warm.foreground_screen_running()


# ---------------------------------------------------------------------------
# Boot seed (local-only)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_india_store_writes_identity_rows() -> None:
    touched = await fundamentals_warm.seed_india_store()
    assert touched > 2000  # the real india-all universe
    rows = await fundamentals_store.fetch_rows(["RELIANCE.NS"])
    rel = rows["RELIANCE.NS"]
    assert rel["exchange"] == "NSE"
    assert rel["scrip_code"] == "500325"  # joined from the BSE master
    assert rel["isin"] == "INE002A01018"
    # The seed carries no tier stamps — identity only.
    assert rel["v7_updated_at"] is None


# ---------------------------------------------------------------------------
# v7 sweep (stale-only, store-backed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sweep_once_fetches_only_stale_symbols(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import screener_universe_india

    monkeypatch.setattr(
        screener_universe_india,
        "load_india_universe",
        _tiny_universe(["FRESH.NS", "STALE.NS"]),
    )
    # FRESH already has live tiers; STALE has never been fetched.
    await fundamentals_store.upsert_v7(
        "FRESH.NS",
        Fundamentals(symbol="FRESH.NS", market_cap=1e12, provider="test"),
        Quote(
            symbol="FRESH.NS",
            price=10.0,
            change=0.0,
            change_percent=0.0,
            volume=1.0,
            currency="INR",
            timestamp=datetime.now(tz=UTC),
            provider="test",
        ),
    )
    requested: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "getcrumb" in request.url.path:
            return httpx.Response(200, text="crumb")
        if request.url.path.endswith("/v7/finance/quote"):
            symbols = (request.url.params.get("symbols") or "").split(",")
            requested.extend(symbols)
            return httpx.Response(
                200, json={"quoteResponse": {"result": [_v7_row(s) for s in symbols]}}
            )
        return httpx.Response(200, text="ok")

    yb.reset_for_tests(httpx.MockTransport(handler))

    throttled = await fundamentals_warm._sweep_once()
    assert throttled is False
    assert requested == ["STALE.NS"]
    row = (await fundamentals_store.fetch_rows(["STALE.NS"]))["STALE.NS"]
    assert row["market_cap"] == 5e12
    assert row["shares_outstanding"] == 4e9


# ---------------------------------------------------------------------------
# Deep .info crawler
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_crawl_once_respects_priority_and_pause(monkeypatch: pytest.MonkeyPatch) -> None:
    from services import screener_universe_india

    monkeypatch.setattr(
        screener_universe_india,
        "load_india_universe",
        _tiny_universe(["BIG.NS", "SMALL.NS"]),
    )
    monkeypatch.setattr(fundamentals_warm, "_CRAWL_JITTER_RANGE", (0.0, 0.001))
    await fundamentals_store.seed_universe(
        [
            {"symbol": "BIG.NS", "shares_outstanding": 1.0},
            {"symbol": "SMALL.NS"},
        ]
    )
    await fundamentals_store.upsert_v7(
        "BIG.NS",
        Fundamentals(symbol="BIG.NS", market_cap=9e12, provider="t"),
        None,
    )

    fetched: list[str] = []

    async def fake_fund(symbol: str) -> Fundamentals:
        fetched.append(symbol)
        return Fundamentals(symbol=symbol, sector="Technology", roe=0.2, provider="yf")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)

    # Paused while a foreground screen runs: the crawl must NOT finish.
    fundamentals_warm.screen_started()
    task = asyncio.create_task(fundamentals_warm._crawl_once())
    await asyncio.sleep(0.05)
    assert not task.done()
    assert fetched == []
    fundamentals_warm.screen_finished()
    count = await task
    assert count == 2
    # Priority: never-fetched by market cap desc — BIG before SMALL.
    assert fetched[0] == "BIG.NS"
    row = (await fundamentals_store.fetch_rows(["BIG.NS"]))["BIG.NS"]
    assert row["sector"] == "Technology"
    assert row["sector_source"] == "yf"


# ---------------------------------------------------------------------------
# Lifespan start/stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_stop_clean_no_leaked_tasks() -> None:
    # Region defaults to US in tests — the loops idle without network or
    # store writes, and stop cancels + awaits both tasks.
    fundamentals_warm.start_warm_fundamentals()
    assert fundamentals_warm._sweep_task is not None
    assert fundamentals_warm._crawl_task is not None
    sweep_task = fundamentals_warm._sweep_task
    crawl_task = fundamentals_warm._crawl_task
    await asyncio.sleep(0.02)
    assert not sweep_task.done()
    await fundamentals_warm.stop_warm_fundamentals()
    assert sweep_task.done()
    assert crawl_task.done()
    assert fundamentals_warm._sweep_task is None
    assert fundamentals_warm._crawl_task is None


@pytest.mark.asyncio
async def test_start_is_idempotent() -> None:
    fundamentals_warm.start_warm_fundamentals()
    first = fundamentals_warm._sweep_task
    fundamentals_warm.start_warm_fundamentals()
    assert fundamentals_warm._sweep_task is first
    await fundamentals_warm.stop_warm_fundamentals()
