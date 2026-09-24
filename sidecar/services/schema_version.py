"""Forward-only SQLite schema migrations keyed on ``PRAGMA user_version``.

Each store lists its steps in order; step ``n`` (1-based) takes a database from
``user_version`` ``n - 1`` to ``n``. Step 1 is the store's schema as it stood
before versioning (``CREATE IF NOT EXISTS`` plus its additive column guards), so
an unversioned database from any earlier build lands on version 1. A database
whose version is newer than the steps this build knows was written by a newer
build: it is logged and left untouched, never downgraded (R15-LIFECYCLE-024).
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Sequence

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


def _version(conn: sqlite3.Connection) -> int:
    return int(conn.execute("PRAGMA user_version").fetchone()[0])
