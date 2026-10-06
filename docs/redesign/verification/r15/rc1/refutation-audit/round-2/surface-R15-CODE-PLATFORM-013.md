# Refutation audit round 2: R15-CODE-PLATFORM-013 (group surface, key rc1-verifier:16) at 4c6dfe8c (code tree; HEAD a3275f64, docs-only diff)

Verdict: **partial**. Audited 18:15-18:21 IST.

## Certification history
- batch-10 VERDICTS.json: certified (workspace.test "never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on"). Fix commit 168dad71.
- Round-1 refutation audit (REFUTATION_AUDIT.json @6741387b): **partial**. The Settings > Modules toggle was a fourth writer that bypassed the lifecycle owner.
- batch-12 VERDICTS.json: certified. SettingsPanel test "toggling a bridged plugin module routes through the marketplace lifecycle".

## Entry's own repro at the candidate
The repro: restoring an older blob with plugin:x=false hides a plugin re-enabled since, and the never-persisted default is spelled at four sites.
Command: `node_modules/.bin/vitest run src/lib/workspace.test.ts src/lib/plugin-runtime.test.ts src/store/workspace.test.ts -t "PLATFORM-013|defaultEnabled|factory reset" --reporter=verbose`
```
 ✓ src/lib/plugin-runtime.test.ts > PluginRuntime — the one never-persisted default (R15-CODE-PLATFORM-013) > a patch or load of a never-seen plugin uses defaultEnabled, never a hard-coded true
 ✓ src/lib/workspace.test.ts > never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on (R15-CODE-PLATFORM-013)
 ✓ src/store/workspace.test.ts > resetToDefaultLayout (Settings / menu) is the factory reset: drawings and module choices go
```
The batch-12 Settings test needs a scratch config with the @tiptap/extension-list stub alias, the same stale-install environment issue that round 1 recorded:
`vitest run --config <scratch>/vt/vitest.settings.config.mts -t "marketplace lifecycle"`
```
 ✓ src/components/SettingsPanel.test.tsx > SettingsPanel > toggling a bridged plugin module routes through the marketplace lifecycle, not setModuleEnabled directly
```
The entry's stated restore repro and the round-1 Settings-toggle writer are both fixed. src/lib/workspace.ts:309-313 keeps the live plugin:* flags on restore.

## Verifier's claim (rc1-verifier:16, PLAUSIBLE, code-level only), driven live
src/store/workspace.ts:176-184 `resetToDefaultLayout` calls `useModulesStore.getState().setEnabledMap({})`. That wholesale replace drops every plugin:* flag. The flags are written only by the lifecycle owner, through bridgePluginModule/unbridgePluginModule (src/lib/plugin-bootstrap.ts:180-194), and the restore path at workspace.ts:309-313 deliberately preserves them. A module is enabled unless its flag is `false` (src/store/modules.ts:79). So a plugin disabled at runtime has its module stay in the registry with flag=false (appendModules never removes it), and the reset turns that plugin's contributions back on.

Driven with the real pluginHost.attach/detach and the real workspace store. The scratch test is <scratch>/refaudit2-surface/vt/plat013.test.tsx; it mocks only syncPluginAgents (network) and autosaveLayout, and uses a proxy fake of the dockview api:
`node_modules/.bin/vitest run --config <scratch>/vt/vitest.config.mts <scratch>/vt/plat013.test.tsx`
```
REFAUDIT plugin: vysted-example panels:  commands: example.hello
REFAUDIT after attach flag: true
REFAUDIT after detach (plugin disabled) flag: false module in registry: true plugin commands live: 0 plugin panels live: 0
REFAUDIT reset error: none
REFAUDIT after resetToDefaultLayout flag: undefined module in registry: true plugin commands live: 1 plugin panels live: 0
```
Before the reset, the disabled plugin's command `example.hello` is absent from enabledCommands, which is correct. After "Reset to default layout" (Settings button SettingsPanel.tsx:1724, palette command-palette.ts:178), the flag is `undefined`, which means enabled, and the command is live again. Meanwhile the runtime, plugins.db and the Marketplace still report the plugin disabled. No catalog plugin with panels resolves under test, so I could not show panels. They take the identical path (`enabledPanels` also filters on `enabled[id] !== false`).

A second non-owner writer of the same class exists: Settings import (SettingsPanel.tsx:2071-2079). `buildSettingsExport` (SettingsPanel.tsx:2002) exports plugin:* flags, and import writes them back through setEnabledMap for any known module id, again bypassing the lifecycle.

## Why partial
The verifier's plausible claim holds live, so it is not a verifier error. It is not a regression of the entry's own repro either: the restore path and the Settings toggle hold fixed. The entry's defect class, plugin-lifecycle-split ("no single owner for the enabled fact"), is still reachable through two more writers that change plugin:* flags without the lifecycle owner: reset, and settings import. The fix_shape names the class ("one lifecycle owner writes both").
Note that src/store/workspace.test.ts's reset test asserts `enabled` toEqual({}). It seeds no plugin keys, so it does not pin the defect, but it also never exercises the class.

## Root cause
src/store/workspace.ts:184 (`setEnabledMap({})`) and src/components/SettingsPanel.tsx:2079 (import `setEnabledModules(next)` with plugin:* keys). Both reach src/store/modules.ts:76 `setEnabledMap: (enabled) => set({ enabled })`, which lets any caller overwrite the lifecycle-owned plugin:* flags.

## Fix shape
Make the shared setter enforce the single owner once, instead of patching each caller. src/store/modules.ts:76 becomes `setEnabledMap: (enabled) => set((s) => ({ enabled: { ...nonPluginFlags(enabled), ...pluginFlags(s.enabled) } }))`. The plugin:* flags then change only through setModuleEnabled, which bridge/unbridge (the lifecycle owner) call. This covers reset, settings import and restore in one place, and the explicit merge in src/lib/workspace.ts:311-314 becomes redundant (it can stay or collapse to `setEnabledMap(workspace.enabledModules)`). Optionally drop plugin:* keys from buildSettingsExport.

## Acceptance test
In src/store/workspace.test.ts, add "resetToDefaultLayout keeps lifecycle-owned plugin:* flags (R15-CODE-PLATFORM-013)". Seed with `setEnabledMap({news:false})` then `setModuleEnabled("plugin:vysted-example", false)`, call resetToDefaultLayout, and expect `enabled` toEqual({"plugin:vysted-example": false}). Add a modules.test/SettingsPanel.test case: importing a bundle with `enabledModules: {"plugin:vysted-example": true}` while the live flag is false leaves it false.

Live re-proof: rerun the scratch plat013 test. It must print `after resetToDefaultLayout flag: false ... plugin commands live: 0`.

## Certification-failure count
Batch not_certified lists: 0. Round-1 refutation audit: 1 (partial). This gate: 1 (partial). **Total 2.**
