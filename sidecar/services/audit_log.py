"""Append-only audit log — BLUEPRINT §6.5 #4.

Every order proposal, every confirmation, every placement, every kill-switch
fire, every disclaimer ack lands here. The log is exportable and survives
app restarts. It is the user's own record of what the terminal did on their
behalf.

The append-only guarantee is enforced at the DB level via SQLite triggers
(see ``models/audit_log.py`` AUDIT_LOG_DDL). Two connection contexts:

- :func:`_writer_connection` — the broker-adapter writer role. Issues INSERT
  + SELECT. Even if a writer mistakenly attempts UPDATE/DELETE the trigger
  raises ``sqlite3.OperationalError`` with the explicit message
  ``"audit log is append-only: UPDATE not permitted"`` /
  ``"... DELETE not permitted"``.
- :func:`_reader_connection` — opens with ``PRAGMA query_only=ON`` so even
  INSERT is physically refused at the connection level. Used by the
  ``GET /safety/audit-log`` route and CSV exports.

The dedicated safety-layer audit suite (Teammate S) asserts the trigger
raises at the SQL level + the reader connection refuses writes. The
audit log is the v0.5.0 distribution's notion of regulatory-grade
order traceability — sentinel-evidence in the Tradesa V2 sense.
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from config import get_data_dir
from models.audit_log import AUDIT_LOG_DB_FILENAME, AUDIT_LOG_DDL
from models.safety import AuditLogAppendRequest, AuditLogEntry


def _db_path() -> str:
    """Resolve the audit-log database path under the current data directory."""
    return str(get_data_dir() / AUDIT_LOG_DB_FILENAME)


def _apply_schema(conn: sqlite3.Connection) -> None:
    """Apply the AUDIT_LOG_DDL idempotently — schema + indices + triggers."""
    conn.executescript(AUDIT_LOG_DDL)


@contextmanager
def _writer_connection() -> Iterator[sqlite3.Connection]:
    """Open a writer connection — INSERT + SELECT allowed, UPDATE/DELETE
    blocked by the triggers in the DDL.

    The schema is applied lazily on every connect so a fresh data directory
    (or a test tmp_path) just works. WAL journal mode is enabled to
    minimise writer-lock contention (the kill-switch handler may write
    while the UI is tailing).
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        _apply_schema(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


@contextmanager
def _reader_connection() -> Iterator[sqlite3.Connection]:
    """Open a reader-only connection. ``PRAGMA query_only=ON`` refuses any
    write at the connection level, regardless of which role issued it.

    Used by ``GET /safety/audit-log`` and the CSV export route. The reader
    never applies the schema — assumes a writer has run at least once.
    """
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA query_only=ON")
        yield conn
    finally:
        conn.close()


def _row_to_entry(row: sqlite3.Row) -> AuditLogEntry:
    """Map a DB row to an :class:`AuditLogEntry` Pydantic model."""
    payload_raw: Any = json.loads(row["payload_json"])
    payload = payload_raw if isinstance(payload_raw, dict) else {}
    return AuditLogEntry(
        id=row["id"],
        timestampMs=row["timestamp_ms"],
        broker=row["broker"],
        accountId=row["account_id"],
        action=row["action"],
        payload=payload,
        source=row["source"],
        outcome=row["outcome"],
    )


def append(req: AuditLogAppendRequest) -> int:
    """Insert a new audit-log row and return its monotonically-increasing id.

    The DB's BEFORE-UPDATE / BEFORE-DELETE triggers do not fire on INSERT, so
    the standard path is unaffected; only mutation attempts raise.
    """
    payload_json = json.dumps(req.payload)
    with _writer_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO audit_orders
                (timestamp_ms, broker, account_id, action, payload_json, source, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                req.timestamp_ms,
                req.broker,
                req.account_id,
                req.action,
                payload_json,
                req.source,
                req.outcome,
            ),
        )
        row_id = cursor.lastrowid
        if row_id is None:  # pragma: no cover - INSERT always assigns an id
            raise RuntimeError("audit-log INSERT did not yield an id")
        return row_id


def tail(limit: int = 200) -> list[AuditLogEntry]:
    """Return the most-recent ``limit`` entries, newest first."""
    with _reader_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp_ms, broker, account_id, action,
                   payload_json, source, outcome
            FROM audit_orders
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [_row_to_entry(row) for row in rows]


def range_(start_ms: int, end_ms: int) -> list[AuditLogEntry]:
    """Return entries whose ``timestamp_ms`` falls in the closed range.

    Named ``range_`` (with trailing underscore) so the symbol does not
    shadow the Python builtin in callers that ``from services.audit_log
    import *``.
    """
    with _reader_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, timestamp_ms, broker, account_id, action,
                   payload_json, source, outcome
            FROM audit_orders
            WHERE timestamp_ms BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_ms, end_ms),
        ).fetchall()
    return [_row_to_entry(row) for row in rows]


def export_csv(start_ms: int | None = None, end_ms: int | None = None) -> str:
    """Stream all (or a date-ranged subset of) audit entries as CSV text.

    Used by the UI's "Export audit log" button and by the dedicated safety
    audit suite as a regression-evidence capture. CSV columns mirror the
    on-disk schema 1:1; ``payload`` is kept as a JSON-encoded string so a
    user-facing tool can re-parse it.
    """
    where_clause = ""
    params: tuple[int, ...] = ()
    if start_ms is not None and end_ms is not None:
        where_clause = "WHERE timestamp_ms BETWEEN ? AND ?"
        params = (start_ms, end_ms)

    with _reader_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, timestamp_ms, broker, account_id, action,
                   payload_json, source, outcome
            FROM audit_orders
            {where_clause}
            ORDER BY id ASC
            """,
            params,
        ).fetchall()

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "id",
            "timestamp_ms",
            "broker",
            "account_id",
            "action",
            "payload_json",
            "source",
            "outcome",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["id"],
                row["timestamp_ms"],
                row["broker"],
                row["account_id"],
                row["action"],
                row["payload_json"],
                row["source"],
                row["outcome"],
            ]
        )
    return out.getvalue()


def count() -> int:
    """Return the total row count — used by tests + the UI's audit-log header.

    Opens a writer connection (which applies the schema if missing) so that
    a count on a fresh DB returns 0 instead of raising. The operation itself
    issues only SELECT.
    """
    with _writer_connection() as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM audit_orders").fetchone()
    return int(row["n"])
