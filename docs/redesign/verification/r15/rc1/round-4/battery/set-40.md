# set-40 — batch-10/W1-runtime-backtest (rc1-battery-18, round 4)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar on :52358. Raw probe output
under `battery/raw/set-40/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-050 | in-process `_split_system_and_messages()` with a stable persona + a per-turn-changing preamble across two turns | persona block byte-identical across turns and carries the `cache_control` breakpoint; the changing preamble is a separate later block | holds |
| R15-LEAD-018 | replayed the real captured `nemotron_cot.jsonl` fixture (27 chunks, 1 echoed content chunk) through `ReasoningSplitter` | 296 chars of reasoning went out as THINKING events; 0 chars leaked into the ANSWER/delta channel (echo recognized as a reasoning prefix and dropped) | holds |
| R15-CODE-PLATFORM-029 | in-process `run_backtest` on a flat market, 4 scripted buys of 10 (independent qty from the pinned test's 3-buy case) | 1 trade row, quantity=40, final equity = capital − total fees exactly (no orphaned lots) | holds |
| R15-LIFECYCLE-015 | in-process `backtest_store` with 34 variant results (>32 capacity), then a simulated restart (`reset_for_tests()` + re-`get`) | run-00 evicted from the in-memory LRU but still readable via disk fallback and after a simulated restart; `list_runs()` newest-first (`run-33`…`run-00`) | holds |
| R15-UI-010 | live HTTP `POST /backtest/run` on own sidecar with `window=0`/`-5`/`""` | all three return a clean `422` with a readable `detail` (`` `window` must be between 5 and 200 `` / `` `window` must be an integer ``), never a raw Python traceback; frontend clamp logic present in `strategy-picker.tsx:130-185` (min/max rendered from schema + `Math.max`/`Math.min` clamp), separately pinned by `BacktestPanel.test.tsx:464` | holds |
| R15-UI-011 | frontend-only (AbortController + Stop button); no sidecar signal, no GUI/browser tool available this role (playwright/tauri-mcp failed to connect: node/npx not on PATH) | code inspection: `AbortController` wiring in `src/store/backtest.ts`, Stop button in `BacktestPanel.tsx`; pinned by `BacktestPanel.test.tsx:481-512` describe block "BacktestPanel Stop (R15-UI-011)" | ci_pinned (BacktestPanel.test.tsx:481-512) |

COVERAGE: 6/6 ids raw; no raw: none (UI-011's raw file records the NOT-RUN reason and the code-inspection evidence).
