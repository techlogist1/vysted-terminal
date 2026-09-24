"""Tests for the Phase 6 ``services.data_cache`` SQLite TTL cache."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from services import data_cache


@pytest.fixture(autouse=True)
def _isolated_cache(tmp_path: Path) -> None:
    """Point the cache at a tmp file per test, and reset on teardown."""
    data_cache.reset_for_tests(tmp_path / "test_cache.db")
    yield
    data_cache.reset_for_tests(None)


@pytest.mark.asyncio
async def test_set_then_get_hit_returns_value() -> None:
    await data_cache.set("macro:fred:GDP", {"observations": [1, 2, 3]})
    got = await data_cache.get("macro:fred:GDP", ttl_seconds=60)
    assert got == {"observations": [1, 2, 3]}


@pytest.mark.asyncio
async def test_get_miss_returns_none() -> None:
    got = await data_cache.get("not-there", ttl_seconds=60)
    assert got is None


@pytest.mark.asyncio
async def test_get_stale_returns_none() -> None:
    await data_cache.set("k", "v")
    # ttl=0.0 — every row immediately considered stale.
    got = await data_cache.get("k", ttl_seconds=0)
    assert got is None


@pytest.mark.asyncio
async def test_set_upsert_overwrites_value_and_bumps_timestamp() -> None:
    await data_cache.set("k", "old")
    before = time.time()
    await asyncio.sleep(0.01)
    await data_cache.set("k", "new")
    got = await data_cache.get("k", ttl_seconds=60)
    assert got == "new"
    # ``updated_at`` was bumped past ``before``.
    raw_row = (
        data_cache._get_conn()
        .execute(  # type: ignore[attr-defined]
            "SELECT updated_at FROM cache WHERE key = ?", ("k",)
        )
        .fetchone()
    )
    assert raw_row is not None
    assert raw_row[0] >= before


@pytest.mark.asyncio
async def test_invalidate_by_prefix_drops_matching_rows() -> None:
    await data_cache.set("macro:fred:GDP", 1)
    await data_cache.set("macro:fred:UNRATE", 2)
    await data_cache.set("sec:filing:0001", 3)
    dropped = await data_cache.invalidate("macro:fred:")
    assert dropped == 2
    assert await data_cache.get("macro:fred:GDP", 60) is None
    assert await data_cache.get("macro:fred:UNRATE", 60) is None
    assert await data_cache.get("sec:filing:0001", 60) == 3


@pytest.mark.asyncio
async def test_invalidate_empty_prefix_raises() -> None:
    with pytest.raises(ValueError):
        await data_cache.invalidate("")


@pytest.mark.asyncio
async def test_clear_drops_every_row() -> None:
    await data_cache.set("a", 1)
    await data_cache.set("b", 2)
    assert await data_cache.size() == 2
    await data_cache.clear()
    assert await data_cache.size() == 0


@pytest.mark.asyncio
async def test_concurrent_sets_serialize_through_lock() -> None:
    """Many concurrent ``set`` calls all land without losing rows."""
    keys = [f"concurrent:{i}" for i in range(50)]

    async def write(key: str) -> None:
        await data_cache.set(key, key)

    await asyncio.gather(*(write(k) for k in keys))
    assert await data_cache.size() == 50
    for key in keys:
        assert await data_cache.get(key, 60) == key


@pytest.mark.asyncio
async def test_get_with_zero_ttl_always_misses() -> None:
    await data_cache.set("k", "v")
    assert await data_cache.get("k", ttl_seconds=0) is None
    assert await data_cache.get("k", ttl_seconds=-1) is None


@pytest.mark.asyncio
async def test_db_path_returns_configured_path(tmp_path: Path) -> None:
    expected = tmp_path / "test_cache.db"
    # Already pointed there by the autouse fixture.
    assert data_cache.db_path() == expected


@pytest.mark.asyncio
async def test_value_can_be_nested_json() -> None:
    payload = {
        "rows": [{"date": "2026-05-16", "value": 1.23}, {"date": "2026-05-17", "value": 4.56}],
        "metadata": {"source": "FRED", "series_id": "GDP"},
    }
    await data_cache.set("complex", payload)
    got = await data_cache.get("complex", 60)
    assert got == payload


@pytest.mark.asyncio
async def test_ensure_build_keeps_rows_of_the_same_build() -> None:
    await data_cache.ensure_build("0.8.0")
    await data_cache.set("sec:filings:AAPL", {"rows": 1})
    assert await data_cache.ensure_build("0.8.0") is False
    assert await data_cache.get("sec:filings:AAPL", 60) == {"rows": 1}


@pytest.mark.asyncio
async def test_ensure_build_drops_rows_written_by_another_build() -> None:
    # A cache from a build that predates the version stamp is stale too.
    await data_cache.set("shareholding:SIL", {"split": "pre-fix"})
    assert await data_cache.ensure_build("0.8.0") is True
    await data_cache.set("sec:filings:AAPL", {"rows": "0.8.0"})
    assert await data_cache.ensure_build("0.8.1") is True
    assert await data_cache.get("sec:filings:AAPL", 60) is None
    assert await data_cache.size() == 0


@pytest.mark.asyncio
async def test_ensure_build_keeps_rows_written_after_the_switch() -> None:
    await data_cache.ensure_build("0.8.0")
    assert await data_cache.ensure_build("0.8.1") is True
    await data_cache.set("macro:fred:GDP", {"v": 1})
    assert await data_cache.ensure_build("0.8.1") is False
    assert await data_cache.get("macro:fred:GDP", 60) == {"v": 1}


# ---------------------------------------------------------------------------
# get_with_meta (R15-DATA-068) — as-of stamping
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_with_meta_hit_returns_value_and_fetch_time() -> None:
    before = time.time()
    await data_cache.set("earnings:AAPL:history", {"symbol": "AAPL"})
    after = time.time()
    got = await data_cache.get_with_meta("earnings:AAPL:history", ttl_seconds=60)
    assert got is not None
    value, fetched_at = got
    assert value == {"symbol": "AAPL"}
    assert before <= fetched_at <= after


@pytest.mark.asyncio
async def test_get_with_meta_miss_returns_none() -> None:
    assert await data_cache.get_with_meta("not-there", ttl_seconds=60) is None


@pytest.mark.asyncio
async def test_get_with_meta_stale_returns_none() -> None:
    await data_cache.set("k", "v")
    assert await data_cache.get_with_meta("k", ttl_seconds=0) is None


@pytest.mark.asyncio
async def test_get_with_meta_fetch_time_is_the_original_set_not_the_read_time() -> None:
    # A case not written against: reading twice must keep returning the
    # SAME fetched_at, proving it is the row's write time, not read time.
    await data_cache.set("k", "v")
    first = await data_cache.get_with_meta("k", ttl_seconds=60)
    await asyncio.sleep(0.05)
    second = await data_cache.get_with_meta("k", ttl_seconds=60)
    assert first is not None and second is not None
    assert first[1] == second[1]


@pytest.mark.asyncio
async def test_a_set_past_the_ceiling_evicts_the_oldest_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R15-DATA-096: the cache had no ceiling. Past it, the least recently
    written rows go; a re-written old key counts as recent."""
    monkeypatch.setattr(data_cache, "MAX_ROWS", 3)
    for key in ("a", "b", "c"):
        await data_cache.set(key, key)
        await asyncio.sleep(0.01)
    await data_cache.set("a", "a2")  # refreshes a: b is now the oldest
    await asyncio.sleep(0.01)
    await data_cache.set("d", "d")
    assert await data_cache.size() == 3
    assert await data_cache.get("b", ttl_seconds=60) is None
    assert [await data_cache.get(k, ttl_seconds=60) for k in ("a", "c", "d")] == ["a2", "c", "d"]


@pytest.mark.asyncio
async def test_sqlite_work_runs_off_the_event_loop_thread() -> None:
    import threading

    threads: set[int] = set()
    data_cache._get_conn().set_trace_callback(lambda _sql: threads.add(threading.get_ident()))
    await data_cache.set("k", "v")
    await data_cache.get("k", ttl_seconds=60)
    await data_cache.invalidate("k")
    assert threads
    assert threading.get_ident() not in threads
