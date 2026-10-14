# batch-11/W4-registry-loop (set-52)

Re-proved live against candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar on `:52350`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-026 | `ps -p <sidecar pid> -o etime,utime,time` sampled 6x across a 231s idle window (own sidecar, own data dir, zero requests during the window). | utime delta 7.17s→8.27s over 231s wall = 0.48% process-wide CPU, with no upward trend across the 6 samples (housekeeping-shaped, not a runaway loop-thread burn). Well below the register's pre-fix ~60% baseline and below the batch-11 verifier's own fresh measurement (3.3%, which they noted was inflated by eval-window overlap). Not a full undisturbed 5-minute window (harness per-call time budget) — see raw file for the sample-by-sample data and the caveat. | holds |
| R15-DATA-071 | Live `GET /history/KARNAVATI.BO?range=1y` (cold cache) and `GET /history/TRADEWELL.BO?range=1y`. | KARNAVATI.BO: provider bse, 255 bars (2025-09-12→2026-09-25), `partial: false` — a complete year, not the pre-fix 8-bar cap. TRADEWELL.BO: provider bse, 144 bars, `partial: false`. Bar counts are 1 lower than the batch-11 certification's 256/145 (one additional trading day has since elapsed — not a regression). | holds |

COVERAGE: 2/2 ids raw; no raw: none.
