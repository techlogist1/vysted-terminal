"""SQLite-backed Delegate-run store (FR-027 durability).

A Delegate run must SURVIVE the launching HTTP connection closing — the run row
lives here, in ``config.get_data_dir()``, not in process memory. The detached
asyncio task (``run_manager``) updates this row as it works; the run-tray UI
reads it through ``GET /runs`` long after the launch request returned. If the
sidecar restarts mid-run the task is gone but the row persists with its last
status/cost/checkpoint, so the foreground view can still show what happened.

Mirrors the ``agents_store`` pattern field-for-field: per-call connection,
path resolved per call (so a test pointing ``VYSTED_DATA_DIR`` at ``tmp_path``
hits its own database), ``CREATE TABLE IF NOT EXISTS`` schema, CRUD only — no
migrations, no soft-deletes. The run executor is the only writer.

Columns mirror the run lifecycle:

- ``id`` — primary key (a uuid4 hex string).
- ``agent_id`` / ``agent_name`` — which agent the run drives.
- ``mode`` — always ``"delegate"`` for a background run (kept as a column so a
  future foreground-runs surface can reuse the table).
- ``status`` — ``running | paused | done | error | cancelled``.
- ``budget_json`` — the :class:`~models.run.RunBudget` ceilings (JSON).
- ``cost_json`` — the :class:`~models.run.RunCost` running total (JSON).
- ``detail`` — the abort/error reason or completion note (the breach reason
  lands here on a BudgetGuard breach — SC-008's stated reason).
- ``question`` — an outstanding human-in-the-loop question (FR-028) or NULL.
- ``checkpoint_json`` — the accumulated messages list at the last checkpoint, so
  a paused/aborted run can be resumed (FR-028).
- ``created_at`` / ``updated_at`` — epoch seconds.

The BYOK ``api_key`` is NEVER persisted here — it lives only on the in-memory
task. This store holds no secret.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from config import get_data_dir
from models.run import RunBudget, RunCost, RunDetail, RunStatus, RunSummary

DB_FILENAME = "delegate_runs.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'delegate',
    status TEXT NOT NULL,
    budget_json TEXT NOT NULL DEFAULT '{}',
    cost_json TEXT NOT NULL DEFAULT '{}',
    detail TEXT,
    question TEXT,
    checkpoint_json TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
)
"""


def _db_path() -> str:
    """Resolve the runs database path under the current data directory."""
    return str(get_data_dir() / DB_FILENAME)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yield a connection with the schema ensured; commit on clean exit."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_schema() -> None:
    """Create the ``runs`` table if it does not yet exist (idempotent)."""
    with _connect():
        pass


def reset_for_tests() -> None:
    """Drop every row so a test starts from an empty store.

    The store has no module-level cache — the database file is the only state —
    so this is a ``DELETE`` rather than a singleton reset. Tests that point
    ``VYSTED_DATA_DIR`` at a fresh ``tmp_path`` already get an empty store; this
    helper is for tests that share a data dir within one run.
    """
    with _connect() as conn:
        conn.execute("DELETE FROM runs")


def _row_to_summary(row: sqlite3.Row) -> RunSummary:
    """Map a database row to the ``RunSummary`` model (cost/budget decoded)."""
    cost_raw: Any = json.loads(row["cost_json"] or "{}")
    budget_raw: Any = json.loads(row["budget_json"] or "{}")
    return RunSummary(
        id=row["id"],
        agent_id=row["agent_id"],
        agent_name=row["agent_name"],
        mode=row["mode"],
        status=row["status"],
        cost=RunCost.model_validate(cost_raw if isinstance(cost_raw, dict) else {}),
        budget=RunBudget.model_validate(budget_raw if isinstance(budget_raw, dict) else {}),
        detail=row["detail"],
        question=row["question"],
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


def _row_to_detail(row: sqlite3.Row) -> RunDetail:
    """Map a row to ``RunDetail`` — a summary plus a transcript digest."""
    summary = _row_to_summary(row)
    checkpoint_raw: Any = json.loads(row["checkpoint_json"] or "[]")
    messages = checkpoint_raw if isinstance(checkpoint_raw, list) else []
    return RunDetail(
        **summary.model_dump(),
        transcript=_digest_transcript(messages),
        checkpoint_messages=len(messages),
    )


def _digest_transcript(messages: list[Any]) -> list[dict[str, Any]]:
    """Build a terse role-tagged digest of the checkpointed messages.

    System prompts are elided (they are the agent persona, not run progress) and
    content is truncated so the foreground view stays light. The full checkpoint
    is what ``resume_run`` re-enters from; this is just the human-readable view.
    """
    digest: list[dict[str, Any]] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = msg.get("role")
        if role == "system":
            continue
        content = msg.get("content")
        text = content if isinstance(content, str) else json.dumps(content, default=str)
        digest.append({"role": role, "content": text[:500]})
    return digest


def create_run(
    *,
    run_id: str,
    agent_id: str,
    agent_name: str,
    budget: RunBudget,
    mode: str = "delegate",
    status: RunStatus = "running",
    now: int | None = None,
) -> RunSummary:
    """Insert a new run row (status ``running`` by default) and return it."""
    timestamp = now if now is not None else int(time.time())
    budget_json = json.dumps(budget.model_dump(mode="json"))
    cost_json = json.dumps(RunCost().model_dump(mode="json"))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runs
                (id, agent_id, agent_name, mode, status, budget_json, cost_json,
                 detail, question, checkpoint_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                agent_id,
                agent_name,
                mode,
                status,
                budget_json,
                cost_json,
                None,
                None,
                None,
                timestamp,
                timestamp,
            ),
        )
    stored = get_run(run_id)
    if stored is None:  # pragma: no cover - INSERT always yields a row
        raise RuntimeError("run insert did not return a row")
    return stored


def get_run(run_id: str) -> RunDetail | None:
    """Return one run with its transcript digest, or ``None`` if unknown."""
    with _connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return _row_to_detail(row) if row else None


def list_runs() -> list[RunSummary]:
    """Return every run, newest first (by ``created_at`` then ``id``)."""
    with _connect() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC, id DESC").fetchall()
    return [_row_to_summary(row) for row in rows]


def update_run(
    run_id: str,
    *,
    status: RunStatus | None = None,
    cost: RunCost | dict[str, Any] | None = None,
    detail: str | None = None,
    question: str | None = None,
    checkpoint: list[Any] | None = None,
    clear_question: bool = False,
    now: int | None = None,
) -> RunSummary | None:
    """Patch the mutable fields on a run; return the updated row or ``None``.

    Only the explicitly-provided fields change — a ``None`` argument leaves the
    column untouched (so a cost update does not wipe a stored ``detail``). The
    one exception is ``question``: pass ``clear_question=True`` to null it out
    (resolving a human-in-the-loop pause), since ``None`` means "leave as-is".
    """
    sets: list[str] = []
    params: list[Any] = []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if cost is not None:
        cost_payload = cost.model_dump(mode="json") if isinstance(cost, RunCost) else dict(cost)
        sets.append("cost_json = ?")
        params.append(json.dumps(cost_payload))
    if detail is not None:
        sets.append("detail = ?")
        params.append(detail)
    if clear_question:
        sets.append("question = ?")
        params.append(None)
    elif question is not None:
        sets.append("question = ?")
        params.append(question)
    if checkpoint is not None:
        sets.append("checkpoint_json = ?")
        params.append(json.dumps(checkpoint, default=str))
    sets.append("updated_at = ?")
    params.append(now if now is not None else int(time.time()))
    params.append(run_id)

    with _connect() as conn:
        cursor = conn.execute(
            f"UPDATE runs SET {', '.join(sets)} WHERE id = ?",  # noqa: S608 — columns are literals
            tuple(params),
        )
        if cursor.rowcount == 0:
            return None
    stored = get_run(run_id)
    return stored


def get_checkpoint(run_id: str) -> list[Any]:
    """Return the persisted checkpoint message list for a run (``[]`` if none)."""
    with _connect() as conn:
        row = conn.execute("SELECT checkpoint_json FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None or not row["checkpoint_json"]:
        return []
    decoded = json.loads(row["checkpoint_json"])
    return decoded if isinstance(decoded, list) else []
