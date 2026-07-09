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
from services.errors import ProviderError


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


@pytest.mark.asyncio
async def test_crawl_failures_rotate_out_and_never_wedge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Permanently-failing symbols (Yahoo doesn't cover thousands of BSE
    scrips) must NOT wedge the crawler: a failed fetch stamps the symbol out
    of the priority head, so the next cycle moves PAST it instead of retrying
    the same batch forever."""
    from services import screener_universe_india

    monkeypatch.setattr(
        screener_universe_india,
        "load_india_universe",
        _tiny_universe(["DEAD1.BO", "DEAD2.BO"]),
    )
    monkeypatch.setattr(fundamentals_warm, "_CRAWL_JITTER_RANGE", (0.0, 0.001))
    await fundamentals_store.seed_universe([{"symbol": "DEAD1.BO"}, {"symbol": "DEAD2.BO"}])

    calls: list[str] = []

    async def always_fails(symbol: str) -> Fundamentals:
        calls.append(symbol)
        raise RuntimeError("yahoo has never heard of this scrip")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", always_fails)

    assert await fundamentals_warm._crawl_once() == 0
    assert sorted(calls) == ["DEAD1.BO", "DEAD2.BO"]
    rows = await fundamentals_store.fetch_rows(["DEAD1.BO", "DEAD2.BO"])
    assert all(r["info_failed_at"] is not None for r in rows.values())
    # The next cycle selects an EMPTY batch — zero re-fetches of the failures.
    assert await fundamentals_warm._crawl_once() == 0
    assert len(calls) == 2, "wedge: the crawler re-selected permanently-failing symbols"


@pytest.mark.asyncio
async def test_crawl_rate_limit_does_not_mark_failure_but_generic_error_does(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A throttle (``ProviderError`` ``kind="rate_limited"``) must NOT stamp
    ``info_failed_at`` — that field drives the 24 h retry rotation, which is
    for symbols Yahoo genuinely has no data for, not ones merely throttled
    this cycle; stamping a throttle would silently stall coverage for a
    whole day. A non-throttle failure still stamps as before."""
    from services import screener_universe_india

    monkeypatch.setattr(
        screener_universe_india,
        "load_india_universe",
        _tiny_universe(["THROTTLED.NS", "BROKEN.NS"]),
    )
    monkeypatch.setattr(fundamentals_warm, "_CRAWL_JITTER_RANGE", (0.0, 0.001))
    await fundamentals_store.seed_universe([{"symbol": "THROTTLED.NS"}, {"symbol": "BROKEN.NS"}])

    async def flaky(symbol: str) -> Fundamentals:
        if symbol == "THROTTLED.NS":
            raise ProviderError("yahoo throttled us", kind="rate_limited")
        raise RuntimeError("yahoo has never heard of this scrip")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", flaky)

    assert await fundamentals_warm._crawl_once() == 0
    rows = await fundamentals_store.fetch_rows(["THROTTLED.NS", "BROKEN.NS"])
    assert rows["THROTTLED.NS"]["info_failed_at"] is None
    assert rows["BROKEN.NS"]["info_failed_at"] is not None


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


# ---------------------------------------------------------------------------
# R11 (D54) — bhavcopy EOD wiring
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bhavcopy_refresh_writes_eod_and_derives_mcap_only_when_v7_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bhavcopy lane fills EOD price/volume for the NSE universe and
    derives market cap (close × seeded shares) ONLY where the v7 valuation
    tier is stale/missing — a fresh v7 mcap is never downgraded."""
    from datetime import date

    from models.fundamentals import Fundamentals
    from services import nse_bhavcopy
    from services.nse_bhavcopy import BhavcopyResult, BhavRow

    # Two store rows: STALECO has only seeded shares (v7 never fetched);
    # FRESHCO has a FRESH v7 mcap that must survive.
    await fundamentals_store.seed_fundamentals(
        [
            {
                "symbol": "STALECO.NS",
                "seed_as_of": 1.0,
                "shares_outstanding": 1_000_000.0,
            }
        ]
    )
    await fundamentals_store.upsert_v7(
        "FRESHCO.NS",
        Fundamentals(
            symbol="FRESHCO.NS",
            market_cap=9e9,
            shares_outstanding=2_000_000.0,
            provider="t",
        ),
        None,
    )

    fake = BhavcopyResult(
        trade_date=date(2026, 7, 8),
        rows={
            "STALECO": BhavRow(
                close=50.0, prev_close=48.0, volume=1000.0, high=None, low=None, series="EQ"
            ),
            "FRESHCO": BhavRow(
                close=100.0, prev_close=99.0, volume=2000.0, high=None, low=None, series="EQ"
            ),
        },
    )

    async def _fake_fetch(max_lookback_days: int = 7):
        return fake

    monkeypatch.setattr(nse_bhavcopy, "fetch_latest", _fake_fetch)

    def _fake_universe_local(universe_id):
        from models.screener import ScreenerUniverse

        return ScreenerUniverse(
            id="nse-all",
            label="t",
            symbols=["STALECO.NS", "FRESHCO.NS", "NOTINBHAV.NS"],
            asset_class="equity",
        )

    from services import screener_universe_india

    monkeypatch.setattr(screener_universe_india, "load_india_universe", _fake_universe_local)

    updated = await fundamentals_warm.bhavcopy_refresh_once()
    assert updated == 2  # NOTINBHAV had no bhavcopy row

    rows = await fundamentals_store.fetch_rows(["STALECO.NS", "FRESHCO.NS"])
    stale = rows["STALECO.NS"]
    assert stale["quote_price"] == 50.0
    assert stale["quote_timestamp"] == "2026-07-08"
    assert stale["market_cap"] == 50.0 * 1_000_000.0  # derived: v7 was missing
    assert stale["eod_updated_at"] is not None
    assert stale["v7_updated_at"] is None  # the EOD lane never fakes v7

    fresh = rows["FRESHCO.NS"]
    assert fresh["quote_price"] == 100.0
    assert fresh["market_cap"] == 9e9  # fresh v7 mcap kept, not derived-over


@pytest.mark.asyncio
async def test_bhavcopy_refresh_degrades_to_zero_on_unreachable_archive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from services import nse_bhavcopy

    async def _fake_fetch(max_lookback_days: int = 7):
        return None

    monkeypatch.setattr(nse_bhavcopy, "fetch_latest", _fake_fetch)
    assert await fundamentals_warm.bhavcopy_refresh_once() == 0
