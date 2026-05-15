"""SQLite-backed Custom Agent Builder store.

Mirrors the sidecar-owned-persistence pattern from ``plugins_store`` field-for-
field (CLAUDE.md gotcha — no localStorage, every user-defined object lives in
``config.get_data_dir()``). The Custom Agent Builder UI (BLUEPRINT module 36,
Phase 3 Teammate C) writes through this module via ``routers.custom_agents``;
the chat sidebar's agent picker reads it through ``GET /custom-agents``.

Schema is mirrored 1:1 from ``models.custom_agent.CustomAgentRead``:

- ``id`` — primary key; MUST start with the ``custom:`` prefix (the router
  validates this on insert; this module trusts callers and only enforces
  uniqueness here).
- ``name``, ``philosophy``, ``system_prompt`` — display + behaviour strings.
- ``tools_json`` — JSON array of tool ids the agent may call; opaque to the
  store.
- ``default_provider`` — one of the seven BYOK provider ids.
- ``default_model`` — optional recommended model id (free-form string).
- ``icon`` — Lucide icon name or asset path; optional.
- ``created_at`` / ``updated_at`` — epoch seconds (int) so the UI can show
  "last saved" and sort by recency.

The store is intentionally CRUD-only — no schema migrations, no soft-deletes,
no audit log. The Custom Agent Builder UI is the only writer.
"""

from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from config import get_data_dir
from models.custom_agent import CustomAgentCreate, CustomAgentRead, CustomAgentUpdate

DB_FILENAME = "custom_agents.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS custom_agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    philosophy TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    tools_json TEXT NOT NULL DEFAULT '[]',
    default_provider TEXT NOT NULL,
    default_model TEXT,
    icon TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
)
"""


def _db_path() -> str:
    """Resolve the custom-agents database path under the current data directory."""
    return str(get_data_dir() / DB_FILENAME)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    """Yield a connection with the schema ensured; commit on clean exit.

    Path resolved per call so tests pointing ``VYSTED_DATA_DIR`` at a
    ``tmp_path`` always hit their own database.
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
    """Create the ``custom_agents`` table if it does not yet exist (idempotent)."""
    with _connect():
        pass


def _row_to_read(row: sqlite3.Row) -> CustomAgentRead:
    """Map a database row to the ``CustomAgentRead`` Pydantic model."""
    tools_raw: Any = json.loads(row["tools_json"])
    tools = [str(item) for item in tools_raw] if isinstance(tools_raw, list) else []
    return CustomAgentRead(
        id=row["id"],
        name=row["name"],
        philosophy=row["philosophy"],
        system_prompt=row["system_prompt"],
        tools=tools,
        default_provider=row["default_provider"],
        default_model=row["default_model"],
        icon=row["icon"],
        created_at=int(row["created_at"]),
        updated_at=int(row["updated_at"]),
    )


def list_agents() -> list[CustomAgentRead]:
    """Return every stored custom agent, ordered by id (stable alphabetical)."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, name, philosophy, system_prompt, tools_json, "
            "default_provider, default_model, icon, created_at, updated_at "
            "FROM custom_agents ORDER BY id"
        ).fetchall()
    return [_row_to_read(row) for row in rows]


def get_agent(agent_id: str) -> CustomAgentRead | None:
    """Return one custom agent's record, or ``None`` if it does not exist."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, name, philosophy, system_prompt, tools_json, "
            "default_provider, default_model, icon, created_at, updated_at "
            "FROM custom_agents WHERE id = ?",
            (agent_id,),
        ).fetchone()
    return _row_to_read(row) if row else None


def create_agent(payload: CustomAgentCreate, *, now: int | None = None) -> CustomAgentRead:
    """Insert a new custom agent; raises ``sqlite3.IntegrityError`` on id collision.

    The caller (the router) catches ``IntegrityError`` and translates it to a
    409 response so the UI surfaces "an agent with that id already exists"
    rather than a generic 500.
    """
    timestamp = now if now is not None else int(time.time())
    tools_json = json.dumps(list(payload.tools))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO custom_agents
                (id, name, philosophy, system_prompt, tools_json,
                 default_provider, default_model, icon, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.id,
                payload.name,
                payload.philosophy,
                payload.system_prompt,
                tools_json,
                payload.default_provider,
                payload.default_model,
                payload.icon,
                timestamp,
                timestamp,
            ),
        )
    stored = get_agent(payload.id)
    if stored is None:  # pragma: no cover - INSERT always yields a row
        raise RuntimeError("custom agent insert did not return a row")
    return stored


def update_agent(
    agent_id: str,
    payload: CustomAgentUpdate,
    *,
    now: int | None = None,
) -> CustomAgentRead | None:
    """Replace the mutable fields on an existing custom agent.

    The id and ``created_at`` columns are immutable — only the user-editable
    fields plus ``updated_at`` change. Returns ``None`` if the agent does not
    exist, so the router can translate that to a 404.
    """
    timestamp = now if now is not None else int(time.time())
    tools_json = json.dumps(list(payload.tools))
    with _connect() as conn:
        cursor = conn.execute(
            """
            UPDATE custom_agents
            SET name = ?,
                philosophy = ?,
                system_prompt = ?,
                tools_json = ?,
                default_provider = ?,
                default_model = ?,
                icon = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.name,
                payload.philosophy,
                payload.system_prompt,
                tools_json,
                payload.default_provider,
                payload.default_model,
                payload.icon,
                timestamp,
                agent_id,
            ),
        )
        if cursor.rowcount == 0:
            return None
    return get_agent(agent_id)


def delete_agent(agent_id: str) -> bool:
    """Delete a custom agent; return ``True`` if a row was removed."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM custom_agents WHERE id = ?", (agent_id,))
        return cursor.rowcount > 0
