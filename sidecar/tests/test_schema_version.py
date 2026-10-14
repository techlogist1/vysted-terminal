"""Schema versioning of every SQLite store and the pre-upgrade backup (R15-LIFECYCLE-024)."""

from __future__ import annotations

import asyncio
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
    with portfolio_db._connect():
        pass


def _open_agents(_: Path) -> None:
    with agents_store._connect():
        pass


def _open_workflows(_: Path) -> None:
    with workflow_store._connect():
        pass


def _open_plugins(_: Path) -> None:
    with plugins_store._connect():
        pass


def _open_runs(_: Path) -> None:
    with runs_store._connect():
        pass


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
        "VALUES ('KEEP', 'a', 'A', 'done', strftime('%s', 'now'), strftime('%s', 'now'))",
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
    data_cache.reset_for_tests(tmp_path / data_cache.DB_FILENAME)
    await data_cache.ensure_build("0.8.0")  # first boot of an empty data dir: nothing to back up
    assert not (tmp_path / "backups").exists()

    (tmp_path / "workflows.db").write_bytes(b"old build's workflows")
    (tmp_path / "workspaces").mkdir()
    (tmp_path / "workspaces" / "__autosave__.vysted-workspace").write_text("{}", encoding="utf-8")
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "vysted.log").write_text("log", encoding="utf-8")

    await data_cache.ensure_build("0.8.0")
    assert not (tmp_path / "backups").exists()

    await data_cache.ensure_build("0.9.0")
    backups = tmp_path / "backups"
    assert [p.name for p in backups.iterdir()] == ["0.8.0"]
    copy = backups / "0.8.0"
    assert (copy / "workflows.db").read_bytes() == b"old build's workflows"
    assert (copy / "workspaces" / "__autosave__.vysted-workspace").read_text(
        encoding="utf-8"
    ) == "{}"
    assert (copy / data_cache.DB_FILENAME).exists()
    assert not (copy / "logs").exists()
    assert not (copy / "backups").exists()

    await data_cache.ensure_build("0.9.0")
    assert [p.name for p in backups.iterdir()] == ["0.8.0"]


@pytest.mark.asyncio
async def test_a_pre_meta_data_dir_is_backed_up_on_the_first_boot_only(tmp_path: Path) -> None:
    """R15-LIFECYCLE-024 case a: a released build from before the meta row left
    user stores and a cache with no build recorded; the first boot backs it up."""
    (tmp_path / portfolio_db.DB_FILENAME).write_bytes(b"positions")
    (tmp_path / "workspaces").mkdir()
    (tmp_path / "workspaces" / "__autosave__.vysted-workspace").write_text("{}", encoding="utf-8")
    _write(
        tmp_path / data_cache.DB_FILENAME,
        "CREATE TABLE cache (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at REAL NOT "
        "NULL); INSERT INTO cache VALUES ('old', '1', 1)",
    )
    data_cache.reset_for_tests(tmp_path / data_cache.DB_FILENAME)

    assert await data_cache.ensure_build("0.9.0") is True

    backups = tmp_path / "backups"
    [copy] = list(backups.iterdir())
    assert copy.name.startswith("unversioned-")
    assert (copy / portfolio_db.DB_FILENAME).read_bytes() == b"positions"
    assert (copy / "workspaces" / "__autosave__.vysted-workspace").exists()

    assert await data_cache.ensure_build("0.9.0") is False
    assert list(backups.iterdir()) == [copy]


@pytest.mark.asyncio
async def test_a_first_boot_with_only_empty_saved_dirs_takes_no_backup(tmp_path: Path) -> None:
    (tmp_path / "workspaces").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "logs" / "vysted.log").write_text("log", encoding="utf-8")
    data_cache.reset_for_tests(tmp_path / data_cache.DB_FILENAME)

    await data_cache.ensure_build("0.9.0")

    assert not (tmp_path / "backups").exists()


def _quarantined(db: Path) -> list[Path]:
    return sorted(db.parent.glob(f"{db.name}.corrupt-*"))


@pytest.mark.parametrize(("store", "filename", "old_schema", "open_store"), STORES, ids=STORE_IDS)
def test_a_store_with_a_corrupt_header_is_quarantined_and_opens_empty(
    tmp_path: Path,
    store: object,
    filename: str,
    old_schema: str,
    open_store: Callable[[Path], None],
) -> None:
    """R15-FINAL-008: a bad header no longer fails every open of the store."""
    db = tmp_path / filename
    damaged = b"this is not a sqlite database " * 200
    db.write_bytes(damaged)

    open_store(db)

    kept = _quarantined(db)
    assert len(kept) == 1
    assert kept[0].read_bytes() == damaged  # the damaged file is kept byte-identical
    assert _user_version(db) == len(store._STEPS)  # type: ignore[attr-defined]
    table = old_schema.split()[2]
    with contextlib.closing(sqlite3.connect(db)) as conn:
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0  # noqa: S608


def test_a_truncated_store_is_quarantined(tmp_path: Path) -> None:
    db = tmp_path / portfolio_db.DB_FILENAME
    with portfolio_db._connect() as conn:
        conn.executemany(
            "INSERT INTO positions (symbol, quantity, cost_basis) VALUES (?, 1, 1)",
            [("X" * 400,)] * 300,
        )
    truncated = db.read_bytes()[: db.stat().st_size // 2]
    db.write_bytes(truncated)

    with portfolio_db._connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0

    assert [p.read_bytes() for p in _quarantined(db)] == [truncated]


def test_quarantine_moves_the_wal_and_shm_with_the_database(tmp_path: Path) -> None:
    db = tmp_path / "x.db"
    for name in ("x.db", "x.db-wal", "x.db-shm"):
        (tmp_path / name).write_bytes(name.encode())

    moved = schema_version._quarantine(db)

    stamp = moved.name.removeprefix("x.db.corrupt-")
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(
        f"{name}.corrupt-{stamp}" for name in ("x.db", "x.db-wal", "x.db-shm")
    )
    assert moved.read_bytes() == b"x.db"


def test_a_locked_database_is_not_quarantined(tmp_path: Path) -> None:
    db = tmp_path / "locked.db"
    steps = (schema_version.statements("CREATE TABLE IF NOT EXISTS a (x)"),)
    with contextlib.closing(sqlite3.connect(db, isolation_level=None)) as holder:
        holder.execute("BEGIN EXCLUSIVE")
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            schema_version.open_migrated(db, steps, timeout=0)
        holder.execute("ROLLBACK")
    assert _quarantined(db) == []
    conn, version = schema_version.open_migrated(db, steps)
    conn.close()
    assert version == 1


def test_a_corrupt_data_cache_does_not_fail_the_sidecar_boot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from fastapi.testclient import TestClient

    from app import create_app

    db = tmp_path / data_cache.DB_FILENAME
    damaged = b"not a database " * 100
    db.write_bytes(damaged)
    data_cache.reset_for_tests(None)
    # The TestClient's loop would otherwise keep the module lock bound past this test.
    monkeypatch.setattr(data_cache, "_lock", asyncio.Lock())

    with TestClient(create_app()):
        pass

    assert [p.read_bytes() for p in _quarantined(db)] == [damaged]
    assert _user_version(db) == len(data_cache._STEPS)
