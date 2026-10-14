# Set: lows-P1/runs-durable-delegate (set-70) — rc1-battery-19 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-031 | design; in-process routers.runs via TestClient over a real runs_store (data dir temp), GET /runs and /runs/{id}; live GET /runs on :52359 | rows carry snake_case keys only (agent_id, created_at, updated_at, ...), 0 camelCase keys in list or detail; pinned test_runs_rows_carry_only_snake_case_keys | holds |
| R15-CODE-AGENT-032 | design; in-process 105 live + 4 old terminal rows | GET /runs returns exactly LIST_LIMIT 100 rows, no checkpoint field in list rows; fresh-process open prunes old done/error/cancelled rows, keeps old paused | holds |
| R15-DOCS-021 | read docs/CURRENT_STATE.md persistence table + gaps, grep stores | table lists custom_agents.db (802) and delegate_runs.db (804); gap note now "six of the seven" and names delegate_runs.db's additive migration | holds |

COVERAGE: 3/3 ids raw (battery/raw/set-70/); no raw: none
