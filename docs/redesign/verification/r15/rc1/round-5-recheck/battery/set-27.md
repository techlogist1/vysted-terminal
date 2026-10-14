# batch-7/W3-unattended-chart-workspace

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: rc1-battery-8 shard, source, port 52348, data dir rc1-round-5-recheck-data-rc1-battery-8 (copied from seed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-023 | Saved data.fetch_quote(AAPL)->action.webhook workflow (2nd attempt, corrected config key secret_ref + edge sourcePort quote->targetPort value after a first attempt used the wrong key name); registered webhook ref b8-hook -> http://localhost:52349/hook; everyMinutes:1 -> 422 (ge=5); everyMinutes:5 -> schedule created 19:45:08 IST. | Fired unattended twice, 19:50:18 and 19:55:18 IST (exactly 5:00 apart), both lastStatus=ok, receiver got {workflow,node,value:<AAPL quote>} each time. Webhook URL 0 occurrences in sidecar log and workflows.db. | holds |
| R15-CODE-PLATFORM-018 | POST /workflow/run with quant.price_option american/binomial/20000 steps while polling /health concurrently (13 polls total across 2 attempts) | Health: 200, 0.9-6.9ms every poll throughout a 9.92s run (6.29s in-worker compute). ProcessPoolExecutor worker process (spawn_main) observed at 98% CPU while /health stayed sub-ms. | holds |
| R15-UI-020 | Pinned test src/store/chart-drawings.test.ts:62 "(R15-UI-020)" | Not vitest-executed per role rule (never run vitest suites); test confirmed present, matches store's drawingsFor(panel,symbol,timeframe) keying. | ci_pinned |
| R15-UI-023 | Pinned tests src/modules/chart/ChartPanel.test.tsx:423,:444 "(R15-UI-023)" | Not vitest-executed; both tests confirmed present. | ci_pinned |
| R15-UI-031 | Pinned test src/modules/equity-overview/EquityOverviewPanel.test.tsx:342 "(R15-UI-031)" | Not vitest-executed; test + narrativeSeqRef guard confirmed present. | ci_pinned |
| R15-UI-026 | Pinned tests src/modules/watchlist/WatchlistPanel.test.tsx:179-244 "(R15-UI-026)" | Not vitest-executed; tests confirmed present. | ci_pinned |
| R15-CODE-FRONTEND-019 | chmod 555 workspaces dir -> POST /workspace | 507 "Could not write the workspace: Permission denied"; restored -> 200 saved. Frontend leg (response.ok check, 3-failure threshold) source-confirmed at src/lib/workspace.ts:1046-1093. | holds |
| R15-DATA-090 | Save v1, save v2 (creates .bak), truncate live file to `{"trunc`, GET | Served `{"v":1}` from .bak; truncated file quarantined as `.corrupt-1790518283002` (kept, not deleted); non-dict workspace body -> 422. | holds |
| R15-UI-046 | GET /workspace (raw sidecar list) + source read of client filter/guard | Sidecar still lists `__autosave__` raw (by design); client listWorkspaces() filters reserved names (workspace.ts:738-740); saveWorkspace/deleteWorkspace both route through userWorkspaceName() which throws on `__`-prefixed names (workspace.ts:742-751,759,1229). | holds |

COVERAGE: 9/9 ids raw; no raw: none.
