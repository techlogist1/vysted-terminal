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
- ``status`` — ``planned | running | paused | done | error | cancelled``; every
  change goes through :data:`TRANSITIONS` (R15-CODE-AGENT-010).
- ``budget_json`` — the :class:`~models.run.RunBudget` ceilings (JSON).
- ``cost_json`` — the :class:`~models.run.RunCost` running total (JSON).
- ``detail`` — the abort/error reason or completion note (the breach reason
  lands here on a BudgetGuard breach — SC-008's stated reason).
- ``question`` — an outstanding human-in-the-loop question (FR-028) or NULL.
- ``checkpoint_json`` — ``{prompt, turns[]}``: the original prompt and every
  turn after it in order (the model's text, ``[tool → result]`` steps, the
  human's answers), so a paused/aborted run resumes the same conversation
  (FR-028, R15-AGENT-036). Older rows hold a flat message list; they are read
  as legacy (first user turn = prompt).
- ``options_json`` — the NON-SECRET launch options that must survive a resume
  (R10, E2 tail: ``research_depth`` + ``region``). Resume re-merges them into
  the spawned driver so the depth ContextVar floor / region are re-threaded
  instead of silently resetting to defaults mid-conversation. Allow-listed
  keys only — NEVER an api key.
- ``provider`` / ``model`` — the provider and model the run was launched with
  (NULL = the agent default), re-used by every resume (R15-AGENT-035).
- ``output_json`` — the run's collectable output, written when it ends
  (R15-AGENT-013): ``answer`` (the full final text, untruncated), ``brief``
  (the last ``publish_brief`` input) and ``host_actions`` (the host-action
  ``tool_use`` events it proposed). The frontend delivers it once to the
  originating chat thread through the normal proposed-changes gate.
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

#: The run lifecycle (R15-CODE-AGENT-010): each status maps to the statuses it
#: may be entered FROM. ``done`` is terminal; ``error`` and ``cancelled`` are
#: left only by a resume; ``planned`` and ``paused`` wait on the user.
TRANSITIONS: dict[RunStatus, frozenset[RunStatus]] = {
    "planned": frozenset({"running"}),
    "running": frozenset({"planned", "paused", "error", "cancelled"}),
    "paused": frozenset({"running"}),
    "done": frozenset({"running"}),
    "error": frozenset({"running"}),
    "cancelled": frozenset({"planned", "running", "paused"}),
}


class RunNotFound(LookupError):
    """No run with this id exists (404)."""


class RunStateError(RuntimeError):
    """The run exists but its status does not allow this change (409)."""


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
    options_json TEXT,
    output_json TEXT,
    provider TEXT,
    model TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
)
"""

#: The ONLY launch-option keys persisted to ``options_json`` (R10): the
#: research-depth floor and the locale. Allow-list, never a block-list — a
#: future secret-bearing option can never leak into SQLite by omission.
_PERSISTED_OPTION_KEYS = ("research_depth", "region")


def _persistable_options(options: dict[str, Any] | None) -> dict[str, str]:
    """Filter launch options down to the persisted allow-list (strings only)."""
    if not options:
        return {}
    return {
        key: value
        for key, value in options.items()
        if key in _PERSISTED_OPTION_KEYS and isinstance(value, str) and value
    }


def _db_path() -> str:
    """Resolve the runs database path under the current data directory."""
    return str(get_data_dir() / DB_FILENAME)


def _ensure_added_columns(conn: sqlite3.Connection) -> None:
    """Additive migration: older databases predate ``options_json`` (R10),
    ``output_json`` (R15-AGENT-013) and ``provider``/``model`` (R15-AGENT-035).

    ``CREATE TABLE IF NOT EXISTS`` covers a fresh file; an existing table needs
    the ALTER guard. PRAGMA is cheap enough to run per-connection.
    """
    columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
    for column in ("options_json", "output_json", "provider", "model"):
        if column not in columns:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {column} TEXT")


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yield a connection with the schema ensured; commit on clean exit."""
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        _ensure_added_columns(conn)
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
        provider=row["provider"],
        model=row["model"],
        detail=row["detail"],
        question=row["question"],
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


def _checkpoint_messages(raw: Any) -> list[Any]:
    """The checkpoint as one flat message list (the prompt, then its turns)."""
    if isinstance(raw, dict):
        return [{"role": "user", "content": raw.get("prompt", "")}, *(raw.get("turns") or [])]
    return raw if isinstance(raw, list) else []


def _row_to_detail(row: sqlite3.Row) -> RunDetail:
    """Map a row to ``RunDetail`` — a summary plus a transcript digest."""
    summary = _row_to_summary(row)
    messages = _checkpoint_messages(json.loads(row["checkpoint_json"] or "[]"))
    output: Any = json.loads(row["output_json"] or "{}")
    return RunDetail(
        **summary.model_dump(),
        transcript=_digest_transcript(messages),
        checkpoint_messages=len(messages),
        answer=output.get("answer"),
        brief=output.get("brief"),
        host_actions=output.get("host_actions") or [],
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
    options: dict[str, Any] | None = None,
    provider: str | None = None,
    model: str | None = None,
    now: int | None = None,
) -> RunSummary:
    """Insert a new run row (status ``running`` by default) and return it.

    ``options`` is filtered through the :data:`_PERSISTED_OPTION_KEYS`
    allow-list (research_depth, region) — NEVER a key/secret (R10).
    """
    timestamp = now if now is not None else int(time.time())
    budget_json = json.dumps(budget.model_dump(mode="json"))
    cost_json = json.dumps(RunCost().model_dump(mode="json"))
    persisted = _persistable_options(options)
    options_json = json.dumps(persisted) if persisted else None
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO runs
                (id, agent_id, agent_name, mode, status, budget_json, cost_json,
                 detail, question, checkpoint_json, options_json, provider, model,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                options_json,
                provider,
                model,
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
    from_status: frozenset[RunStatus] | None = None,
    cost: RunCost | dict[str, Any] | None = None,
    detail: str | None = None,
    question: str | None = None,
    checkpoint: dict[str, Any] | list[Any] | None = None,
    output: dict[str, Any] | None = None,
    clear_question: bool = False,
    now: int | None = None,
) -> RunDetail:
    """Patch the mutable fields on a run and return the updated row.

    Only the explicitly-provided fields change — a ``None`` argument leaves the
    column untouched (so a cost update does not wipe a stored ``detail``). The
    one exception is ``question``: pass ``clear_question=True`` to null it out
    (resolving a human-in-the-loop pause), since ``None`` means "leave as-is".

    A ``status`` change is applied only from a status :data:`TRANSITIONS`
    allows (narrowed further by ``from_status``), as one conditional UPDATE, so
    two racing writers cannot both win. Raises :class:`RunNotFound` for an
    unknown id and :class:`RunStateError` for a disallowed change; the row is
    then left untouched.
    """
    sets: list[str] = []
    params: list[Any] = []
    allowed: frozenset[RunStatus] = frozenset()
    if status is not None:
        allowed = TRANSITIONS[status] & (from_status or TRANSITIONS[status])
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
    if output is not None:
        sets.append("output_json = ?")
        params.append(json.dumps(output, default=str))
    sets.append("updated_at = ?")
    params.append(now if now is not None else int(time.time()))
    params.append(run_id)
    where = "id = ?"
    if status is not None:
        where += f" AND status IN ({', '.join('?' for _ in allowed)})"
        params.extend(sorted(allowed))

    with _connect() as conn:
        cursor = conn.execute(
            f"UPDATE runs SET {', '.join(sets)} WHERE {where}",  # noqa: S608 — literals only
            tuple(params),
        )
        if cursor.rowcount == 0:
            row = conn.execute("SELECT status FROM runs WHERE id = ?", (run_id,)).fetchone()
            if row is None:
                raise RunNotFound(f"unknown run: {run_id!r}")
            raise RunStateError(f"run {run_id!r} is {row['status']}; it cannot become {status}")
    stored = get_run(run_id)
    if stored is None:  # pragma: no cover - the UPDATE just matched the row
        raise RunNotFound(f"unknown run: {run_id!r}")
    return stored


def get_checkpoint(run_id: str) -> dict[str, Any]:
    """Return a run's checkpoint as ``{prompt, turns}`` (empty prompt if none).

    ``turns`` holds only well-formed user/assistant text turns. A legacy flat
    list is read with its first user turn as the prompt.
    """
    with _connect() as conn:
        row = conn.execute("SELECT checkpoint_json FROM runs WHERE id = ?", (run_id,)).fetchone()
    raw: Any = json.loads(row["checkpoint_json"]) if row and row["checkpoint_json"] else None
    messages = [
        {"role": m["role"], "content": m["content"]}
        for m in _checkpoint_messages(raw)
        if isinstance(m, dict)
        and m.get("role") in ("user", "assistant")
        and isinstance(m.get("content"), str)
        and m["content"]
    ]
    if not messages or messages[0]["role"] != "user":
        first_user = next((i for i, m in enumerate(messages) if m["role"] == "user"), None)
        if first_user is None:
            return {"prompt": "", "turns": []}
        messages = messages[first_user:]
    return {"prompt": messages[0]["content"], "turns": messages[1:]}


def get_options(run_id: str) -> dict[str, str]:
    """Return the persisted non-secret launch options (``{}`` if none).

    Resume/answer re-merge these into the spawned driver's options so the
    research-depth ContextVar floor and the run's region are re-threaded
    (R10 — a resumed run no longer silently resets to NORMAL/default).
    """
    with _connect() as conn:
        row = conn.execute("SELECT options_json FROM runs WHERE id = ?", (run_id,)).fetchone()
    if row is None or not row["options_json"]:
        return {}
    decoded = json.loads(row["options_json"])
    if not isinstance(decoded, dict):
        return {}
    return {k: v for k, v in decoded.items() if isinstance(v, str)}
