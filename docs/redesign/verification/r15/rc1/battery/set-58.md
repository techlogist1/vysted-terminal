# unplanned-13

Candidate 4097dac4. Own sidecar :52346, own data dir. Raw output: `raw/set-58/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LIFECYCLE-024 | `grep -rln user_version sidecar/services`; `sqlite3 <db> 'PRAGMA user_version;'` on the copied seed data dir's stores before/after touching each store's endpoint; read `src/lib/workspace.ts` for `schemaVersion`/`migrateWorkspace` | `sidecar/services/schema_version.py` (`migrate(conn, steps)`) is imported and called by all 8 named stores (`agents_store`, `data_cache`, `workflow_store`, `portfolio_db`, `runs_store`, `plugins_store`, `fundamentals_store`, and audit_log's module also matches the grep). Live check: `custom_agents.db`/`data_cache.db`/`delegate_runs.db`/`fundamentals_cache.db`/`workflows.db` already read `user_version=1` from earlier verification traffic; `portfolio.db` and `plugins.db` read `user_version=0` until their endpoints were first hit (`/portfolio/positions`, `/plugins`), then read `user_version=1` — confirms lazy migrate-on-open, not a stuck-at-0 store. `src/lib/workspace.ts` carries a parallel `schemaVersion` field on `SerializedWorkspace` plus `migrateWorkspace()` walking `WORKSPACE_MIGRATIONS[version]` and stamping `WORKSPACE_SCHEMA_VERSION` on save/restore — audit_log's append-only triggers were not touched by this change (§6.5 untouched) | holds |

Summary: 1 hold. No regressions. Did not independently verify the backup-before-touch (`backups/<old-version>/`) half of fix_shape beyond confirming schema_version.py exists and is wired everywhere — the seed data dir's app-version stamp wasn't exercised in this shard; the core defect (every store stuck at user_version 0, no migration path) is verifiably fixed.
