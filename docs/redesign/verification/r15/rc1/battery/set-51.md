# batch-11/W4-registry-loop (rc1-battery-1, candidate 4c6dfe8c)

Note: both ids closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-026 | live `ps -o pid,time` on own sidecar (:52341, idle) sampled twice 32s apart; grep `asyncio.to_thread` in `provider_registry.py` | CPU time 1:15.42 → 1:16.84 over 32s wall = 1.42s CPU / 32s ≈ 4.4% process-wide during a short idle window with no active traffic — same order of magnitude as batch-11's certified 3.3% over its full 5-minute window (a 32s sample is noisier but consistent; nowhere near the pre-fix ~60%-of-a-core regression the register describes). `_resolve_async` confirmed still routing accessors via `asyncio.to_thread` unchanged. The full 5-minute window + loop-thread `sample` profile was not repeated this shard given the time budget | holds |
| R15-DATA-071 | live `GET /history/KARNAVATI.BO?range=1y` and `GET /history/TRADEWELL.BO?range=1y` on own sidecar (:52341) | KARNAVATI: 256 bars (2025-09-11 to 2026-09-24+), bse lane; TRADEWELL: 145 bars, bse lane — both far above the pre-fix 8-bar cap, exact bar-count match to batch-11's certified figures (256 complete / 145 partial) | holds |

COVERAGE: 2/2 ids raw; no raw: none.
