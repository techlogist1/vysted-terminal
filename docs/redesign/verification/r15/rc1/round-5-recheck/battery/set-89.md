# Regression battery — set-89 (unplanned-3)

Shard: rc1-battery-18. Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52358.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-DATA-023 | `grep` for the stale hardcoded universe-size prefixes (2,675 / 2.7k / 4.9k) in `sidecar/services/screener_universe_india.py` + `sidecar/models/screener.py`; in-process `load_india_universe()` for nse-all/bse-all/india-all. | grep: exit 1 (no matches — stale counts removed from both comments; both now describe shape only, no numbers). In-process: nse-all 3,506 symbols, bse-all 5,042, india-all 5,891 — matches the register's cited live counts exactly. | holds |

COVERAGE: 1/1 ids raw; no raw: none.

## Shard-wide coverage (all 4 sets: set-5, set-8, set-82, set-89)

COVERAGE: 16/16 ids raw; no raw: none.

