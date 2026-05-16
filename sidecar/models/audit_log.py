"""Audit-log SQL DDL constants — the append-only schema.

BLUEPRINT §6.5 #4: "Every order is audit-logged." Vysted enforces this at
the DB level, not just by convention. SQLite triggers on the ``audit_orders``
table raise ``ABORT`` on ``UPDATE`` and ``DELETE``, so even a broker-adapter
writer connection with full SQL permissions cannot mutate or remove a row.
The dedicated safety-layer audit suite (Teammate S) asserts this is true
end-to-end at release time.

The schema lives here as a constant so the test suite can re-apply it to
in-memory SQLite databases for unit tests without touching the real
``~/.vysted-terminal/audit_log.db``.
"""

from __future__ import annotations

#: SQL applied at first connection to ``audit_log.db``. Idempotent; the
#: ``CREATE TABLE IF NOT EXISTS`` + ``CREATE TRIGGER IF NOT EXISTS`` make
#: re-running on subsequent launches a no-op.
AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS audit_orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp_ms INTEGER NOT NULL,
  broker TEXT NOT NULL,
  account_id TEXT NOT NULL,
  action TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  source TEXT NOT NULL,
  outcome TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_orders(timestamp_ms);
CREATE INDEX IF NOT EXISTS idx_audit_broker ON audit_orders(broker);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_orders(action);

-- BLUEPRINT §6.5 #4 enforcement: the audit log is append-only at the DB
-- level. These triggers raise on any UPDATE / DELETE attempt regardless
-- of which connection role issues the statement. Re-applying the DDL is
-- safe because of IF NOT EXISTS; existing triggers retain their bodies.
CREATE TRIGGER IF NOT EXISTS audit_orders_no_update
  BEFORE UPDATE ON audit_orders
  BEGIN
    SELECT RAISE(ABORT, 'audit log is append-only: UPDATE not permitted');
  END;

CREATE TRIGGER IF NOT EXISTS audit_orders_no_delete
  BEFORE DELETE ON audit_orders
  BEGIN
    SELECT RAISE(ABORT, 'audit log is append-only: DELETE not permitted');
  END;
"""

#: Path component appended to ``app_data_dir`` to get the audit DB path.
AUDIT_LOG_DB_FILENAME = "audit_log.db"

#: Service name namespace for the audit log in keychain entries that
#: reference it (none today; reserved for future).
AUDIT_LOG_NAMESPACE = "vysted-audit-log"
