# Set: batch-11/W4-registry-loop (set-51) — candidate ace7dd76, sidecar :52344

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LIFECYCLE-026 | own source sidecar (pid 74594), 3 cycles x 8 cheap GETs per ~52 s (health, resolve x4, quotes, mcp/status) plus two cold BSE history requests; ps cputime | CPU 28.76 s -> 34.66 s = 5.9 s in 161 s wall = 3.7% (entry: ~60%); idle sample 0.3% CPU | holds |
| R15-DATA-071 | cold GET /history/KARNAVATI.BO?range=1y and TRADEWELL.BO | KARNAVATI: provider bse, 255 bars 2025-09-18..2026-10-01, partial false (was <=8); TRADEWELL: bse 143 bars partial false, coverage_start field present | holds |

COVERAGE: 2/2 ids raw; no raw: none
