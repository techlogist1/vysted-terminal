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
  app instance; concurrent ``set`` calls serialise behind the lock.
- **No in-memory hot tier**. SQLite reads from this single-process
  cache are microseconds; an extra LRU layer adds complexity without
  measurable benefit at v0.6.0's expected miss rate.

Public surface
~~~~~~~~~~~~~~

  - :func:`get(key, ttl_seconds)` — returns the cached JSON value if the
    row's ``updated_at`` is within ``ttl_seconds`` of now, else ``None``.
  - :func:`set(key, value)` — upsert. Updates ``updated_at`` to now.
  - :func:`invalidate(key_prefix)` — delete every row whose key starts
    with the prefix. Useful for "drop the whole macro / FRED bucket"
    on user demand.
  - :func:`clear()` — delete every row.
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

logger = logging.getLogger(__name__)

_lock = asyncio.Lock()
_conn: sqlite3.Connection | None = None
_db_path: Path | None = None


def _connect(path: Path) -> sqlite3.Connection:
    """Open a SQLite connection with WAL + schema bootstrap."""
    conn = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(_DDL)
    return conn


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
    if ttl_seconds <= 0:
        return None
    async with _lock:
        cur = _get_conn().execute(
            "SELECT value, updated_at FROM cache WHERE key = ?",
            (key,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    value_text, updated_at = row
    if time.time() - float(updated_at) > ttl_seconds:
        return None
    try:
        return json.loads(value_text)
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
    async with _lock:
        _get_conn().execute(
            "INSERT INTO cache(key, value, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, payload, now),
        )


async def invalidate(key_prefix: str) -> int:
    """Delete every cache row whose key starts with ``key_prefix``.

    Returns the number of rows deleted. ``""`` is rejected to prevent
    accidental "drop everything" — use :func:`clear` if that is intended.
    """
    if not key_prefix:
        raise ValueError("invalidate() requires a non-empty key_prefix; use clear() instead")
    async with _lock:
        cur = _get_conn().execute(
            "DELETE FROM cache WHERE key LIKE ?",
            (f"{key_prefix}%",),
        )
        return cur.rowcount or 0


async def clear() -> None:
    """Delete every row in the cache."""
    async with _lock:
        _get_conn().execute("DELETE FROM cache")


async def size() -> int:
    """Return the current row count — test helper."""
    async with _lock:
        cur = _get_conn().execute("SELECT COUNT(*) FROM cache")
        row = cur.fetchone()
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
