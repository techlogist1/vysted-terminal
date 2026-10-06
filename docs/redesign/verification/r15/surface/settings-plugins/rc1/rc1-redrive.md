# settings-plugins — rc1 owner-drive (candidate 4097dac4)

Worker: claude-sonnet-5 (Sonnet), label `rc1-drive-settings-plugins`. Own sidecar `127.0.0.1:52325`,
source `rc1-cand/sidecar` (read-only), data dir `rc1-data-rc1-drive-settings-plugins` (copied from
`rc1-seed-data`, keyless). Shared read-only stack `:52152/:52153/:52154` used for context only; every
write below (`/llm/keys/validate`, `/plugins/*`, `/news/sources/status`, `/workspace`) went to
`:52325`. Method: mirror `PROMPT_surface_s2.md` OWNER-DRIVE settings-plugins scope — re-drive every
census row that the register marks `fixed`, confirm the still-`open` rows remain honestly broken (not
a regression check gone quiet), read the panel/api code first.

Census baseline: `surface/settings-plugins/EVIDENCE.md` + `COVERAGE.json` (agents Q+P, 2026-09-23).
Register: `docs/redesign/verification/vysted-r15-register.json`.

## Census -> rc1 deltas (fixed rows re-verified live/by code)

| Census raw finding | Register id | Register status | rc1 result | Evidence |
|---|---|---|---|---|
| SURF-SETTINGS-PLUGINS-1 (fake OpenRouter key certified `ok:true`; Tier-B 401 invisible) | R15-RESEARCH-010 | fixed | **now ok** — `POST /llm/keys/validate {provider:openrouter}` with a fake canary key returns `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}`. Code: `sidecar/services/llm/openai.py:792-816` `validate_key` now probes `/key` for OpenRouter instead of the unauthenticated `/models`. | live curl below; code read |
| SURF-SETTINGS-PLUGINS-2 (untrimmed pasted key -> misleading "Connection error") | R15-UI-057 | fixed | **now ok** — client trims (`KeyEntryDialog.tsx:68`, explicit `R15-UI-057` comment) and server also strips (`sidecar/routers/llm.py:109`). | code read |
| SURF-SETTINGS-PLUGINS-3 / R15-UI-058 (export omits prefs; import "succeeds" on any JSON) | R15-UI-058 | fixed | **now ok** — export bundle is v2 (`SettingsPanel.tsx:1958-1977`): adds `searchSettings`, `defaultProviderId`/`defaultModel`, `enabledModules` on top of v1's 3 fields. Import now gates each section by shape and only reports "Imported settings." when `appliedAny` is true; an unrecognised file reports "Could not read that file — expected a Vysted export." (`SettingsPanel.tsx:2018-2110`). | code read |
| SURF-SETTINGS-PLUGINS-4 (NewsAPI key never validated, rejected key silently RSS-only) | R15-DATA-094 | fixed | **now ok** — new route `GET /news/sources/status` (`sidecar/routers/news.py:116-134`) probes the key; live: fake key -> `{"newsapi":"unauthorized"}`, no key -> `{"newsapi":"absent"}`. Wired into `configure()` via `probeNewsApiKeyOrThrow` (`src/store/marketplace.ts:39-53`), throws `"NewsAPI rejected this key"` before the save. | live curl below; code read |
| COD-plugins-8 (Marketplace `configure()` had no error path) | R15-UI-033 | fixed | **now ok** — `MarketplacePanel.tsx:349-357`, explicit `R15-UI-033` comment: `configure().catch()` now sets `validationError` instead of an unhandled rejection. | code read |
| COD-plugins-1 (toggle off is in-memory only; persisted row stays enabled) | R15-CODE-PLATFORM-012 | fixed | **now ok** — `PluginManagerPanel.tsx:172-182` `handleToggle` now calls `marketplace.enable/disable`, which call `runtime.enablePlugin/disablePlugin` then `persistence.save()` (`plugin-bootstrap.ts:81-98`), which now `throw`s on `!response.ok` (was previously swallowed). Live: `POST /plugins/vysted-example/config {enabled:false}` -> `{"enabled":false,...}` persisted (readback via the POST response + a second POST flipping it back to `true`, restored to census baseline). | live curl below; code read |
| SURF-SETTINGS-PLUGINS-6 (Devanagari/punct name 400 with reason dropped; ~210+ char name 500s) | R15-UI-082 | fixed | **now ok, by redesign** — `workspace_store._filename_stem` (`sidecar/services/workspace_store.py:42-58`) now percent-encodes ANY name into a safe filename component (letters/digits/space/`-`/`_` kept, everything else incl. `/`, `.`, NUL encoded), so a name can never escape the workspaces dir or collide with a reserved character. Live: `../evil` -> `200 {"status":"saved","name":"../evil"}` (file on disk: `%2E%2E%2Fevil.vysted-workspace`, listed back as `../evil`, deleted clean). A 234-char name -> `400 {"detail":"Workspace name '...' is too long to save."}` — the reason is no longer dropped and there is no 500. This changes census's expected 400-on-`../evil` into an accepted-and-safely-encoded save, which is a deliberate widening (no path traversal possible), not a defect. | live curl below |

## Still-open rows re-confirmed genuinely still broken (register `open`, not a regression check false negative)

- **R15-UI-081** (`SURF-SETTINGS-PLUGINS-5`/`-7`): `useWorkspaceStore.openPanel` (`src/store/workspace.ts:109-118`)
  only calls `useModulesStore.getState().findPanel(panelId)` — no read of `enabled[moduleId]` anywhere
  in the function. A disabled module's panel still opens via any `ws.openPanel(...)` host action
  (`src/lib/host-actions.ts` has 10+ call sites). Confirmed by code read only (no GUI to click the
  dead "AI Assistant" switch headlessly); matches register `open`.
- Plugin catalog still lists `tradesa-v2` (`enabled:true,installed:true`) via `GET /plugins` on the
  candidate — this is pre-existing seed-data state (a broker plugin row), not something this drive
  added; census already scoped broker plugin rows as out-of-scope (D81 removed the trading UI/order
  path, not the read-only broker plugin registration). Not filed as a finding.

## Raw evidence (this drive)

```
$ curl -sX POST :52325/llm/keys/validate -d '{"provider":"openrouter","api_key":"sk-or-v1-R15CANARY..."}'
{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}

$ curl -s ":52325/news/sources/status" -H 'X-Vysted-Newsapi-Key: R15CANARY-fake-key'
{"newsapi":"unauthorized"}
$ curl -s ":52325/news/sources/status"
{"newsapi":"absent"}

$ curl -sX POST :52325/plugins/vysted-example/config -d '{"installed":true,"enabled":false,...}'
{"plugin_id":"vysted-example","enabled":false,"installed":true,...}
$ curl -sX POST :52325/plugins/vysted-example/config -d '{"installed":true,"enabled":true,...}'   # restored
{"plugin_id":"vysted-example","enabled":true,...}

$ curl -sX POST :52325/workspace -d '{"name":"<234-char name>","workspace":{}}'
400 {"detail":"Workspace name '...' is too long to save."}
$ curl -sX POST :52325/workspace -d '{"name":"../evil","workspace":{}}'
200 {"status":"saved","name":"../evil"}
$ ls .../workspaces/   -> %2E%2E%2Fevil.vysted-workspace, __autosave__.vysted-workspace
$ curl -sX DELETE ":52325/workspace/..%2Fevil"   -> 204  (cleaned up)
```

No canary/secret value was echoed by any response or logged.

## Score summary (register-status cross-check, not a full re-census)

| Row | Census score | rc1 score | Delta |
|---|---|---|---|
| settings-providers (key validation) | broken | ok | fixed (R15-RESEARCH-010, R15-UI-057) |
| settings-advanced-export-import | broken | ok | fixed (R15-UI-058) |
| panel-marketplace (News configure) | partial (configure broken leg) | ok | fixed (R15-DATA-094, R15-UI-033) |
| panel-plugin-manager (toggle) | broken | ok | fixed (R15-CODE-PLATFORM-012) |
| settings-advanced-layouts | partial | ok (redesigned) | fixed (R15-UI-082) |
| settings-advanced-modules (dead switch / reopen) | partial | still broken | no change (R15-UI-081 `open`) |

No regressions found (no census-`ok` row now scores worse). No new defects found in this drive beyond
the register's existing open items for this group.

## Gate-round-2 re-drive at candidate 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2 (26 Sep, this session)

The 25-Sep pass above evidenced candidate `4097dac4`. Between that sha and the gate-round-2
candidate `4c6dfe8c`, `git diff --stat 4097dac4 4c6dfe8c` shows exactly one file in this
group's scope changed: `src/components/SettingsPanel.tsx` (+12/-0), commit `5109567e
fix(platform): route Settings plugin-module toggles through the marketplace lifecycle
(R15-CODE-PLATFORM-013)`. No other file this group depends on (`sidecar/routers/llm.py`,
`sidecar/routers/news.py`, `sidecar/services/workspace_store.py`,
`src/lib/plugin-bootstrap.ts`, `src/store/marketplace.ts`, `src/store/workspace.ts`,
`src/components/PluginManagerPanel.tsx`, `src/modules/marketplace/*`) changed in that range.

**R15-CODE-PLATFORM-013 was `fixed` in the register but carried a `note`**: an rc1
refutation audit at `6741387b` found the fix `partial` — `SettingsPanel.tsx:1938-1941` called
`useModulesStore.setModuleEnabled` directly for a bridged `plugin:<id>` module instead of
routing through `useMarketplaceStore.enable/disable` (the lifecycle owner that also writes
`plugins.db`), so a Settings "off" for a plugin-backed module was silently undone on the next
plugin-bootstrap read of `plugins.db`. Commit `5109567e` (in the 4097dac4..4c6dfe8c range)
fixes exactly this: `SettingsPanel.tsx` now special-cases `module.id.startsWith("plugin:")`
and calls `useMarketplaceStore.getState().enable/disable(pluginId)` instead of
`setModuleEnabled`.

**Verified live**: ran `vitest run src/components/SettingsPanel.test.tsx` against the
candidate worktree (`rc1-cand`, sha `4c6dfe8c`) — 52/52 tests pass, including the pinned
regression test added for this fix ("toggling a bridged plugin module routes through the
marketplace lifecycle, not setModuleEnabled directly", `SettingsPanel.test.tsx:145-169`),
which spies on `useMarketplaceStore.disable` and asserts it (not `setModuleEnabled`) fires for
the `vysted-example` module and that `enabled['plugin:vysted-example']` is never flipped
directly by the Settings panel.

**Re-confirmed unchanged (own sidecar `:52325`, fresh boot from `rc1-cand/sidecar`, same
data dir as the 25-Sep pass, keyless)**:
```
$ curl -sX POST :52325/llm/keys/validate -d '{"provider":"openrouter","api_key":"sk-or-v1-R15CANARY-rc1recheck"}'
{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}
$ curl -s :52325/news/sources/status
{"newsapi":"absent"}
$ curl -sX POST :52325/plugins/vysted-example/config -d '{"installed":true,"enabled":false}'
{"plugin_id":"vysted-example","enabled":false,"installed":true,...}
$ curl -sX POST :52325/plugins/vysted-example/config -d '{"installed":true,"enabled":true}'   # restored
{"plugin_id":"vysted-example","enabled":true,...}
```
All 6 previously-`ok` rows from the 25-Sep pass hold; no regression.

**R15-UI-081 re-confirmed still open, not touched by this range**: `src/store/workspace.ts`
`openPanel` (now at `:109-`) still only calls `useModulesStore.getState().findPanel(panelId)`,
no read of the `enabled` map anywhere in the function — code unchanged between the two
candidates for this file. This is a *different* defect from PLATFORM-013: PLATFORM-013 is
about which store the Settings toggle itself writes to; UI-081 is about `openPanel`/host
actions never consulting the `enabled` map at all, for ANY module (plugin-backed or not).
Fixing PLATFORM-013 does not fix UI-081 — a disabled module's panel (plugin-backed or
first-party) still opens via `ws.openPanel(...)`. Matches register status `open`, no
regression.

No new defects found. Own sidecar `:52325` stopped (sleep-pipe pid 70950) after this re-drive;
shared `:52152` stack untouched.
