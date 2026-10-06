# batch-9/W5-frontend-shell (rc1-battery-7)

Candidate `4c6dfe8c`. 7 certified entries in this writer set were certified in batch-9
VERDICTS.md purely through a scratch (never-committed) vitest driving the real
`resolveKeyboardAction`, `buildPaletteCorpus`, `CommandPalette` and `parseSlashCommand`
against a macOS navigator — no live sidecar route or outside-world check backs any of
them. Per role instructions this shard never runs the full vitest suite; each entry's
pinning test file is confirmed present on the candidate source and cited as `ci_pinned`
(the heavy lane owns re-running it).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-016 | test file presence: `src/store/keybindings.test.ts`, `src/store/command-palette.test.ts` | both present on `4c6dfe8c`; batch-9 cert basis was Cmd+K→palette.open / remap to mod+p / typing-context skip, all asserted in these files | ci_pinned |
| R15-CODE-FRONTEND-016 | test file presence: `src/store/command-palette.test.ts` (dispatcher coverage of the 13 default action ids) | file present | ci_pinned |
| R15-UI-086 | test file presence: `src/store/command-palette.test.ts` (palette row labels incl. remap + Option+1 mac case) | file present | ci_pinned |
| R15-CROSS-PLATFORM-004 | test file presence: `src/store/command-palette.test.ts` (layout corpus, `MENU_PAYLOAD_TO_MODE` keys) | file present | ci_pinned |
| R15-UI-058 | test file presence: `src/components/SettingsPanel.test.tsx` (export/import round-trip, unknown-id drop) | file present | ci_pinned |
| R15-DATA-092 | test file presence: `src/lib/region.test.ts` (region hint derivation, `DEFAULT_REGION` fallback) | file present | ci_pinned |
| R15-UI-052 | test file presence: `src/components/OnboardingBanner.test.tsx`, `src/components/OnboardingFlow.test.tsx`, `src/store/onboarding.test.ts` (keyless/privacy copy) | files present | ci_pinned |

Excluded from this set (not certified in batch-9, so out of scope for a regression check):
R15-UI-027, R15-UI-018, R15-AGENT-088, R15-AGENT-082 (W1+W5 shared leg — see set-35).

Raw output: `battery/raw/set-39/*`.
