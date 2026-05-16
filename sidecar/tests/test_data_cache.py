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
