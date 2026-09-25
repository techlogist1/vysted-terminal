# unplanned-3

Candidate 4097dac4. Raw output: `raw/set-48/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-091 | Read `src/modules/chart/indicators.ts:416-434` (`indicatorByKey`); `src/modules/chart/indicators.test.ts`, `src/lib/host-actions.test.ts:340` | `indicatorByKey` now resolves `base:param` specs (`ema:9`, `ema:21`, `vwap:week`) against their base entry, keeping the full param spec as the returned key — no longer collapsed to the generic base indicator. Pinned tests cover ema:9 vs ema:21 distinctness, vwap:week, and the host-action wiring named for R15-UI-091 directly | holds |

Summary: 1 hold. No regressions.
