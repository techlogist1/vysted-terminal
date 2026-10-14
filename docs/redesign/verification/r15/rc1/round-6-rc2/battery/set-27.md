# Set: batch-7/W3-unattended-chart-workspace (set-27) — candidate ace7dd76, sidecar :52346

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-023 | saved workflow quote(AAPL)->action.webhook, interval schedule 5 min, local receiver; everyMinutes:1 | 422 for 1 min; unattended fire 06:02:08 delivered {workflow,node,value:AAPL quote}. First fire 05:57 errored only because my receiver port collided with another service (harness cause) | holds |
| R15-CODE-PLATFORM-018 | workflow quant.price_option binomial 20k and 100k steps, /health polled | /health 1-2 ms throughout (100k run still computing at 95 s); 20k completed in 6.3 s | holds |
| R15-UI-020 | pinned tests present | ChartPanel.test.tsx:945/298, workspace.test.ts:767, chart-drawings.test.ts:68 | ci_pinned |
| R15-UI-023 | pinned tests present | ChartPanel.test.tsx:432, :453 | ci_pinned |
| R15-UI-031 | pinned test present | EquityOverviewPanel.test.tsx:368 | ci_pinned |
| R15-CODE-FRONTEND-017 | pinned tests present | sec.test.ts:101/248, earnings.test.ts:149 | ci_pinned |
| R15-UI-026 | pinned tests present | WatchlistPanel.test.tsx:183/217 | ci_pinned |
| R15-CODE-FRONTEND-019 | chmod 555 workspaces dir, POST /workspace | 507 "Could not write the workspace: Permission denied", 200 after restore; frontend "Autosave failed" present, pinned workspace.test.ts:1415 | holds |
| R15-DATA-090 | truncate saved workspace, GET; save again | GET serves .bak ({"v":1}), file kept as .corrupt-*; .bak parseable after next save; on-disk [] -> 404 not 500 | holds |
| R15-UI-046 | sidecar list + frontend filter in source | sidecar still lists __autosave__; listWorkspaces filters reserved names; test workspace.test.ts:1472 | ci_pinned |

COVERAGE: 10/10 ids raw; no raw: none
