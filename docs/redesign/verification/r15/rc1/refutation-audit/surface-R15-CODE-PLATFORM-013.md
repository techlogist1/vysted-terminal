# Refutation audit: R15-CODE-PLATFORM-013 (group surface) at HEAD 6741387b

Verdict: **partial**

## Certification
batch-10 VERDICTS.md:60: vitest workspace.test 'never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on'. The fix commit is 168dad71. It derives plugin:* module flags from the runtime and uses one never-persisted default, enabledByDefault.

## Gate verifier refutation (rc1-verifier:14)
code-excerpts.txt: the SettingsPanel.tsx:1936-1941 Modules toggle calls setModuleEnabled(module.id, next) and nothing else. The Marketplace writes to the runtime and plugins.db. No single lifecycle owner exists.

## Entry's own repro at HEAD
`node_modules/.bin/vitest run src/lib/workspace.test.ts src/lib/plugin-runtime.test.ts -t "PLATFORM-013|defaultEnabled"`
```
 Test Files  2 passed (2)
      Tests  2 passed | 85 skipped (87)
```
src/lib/workspace.ts:303-314 at HEAD: `read` drops plugin:* flags and `restore` keeps the live plugin:* flags. An older blob with plugin:x=false therefore no longer hides a re-enabled plugin. The four duplicated defaults now route through one function, plugin-bootstrap.ts:216 `enabledByDefault`, used at plugin-runtime.ts:328 and marketplace.ts:109,125. The entry's stated repro and its default-spelling half are fixed.

## Verifier's claim, driven at HEAD
Scratch test: /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit-surface/vt/refaudit-013.test.tsx. It reuses the SettingsPanel.test.tsx mocks and runs under a scratch vitest config rooted at the repo.
Environment note: the main worktree's node_modules is missing @tiptap/extension-list, which package.json:31 declares. The stock `vitest run src/components/SettingsPanel.test.tsx` therefore fails at import with "Failed to resolve import @tiptap/extension-list" (see /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/refaudit-surface/vt/base.log). The scratch config aliases that package to a stub. This stale-install problem is environmental and unrelated to this entry.

The test bridges a plugin module exactly as plugin-bootstrap.ts:183-186 bridgePluginModule does (appendModules plus setModuleEnabled(true)). It renders SettingsPanel and clicks the plugin module's switch in the Modules region. It then serializes the workspace and simulates a relaunch: deserialize, then runtime attach calls setModuleEnabled(true).
```
REFAUDIT plugin module: plugin:vysted-example title: Vysted Example Plugin panels: 0 commands: 1 enabledCommands has it: true
REFAUDIT after Settings toggle, module flag: false
REFAUDIT enabledCommands still has plugin commands: false enabledPanels contains plugin panel: false
REFAUDIT fetch calls (a plugins.db write would be a sidecar call): []
REFAUDIT serialized enabledModules has plugin flag: false
REFAUDIT after relaunch, module flag: true
      Tests  1 passed (1)
```

## Reasoning
Settings > Modules lists every module in useModulesStore.modules, with no filter on plugin:* ids (SettingsPanel.tsx:1909-1944). Bridged plugins are appended to that same store. The Settings switch writes only the in-memory module flag. It never calls runtime.disablePlugin or plugins.db, and the test recorded no sidecar call. So Settings hides the plugin's panels and commands while the Marketplace and Plugin Manager still show the plugin as active.
Since 168dad71 the workspace blob no longer persists plugin:* flags. On the next launch the runtime attach turns the plugin back on, so the Settings "off" is silently lost.
The entry's defect class is plugin-lifecycle-split ("'Is this plugin on?' lives in two independent stores ... no single owner"), and it is still reachable through this fourth writer. The entry did not enumerate this writer, and the fix did not route it. The verifier is right that the class persists. It is wrong only in implying that the entry's own restore repro regressed, which it did not.

## Root cause
src/components/SettingsPanel.tsx:1938-1941: the Modules toggle calls useModulesStore.setModuleEnabled for plugin:<id> modules and bypasses the lifecycle owner, useMarketplaceStore.enable/disable (runtime plus plugins.db). workspace.ts:309-313 now drops that flag, so the toggle does not persist, and it drifts from plugins.db for the rest of the session.

## Acceptance test
src/components/SettingsPanel.test.tsx: bridge a catalog plugin module (moduleForPlugin(CATALOG_BY_ID['vysted-example']) plus appendModules and setModuleEnabled(true)), render SettingsPanel, and click the '<title> enabled' switch in the Modules region. The test must assert one of two outcomes. Either useMarketplaceStore.getState().disable was called with 'vysted-example' (so runtime.disablePlugin writes plugins.db), or plugin:* modules are not rendered as free toggles in Settings > Modules (they are rendered read-only or with a link to the Marketplace). Either way, useModulesStore.getState().enabled['plugin:vysted-example'] must never be false while the runtime reports the plugin active.
