"""SQLite-backed positions store for the portfolio panel.

Positions are entered manually in v1.0 — broker connection is Phase 5. The
database lives at ``config.get_data_dir() / "portfolio.db"`` so the sidecar owns
persistence and the frontend never touches the filesystem. The schema is created
lazily and idempotently on every access, which keeps a fresh data directory (or
a test ``tmp_path``) working with no migration step.

The portfolio panel computes P&L, weight, and risk metrics in the frontend by
joining these stored positions against live quotes — this layer only persists
the manually entered facts (symbol, quantity, cost basis).
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from config import get_data_dir
from models.portfolio import Position, PositionInput

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
        conn.execute(_SCHEMA)
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


def get_position(position_id: int) -> Position | None:
    """Return one position by id, or ``None`` if it does not exist."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM positions WHERE id = ?", (position_id,)).fetchone()
    return _row_to_position(row) if row else None


def create_position(payload: PositionInput) -> Position:
    """Insert a new position and return the stored record with its assigned id."""
    opened_at = payload.opened_at.isoformat() if payload.opened_at else None
    with _connect() as conn:
        cursor = conn.execute(
            """
            INSERT INTO positions (symbol, quantity, cost_basis, asset_class, opened_at, note)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.symbol,
                payload.quantity,
                payload.cost_basis,
                payload.asset_class,
                opened_at,
                payload.note,
            ),
        )
        new_id = cursor.lastrowid
    created = get_position(int(new_id)) if new_id is not None else None
    if created is None:  # pragma: no cover - insert always yields a row
        raise RuntimeError("position insert did not return a row")
    return created


def update_position(position_id: int, payload: PositionInput) -> Position | None:
    """Overwrite a position's fields; return the updated record or ``None``."""
    opened_at = payload.opened_at.isoformat() if payload.opened_at else None
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE positions
            SET symbol = ?, quantity = ?, cost_basis = ?, asset_class = ?, opened_at = ?, note = ?
            WHERE id = ?
            """,
            (
                payload.symbol,
                payload.quantity,
                payload.cost_basis,
                payload.asset_class,
                opened_at,
                payload.note,
                position_id,
            ),
        )
        if cursor.rowcount == 0:
            return None
    return get_position(position_id)


def delete_position(position_id: int) -> bool:
    """Delete a position by id; return ``True`` if a row was removed."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM positions WHERE id = ?", (position_id,))
        return cursor.rowcount > 0
