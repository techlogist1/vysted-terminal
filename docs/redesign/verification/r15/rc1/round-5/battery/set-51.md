# Regression battery — batch-11/W5-data-reference (set-51)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-013 | direct read of `sidecar/services/screener_universes/sp500.json` at candidate sha | `snapshot_date: 2026-09-24`, 503 symbols; register's own delisted-name list (MMC, FI, ANSS, CTLT, DAY, DFS, HES, HOLX, IPG, JNPR, K, MRO, WBA, CTRA) — 0 present; register's own missing-name list (BXP, NVR, UDR) — all 3 present | holds |

Raw output: `battery/raw/set-51/R15-LEAD-013.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
