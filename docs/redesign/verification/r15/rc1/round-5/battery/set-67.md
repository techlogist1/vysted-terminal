# batch-25/W1-opus (rc1-battery-13, gate round 5)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-013 | `vitest run src/components/SettingsPanel.test.tsx src/lib/workspace.test.ts src/lib/plugin-runtime.test.ts src/store/workspace.test.ts src/store/modules.test.ts` | 5 files, 157/157 passed, incl. all five R15-CODE-PLATFORM-013-named tests: `plugin-runtime.test.ts` "a patch or load of a never-seen plugin uses defaultEnabled, never a hard-coded true", `workspace.test.ts` (lib) "never persists plugin:* flags, and a blob with plugin:x=false keeps an enabled plugin on", `workspace.test.ts` (store) "resetToDefaultLayout keeps lifecycle-owned plugin:* flags", `modules.test.ts` "setEnabledMap keeps the live plugin:* flags and ignores incoming ones", `SettingsPanel.test.tsx` "an import cannot flip a lifecycle-owned plugin:* flag; its non-plugin toggles still apply" | holds (ci_pinned) |

This entry stands at two prior certification failures (rc1 refutation audit round 1: partial;
rc1 gate round 2: partial) and was certified in batch-25 (merge 1373c0d5). Per the lead note's
three-failure rule, a refutation here would be recorded as not-certified for the operator and
NOT opened as a fix round — this run's result is holds, so that rule is moot this round.

Raw: `battery/raw/set-67/vitest-plugin-lifecycle.txt`, `R15-CODE-PLATFORM-013.txt`.

COVERAGE: 1/1 ids raw; no raw: none.
