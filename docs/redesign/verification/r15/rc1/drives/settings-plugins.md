# drive:settings-plugins — rc1 (candidate 4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a)

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

## Deltas

- Census `broken`/`partial` -> rc1 `ok`: 7 rows, all matched to a `fixed` register entry above.
- Census `partial` -> rc1 still not-fully-ok: 1 row (Modules), matches register `open` (R15-UI-081) —
  expected, not a regression.
- No census `ok` row regressed.
- No new defects found in this group beyond what the register already tracks as `open`.

## Notes

- `tradesa-v2` still appears `enabled:true` in `GET /plugins` — pre-existing seed data, a broker
  plugin row out of this group's scope per census (D81 removed trading UI/order path only); not filed.
- Sidecar `:52325` (worker) stopped via its sleep pid after this drive; shared `:52152` untouched.
