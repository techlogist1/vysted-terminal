# lows-P2/frontend-stores (set-80), shard rc1-battery-11, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-026 | pinned test exists + bridge source | workflow.test.ts "append a, take, append b -> b still pending"; store takeNotifications + bridge loops take until empty | ci_pinned |
| R15-CODE-FRONTEND-029 | pinned test exists | CommandPalette.test.tsx "custom agent added while open appears" | ci_pinned |
| R15-CODE-FRONTEND-027 | pinned tests exist | agents.test.ts "refreshCustom 404 -> customStatus error"; sidecar-client.test.ts custom-agents refresh transport; workflow/schedule-control tests | ci_pinned |
| R15-CODE-FRONTEND-030 | pinned test exists | settings.test.ts "R15-CODE-FRONTEND-030: fresh store ... keeps copilot" | ci_pinned |
| R15-CODE-FRONTEND-028 | pinned tests exist | research-spaces.test.ts errored reply round-trips; workspace.test.ts agent spaces survive serialize->deserialize | ci_pinned |

COVERAGE: 5/5 ids raw; no raw: none
