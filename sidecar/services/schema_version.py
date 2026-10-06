"""Forward-only SQLite schema migrations keyed on ``PRAGMA user_version``.

Each store lists its steps in order; step ``n`` (1-based) takes a database from
``user_version`` ``n - 1`` to ``n``. Step 1 is the store's schema as it stood
before versioning (``CREATE IF NOT EXISTS`` plus its additive column guards), so
an unversioned database from any earlier build lands on version 1. A database
whose version is newer than the steps this build knows was written by a newer
build: it is logged and left untouched, never downgraded (R15-LIFECYCLE-024).
Every store opens its database through :func:`open_migrated`, which moves an
unreadable file aside instead of failing every open (R15-FINAL-008).
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

Step = Callable[[sqlite3.Connection], None]


def statements(script: str) -> Step:
    """A step running each ``;``-separated DDL statement of ``script``.

    ``executescript`` would COMMIT the step's transaction, so the statements run
    one by one inside it instead.
    """
    parts = [part.strip() for part in script.split(";") if part.strip()]

    def step(conn: sqlite3.Connection) -> None:
        for part in parts:
            conn.execute(part)

    return step


def migrate(conn: sqlite3.Connection, steps: Sequence[Step]) -> int:
    """Run the steps past the database's ``user_version``; return the version now on disk.

    Each step and its version bump commit together under a write lock, so a
    failed step leaves the database at the last completed version and two
    connections opening an old database never run the same step twice. A
    version above ``len(steps)`` is left as it is.
    """
    target = len(steps)
    current = _version(conn)
    while current < target:
        conn.execute("BEGIN IMMEDIATE")
        try:
            current = _version(conn)  # another connection may have migrated meanwhile
            if current < target:
                steps[current](conn)
                current += 1
                conn.execute(f"PRAGMA user_version = {current}")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
    if current > target:
        logger.warning(
            "schema_version: database is at version %d, newer than this build's %d; left untouched",
            current,
            target,
        )
    return current


def open_migrated(
    path: str | Path,
    steps: Sequence[Step],
    *,
    prepare: Callable[[sqlite3.Connection], None] | None = None,
    row_factory: Any = None,
    quiet: bool = False,
    **connect_kwargs: Any,
) -> tuple[sqlite3.Connection, int]:
    """Connect to ``path`` with ``row_factory``, run ``prepare`` then :func:`migrate`; return the
    connection and the version on disk.

    A file SQLite reports as not a database or malformed (a bad header, a
    truncated file) is renamed with its ``-wal``/``-shm`` to ``.corrupt-<ts>``,
    kept for recovery, and a fresh database is created in its place, so one
    damaged file costs that store's data instead of every open of it failing.
    Any other error (``database is locked``) is raised untouched. A user store
    logs the quarantine as a warning; ``quiet`` (a regenerable cache) as info.
    """
    for attempt in range(2):
        conn = sqlite3.connect(str(path), **connect_kwargs)
        conn.row_factory = row_factory
        try:
            if prepare is not None:
                prepare(conn)
            return conn, migrate(conn, steps)
        except sqlite3.DatabaseError as exc:
            conn.close()
            message = str(exc)
            if attempt or not ("not a database" in message or "malformed" in message):
                raise
            moved = _quarantine(Path(path))
            log = logger.info if quiet else logger.warning
            log(
                "schema_version: %s is unreadable (%s); moved to %s and recreated", path, exc, moved
            )
        except BaseException:
            conn.close()
            raise
    raise AssertionError("unreachable")


def _quarantine(path: Path) -> Path:
    """Rename ``path`` and its -wal/-shm to ``<name>.corrupt-<ts>``; return the db's new path."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    for suffix in ("-wal", "-shm", ""):
        side = path.with_name(path.name + suffix)
        if side.exists():
            side.rename(side.with_name(f"{side.name}.corrupt-{stamp}"))
    return path.with_name(f"{path.name}.corrupt-{stamp}")


def _version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])
