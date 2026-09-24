"""Generic SQLite-backed TTL cache — Phase 6 foundation.

Read-heavy upstreams (SEC EDGAR enforces 10 req/s; ECB / IMF / World Bank
data updates at monthly/quarterly cadences) benefit from a local
cache-on-read with a configurable TTL. This module ships a small
namespaced JSON cache backed by SQLite that any service can route reads
through; the macro provider router and the SEC filings provider are the
v0.6.0 first consumers.

Design choices
~~~~~~~~~~~~~~

- **SQLite**, not in-memory dict: the cache must survive sidecar
  restarts. The portfolio + workspace stores already pull SQLite into
  the bundle, so the marginal cost is one new ``.db`` file.
- **Key as opaque string**, value as JSON: lets callers pick whatever
  namespacing scheme fits — ``macro:fred:GDP``, ``sec:filing:0001193...``,
  ``screener:universe:sp500``. Cache code never parses the key.
- **TTL per ``get``** rather than per ``set``: producers pick the
  freshness window they want for each read, so the same cache row can
  serve a "freshness-tolerant" caller and a "must-be-fresh" caller
  differently without separate cache buckets.
- **``asyncio.Lock`` per process** rather than SQLite's WAL: keeps the
  contention model simple. The sidecar is a single Python process per
  app instance; concurrent ``set`` calls serialise behind the lock. The
  SQLite work itself runs on a worker thread (``asyncio.to_thread``) so a
  slow disk never blocks the event loop (R15-DATA-096).
- **A row ceiling** (:data:`MAX_ROWS`): a ``set`` that takes the table past
  it evicts the least recently written rows, so per-symbol keys cannot grow
  the file without bound (R15-DATA-096).
- **No in-memory hot tier**. SQLite reads from this single-process
  cache are microseconds; an extra LRU layer adds complexity without
  measurable benefit at v0.6.0's expected miss rate.

Public surface
~~~~~~~~~~~~~~

  - :func:`get(key, ttl_seconds)` — returns the cached JSON value if the
    row's ``updated_at`` is within ``ttl_seconds`` of now, else ``None``.
  - :func:`get_with_meta(key, ttl_seconds)` — like :func:`get`, but also
    returns the row's fetch time so a caller can stamp an ``as_of``.
  - :func:`set(key, value)` — upsert. Updates ``updated_at`` to now.
  - :func:`invalidate(key_prefix)` — delete every row whose key starts
    with the prefix. Useful for "drop the whole macro / FRED bucket"
    on user demand.
  - :func:`clear()` — delete every row.
  - :func:`ensure_build(version)` — clear every row once when the sidecar
    version changes (called from the app lifespan).
  - :func:`size()` — current row count. Test helper.
  - :func:`reset_for_tests(path=None)` — close the live connection and
    re-point at an optional alternate db file.
"""

from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from config import get_data_dir

DB_FILENAME = "data_cache.db"

_DDL = """
CREATE TABLE IF NOT EXISTS cache (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at REAL NOT NULL
)
"""
_INDEX_DDL = "CREATE INDEX IF NOT EXISTS cache_updated_at ON cache(updated_at)"

#: The most rows kept; a ``set`` past it evicts the least recently written.
MAX_ROWS = 20_000

#: One row per setting; ``build`` holds the sidecar version that wrote the cache.
_META_DDL = "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_conn: sqlite3.Connection | None = None
_db_path: Path | None = None


def _connect(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL + schema bootstrap."""
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_DDL)
    conn.execute(_INDEX_DDL)
    conn.execute(_META_DDL)
    return conn


async def _run[T](work: Callable[[sqlite3.Connection], T]) -> T:
    """Run ``work`` on the cache connection, off the event loop, one at a time."""
    async with _lock:
        return await asyncio.to_thread(lambda: work(_get_conn()))


async def ensure_build(version: str) -> bool:
    """Clear the cache when it was written by a different sidecar build.

    Rows persist across restarts for up to their TTL, so without this a row
    computed by a build with a since-fixed provider bug keeps being served
    after the upgrade. The lifespan calls this once at boot with the app
    version. Returns ``True`` when the cache was cleared.
    """

    def switch(conn: sqlite3.Connection) -> tuple[bool, Any]:
        row = conn.execute("SELECT value FROM meta WHERE key = 'build'").fetchone()
        if row is not None and row[0] == version:
            return False, row
        conn.execute("DELETE FROM cache")
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('build', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (version,),
        )
        return True, row

    cleared, row = await _run(switch)
    if not cleared:
        return False
    logger.info(
        "data_cache: build %s (cache written by %s) - cleared",
        version,
        row[0] if row else "an unversioned build",
    )
    return True


def _get_conn() -> sqlite3.Connection:
    """Return the live cache connection, creating it on first use."""
    global _conn, _db_path
    if _conn is None:
        _db_path = get_data_dir() / DB_FILENAME
        _conn = _connect(_db_path)
    return _conn


def db_path() -> Path:
    """Return the on-disk cache database path (for diagnostics)."""
    _get_conn()
    assert _db_path is not None
    return _db_path


async def get(key: str, ttl_seconds: float) -> Any | None:
    """Return the cached JSON value for ``key`` if fresh enough.

    Args:
        key: opaque string key; callers are responsible for namespacing.
        ttl_seconds: maximum allowed staleness in seconds. The row's
            ``updated_at`` must satisfy ``now - updated_at <= ttl_seconds``
            for a hit; otherwise the row is treated as stale and ``None``
            is returned (the row is NOT auto-evicted — a subsequent
            :func:`set` overwrites it).

    Returns the decoded JSON value (any shape ``json.loads`` returns) on
    hit, or ``None`` on miss / stale.
    """
    hit = await get_with_meta(key, ttl_seconds)
    return None if hit is None else hit[0]


async def get_with_meta(key: str, ttl_seconds: float) -> tuple[Any, float] | None:
    """Like :func:`get`, but also returns the row's fetch time (R15-DATA-068).

    Args:
        key: opaque string key.
        ttl_seconds: same freshness window as :func:`get`.

    Returns ``None`` on miss / stale, or ``(value, updated_at)`` on a fresh
    hit — ``updated_at`` is the epoch seconds of the original :func:`set`
    call, letting a caller stamp an ``as_of`` that reflects when the data
    was actually fetched rather than when the cache happened to be read.
    """
    if ttl_seconds <= 0:
        return None
    row = await _run(
        lambda conn: conn.execute(
            "SELECT value, updated_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
    )
    if row is None:
        return None
    value_text, updated_at = row
    updated_at = float(updated_at)
    if time.time() - updated_at > ttl_seconds:
        return None
    try:
        return json.loads(value_text), updated_at
    except (TypeError, ValueError):
        logger.warning("data_cache: stored value for %r is not valid JSON; treating as miss", key)
        return None


async def set(key: str, value: Any) -> None:  # noqa: A001 — set matches the cache idiom
    """Upsert a key/value, bumping ``updated_at`` to now.

    Args:
        key: opaque string key.
        value: any JSON-serialisable value. Non-serialisable values
            raise :class:`TypeError` (callers are expected to pass
            ``dict`` / ``list`` of primitives).
    """
    payload = json.dumps(value, default=str)
    now = time.time()

    def upsert(conn: sqlite3.Connection) -> None:
        conn.execute(
            "INSERT INTO cache(key, value, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, payload, now),
        )
        conn.execute(
            "DELETE FROM cache WHERE key IN "
            "(SELECT key FROM cache ORDER BY updated_at DESC LIMIT -1 OFFSET ?)",
            (MAX_ROWS,),
        )

    await _run(upsert)


async def invalidate(key_prefix: str) -> int:
    """Delete every cache row whose key starts with ``key_prefix``.

    Returns the number of rows deleted. ``""`` is rejected to prevent
    accidental "drop everything" — use :func:`clear` if that is intended.
    """
    if not key_prefix:
        raise ValueError("invalidate() requires a non-empty key_prefix; use clear() instead")
    return await _run(
        lambda conn: (
            conn.execute("DELETE FROM cache WHERE key LIKE ?", (f"{key_prefix}%",)).rowcount or 0
        )
    )


async def clear() -> None:
    """Delete every row in the cache."""
    await _run(lambda conn: conn.execute("DELETE FROM cache"))


async def size() -> int:
    """Return the current row count — test helper."""
    row = await _run(lambda conn: conn.execute("SELECT COUNT(*) FROM cache").fetchone())
    return int(row[0]) if row else 0


def reset_for_tests(path: Path | None = None) -> None:
    """Close the live connection and re-point at an optional alt db path.

    The pytest fixtures use this to point each test at a temp file via
    ``tmp_path``. Calling with ``path=None`` reverts to the production
    location returned by :func:`config.get_data_dir`.
    """
    global _conn, _db_path
    if _conn is not None:
        try:
            _conn.close()
        except sqlite3.Error:
            pass
    _conn = None
    _db_path = path
    if path is not None:
        # Eagerly open so the path takes effect immediately.
        _conn = _connect(path)
        _db_path = path
