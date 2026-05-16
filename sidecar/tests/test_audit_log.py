"""Tests for the append-only audit log.

The append-only guarantee is enforced at the DB level via SQLite triggers
(``models/audit_log.py`` AUDIT_LOG_DDL). These tests assert:

  - INSERT works through :func:`audit_log.append`
  - tail / range_ / export_csv return what was inserted
  - UPDATE on ``audit_orders`` raises ``OperationalError`` with the literal
    trigger message ``"audit log is append-only: UPDATE not permitted"``
  - DELETE raises the same with the DELETE-variant message
  - The reader connection (``PRAGMA query_only=ON``) refuses INSERT
"""

from __future__ import annotations

import sqlite3

import pytest

from config import DATA_DIR_ENV
from models.safety import AuditLogAppendRequest
from services import audit_log


@pytest.fixture
def temp_audit_dir(tmp_path: object, monkeypatch: pytest.MonkeyPatch) -> object:
    """Redirect the sidecar data dir so the audit DB lives under tmp_path."""
    monkeypatch.setenv(DATA_DIR_ENV, str(tmp_path))
    return tmp_path


def _sample(action: str = "order-proposed", broker: str = "alpaca") -> AuditLogAppendRequest:
    return AuditLogAppendRequest(
        timestampMs=1_700_000_000_000,
        broker=broker,
        accountId="acct-1",
        action=action,  # type: ignore[arg-type]
        payload={"hello": "world"},
        source="manual",
        outcome="ok",
    )


# ---------------------------------------------------------------------------
# Happy paths
# ---------------------------------------------------------------------------


def test_append_assigns_monotonic_ids(temp_audit_dir: object) -> None:
    a = audit_log.append(_sample(action="order-proposed"))
    b = audit_log.append(_sample(action="order-confirmed"))
    c = audit_log.append(_sample(action="order-placed"))
    assert a < b < c


def test_tail_newest_first(temp_audit_dir: object) -> None:
    audit_log.append(_sample(action="order-proposed"))
    audit_log.append(_sample(action="order-placed"))
    rows = audit_log.tail(limit=10)
    assert [r.action for r in rows] == ["order-placed", "order-proposed"]


def test_tail_respects_limit(temp_audit_dir: object) -> None:
    for _ in range(5):
        audit_log.append(_sample())
    assert len(audit_log.tail(limit=2)) == 2


def test_range_includes_endpoints(temp_audit_dir: object) -> None:
    audit_log.append(
        AuditLogAppendRequest(
            timestampMs=1_000,
            broker="dhan",
            accountId="acct-1",
            action="order-proposed",
            payload={},
            source="manual",
            outcome="ok",
        )
    )
    audit_log.append(
        AuditLogAppendRequest(
            timestampMs=2_000,
            broker="dhan",
            accountId="acct-1",
            action="order-placed",
            payload={},
            source="manual",
            outcome="ok",
        )
    )
    audit_log.append(
        AuditLogAppendRequest(
            timestampMs=3_000,
            broker="dhan",
            accountId="acct-1",
            action="order-cancelled",
            payload={},
            source="manual",
            outcome="ok",
        )
    )
    rows = audit_log.range_(1_000, 2_500)
    assert [r.timestamp_ms for r in rows] == [1_000, 2_000]


def test_export_csv_header_and_rows(temp_audit_dir: object) -> None:
    audit_log.append(_sample())
    csv_text = audit_log.export_csv()
    lines = csv_text.strip().splitlines()
    assert lines[0] == ("id,timestamp_ms,broker,account_id,action,payload_json,source,outcome")
    assert lines[1].split(",")[2] == "alpaca"


def test_count_returns_total(temp_audit_dir: object) -> None:
    assert audit_log.count() == 0
    audit_log.append(_sample())
    audit_log.append(_sample())
    assert audit_log.count() == 2


# ---------------------------------------------------------------------------
# Append-only enforcement — the DB-level triggers MUST raise
# ---------------------------------------------------------------------------


def test_update_raises_with_trigger_message(temp_audit_dir: object) -> None:
    """BLUEPRINT §6.5 #4 — UPDATE on audit_orders is forbidden at the DB level.

    SQLite's RAISE(ABORT, ...) trigger raises ``sqlite3.IntegrityError``, a
    subclass of ``DatabaseError``. The literal trigger message is part of
    the exception text — the dedicated safety audit suite asserts both
    the exception class AND the message string.
    """
    audit_log.append(_sample())

    db_path = audit_log._db_path()  # pylint: disable=protected-access
    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            conn.execute("UPDATE audit_orders SET outcome = 'tampered' WHERE id = 1")
            conn.commit()
        assert "audit log is append-only: UPDATE not permitted" in str(exc_info.value)
    finally:
        conn.close()


def test_delete_raises_with_trigger_message(temp_audit_dir: object) -> None:
    """BLUEPRINT §6.5 #4 — DELETE on audit_orders is forbidden at the DB level."""
    audit_log.append(_sample())

    db_path = audit_log._db_path()  # pylint: disable=protected-access
    conn = sqlite3.connect(db_path)
    try:
        with pytest.raises(sqlite3.IntegrityError) as exc_info:
            conn.execute("DELETE FROM audit_orders WHERE id = 1")
            conn.commit()
        assert "audit log is append-only: DELETE not permitted" in str(exc_info.value)
    finally:
        conn.close()


def test_reader_connection_refuses_writes(temp_audit_dir: object) -> None:
    """The reader connection has PRAGMA query_only=ON — even INSERT raises."""
    # Apply the schema first via a writer call so the reader has a valid DB.
    audit_log.append(_sample())

    with audit_log._reader_connection() as conn:  # pylint: disable=protected-access
        with pytest.raises(sqlite3.OperationalError):
            conn.execute(
                "INSERT INTO audit_orders "
                "(timestamp_ms, broker, account_id, action, payload_json, "
                "source, outcome) VALUES (0, 'x', 'y', 'order-placed', '{}', "
                "'manual', 'ok')"
            )
