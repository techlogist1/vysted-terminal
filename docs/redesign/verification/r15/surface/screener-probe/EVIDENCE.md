# screener-probe — evidence log (R15 wave 2)

Worker model: claude-fable-5-1. Own sidecar `127.0.0.1:52224` (PID 20527, started 15:02 IST by the
dead first attempt, REUSED), data dir `/tmp/claude-501/r15-screener-probe/data` (sqlite `.backup`
copy of the operator's stores, empty keystore). Driver: `/tmp/claude-501/r15-screener-probe/run_screen.py`
(POSTs `/screener/run/stream` exactly as `src/store/screener.ts:366-392` does; one JSON record per run
in this directory).

Continuation note: attempt 1 died at a usage wall after one run (`warm-standing-sector.json`).
Everything below the "Attempt 2" line is this attempt.

## 0. Store state the warm runs are served from (read-only sqlite, 15:20 IST 2026-09-19)

`fundamentals_cache.db` (operator copy): 5,157 rows (2,676 `.NS`, 2,481 `.BO`).

| tier | NSE rows | date spread |
| --- | --- | --- |
| v7 valuation (`v7_updated_at`) | 2,675 | **1,545 rows (58%) last written 2026-07-09 — 72 days old**; 27 on 07-14; 18 on 07-16; rest 09-03..09-19 |
| deep `.info` (`info_updated_at`) | 2,675 | identical to v7, row for row (`v7_updated_at = info_updated_at` on EVERY row) |
| quote / EOD bhavcopy | 2,658 | 2,644 stamped today (nse-bhavcopy) |
| seed pack | 5,050 | 2026-06-13..06-16 |

`v7_updated_at == info_updated_at` on all 5,063 stamped rows means no row has EVER been written by
the v7 batch sweep alone (`fundamentals_store.upsert_v7_batch`) — every valuation value in the
operator's store came through the per-symbol `.info` path (`upsert_info` stamps both,
`sidecar/services/fundamentals_store.py:388-389`).

Yahoo circuit at probe start: `GET /system/provider-health` →
`{"yahoo":{"open":true,"cooldown_remaining":87.7,"consecutive_opens":2,"opens_total":6,"throttles_total":175}}`
(the machine is rate-limited by Yahoo for the whole probe — this IS the rate-limit test).

