# set-79 — unplanned-1 (rc1-battery-16, candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-023 | `grep` for the stale literals `"~2,675"` / `"~2.7k / 4.9k"` in `sidecar/services/screener_universe_india.py` and `sidecar/models/screener.py`; in-process `load_india_universe(...)` for nse-all/bse-all/india-all on candidate venv | grep: zero hits — comments now describe composition without a hardcoded count; live counts nse-all=3506, bse-all=5042, india-all=5891 (matches the register entry's cited live counts) | holds |

No regressions in this set.

COVERAGE: 16/16 ids raw; no raw: none.
