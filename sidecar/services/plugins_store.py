"""SQLite-backed per-plugin config store.

Mirrors the sidecar-owned-persistence pattern from ``portfolio_db`` and
``workspace_store``: the frontend never touches the filesystem, every plugin's
state lives in ``config.get_data_dir() / "plugins.db"``. The schema is created
lazily and idempotently on every connect, so a fresh data directory (or a test
``tmp_path``) just works without a migration step.

Schema is the runtime ``PluginPersistedConfig`` shape mirrored 1:1 from
``types/plugin-runtime.ts``:

- ``plugin_id`` — primary key, the stable plugin id.
- ``enabled`` — INTEGER 0/1; defaults to 1 once the plugin first appears.
- ``settings_json`` — opaque JSON blob the host never inspects.
- ``granted_secret_ids_json`` — JSON array of secret ids the user granted to
  this plugin (resolved to values via the OS keychain when initializing).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from config import get_data_dir
from models.plugins import PluginConfigPayload

DB_FILENAME = "plugins.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS plugin_configs (
    plugin_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    settings_json TEXT NOT NULL DEFAULT '{}',
    granted_secret_ids_json TEXT NOT NULL DEFAULT '[]'
)
"""


def _db_path() -> str:
    """Resolve the plugins database path under the current data directory."""
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
    """Create the ``plugin_configs`` table if it does not yet exist (idempotent)."""
    with _connect():
        pass


def _row_to_payload(row: sqlite3.Row) -> PluginConfigPayload:
    """Map a database row to the ``PluginConfigPayload`` Pydantic model."""
    settings_raw: Any = json.loads(row["settings_json"])
    settings = settings_raw if isinstance(settings_raw, dict) else {}
    granted_raw: Any = json.loads(row["granted_secret_ids_json"])
    granted = [str(item) for item in granted_raw] if isinstance(granted_raw, list) else []
    return PluginConfigPayload(
        plugin_id=row["plugin_id"],
        enabled=bool(row["enabled"]),
        settings=settings,
        granted_secret_ids=granted,
    )


def list_configs() -> list[PluginConfigPayload]:
    """Return every stored plugin config, ordered by plugin id."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT plugin_id, enabled, settings_json, granted_secret_ids_json "
            "FROM plugin_configs ORDER BY plugin_id"
        ).fetchall()
    return [_row_to_payload(row) for row in rows]


def get_config(plugin_id: str) -> PluginConfigPayload | None:
    """Return one plugin's config, or ``None`` if it has never been persisted."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT plugin_id, enabled, settings_json, granted_secret_ids_json "
            "FROM plugin_configs WHERE plugin_id = ?",
            (plugin_id,),
        ).fetchone()
    return _row_to_payload(row) if row else None


def upsert_config(payload: PluginConfigPayload) -> PluginConfigPayload:
    """Persist a plugin config (insert or replace) and return the stored record."""
    settings_json = json.dumps(payload.settings)
    granted_json = json.dumps(list(payload.granted_secret_ids))
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO plugin_configs
                (plugin_id, enabled, settings_json, granted_secret_ids_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(plugin_id) DO UPDATE SET
                enabled = excluded.enabled,
                settings_json = excluded.settings_json,
                granted_secret_ids_json = excluded.granted_secret_ids_json
            """,
            (payload.plugin_id, 1 if payload.enabled else 0, settings_json, granted_json),
        )
    stored = get_config(payload.plugin_id)
    if stored is None:  # pragma: no cover - upsert always yields a row
        raise RuntimeError("plugin config upsert did not return a row")
    return stored


def delete_config(plugin_id: str) -> bool:
    """Delete a plugin's config; return ``True`` if a row was removed."""
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM plugin_configs WHERE plugin_id = ?", (plugin_id,))
        return cursor.rowcount > 0
