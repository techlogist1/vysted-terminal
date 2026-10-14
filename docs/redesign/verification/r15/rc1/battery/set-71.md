# unplanned-1 (rc1-battery-7)

Candidate `4c6dfe8c`. In-process probe against the candidate's own venv. 1 entry re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-023 | `grep` `sidecar/services/screener_universe_india.py:1-10` + `sidecar/models/screener.py:25-40`; in-process `load_india_universe('nse-all'/'bse-all'/'india-all')` | the stale hardcoded counts (`~2,675` docstring, `~2.7k / 4.9k` comment) named in the original repro are gone from both comments — replaced with count-free descriptive prose; live counts nse-all=3506, bse-all=5042, india-all=5891, matching the register's own re-measured figures exactly | holds |

Raw output: `battery/raw/set-71/*`.

COVERAGE: 32/32 ids raw; no raw: none.
