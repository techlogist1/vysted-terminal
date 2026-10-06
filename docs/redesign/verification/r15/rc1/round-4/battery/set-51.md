# batch-11/W4-registry-loop (rc1-battery-23, round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar `127.0.0.1:52363` (idle,
worker pid 10076). Raw output: `raw/set-51/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LIFECYCLE-026 | Own sidecar CPU sampled twice ~104s apart (`ps -o pid,etime,utime,time`) while background curl/python probes for other entries ran against it (not a pure-idle window); grep `asyncio.to_thread` in `provider_registry.py`. | CPU time 0:07.26 → 0:08.24 over ~104s wall = 0.98s CPU / 104s ≈ 0.9% process-wide — well under batch-11's own certified 3.3%-over-5-min figure (which itself is the certified fix, down from a pre-fix ~60%-of-a-core), despite this window including active request traffic from concurrent probes. `_resolve_async` still routes accessors via `asyncio.to_thread` (`provider_registry.py:465`) unchanged. | holds |
| R15-DATA-071 | Live `GET /history/KARNAVATI.BO?range=1y` and `GET /history/TRADEWELL.BO?range=1y` on own sidecar. | KARNAVATI: 255 bars, `provider:"bse"`, `partial:false`; TRADEWELL: 144 bars, `provider:"bse"`, `partial:false` — both far above the pre-fix 8-bar cap; within 1 bar of batch-11's certified 256/145 (expected, one extra trading day has rolled since certification). | holds |

**Set result: 2/2 holds.**

COVERAGE: 2/2 ids raw.
