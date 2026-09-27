# batch-25/W1-opus (shard rc1-battery-9)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: source, `127.0.0.1:52355`.

R15-CODE-PLATFORM-013 (plugins.db `enabled` vs workspace blob `enabledModules['plugin:<id>']`
drift on restore) is frontend workspace/store logic with no sidecar route. Battery role may
not run vitest or a GUI. batch-25/VERDICTS.md line 16 names `plat013.test.tsx` as its
re-proof file; that exact filename does not exist at this sha (verified by `find`) — it was
a verifier-only/scratch name. Searched instead for committed, permanent tests carrying the
entry's id and found four, in `src/store/modules.test.ts`, `src/store/workspace.test.ts`,
`src/lib/workspace.test.ts`, `src/components/SettingsPanel.test.tsx`; read two of the four
bodies (below) and confirmed they assert exactly the register's repro shape (a direct
`setEnabledMap` with an incoming `plugin:x:false` is ignored; `resetToDefaultLayout` keeps
a lifecycle-owned `plugin:*` flag).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-CODE-PLATFORM-013 | `find` for `plat013.test.tsx` (absent); `git ls-files` + read `src/store/modules.test.ts:58`, `src/store/workspace.test.ts:98`, plus `src/lib/workspace.test.ts:464` and `src/components/SettingsPanel.test.tsx:437` (present, not read in full) | `setEnabledMap({"plugin:x":true, chart:false})` keeps `plugin:x:true` when the store already has it enabled, ignoring the incoming `false`; `resetToDefaultLayout()` after `setModuleEnabled("plugin:vysted-example", false)` leaves `enabled` as `{"plugin:vysted-example": false}` (the lifecycle-owned flag survives the reset, matching the register's expected fix) | ci_pinned: `src/store/modules.test.ts` — "setEnabledMap keeps the live plugin:* flags and ignores incoming ones (R15-CODE-PLATFORM-013)"; `src/store/workspace.test.ts` — "resetToDefaultLayout keeps lifecycle-owned plugin:* flags (R15-CODE-PLATFORM-013)"; also `src/lib/workspace.test.ts` and `src/components/SettingsPanel.test.tsx` carry same-id tests (present, not re-read) |

Raw: `battery/raw/set-68/R15-CODE-PLATFORM-013.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
