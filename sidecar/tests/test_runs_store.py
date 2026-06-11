"""runs_store tests — CRUD round-trip for the durable Delegate-run store.

The store backs FR-027 durability: a run row survives the launching request.
These tests point ``VYSTED_DATA_DIR`` at a ``tmp_path`` so each test hits its
own SQLite file, then exercise create / get / list / update and the checkpoint
round-trip.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from config import DATA_DIR_ENV
from models.run import RunBudget, RunCost
from services import runs_store


@pytest.fixture(autouse=True)
def _isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))


def test_create_and_get_round_trip() -> None:
    budget = RunBudget(max_tokens=5000, max_spend_usd=1.5)
    created = runs_store.create_run(
        run_id="run-1",
        agent_id="copilot",
        agent_name="Copilot",
        budget=budget,
        now=1000,
    )
    assert created.id == "run-1"
    assert created.status == "running"
    assert created.cost.tokens == 0
    assert created.budget.max_tokens == 5000

    fetched = runs_store.get_run("run-1")
    assert fetched is not None
    assert fetched.agent_id == "copilot"
    assert fetched.agent_name == "Copilot"
    assert fetched.budget.max_spend_usd == 1.5
    assert fetched.transcript == []
    assert fetched.checkpoint_messages == 0


def test_get_unknown_returns_none() -> None:
    assert runs_store.get_run("nope") is None


def test_list_runs_newest_first() -> None:
    runs_store.create_run(run_id="a", agent_id="x", agent_name="X", budget=RunBudget(), now=1000)
    runs_store.create_run(run_id="b", agent_id="y", agent_name="Y", budget=RunBudget(), now=2000)
    runs_store.create_run(run_id="c", agent_id="z", agent_name="Z", budget=RunBudget(), now=1500)
    ids = [r.id for r in runs_store.list_runs()]
    assert ids == ["b", "c", "a"]


def test_update_cost_and_status() -> None:
    runs_store.create_run(
        run_id="run-1", agent_id="x", agent_name="X", budget=RunBudget(), now=1000
    )
    updated = runs_store.update_run(
        "run-1",
        status="done",
        cost=RunCost(tokens=1234, spend_usd=0.05, steps=3),
        detail="completed",
        now=2000,
    )
    assert updated is not None
    assert updated.status == "done"
    assert updated.cost.tokens == 1234
    assert updated.cost.spend_usd == 0.05
    assert updated.cost.steps == 3
    assert updated.detail == "completed"
    assert updated.updated_at == 2000


def test_update_cost_does_not_wipe_detail() -> None:
    """A cost-only update leaves a previously-set detail intact."""
    runs_store.create_run(
        run_id="run-1", agent_id="x", agent_name="X", budget=RunBudget(), now=1000
    )
    runs_store.update_run("run-1", detail="halfway", now=1100)
    runs_store.update_run("run-1", cost=RunCost(tokens=10), now=1200)
    fetched = runs_store.get_run("run-1")
    assert fetched is not None
    assert fetched.detail == "halfway"
    assert fetched.cost.tokens == 10


def test_question_set_and_cleared() -> None:
    runs_store.create_run(
        run_id="run-1", agent_id="x", agent_name="X", budget=RunBudget(), now=1000
    )
    runs_store.update_run("run-1", status="paused", question="Approve?")
    paused = runs_store.get_run("run-1")
    assert paused is not None
    assert paused.status == "paused"
    assert paused.question == "Approve?"

    runs_store.update_run("run-1", status="running", clear_question=True)
    resumed = runs_store.get_run("run-1")
    assert resumed is not None
    assert resumed.question is None


def test_checkpoint_round_trip_and_transcript_digest() -> None:
    runs_store.create_run(
        run_id="run-1", agent_id="x", agent_name="X", budget=RunBudget(), now=1000
    )
    messages = [
        {"role": "system", "content": "persona prompt — elided"},
        {"role": "user", "content": "research NVDA"},
        {"role": "assistant", "content": "Looking into it."},
    ]
    runs_store.update_run("run-1", checkpoint=messages)
    assert runs_store.get_checkpoint("run-1") == messages

    detail = runs_store.get_run("run-1")
    assert detail is not None
    # System turns are elided from the digest; user + assistant survive.
    assert detail.checkpoint_messages == 3
    roles = [m["role"] for m in detail.transcript]
    assert roles == ["user", "assistant"]


def test_update_unknown_returns_none() -> None:
    assert runs_store.update_run("ghost", status="done") is None


def test_reset_for_tests_clears_rows() -> None:
    runs_store.create_run(
        run_id="run-1", agent_id="x", agent_name="X", budget=RunBudget(), now=1000
    )
    assert len(runs_store.list_runs()) == 1
    runs_store.reset_for_tests()
    assert runs_store.list_runs() == []


# ---------------------------------------------------------------------------
# R10 — non-secret options persistence (research_depth / region re-thread)
# ---------------------------------------------------------------------------


def test_options_round_trip_is_allowlisted() -> None:
    """Only research_depth/region persist; anything else (a rogue key, an
    object) is dropped by the allow-list — NEVER stored (R10)."""
    runs_store.create_run(
        run_id="run-1",
        agent_id="x",
        agent_name="X",
        budget=RunBudget(),
        options={
            "research_depth": "deep",
            "region": "IN",
            "api_key": "sk-must-not-persist",  # not allow-listed
            "history": [{"role": "user", "content": "x"}],  # not a string
        },
        now=1000,
    )
    assert runs_store.get_options("run-1") == {"research_depth": "deep", "region": "IN"}
    # The rogue key is nowhere in the database file's row.
    import sqlite3

    from config import get_data_dir

    conn = sqlite3.connect(str(get_data_dir() / runs_store.DB_FILENAME))
    try:
        row = conn.execute("SELECT options_json FROM runs WHERE id = 'run-1'").fetchone()
    finally:
        conn.close()
    assert "sk-must-not-persist" not in (row[0] or "")


def test_options_default_empty() -> None:
    runs_store.create_run(
        run_id="run-1", agent_id="x", agent_name="X", budget=RunBudget(), now=1000
    )
    assert runs_store.get_options("run-1") == {}
    assert runs_store.get_options("ghost") == {}


def test_options_column_migrates_an_older_database() -> None:
    """A pre-R10 database (no options_json column) gains it via the ALTER
    guard on first connect — additive, no data loss."""
    import sqlite3

    from config import get_data_dir

    db_path = str(get_data_dir() / runs_store.DB_FILENAME)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE runs (
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
    )
    conn.execute(
        "INSERT INTO runs (id, agent_id, agent_name, status, created_at, updated_at) "
        "VALUES ('legacy-1', 'x', 'X', 'done', 1000, 1000)"
    )
    conn.commit()
    conn.close()

    # First store access migrates; the legacy row survives with empty options.
    assert runs_store.get_options("legacy-1") == {}
    legacy = runs_store.get_run("legacy-1")
    assert legacy is not None and legacy.status == "done"
    # And new writes land in the migrated column.
    runs_store.create_run(
        run_id="run-2",
        agent_id="x",
        agent_name="X",
        budget=RunBudget(),
        options={"research_depth": "ultra", "region": "US"},
        now=2000,
    )
    assert runs_store.get_options("run-2") == {"research_depth": "ultra", "region": "US"}
