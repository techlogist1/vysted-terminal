# batch-11/W2-runtime-schema (rc1-battery-1, candidate 4c6dfe8c)

Note: both ids closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-AGENT-009 | python `ast` walk over `services/agent_runtime.py` measuring `invoke_agent`/`_dispatch_round` line spans | `invoke_agent` = 101 lines (batch-11 cert: 95 lines, 488 at base — small drift from later unrelated commits touching the same region, still an order of magnitude under the pre-fix monolith, not a regression back toward it); `_dispatch_round` = 182 lines (cert: 152, same class of drift). `test_runtime_phases.py` present. Exact-line-count and full regression-suite pass are the heavy lane's job (pytest not re-run here) | holds |
| R15-LIFECYCLE-024 | grep `schema_version`/`migrate` across `sidecar/services/*_store.py`, `data_cache.py`, `portfolio_db.py`, `runs_store.py`; `schema_version.py:37 def migrate(...)` present | `schema_version` referenced in `fundamentals_store.py`, `agents_store.py`, `data_cache.py`, `workflow_store.py`, `plugins_store.py`, `portfolio_db.py`, `runs_store.py` — matches the 7-store list batch-11 certified. The live repro (boot with an old `data_cache` build marker, observe the backup dir + user_version bump) needs a second isolated data-dir boot with a doctored marker and was not repeated this shard given the time budget; static structural presence substitutes | ci_pinned |

COVERAGE: 2/2 ids raw; no raw: none.
