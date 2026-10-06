# Set: lows-P1/research-extraction-synthesis (set-69) — candidate ace7dd76, sidecar :52345

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-042 | in-process `_stamp_source_floor` on a structured-only no-web bundle, a 2-source and a 3-source bundle | 0 sources -> note "0 sources (below 3)"; 2 -> "2 sources (below 3)" + md "_Cited: 2 sources (below 3)._"; 3 -> no marker; fast.py:722 stamps `source_floor` leg (pinned `test_below_floor_marker`) | holds |
| R15-RESEARCH-040 | `grep estimate src/modules/chat` (the entry's repro, now non-empty) | DepthControl.tsx:75-89,153 renders `formatResearchCostEstimate` for Tier B before dispatch; pinned by DepthControl.test.tsx:18 "Tier B + ULTRA renders an estimate before dispatch" (vitest, heavy lane) | ci_pinned |

COVERAGE: 2/2 ids raw; no raw: none
