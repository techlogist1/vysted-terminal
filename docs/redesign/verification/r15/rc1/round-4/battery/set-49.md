# set-49 — batch-11/W2-runtime-schema (rc1-battery-22, round-4, candidate 1006c6da)

No sidecar boot needed for these two (source inspection + in-process module calls against
candidate's `sidecar/.venv`). Raw per-id files under `battery/raw/set-49/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-009 | ast line-count of `invoke_agent`/`_dispatch_round` in candidate's `sidecar/services/agent_runtime.py`; test-count of `sidecar/tests/test_runtime_phases.py` | `invoke_agent` is 101 lines (cert recorded 95 — small drift, still far below the base's ~488), `_dispatch_round` is 182 lines. `test_runtime_phases.py` has 9 direct phase tests and its docstring cites R15-CODE-AGENT-009 directly. The split-loop structure the fix introduced is intact; the "212 passed" regression-suite figure itself is ci-pinned (not re-run here — pytest suites are the heavy lane's job). | holds |
| R15-LIFECYCLE-024 | in-process: copied seed data dir, set `data_cache.db` meta `build='0.7.9-prior'`, called `data_cache.ensure_build('0.8.0')`; touched all 7 stores; called `schema_version.migrate` on a fresh conn, a second no-op call, and a conn pre-set to `user_version=7` against a 1-step build | Backup created at `<data_dir>/backups/0.7.9-prior/` including `data_cache.db`; meta build updated to `0.8.0`; cache cleared to 0 rows. All 7 stores (`data_cache`, `fundamentals_cache`, `workflows` at boot; `portfolio`, `delegate_runs`, `plugins`, `custom_agents` on first touch) go from `user_version 0` to `1`. Fresh migrate → 1 (step ran once); second call is a no-op (step still ran only once total). A conn pre-set to 7 vs a 1-step build logs `"database is at version 7, newer than this build's 1; left untouched"` and stays at 7 (no downgrade) — exact match to the cert's described behavior. `src/lib/workspace.test.ts` (vitest, not re-run) still carries the `schemaVersion` round-trip. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
