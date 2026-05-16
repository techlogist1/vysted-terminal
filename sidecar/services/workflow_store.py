"""SQLite-backed save/load for workflow specs.

Mirrors the sidecar-owned-persistence pattern from ``plugins_store`` and
``portfolio_db``: the frontend never touches the filesystem; every
workflow's persisted state lives in ``config.get_data_dir() / "workflows.db"``.

Schema is the runtime :class:`WorkflowSpec` shape serialised as JSON
(``spec_json``) plus ``updated_at`` for sort + diff. Per-workflow id is
the primary key — frontend assigns a UUID at first save, the engine
echoes it back on every subsequent save (upsert).
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager

from config import get_data_dir
from models.workflow import WorkflowSpec

DB_FILENAME = "workflows.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workflows_updated ON workflows(updated_at DESC);
"""


def _db_path() -> str:
    return str(get_data_dir() / DB_FILENAME)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _row_to_spec(row: sqlite3.Row) -> WorkflowSpec:
    return WorkflowSpec.model_validate(json.loads(row["spec_json"]))


def list_workflows() -> list[WorkflowSpec]:
    """Return every saved workflow, newest-updated first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, spec_json, updated_at FROM workflows ORDER BY updated_at DESC"
        ).fetchall()
    return [_row_to_spec(row) for row in rows]


def get_workflow(workflow_id: str) -> WorkflowSpec | None:
    """Return one workflow by id, or ``None``."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, spec_json, updated_at FROM workflows WHERE id = ?",
            (workflow_id,),
        ).fetchone()
    return _row_to_spec(row) if row else None


def save_workflow(spec: WorkflowSpec) -> WorkflowSpec:
    """Insert or replace a workflow, stamping ``updated_at`` to now."""
    now_ms = int(time.time() * 1000)
    stamped = spec.model_copy(update={"updated_at": now_ms})
    payload_json = stamped.model_dump_json(by_alias=True)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO workflows (id, name, spec_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                spec_json = excluded.spec_json,
                updated_at = excluded.updated_at
            """,
            (stamped.id, stamped.name, payload_json, now_ms),
        )
    return stamped


def delete_workflow(workflow_id: str) -> bool:
    """Delete a workflow; return ``True`` if a row was removed."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
        return cursor.rowcount > 0
