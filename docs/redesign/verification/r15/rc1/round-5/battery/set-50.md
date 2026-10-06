# batch-11/W4-registry-loop (rc1-battery-13, gate round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Own sidecar :52353 (data dir
`rc1-round-5-data-rc1-battery-13`, fresh seed copy — confirmed cold cache for KARNAVATI.BO
via `sqlite3 data_cache.db` before the live call).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-071 | live: `curl http://127.0.0.1:52353/history/KARNAVATI.BO?range=1y` on a confirmed-cold data_cache | `provider:"bse"`, `partial:false`, 255 bars spanning 2025-09-12 to 2026-09-25 (a full year) — not the pre-fix <=8-bar silent-partial shape, and the `partial` field is now present on the response | holds |
| R15-LIFECYCLE-026 | `pytest tests/test_loop_idle.py -v` (the pinned unit test exercising the profiled root cause — the fundamentals_warm crawl loop) + a live idle-CPU spot sample on my own booted sidecar (pid 57961, no requests sent) over a ~23s window | pytest: 2/2 passed. Live sample: utime grew ~0.02s over ~23s wall (well under 1% CPU) — no idle burn observed | holds |

Raw: `battery/raw/set-50/R15-DATA-071-live.json`, `R15-DATA-071.txt`,
`pytest-test_loop_idle.txt`, `R15-LIFECYCLE-026.txt`.

COVERAGE: 2/2 ids raw; no raw: none.
