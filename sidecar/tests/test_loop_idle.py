"""R15-LIFECYCLE-026 — the deep .info crawler idles when nothing is due.

Profiled cause of the idle CPU burn: the crawler re-selected the same 20
largest caps every cycle whether or not their .info was fresh, and re-fetched
them every few seconds forever (each fetch ran yfinance on the event loop).
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from models.fundamentals import Fundamentals
from models.screener import ScreenerUniverse
from services import fundamentals_store, fundamentals_warm, provider_health


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fundamentals_store.reset_for_tests(tmp_path / "fundamentals_test.db")
    fundamentals_warm.reset_for_tests()
    provider_health.reset_for_tests()
    monkeypatch.setattr(fundamentals_warm, "get_region", lambda: "IN")
    yield
    fundamentals_store.reset_for_tests(None)
    fundamentals_warm.reset_for_tests()
    provider_health.reset_for_tests()


def _universe(monkeypatch: pytest.MonkeyPatch, symbols: list[str]) -> None:
    from services import screener_universe_india

    monkeypatch.setattr(
        screener_universe_india,
        "load_india_universe",
        lambda _id: ScreenerUniverse(
            id="india-all", label="India", symbols=symbols, asset_class="equity"
        ),
    )


async def _seed(symbol: str, market_cap: float, info_age_s: float | None) -> None:
    """A store row with ``market_cap`` whose .info was fetched ``info_age_s`` ago."""
    await fundamentals_store.seed_universe([{"symbol": symbol}])
    await fundamentals_store.upsert_v7(
        symbol, Fundamentals(symbol=symbol, market_cap=market_cap, provider="t"), None
    )
    if info_age_s is None:
        return
    real = time.time
    with pytest.MonkeyPatch.context() as m:
        m.setattr(time, "time", lambda: real() - info_age_s)
        await fundamentals_store.upsert_info(
            symbol, Fundamentals(symbol=symbol, roe=0.1, provider="yf")
        )


def _record_fetches(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    fetched: list[str] = []

    async def fake_fund(symbol: str) -> Fundamentals:
        fetched.append(symbol)
        return Fundamentals(symbol=symbol, roe=0.2, provider="yf")

    monkeypatch.setattr("services.provider_registry.get_fundamentals", fake_fund)
    return fetched


@pytest.mark.asyncio
async def test_crawl_loop_wakes_at_most_once_a_minute_when_all_info_is_fresh(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    symbols = ["RELIANCE.NS", "TCS.NS", "INFY.NS"]
    _universe(monkeypatch, symbols)
    for i, sym in enumerate(symbols):
        await _seed(sym, market_cap=1e13 - i, info_age_s=3600)
    fetched = _record_fetches(monkeypatch)

    # A fake clock: every sleep advances it; stop the loop after 5 simulated minutes.
    clock = [0.0]
    cycles = [0]
    real_sleep = asyncio.sleep
    real_crawl_once = fundamentals_warm._crawl_once

    async def fake_sleep(seconds: float) -> None:
        clock[0] += seconds
        if clock[0] >= 300:
            raise asyncio.CancelledError
        await real_sleep(0)

    async def counted_crawl_once() -> int:
        cycles[0] += 1
        return await real_crawl_once()

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(fundamentals_warm, "_crawl_once", counted_crawl_once)
    with pytest.raises(asyncio.CancelledError):
        await fundamentals_warm._crawl_loop()

    assert fetched == []
    assert cycles[0] <= 5


@pytest.mark.asyncio
async def test_stale_row_behind_fresh_larger_caps_is_crawled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The starvation half of the same selection bug: with a one-symbol batch,
    # a fresh larger cap must not keep the stale smaller one out.
    _universe(monkeypatch, ["BIG.NS", "SMALL.NS"])
    monkeypatch.setattr(fundamentals_warm, "_CRAWL_BATCH", 1)
    monkeypatch.setattr(fundamentals_warm, "_CRAWL_JITTER_RANGE", (0.0, 0.001))
    await _seed("BIG.NS", market_cap=9e12, info_age_s=3600)
    await _seed("SMALL.NS", market_cap=1e9, info_age_s=fundamentals_store.TTL_INFO_SECONDS + 60)
    fetched = _record_fetches(monkeypatch)

    assert await fundamentals_warm._crawl_once() == 1
    assert fetched == ["SMALL.NS"]
