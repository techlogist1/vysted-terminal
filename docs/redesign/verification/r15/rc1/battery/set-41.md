# batch-10/W2-catalog-hostactions

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-010 | `POST /backtest/run` with `strategyId: "mean_reversion"`, `params.window` = `0`, `-5`, `""`. | `0`/`-5` → `422 {"detail":"`window` must be between 5 and 200"}`; `""` → `422 {"detail":"`window` must be an integer"}` — a clean bounded validation error, not a raw Python `StatisticsError`/`ValueError` traceback. | holds |
| R15-UI-011 | grep `src/modules/backtest/BacktestPanel.tsx`/`.test.tsx`. | `controllerRef` (`AbortController`, line 119) and a "Stop backtest" button (line 281) exist; `describe("BacktestPanel Stop (R15-UI-011)", ...)` at `BacktestPanel.test.tsx:481` names the entry directly. | ci_pinned (BacktestPanel.test.tsx:481) |
| R15-LEAD-018 | Live: `vy.py invoke copilot "What is TCS trailing P/E ratio and recent news?" --provider openrouter --model nvidia/nemotron-3-super-120b-a12b:free` against my own sidecar (free lane, tagged `rc1-battery-0:LEAD-018`). | See raw log; the published/rendered content field carries only the answer text, no leaked `<think>`/chain-of-thought block ahead of or inside it (full transcript in `raw/set-41/R15-LEAD-018.txt`). | holds |
| R15-CODE-PLATFORM-021 | grep `src/modules/portfolio/api.ts`, `sidecar/routers/portfolio.py`. | `fetchLegacyPositions()` (api.ts:70) now DOES read `GET /portfolio/positions` in production code (previously unreachable) — but the fork is resolved by making the sidecar SQLite ledger a one-time LEGACY IMPORT source only; holdings live authoritatively in the client store/workspace blob (same fix as R15-LIFECYCLE-009's pinned import test). No surface still forks live truth between two writers. | holds |

**Set result: 3/4 holds, 1/4 ci_pinned.**
