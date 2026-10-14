# rc1-battery-9 — set-26 (batch-7/W3-unattended-chart-workspace)

Candidate: `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Sidecar `:52349` from source, data dir
`rc1-round-5-data-battery-9` (copied from the ISO seed).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-023 | Saved workflow `data.fetch_quote AAPL → action.webhook`; registered webhook ref via `PUT /workflow/webhooks/{ref}` (`http://localhost:52999/hook`, local receiver); `POST /workflow/schedules {everyMinutes:1}` then `{everyMinutes:5}`; left unattended (no further calls) for the live sidecar's own 60 s-tick scheduler loop. | `everyMinutes:1` → 422 (`ge=5`). `everyMinutes:5` → schedule created. ~6 min later, unattended: `lastFiredAt` set, `lastStatus:"ok"`, and the local receiver got `{"workflow":"b9v unattended AAPL webhook","node":"n2","value":{symbol:AAPL, price:341.07,...}}`. `GET /workflow/webhooks` lists only `["b9v-ref"]`, never the URL. | holds |
| R15-CODE-FRONTEND-019 | `chmod 555` the sidecar's `workspaces/` dir; `POST /workspace {name,workspace:{}}`. | `507 {"detail":"Could not write the workspace: Permission denied"}`. | holds |
| R15-CODE-PLATFORM-018 | In-process python call (candidate venv) invoking `workflow_nodes.quant_nodes.price_option` (monte-carlo, 5,000,000 paths) while polling `GET /health` on :52349 every 0.2 s throughout. | Pricing took 3.13 s; 16 health polls landed during it, worst latency 16.6 ms (vs. the 6.4 s freeze the defect described). `services/quant/pool.py` runs every quant handler through a 2-worker `ProcessPoolExecutor` off the event loop. | holds |
| R15-DATA-090 | Saved `b9v-ws2` v1, then v2 (creates `.bak` of v1); truncated the live `.vysted-workspace` file; `GET /workspace/b9v-ws2`; then a further save; then a non-dict `workspace` body. | GET served the `.bak` (v1, `{"v":1}`), quarantined the truncated file as `.corrupt-<ts>`; the next save left `.bak` parseable (still `{"v":1}`); non-dict body → 422 `dict_type`. | holds |
| R15-UI-020 | Pinned tests: `src/store/chart-drawings.test.ts:62`, `src/modules/chart/ChartPanel.test.tsx:289,936` (all named `(R15-UI-020)`). | Present unchanged in the candidate source. Not re-executed (vitest suites are the heavy lane's). | ci_pinned |
| R15-UI-023 | Pinned tests: `src/modules/chart/ChartPanel.test.tsx:423,444` (`(R15-UI-023)`). | Present unchanged. | ci_pinned |
| R15-UI-026 | Pinned tests: `src/modules/watchlist/WatchlistPanel.test.tsx:179-213,213` (`(R15-UI-026)`). | Present unchanged. | ci_pinned |
| R15-UI-031 | Pinned test: `src/modules/equity-overview/EquityOverviewPanel.test.tsx:342` (`(R15-UI-031)`). | Present unchanged. | ci_pinned |
| R15-UI-046 | First probed live via raw sidecar HTTP (`POST /workspace {name:"__mine"}` → 200, `DELETE /workspace/__autosave__` → 204) — this bypasses the guard, which lives client-side in `src/lib/workspace.ts` (`saveWorkspace`/`deleteWorkspace`), not the sidecar router. Corrected to the pinned test: `src/lib/workspace.test.ts:1389` `"hides the reserved __autosave__ slot and refuses reserved names (R15-UI-046)"`. | Guard (`workspace.ts:742-749`, `WorkspaceError` on a `__` prefix) present unchanged in the candidate source. | ci_pinned |

COVERAGE: 9/9 ids raw.
