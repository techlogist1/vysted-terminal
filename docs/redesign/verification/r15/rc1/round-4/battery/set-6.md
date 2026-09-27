# Set 6 — batch-3/W2-agent-frontend-gate (rc1-battery-20)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar `127.0.0.1:52360` (fresh
copy of `rc1-round-4-seed-data`). Frontend-only entries (Zustand store / React
component / TipTap logic) cannot be executed without vitest+jsdom or a live GUI;
both are out of scope for this role ("never run vitest or pytest suites", "No
GUI"), so those are verified by direct source inspection against the exact
mechanism the batch-3 certification named, and verdicted `ci_pinned` naming the
committed test that actually exercises the behavior. `R15-AGENT-014`'s sidecar
half (`GET /custom-agents`) is live-checked directly.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-080 | Source check: `types/proposed-change.ts` `AUTO_APPLIED_KINDS`/`autoApplies` | `AUTO_APPLIED_KINDS = ["panel","chart","watchlist"]`; `data-write`/`settings` excluded — matches the certified allow-list rewrite | ci_pinned (src/store/proposed-changes.test.ts:128,139) |
| R15-CODE-FRONTEND-008 | same mechanism as AGENT-080 (duplicate defect, same fix) | same | ci_pinned (src/store/proposed-changes.test.ts:128,139) |
| R15-CODE-FRONTEND-003 | Source check: `src/lib/host-actions.ts:760-763` `noteMode` | `str(input,"mode") === "replace" ? "replace" : "append"` — anything but explicit `replace` is append | ci_pinned (src/lib/host-actions.test.ts:1241) |
| R15-CODE-FRONTEND-014 | Source check: `src/lib/host-actions.ts:768-776` layout-name fallback | falls back to "Agent layout" only when no saved layout is active ("default") — matches the certified fix | ci_pinned (src/lib/host-actions.test.ts:1257,1273) |
| R15-UI-001 | Source check: `src/modules/notes/NotesPanel.tsx:150-206` | rewritten `shownRef`/`pendingRef` pair: scope switch flushes to the PRIOR scope before loading the new one, `setContent(..., {emitUpdate:false})` on store-driven loads, unmount flush via `useEffect(() => flush, [flush])` | ci_pinned (src/modules/notes/NotesPanel.test.tsx:46,66) |
| R15-UI-002 | Source check: `src/components/CommandPalette.tsx:55,204-207,394` | both ticker-pick call sites route through `loadSymbolIntoChart` (the always-consumed chart-command channel), not the opt-in chart-sync bus | ci_pinned (src/components/CommandPalette.test.tsx:217) |
| R15-AGENT-014 | `curl -s http://127.0.0.1:52360/custom-agents` (fresh data dir, pre-sync) + source check `src/lib/plugin-bootstrap.ts:225,229,269-280` | live: `[]` (no agents registered yet, as expected pre-boot-sync); source: `bootstrapPlugins()`'s catalog loop calls `runtime.loadPlugin(plugin)` for every enabled row → `pluginHost.attach` → `syncPluginAgents(pluginId, true)` — the boot-time call chain the fix added is present | ci_pinned (src/lib/plugin-bootstrap.test.ts:43,50) — sidecar half holds live, frontend boot-loop half needs vitest |

COVERAGE: 7/7 ids raw.
