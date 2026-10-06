# settings-plugins — RC1 gate round 4 re-drive

Worker: claude-sonnet-5. Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Own sidecar
`127.0.0.1:52325`, source run, isolated keyless data dir (copy of `rc1-round-4-seed-data`).
Method: re-run each census-broken row's exact repro live; code-read every fix's cited
file:line in the candidate worktree; re-check every open low for regression. Raw files below
are all in `docs/redesign/verification/r15/surface/settings-plugins/rc1/round-4/`.

## Scored table (census → rc1 round-4)

| # | Row | Census (23 Sep) | RC1 round-4 | Score | Raw file |
|---|---|---|---|---|---|
| 1 | settings-providers: fake OpenRouter key validate | broken — `ok:true` for any string (R15-RESEARCH-010/R15-UI-008) | `POST /llm/keys/validate` now probes `GET /key` (401 on a bad key) → `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` | **regression→fixed, ok** | 01-fake-openrouter-key-validate.txt |
| 2 | settings-providers: untrimmed key (trailing space) | broken — 'transport error: Connection error.' misread as an outage (R15-UI-057) | `KeyEntryDialog.tsx:68` now trims before calling `validateProvider`; sidecar-level probe with/without trailing space both return the honest `"OpenAI rejected this key."`, not a transport error | **fixed, ok** | 02-openai-key-trailing-space-sidecar-level.txt, 03-openai-key-trimmed-sidecar-level.txt |
| 3 | settings-research: Tier B research with an uncertified key | broken — 401 invisible in the trace, model fabricated sources (SURF-SETTINGS-PLUGINS-1) | Since #1 now rejects the key at save time, the scenario cannot recur; also `deep_research.py:714-716` documents an `engine`/`status=error` step is now emitted on any HTTP error so a failure this class would surface in-trace even if a key later went bad post-save | **fixed, ok** | code:`sidecar/services/agent_tools/deep_research.py:690-716` |
| 4 | settings-region: "Defaults to United States" copy while live default is IN | partial (COD-frontend-panels-shell-chrome-4 / R15-DATA-092) | `SettingsPanel.tsx:1427-1429` now reads `` `Defaults to ${regionConfig(DEFAULT_REGION).label}.` `` (DEFAULT_REGION="IN") and the hint states it drives the sidecar region header, not just formatting | **fixed, ok** | code:`src/components/SettingsPanel.tsx:1424-1429`, `src/lib/region.ts:39` |
| 5 | settings-keybindings: cross-platform conflict miss | broken (COD-frontend-panels-shell-chrome-3 / R15-UI-027) | `keybindings.ts:371-388`: `conflicts()` now resolves `"mod"` → platform `"meta"`/`"ctrl"` before grouping, so `mod+k` vs `ctrl+k` collide off-macOS as they should | **fixed, ok** | code:`src/store/keybindings.ts:334-388` |
| 6 | panel-plugin-manager: disable toggle sends zero requests, doesn't persist | broken (COD-plugins-1) | `disablePlugin` → `patchConfig(pluginId,{enabled:false})` → live `POST /plugins/vysted-example/config {enabled:false}` returns 200 and a follow-up `GET /plugins` reads back `enabled:false`; re-enabled for cleanliness, read back `enabled:true` | **fixed, ok** | 11-plugin-disable-vysted-example.txt, 12-plugins-list-after-disable.txt, 13-plugin-reenable-vysted-example.txt |
| 7 | panel-marketplace / settings-advanced-integrations: NewsAPI key saved with no probe | broken (R15-DATA-094 / adjacent to R15-UI-089) | New route `GET /news/sources/status` (`news.py:116-134`); `marketplace.ts:39-51` calls it and throws "NewsAPI rejected this key" before the config write. Live: no key → `absent`; fake key → `unauthorized` | **fixed, ok** | 04-news-sources-status-nokey.txt, 05-news-sources-status-fakekey.txt |
| 8 | settings-advanced-layouts: Unicode/long workspace name 400 (reason discarded) / 500 | partial (R15-UI-082) | Live: Devanagari name → 200 saved (not even a 400 now); path-like name `../evil` → 200 saved; a 250-char repeated name → clean `400` with the full reason in `detail` (`"...' is too long to save."`), no 500/Errno-63. Traced to a different register id's fix, `e851c0ef fix(workspace): research spaces save and load under any name (R15-CODE-FRONTEND-004)`, not R15-UI-082 itself — the register entry appears stale (still `open low`) but the behaviour no longer reproduces | **census-partial → now ok** (fixing commit e851c0ef, register id R15-CODE-FRONTEND-004, not the R15-UI-082 id itself — flagging the mismatch, not filing a new finding since severity is low and behavior only improved) | 06-workspace-unicode-name.txt, 07-workspace-longname-250.txt, 08-workspace-path-traversal-name.txt |
| 9 | settings-advanced-export-import: Export misses fields / Import "succeeds" on any JSON | broken (R15-UI-058) | `buildSettingsExport()` now includes `searchSettings`, `defaultProviderId`/`defaultModel`, `enabledModules` (was 3 fields, now 6 groups); `handleImportFile` only reports success (`appliedAny`) per section that structurally matches, else "Could not read that file — expected a Vysted export." `setAll` merges an absent field over CURRENT state, not the seed | **fixed, ok** | code:`src/components/SettingsPanel.tsx:1980-2090`, `src/store/settings.ts:255-320` |
| 10 | panel-plugin-manager / CODE-PLATFORM-013: dual enabled-state stores drift on workspace restore | fixed per register | `workspace.ts:300-312`: the `enabledModules` persisted slice now filters OUT `plugin:*` keys via `moduleFlags(...,false)` with an explicit comment that plugin state derives from `plugins.db` alone, never the workspace blob — confirmed via `ef102fa5 fix(modules): setEnabledMap keeps lifecycle-owned plugin:* flags` + `5109567e fix(platform): route Settings plugin-module toggles through the marketplace lifecycle` | **fixed, ok** | code:`src/lib/workspace.ts:289-312` |
| 11 | settings-advanced-integrations: dead "Open Marketplace" button (`marketplace-panel` vs `marketplace`) | broken (R15-UI-065, open low) | `PluginManagerPanel.tsx:72,1709` still call `openPanel("marketplace-panel")`; the real panel id is `"marketplace"` (`modules/marketplace/index.ts:13,17`) — unchanged, no regression, matches register (open, low) | **unchanged, broken (known, low)** | code:`src/components/PluginManagerPanel.tsx:72`, `src/modules/marketplace/index.ts:13-32` |
| 12 | settings-advanced-modules: dead "AI Assistant" switch + disabled module's panel still opens | broken (R15-UI-081, open low) | `AgentDock.tsx` reads only `useAgentDockStore` (collapsed/width/maximized) — never `useModulesStore.enabled["chat"]`, so the switch is still cosmetic; `host-actions.ts` still calls `ws.openPanel(...)` directly at every host-action call site (portfolio/notes/screener/brief) with no enabled-flag guard — unchanged, matches register (open, low) | **unchanged, broken (known, low)** | code:`src/components/AgentDock.tsx:21-27`, `src/lib/host-actions.ts:1537,1573,1709,1804,1866` |
| 13 | provider-health-breaker: no Settings-panel surface | ok (documented fact) | Still true for Settings; incidentally, `StatusChrome.tsx:74-118` now polls the same `/system/provider-health` endpoint for an unrelated NSE-exchange fallthrough indicator (R15-LIFECYCLE-021) — a different consumer, not a Settings feature, not a finding | **unchanged, ok** | 16-provider-health.txt, 17-provider-health-frontend-grep.txt |
| 14 | settings-searxng: managed-instance status | partial (environment-dependent) | Live: `state:"degraded"`, engines CAPTCHA/rate-limited (Brave suspended, DDG CAPTCHA, Startpage CAPTCHA) — an upstream/environment condition, not a candidate defect; matches SURF-RESEARCH-BRIEFS-4's documented class | **unchanged, partial (environment)** | 14-searxng-status.txt, 15-search-status.txt |
| 15 | settings-advanced-about | ok | `/health` still reports `version:"0.8.0"`, consistent | **unchanged, ok** | 18-health-version.txt |
| 16 | settings-providers: keyless model catalog fallback | ok | `GET /llm/models?provider=openai` (no key) still returns `source:"fallback"` with the honest note | **unchanged, ok** | 19-llm-models-openai-keyless.txt |

## Deltas vs census (23 Sep)

**Census broken → now ok (regressions resolved):**
- R15-RESEARCH-010 / R15-UI-008 (fake key certification) — fixing commits touch
  `sidecar/services/llm/openai.py` (`validate_key` now probes `/key` for openrouter) and
  `openrouter_catalog.py`.
- R15-UI-057 (untrimmed key) — `KeyEntryDialog.tsx:68`.
- R15-UI-027 (cross-platform keybinding conflict miss) — `keybindings.ts:371-388`.
- R15-DATA-092 (region copy stale) — `SettingsPanel.tsx:1427-1429`.
- R15-DATA-094 (NewsAPI no-probe) — `news.py:116-134` + `marketplace.ts:39-51`.
- R15-UI-058 (export/import) — `SettingsPanel.tsx` `ExportImportSection` + `settings.ts:255-320`.
- R15-CODE-PLATFORM-013 (dual plugin-enabled store) — `ef102fa5` + `5109567e`.
- COD-plugins-1 (disable toggle no-op) — same `5109567e` routes it through
  `patchConfig`/`disablePlugin`.
- Bonus (not this group's register id but reproduces the same repro shape as R15-UI-082):
  workspace-name 400/500 handling fixed by `e851c0ef` (R15-CODE-FRONTEND-004). Flagging the
  id mismatch for the lead; not filed as a new finding (severity low, behavior only improved,
  no regression).

**Still open, unchanged (no regression, matches register's accepted-low state):**
- R15-UI-065 (dead "Open Marketplace" button, `marketplace-panel` id mismatch).
- R15-UI-081 (dead "AI Assistant" module switch; disabled module's panel still opens via
  host actions).

**Census ok → still ok:** panel-settings shell, About, keyless model-catalog fallback,
provider-health-breaker (no Settings surface).

## Notes
- Trading/broker scope: `vysted-kite` (disabled/not-installed) and `tradesa-v2` present in
  `GET /plugins` — not analysed, out of scope (D81).
- No secret was ever printed; all keys used were fake canaries
  (`sk-or-v1-R15CANARY-round4-not-a-real-key`, etc.), grep-checked absent from responses.
- Did not re-drive `settings-section-nav` scroll behaviour or Export/Import's `<a download>`
  click path (both NEEDS-GUI per census, unchanged, headless lane cannot reach them).
