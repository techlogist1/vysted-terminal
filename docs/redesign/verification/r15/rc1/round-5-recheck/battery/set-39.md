# Set 39 — batch-9/W5-frontend-shell (rc1-battery-24)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. No GUI available to this role; vitest suites are the heavy lane's — every entry below was certified in batch-9's VERDICTS.md via scratch (uncommitted) vitest against real modules, and each now has a committed, named pinned test in the candidate tree covering the same class. Verdict `ci_pinned` names that test; raw files record the located test + a static source spot-check (never the sole basis for the verdict, but confirming the code path still exists).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-016 | Located pinned test (no live/vitest run possible here) | `keybindings.test.ts:283` `resolveKeyboardAction — the one dispatcher's resolution (R15-UI-016 / R15-CODE-FRONTEND-016)` resolves every `DEFAULT_KEYBINDINGS` id on its default chord; `registerAction`/`resolveKeyboardAction` still exported in `src/store/keybindings.ts` | ci_pinned |
| R15-CODE-FRONTEND-016 | Located pinned test | same test as UI-016 (shared describe block, both ids named in its title) | ci_pinned |
| R15-UI-086 | Located pinned test | `CommandPalette.test.tsx:170` `an action row shows its current (remapped) chord as a <kbd> (R15-UI-086)` | ci_pinned |
| R15-CROSS-PLATFORM-004 | Located pinned test | `command-palette.test.ts:358-375` `describe("dispatchLayoutMenuCommand")`, comment explicitly pins it to R15-CROSS-PLATFORM-004 as the one dispatch shared by palette + macOS menu bridge | ci_pinned |
| R15-UI-058 | Located pinned tests | `keybindings.test.ts:85,94`, `settings.test.ts:134`, `search-settings.test.ts:243`, all named `R15-UI-058: ...` | ci_pinned |
| R15-DATA-092 | Located pinned tests | `region.test.ts:5` comment + `SettingsPanel.test.tsx:471` `Region & locale states the actual default and what region controls (R15-DATA-092)` | ci_pinned |
| R15-UI-052 | Located pinned tests | `OnboardingFlow.test.tsx:50` `describe("OnboardingFlow welcome step (R15-UI-052)")`, `OnboardingBanner.test.tsx:57` `does not claim nothing leaves the machine (R15-UI-052)` | ci_pinned |

COVERAGE: 7/7 ids raw; no raw: none.
