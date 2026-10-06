# batch-9/W5-frontend-shell (shard rc1-battery-17)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Frontend-store/UI-copy entries; no
sidecar round-trip applies to any of these (verified via pinned vitest + live source read).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-016 | Pinned vitest `keybindings.test.ts:283 describe("resolveKeyboardAction — the one dispatcher's resolution (R15-UI-016 / R15-CODE-FRONTEND-016)")`. | Test present, unmodified: a single dispatcher resolves all 13 default ids incl. `palette.open`, `save/load workspace`, `open chart/watchlist/news/portfolio/settings`. | ci_pinned |
| R15-CODE-FRONTEND-016 | Same pinned describe block as UI-016 (both fixed by the same one-dispatcher change). | Same evidence. | ci_pinned |
| R15-UI-086 | Pinned vitest `CommandPalette.test.tsx:170 "an action row shows its current (remapped) chord as a <kbd> (R15-UI-086)"`. | Test present, unmodified. | ci_pinned |
| R15-CROSS-PLATFORM-004 | Pinned vitest `command-palette.test.ts:358` (routing-contract pin) + live source grep of `src/store/command-palette.ts`: `MENU_PAYLOAD_TO_MODE` keys generate `"Layout: …"` palette rows for every mode incl. `default` (reset), independent of the macOS-only native menu. | Test present; source shows the 5 Layout rows generated from the same `MENU_PAYLOAD_TO_MODE` map the Mac menu uses, reachable via the command palette on any OS. | ci_pinned |
| R15-UI-058 | Pinned vitest `SettingsPanel.test.tsx:362-471` (Import gating + SettingsExport v2 block, incl. `:451` searxngUrl preserve and `:471` region hint) + `settings.test.ts:134`, `search-settings.test.ts:243`, `keybindings.test.ts:85,94` (all tagged R15-UI-058: setAll/merge preserves current state on a partial bundle, rejects unknown action ids). | All 5 pinned tests present, unmodified, cover export v2 field completeness and import merge/reject semantics from the register repro. | ci_pinned |
| R15-DATA-092 | Pinned vitest `region.test.ts` (`DEFAULT_REGION is India`, `regionConfig falls back to DEFAULT_REGION`) + live source grep: `region.ts:39 export const DEFAULT_REGION: Region = "IN"`; `SettingsPanel.tsx:1429 hint={\`Defaults to ${regionConfig(DEFAULT_REGION).label}.\`}` (renders "Defaults to India"), `:1427` hint text now states region affects the sidecar request, not just number formatting. | Source confirms dynamic, correct hint copy; tests pin the fallback behaviour. | holds (source-verified) / ci_pinned (behavioural fallback) |
| R15-UI-052 | Pinned vitest `OnboardingFlow.test.tsx:50 describe("OnboardingFlow welcome step (R15-UI-052)")` + `OnboardingBanner.test.tsx:57 "does not claim nothing leaves the machine"` + live source grep: `OnboardingFlow.tsx:241` now says "Live quotes, charts, news and screeners run right now" (dropped "web research"); `:233` and `OnboardingBanner.tsx:68-69` state "market data and web searches go to public providers"; `:260` local-model card states it "still reaches out for market data and web searches". | Source confirms the false "no web research without a key" and "fully private/offline" claims are gone; copy is now accurate. | holds (source-verified) / ci_pinned |

Raw: `battery/raw/set-38/<id>.txt` for all 7 ids.

COVERAGE: 7/7 ids raw; no raw: none.
