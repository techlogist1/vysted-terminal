# batch-11/W5-data-reference (rc1-battery-1, candidate 4c6dfe8c)

Note: closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-013 | in-process load of `sidecar/services/screener_universes/sp500.json`; spot-check recent adds/removes | `snapshot_date: 2026-09-24`, `count: 503`. Recent adds present: PLTR, DELL, WDAY, XYZ, APP, COIN, HOOD (all True). Delisted/removed absent: WBA, ANSS, HES, JNPR (all False) — exact match to batch-11's certified 503-row, 0-missing/0-extra diff against Wikipedia's live table. Wikipedia's table was not re-fetched live this shard (already independently cross-checked by batch-11's fresh verifier); the bundled snapshot file itself was inspected directly on the candidate | holds |

COVERAGE: 1/1 ids raw; no raw: none.
