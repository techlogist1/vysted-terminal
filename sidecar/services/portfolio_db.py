"""SQLite legacy positions ledger.

Holdings are owned by the workspace blob (the frontend portfolios store); this
ledger is where they lived before the move, and the app reads it once to import
them (R15-LIFECYCLE-009). No app surface writes it, so it has no writers
(R15-CODE-PLATFORM-021). The database lives at
``config.get_data_dir() / "portfolio.db"``; the schema is created lazily and
idempotently on every access, which keeps a fresh data directory (or a test
``tmp_path``) working with no migration step.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from config import get_data_dir
from models.portfolio import Position
from services import schema_version

DB_FILENAME = "portfolio.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quantity REAL NOT NULL,
    cost_basis REAL NOT NULL,
    asset_class TEXT NOT NULL DEFAULT 'equity',
    opened_at TEXT,
    note TEXT
)
"""

#: Forward-only migrations, one per ``user_version`` (R15-LIFECYCLE-024).
_STEPS = (schema_version.statements(_SCHEMA),)


def _db_path() -> str:
    """Resolve the portfolio database path under the current data directory."""
    return str(get_data_dir() / DB_FILENAME)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yield a connection with the schema ensured; commits on clean exit.

    The path is resolved per call rather than cached so a test that points
    ``VYSTED_DATA_DIR`` at a ``tmp_path`` always hits its own database.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        schema_version.migrate(conn, _STEPS)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema() -> None:
    """Create the ``positions`` table if it does not yet exist (idempotent)."""
    with _connect():
        pass


def _row_to_position(row: sqlite3.Row) -> Position:
    """Map a database row to the ``Position`` Pydantic model."""
    opened_at = row["opened_at"]
    return Position(
        id=row["id"],
        symbol=row["symbol"],
        quantity=row["quantity"],
        cost_basis=row["cost_basis"],
        asset_class=row["asset_class"],
        opened_at=datetime.fromisoformat(opened_at) if opened_at else None,
        note=row["note"],
    )


def list_positions() -> list[Position]:
    """Return every stored position, oldest id first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM positions ORDER BY id").fetchall()
    return [_row_to_position(row) for row in rows]
