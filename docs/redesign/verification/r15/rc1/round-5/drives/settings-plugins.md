# settings-plugins — rc1 gate round 5 owner-drive (candidate 9bc600ec)

Worker: claude-sonnet-5 (Sonnet), label `rc1-drive-settings-plugins`. Own sidecar
`127.0.0.1:52325`, source `rc1-round-5-cand/sidecar` (read-only), data dir
`rc1-round-5-data-settings-plugins` (copied from `rc1-round-5-seed-data`, keyless). Shared
`:52152/:52153/:52154` used only for code/context reference, never written to. Every write
below went to `:52325`.

Method: `PROMPT_surface_s2.md` OWNER-DRIVE settings-plugins scope. Baseline = census
`surface/settings-plugins/EVIDENCE.md`/`COVERAGE.json` (agents Q+P, 23 Sep) and the register
(`vysted-r15-register.json`). Cross-checked the prior gate rounds' method via
`surface/settings-plugins/rc1/rc1-redrive.md` and `rc1/round-4/*` (context/method only — not
cited as this round's evidence; every number below is a fresh curl/grep/vitest run against
this round's own sidecar and this round's candidate worktree, saved under
`surface/settings-plugins/rc1/round-5/`).

All 6 census raw findings map to register entries; none are in the 9 operator-adjudicated
entries or the three-failure-rule list, so an ordinary re-drive applies.

## Census → register → rc1 round-5 deltas

| # | Census raw finding | Register id (status) | rc1 round-5 result | Raw file |
|---|---|---|---|---|
| 1 | SURF-SETTINGS-PLUGINS-1 (fake OpenRouter key certified `ok:true`) | R15-RESEARCH-010 (fixed) | **ok, holds** — `POST /llm/keys/validate {openrouter}` fake key → `{"ok":false,"reason":"invalid","detail":"OpenRouter rejected this key."}` | `01-openrouter-fake-key-validate.txt` |
| 2 | SURF-SETTINGS-PLUGINS-2 (untrimmed key → misleading "Connection error") | R15-UI-057 (fixed) | **ok, holds** — trailing space (OpenAI) and trailing `\n` (Anthropic) both trim server-side and return the real "rejected this key" message, not a transport error | `02-openai-key-trailing-space.txt`, `03-anthropic-key-trailing-newline.txt` |
| 3 | SURF-SETTINGS-PLUGINS-4 (NewsAPI key never validated) | R15-DATA-094 (fixed) | **ok, holds** — `GET /news/sources/status` no key → `absent`, fake key → `unauthorized` | `04-newsapi-status-nokey.txt`, `05-newsapi-status-fakekey.txt` |
| 4 | COD-plugins-1 (disable is in-memory only) | R15-CODE-PLATFORM-012 (fixed) | **ok, holds** — `POST /plugins/vysted-example/config {enabled:false}` persists; `GET /plugins` readback shows `enabled:false`, then restored to `true` | `06`, `07`, `08`, `09` |
| 5 | SURF-SETTINGS-PLUGINS-6 (Unicode/punct name 400 reason dropped; ~210+ char 500s) | R15-UI-082 (fixed by redesign) | **ok, holds** — Devanagari name saves 200 and reads back clean; `../evil5`-shaped name saves 200 (percent-encoded on disk, no traversal); a 240-char name gets `400 {"detail":"Workspace name '...' is too long to save."}`, never a 500 | `10`, `11`, `12`, `13`, `14` |
| 6 | SURF-SETTINGS-PLUGINS-3 (export omits prefs; import "succeeds" on any JSON) | R15-UI-058 (fixed) | **ok, holds (code-read)** — export v2 (`searchSettings`, `defaultProviderId`/`defaultModel`, `enabledModules` on top of v1); import gates on `appliedAny`, only reports "Imported settings." when something real was applied, else "Could not read that file — expected a Vysted export." | `17-ui058-export-import-grep.txt` |

## New-since-last-redrive fix in this group's file set

`git diff 4c6dfe8c..9bc600ec` across every file this group depends on (`SettingsPanel.tsx`,
`MarketplacePanel.tsx`, `PluginManagerPanel.tsx`, `store/{modules,marketplace,workspace}.ts`,
`routers/{llm,news}.py`, `services/{workspace_store,plugins_store}.py`,
`lib/plugin-{bootstrap,runtime}.ts`, `KeyEntryDialog.tsx`) shows exactly **one** changed file:
`src/store/modules.ts` (commit `ef102fa5`, "setEnabledMap keeps lifecycle-owned plugin:* flags",
R15-CODE-PLATFORM-013 follow-up). A bulk enabled-map write (factory reset, Settings import) used
to replace the whole map wholesale, which could silently disable an active plugin's panels or
resurrect a disabled one; the setter now preserves live `plugin:*` flags and only
`setModuleEnabled` (the lifecycle owner) moves them. Ran the candidate's own pinned tests live:
`npx vitest run src/store/modules.test.ts src/store/workspace.test.ts
src/components/SettingsPanel.test.tsx` → **69/69 pass**, including the new regression test for
this exact fix. `18-full-history-scan.txt`, `19-vitest-settings-modules-workspace.txt`.

## Still-open rows re-confirmed genuinely still broken (register `open`, low, not a regression)

- **R15-UI-081** (dead "AI Assistant" module switch + a disabled module's panel still opens):
  code-read, `src/store/workspace.ts` `openPanel` only calls
  `useModulesStore.getState().findPanel(panelId)` — no read of the `enabled` map anywhere in the
  function, unchanged since the last redrive. `chat/index.ts` still registers the "AI Assistant"
  module with `title: "AI Assistant"` and no wired panels/commands for its switch.
  `15-ui081-openpanel-code.txt`, `21-ui081-ai-assistant-switch-grep.txt`.
- Plugin catalog still lists `tradesa-v2` (a broker plugin row, out of scope per D81) — pre-existing
  seed-data state, not filed.

## Observation for the lead (not filed as a finding — nothing broken, register bookkeeping only)

**R15-UI-089** ("Plugin data credentials [NewsAPI] saved with no validation, unlike LLM keys")
is still marked `open` (low) in the register, but its own repro no longer reproduces on this
candidate: `MarketplacePanel.tsx`'s `CredentialForm` calls `useMarketplaceStore.configure()`,
which (since the R15-DATA-094/R15-UI-033 commit `4c40215e`, already in the tree before this
round) runs `probeNewsApiKeyOrThrow` for `vysted-news`/`newsapi_key` and never grants a rejected
key — confirmed by the candidate's own committed test
(`src/store/marketplace.test.ts:137-141`, "vy" `configure("vysted-news",
{newsapi_key:"bad-key"})` → rejects `"NewsAPI rejected this key"`, grant not persisted). This
looks like the same fix that closed R15-DATA-094 also closes UI-089's exact repro; the register's
`open` status for UI-089 (last triaged `still_reproduces` at `e032be7`, apparently before/without
re-testing against the current CredentialForm code) may be stale. Not re-filed as a new
finding since nothing is broken; flagging for the register owner to re-check UI-089 against
`4c40215e`+.

## Score summary

| Row | Census score | rc1 round-5 score | Delta |
|---|---|---|---|
| settings-providers (key validation) | broken | ok | fixed, holds |
| settings-advanced-export-import | broken | ok | fixed, holds |
| panel-marketplace (News configure) | partial | ok | fixed, holds (+ UI-089 looks closed as a side effect, unconfirmed by register) |
| panel-plugin-manager (toggle) | broken | ok | fixed, holds |
| settings-advanced-layouts | partial | ok (redesigned) | fixed, holds |
| settings-advanced-modules (dead switch / reopen) | partial | broken | no change (R15-UI-081 open) |

No regressions (no previously-`ok`/`fixed` row scores worse on this candidate). No new defects
found in this group's surface. Own sidecar `:52325` stopped after this drive (sleep-pipe pid
recorded in the log); shared `:52152` stack untouched; no secret/canary value was ever echoed
by a response or found in the sidecar log.
