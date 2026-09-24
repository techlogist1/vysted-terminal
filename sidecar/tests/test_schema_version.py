"""Schema versioning of every SQLite store and the pre-upgrade backup (R15-LIFECYCLE-024)."""

from __future__ import annotations

import contextlib
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest

from config import DATA_DIR_ENV
from services import (
    agents_store,
    data_cache,
    fundamentals_store,
    plugins_store,
    portfolio_db,
    runs_store,
    schema_version,
    workflow_store,
)


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    yield
    data_cache.reset_for_tests(None)
    fundamentals_store.reset_for_tests(None)


def _open_portfolio(_: Path) -> None:
    portfolio_db._ensure_schema()


def _open_agents(_: Path) -> None:
    agents_store._ensure_schema()


def _open_workflows(_: Path) -> None:
    with workflow_store._connect():
        pass


def _open_plugins(_: Path) -> None:
    plugins_store._ensure_schema()


def _open_runs(_: Path) -> None:
    runs_store._ensure_schema()


def _open_fundamentals(db: Path) -> None:
    fundamentals_store.reset_for_tests(db)
    fundamentals_store._connect().close()


def _open_data_cache(db: Path) -> None:
    data_cache.reset_for_tests(db)


#: store module, db file, an unversioned database as an older build left it, the opener.
STORES: list[tuple[object, str, str, Callable[[Path], None]]] = [
    (
        portfolio_db,
        portfolio_db.DB_FILENAME,
        "CREATE TABLE positions (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT NOT NULL, "
        "quantity REAL NOT NULL, cost_basis REAL NOT NULL, asset_class TEXT NOT NULL DEFAULT "
        "'equity', opened_at TEXT, note TEXT); "
        "INSERT INTO positions (symbol, quantity, cost_basis) VALUES ('KEEP', 1, 1)",
        _open_portfolio,
    ),
    (
        agents_store,
        agents_store.DB_FILENAME,
        "CREATE TABLE custom_agents (id TEXT PRIMARY KEY, name TEXT NOT NULL, philosophy TEXT "
        "NOT NULL, system_prompt TEXT NOT NULL, tools_json TEXT NOT NULL DEFAULT '[]', "
        "default_provider TEXT NOT NULL, default_model TEXT, icon TEXT, created_at INTEGER "
        "NOT NULL, updated_at INTEGER NOT NULL); INSERT INTO custom_agents VALUES "
        "('KEEP', 'n', 'p', 's', '[]', 'ollama', NULL, NULL, 1, 1)",
        _open_agents,
    ),
    (
        workflow_store,
        workflow_store.DB_FILENAME,
        "CREATE TABLE workflows (id TEXT PRIMARY KEY, name TEXT NOT NULL, spec_json TEXT NOT "
        "NULL, updated_at INTEGER NOT NULL); INSERT INTO workflows VALUES ('KEEP', 'n', '{}', 1)",
        _open_workflows,
    ),
    (
        plugins_store,
        plugins_store.DB_FILENAME,
        "CREATE TABLE plugin_configs (plugin_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL "
        "DEFAULT 1, settings_json TEXT NOT NULL DEFAULT '{}', granted_secret_ids_json TEXT NOT "
        "NULL DEFAULT '[]'); INSERT INTO plugin_configs (plugin_id) VALUES ('KEEP')",
        _open_plugins,
    ),
    (
        runs_store,
        runs_store.DB_FILENAME,
        "CREATE TABLE runs (id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, agent_name TEXT NOT "
        "NULL, mode TEXT NOT NULL DEFAULT 'delegate', status TEXT NOT NULL, budget_json TEXT NOT "
        "NULL DEFAULT '{}', cost_json TEXT NOT NULL DEFAULT '{}', detail TEXT, question TEXT, "
        "checkpoint_json TEXT, created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL); "
        "INSERT INTO runs (id, agent_id, agent_name, status, created_at, updated_at) "
        "VALUES ('KEEP', 'a', 'A', 'done', 1, 1)",
        _open_runs,
    ),
    (
        fundamentals_store,
        fundamentals_store.DB_FILENAME,
        "CREATE TABLE fundamentals (symbol TEXT PRIMARY KEY); "
        "INSERT INTO fundamentals (symbol) VALUES ('KEEP')",
        _open_fundamentals,
    ),
    (
        data_cache,
        data_cache.DB_FILENAME,
        "CREATE TABLE cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT "
        "NULL); INSERT INTO cache VALUES ('KEEP', '1', 1)",
        _open_data_cache,
    ),
]
STORE_IDS = [store.__name__.rsplit(".", 1)[-1] for store, *_ in STORES]


def _user_version(db: Path) -> int:
    with contextlib.closing(sqlite3.connect(db)) as conn:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])


def _write(db: Path, script: str, user_version: int = 0) -> None:
    with contextlib.closing(sqlite3.connect(db)) as conn:
        conn.executescript(script)
        conn.execute(f"PRAGMA user_version = {user_version}")
        conn.commit()


@pytest.mark.parametrize(("store", "filename", "old_schema", "open_store"), STORES, ids=STORE_IDS)
def test_an_unversioned_store_migrates_once_and_a_second_open_is_a_no_op(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    store: object,
    filename: str,
    old_schema: str,
    open_store: Callable[[Path], None],
) -> None:
    db = tmp_path / filename
    _write(db, old_schema)
    steps = store._STEPS  # type: ignore[attr-defined]
    ran: list[int] = []
    counted = tuple(
        (lambda conn, i=i, step=step: (ran.append(i), step(conn))[1])
        for i, step in enumerate(steps)
    )
    monkeypatch.setattr(store, "_STEPS", counted)

    open_store(db)
    assert _user_version(db) == len(steps)
    assert ran == list(range(len(steps)))

    open_store(db)
    assert ran == list(range(len(steps)))  # nothing re-ran

    table = old_schema.split()[2]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        kept = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
    assert kept == 1  # the older build's row survives


@pytest.mark.parametrize(("store", "filename", "old_schema", "open_store"), STORES, ids=STORE_IDS)
def test_a_database_from_a_newer_build_is_left_untouched(
    tmp_path: Path,
    store: object,
    filename: str,
    old_schema: str,
    open_store: Callable[[Path], None],
    caplog: pytest.LogCaptureFixture,
) -> None:
    db = tmp_path / filename
    future = len(store._STEPS) + 5  # type: ignore[attr-defined]
    _write(db, old_schema, user_version=future)
    table = old_schema.split()[2]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        before = conn.execute(f"PRAGMA table_info({table})").fetchall()

    open_store(db)

    assert _user_version(db) == future
    with contextlib.closing(sqlite3.connect(db)) as conn:
        assert conn.execute(f"PRAGMA table_info({table})").fetchall() == before
    assert "newer than this build" in caplog.text


def test_a_failed_step_rolls_back_to_the_last_completed_version(tmp_path: Path) -> None:
    def boom(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE TABLE half (x)")
        raise RuntimeError("step 2 failed")

    with contextlib.closing(sqlite3.connect(tmp_path / "x.db")) as conn:
        with pytest.raises(RuntimeError):
            schema_version.migrate(conn, (schema_version.statements("CREATE TABLE a (x)"), boom))
        assert conn.execute("PRAGMA user_version").fetchone()[0] == 1
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
    assert tables == {"a"}


@pytest.mark.asyncio
async def test_a_build_change_backs_the_data_dir_up_once_and_the_same_build_never(
    tmp_path: Path,
) -> None:
    (tmp_path / "workflows.db").write_bytes(b"old build's workflows")
    (tmp_path / "workspaces").mkdir()
    (tmp_path / "workspaces" / "__autosave__.vysted-workspace").write_text("{}")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "vysted.log").write_text("log")
    data_cache.reset_for_tests(tmp_path / data_cache.DB_FILENAME)

    await data_cache.ensure_build("0.8.0")  # first boot: nothing to back up
    assert not (tmp_path / "backups").exists()

    await data_cache.ensure_build("0.8.0")
    assert not (tmp_path / "backups").exists()

    await data_cache.ensure_build("0.9.0")
    backups = tmp_path / "backups"
    assert [p.name for p in backups.iterdir()] == ["0.8.0"]
    copy = backups / "0.8.0"
    assert (copy / "workflows.db").read_bytes() == b"old build's workflows"
    assert (copy / "workspaces" / "__autosave__.vysted-workspace").read_text() == "{}"
    assert (copy / data_cache.DB_FILENAME).exists()
    assert not (copy / "logs").exists()
    assert not (copy / "backups").exists()

    await data_cache.ensure_build("0.9.0")
    assert [p.name for p in backups.iterdir()] == ["0.8.0"]
