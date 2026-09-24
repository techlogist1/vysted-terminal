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
import logging
import sqlite3
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from config import get_data_dir
from models.workflow import (
    WORKFLOW_SPEC_VERSION,
    SavedWorkflows,
    ScheduleCreate,
    UnreadableWorkflow,
    WorkflowSchedule,
    WorkflowSpec,
)
from services import schema_version

_log = logging.getLogger(__name__)

DB_FILENAME = "workflows.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    spec_json TEXT NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_workflows_updated ON workflows(updated_at DESC);
CREATE TABLE IF NOT EXISTS schedules (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    trigger_json TEXT NOT NULL,
    enabled INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    last_fired_at INTEGER,
    last_seen TEXT,
    last_status TEXT,
    last_detail TEXT
);
"""

#: Forward-only migrations, one per ``user_version`` (R15-LIFECYCLE-024).
_STEPS = (schema_version.statements(_SCHEMA),)


def _db_path() -> str:
    return str(get_data_dir() / DB_FILENAME)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        schema_version.migrate(conn, _STEPS)
        yield conn
        conn.commit()
    finally:
        conn.close()


class UnsupportedWorkflowVersion(ValueError):
    """A saved spec's schema major is not the one this build reads."""


def _row_to_spec(row: sqlite3.Row) -> WorkflowSpec:
    spec = WorkflowSpec.model_validate(json.loads(row["spec_json"]))
    if spec.version != WORKFLOW_SPEC_VERSION:
        raise UnsupportedWorkflowVersion(
            f"saved with workflow schema version {spec.version}; "
            f"this build reads version {WORKFLOW_SPEC_VERSION}"
        )
    return spec


def list_workflows() -> SavedWorkflows:
    """Return every openable saved workflow, newest-updated first.

    A row that no longer validates (or is another schema major) is logged and
    listed under ``unreadable`` instead of failing the whole list.
    """
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, spec_json, updated_at FROM workflows ORDER BY updated_at DESC"
        ).fetchall()
    saved = SavedWorkflows(workflows=[])
    for row in rows:
        try:
            saved.workflows.append(_row_to_spec(row))
        except ValueError as exc:  # ValidationError / JSONDecodeError / version
            _log.warning("workflow_store: saved workflow %r is unreadable: %s", row["id"], exc)
            saved.unreadable.append(
                UnreadableWorkflow(id=row["id"], name=row["name"], reason=str(exc))
            )
    return saved


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
        conn.execute("DELETE FROM schedules WHERE workflow_id = ?", (workflow_id,))
        return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Schedules (R15-AGENT-023)
# ---------------------------------------------------------------------------


def _row_to_schedule(row: sqlite3.Row) -> WorkflowSchedule:
    return WorkflowSchedule(
        id=row["id"],
        workflowId=row["workflow_id"],
        trigger=json.loads(row["trigger_json"]),
        enabled=bool(row["enabled"]),
        createdAt=row["created_at"],
        lastFiredAt=row["last_fired_at"],
        lastSeen=row["last_seen"],
        lastStatus=row["last_status"],
        lastDetail=row["last_detail"],
    )


def list_schedules() -> list[WorkflowSchedule]:
    """Every schedule, oldest first."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM schedules ORDER BY created_at").fetchall()
    return [_row_to_schedule(row) for row in rows]


def get_schedule(schedule_id: str) -> WorkflowSchedule | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
    return _row_to_schedule(row) if row else None


def create_schedule(body: ScheduleCreate, *, now_ms: int | None = None) -> WorkflowSchedule:
    """Persist a new schedule for an existing saved workflow."""
    created_at = int(time.time() * 1000) if now_ms is None else now_ms
    schedule_id = f"sch-{uuid.uuid4().hex[:12]}"
    with _connect() as conn:
        conn.execute(
            "INSERT INTO schedules (id, workflow_id, trigger_json, enabled, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                schedule_id,
                body.workflow_id,
                body.trigger.model_dump_json(by_alias=True),
                int(body.enabled),
                created_at,
            ),
        )
    return WorkflowSchedule(
        id=schedule_id,
        workflowId=body.workflow_id,
        trigger=body.trigger,
        enabled=body.enabled,
        createdAt=created_at,
    )


def set_schedule_enabled(schedule_id: str, enabled: bool) -> WorkflowSchedule | None:
    with _connect() as conn:
        conn.execute("UPDATE schedules SET enabled = ? WHERE id = ?", (int(enabled), schedule_id))
    return get_schedule(schedule_id)


def delete_schedule(schedule_id: str) -> bool:
    with _connect() as conn:
        return conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,)).rowcount > 0


def mark_schedule_fired(schedule_id: str, fired_at_ms: int, last_seen: str | None) -> None:
    """Record a fire as started (the scheduler's due check reads ``last_fired_at``)."""
    with _connect() as conn:
        conn.execute(
            "UPDATE schedules SET last_fired_at = ?, last_seen = COALESCE(?, last_seen),"
            " last_status = 'running', last_detail = NULL WHERE id = ?",
            (fired_at_ms, last_seen, schedule_id),
        )


def record_schedule_outcome(schedule_id: str, status: str, detail: str | None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE schedules SET last_status = ?, last_detail = ? WHERE id = ?",
            (status, detail, schedule_id),
        )
