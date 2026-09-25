# unplanned-7

Candidate 4097dac4. Raw output: `raw/set-52/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-013 | Read `src/lib/plugin-bootstrap.ts:213-217`; `grep -n enabledByDefault src/lib/plugin-bootstrap.ts src/store/marketplace.ts` | `enabledByDefault(pluginId)` reads the catalog's `preinstalled` flag as the ONE shared source (doc comment cites R15-CODE-PLATFORM-013 directly); both `plugin-bootstrap.ts` (lines 254, 279) and `src/store/marketplace.ts` (import line 20, usage 109/125) call this same function — no independent enabled-state drift between runtime/boot/marketplace | holds |
| R15-CODE-PLATFORM-014 | Read `src/store/marketplace.ts` `configure()` (~lines 190-233) | After a secret save: `await runtime.reloadPlugin(row.discovered)` then `refreshFromRuntime()`/`refresh()` — comment: "Restart so initialize() receives the new secrets via PluginConfig.secrets (a disabled plugin stays stopped — loadPlugin honours the persisted flag)." The plugin is reloaded so `initialize()` picks up new secrets without an app restart | holds |

Summary: 2 holds. No regressions.
