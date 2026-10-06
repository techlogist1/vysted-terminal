# drive:settings-plugins — rc1 (candidate 4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2, gate round 2)

Re-drive of the 25-Sep pass (candidate `4097dac4`) against the gate-round-2 candidate. Only
one file in this group's scope changed between the two shas: `SettingsPanel.tsx` (commit
`5109567e`, R15-CODE-PLATFORM-013 fix). Full delta in
`surface/settings-plugins/rc1/rc1-redrive.md` under "Gate-round-2 re-drive".

Full detail + raw evidence: `surface/settings-plugins/rc1/rc1-redrive.md`. Own sidecar `:52325` on
`rc1-data-rc1-drive-settings-plugins` (keyless, copied from `rc1-seed-data`); shared `:52152` used
read-only for context. Method: `PROMPT_surface_s2.md` OWNER-DRIVE settings-plugins scope, seeded from
`surface/settings-plugins/EVIDENCE.md`/`COVERAGE.json` (census, agents Q+P).

## Scored table

| Interaction | Census | rc1 | Fixing register id | Evidence |
|---|---|---|---|---|
| AI Providers: fake OpenRouter key validate | broken | ok | R15-RESEARCH-010 | live `POST /llm/keys/validate` -> `ok:false, reason:invalid` |
| AI Providers: whitespace-padded key | broken | ok | R15-UI-057 | code: `KeyEntryDialog.tsx:68` trim + `llm.py:109` strip |
| Advanced > Export/Import | broken | ok | R15-UI-058 | code: export v2 (`SettingsPanel.tsx:1958-1977`), import gated per-section (`:2018-2110`) |
| Marketplace: configure() error path | partial | ok | R15-UI-033 | code: `MarketplacePanel.tsx:349-357` `.catch()` |
| Marketplace: NewsAPI key probe | broken | ok | R15-DATA-094 | live `GET /news/sources/status` -> `unauthorized` on fake key |
| Plugin Manager: enable/disable toggle persistence | broken | ok | R15-CODE-PLATFORM-012 | live `POST /plugins/vysted-example/config` round-trips `enabled:false` then restored `true` |
| Advanced > Layouts: punct/long name handling | partial | ok (redesigned) | R15-UI-082 | live: 234-char name -> 400 with reason kept; `../evil` -> 200, percent-encoded on disk, no traversal |
| Advanced > Modules: dead "AI Assistant" switch / disabled module still opens | partial | still broken | — (R15-UI-081 `open`, expected) | code: `workspace.ts:109-118` `openPanel` never reads `enabled[moduleId]` |
| Advanced > Modules: bridged plugin toggle wrote the wrong store (silently undone on relaunch) | n/a (found by rc1 refutation audit @6741387b, not census) | ok | R15-CODE-PLATFORM-013 | `SettingsPanel.tsx` now routes `plugin:<id>` toggles through `useMarketplaceStore.enable/disable`; `vitest run SettingsPanel.test.tsx` 52/52 pass incl. the pinned regression test |

## Deltas

- Census `broken`/`partial` -> rc1 `ok`: 7 rows, all matched to a `fixed` register entry (25-Sep pass).
- rc1-refutation-audit `partial` -> rc1 (gate round 2) `ok`: 1 row (bridged plugin toggle store split),
  matched to R15-CODE-PLATFORM-013's fix commit `5109567e`, verified via a passing pinned vitest test.
- Census `partial` -> rc1 still not-fully-ok: 1 row (Modules dead switch / disabled-module-still-opens),
  matches register `open` (R15-UI-081) — expected, not a regression. Distinct defect from
  PLATFORM-013 (which store the toggle writes) vs UI-081 (openPanel never reads the enabled map at
  all, for any module) — fixing one does not fix the other.
- No census/previous-pass `ok` row regressed (re-confirmed live on the new candidate: key validate,
  NewsAPI probe, plugin toggle round-trip).
- No new defects found in this group beyond what the register already tracks as `open`.

## Notes

- `tradesa-v2` still appears `enabled:true` in `GET /plugins` — pre-existing seed data, a broker
  plugin row out of this group's scope per census (D81 removed trading UI/order path only); not filed.
- Only one file in this group's scope changed between candidate `4097dac4` (25-Sep pass) and
  `4c6dfe8c` (gate round 2): `SettingsPanel.tsx` (the PLATFORM-013 fix). All sidecar routers and
  other frontend files this group depends on are byte-identical across the two shas.
- Sidecar `:52325` (worker) stopped via its sleep-pipe pid after this drive; shared `:52152` untouched.
