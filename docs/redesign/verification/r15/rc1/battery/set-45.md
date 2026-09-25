# batch-10/W8-plugins-dock (rc1-battery-7)

Candidate `4097dac4`. 4 of 5 entries in this writer set were certified purely through vitest;
1 (UI-084) was itself certified `needs_gui`. No live sidecar work applies to this set.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-012 | test file presence: `src/components/PluginManagerPanel.test.tsx` (toggle-off persists `enabled:false` + detaches) | file present on `4097dac4` | ci_pinned |
| R15-CODE-PLATFORM-013 | test file presence: `src/store/workspace.test.ts` (never persists `plugin:*` flags) | file present | ci_pinned |
| R15-CODE-PLATFORM-014 | test file presence: `src/lib/plugin-runtime.test.ts` (`loadPlugin` idempotent, `reloadPlugin` re-runs initialize, honours persisted disabled config) | file present | ci_pinned |
| R15-AGENT-057 | test file presence: `src/lib/plugin-agents.test.ts` (POST/DELETE checks `response.ok` on a 409) | file present | ci_pinned |
| R15-UI-084 | GUI check (dock maximize spans cockpit at 2560px, restores prior width) | no GUI available to this headless shard (harness: "No GUI") | needs_gui |

Excluded from this set (not certified in batch-10): none — all 5 entries in W8 were certified
(4 certified + 1 needs_gui).
