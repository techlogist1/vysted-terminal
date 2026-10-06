# batch-9/W5-frontend-shell (rc1-battery-19, set-39)

Candidate: `1006c6da694ede5776c3dabbd27b305aeb56b5ad`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-016 | frontend-only (keydown dispatcher); source read + pinned tests named | `keybindings.ts` registerAction + global listener present; pinned tests cover "resolves every default id" and "remap fires only on new chord" | ci_pinned (keybindings.test.ts:284, :300) |
| R15-CODE-FRONTEND-016 | frontend-only, shares the same dispatcher as UI-016 | same source, same pinned test (fix_shape's exact acceptance criterion) | ci_pinned (keybindings.test.ts:284) |
| R15-UI-086 | frontend-only (palette row `<kbd>` render); source read + pinned test named | `PaletteItemRow` now renders the resolved binding; pinned test tagged with this register id | ci_pinned (CommandPalette.test.tsx:170) |
| R15-CROSS-PLATFORM-004 | frontend-only (palette layout-mode registry) + Rust `#[cfg(macos)]` gate (unexercisable either way on this Mac) | `dispatchLayoutMenuCommand` is now the one dispatch both the palette and the macOS menu route through; palette exposes all 5 modes (`MENU_PAYLOAD_TO_MODE`); Rust menu stays macOS-only by documented, unchanged design | ci_pinned (command-palette.test.ts:358, layout-templates.test.ts:553) |
| R15-UI-058 | frontend-only (settings export v2 / import merge); source + 4 explicitly-tagged pinned tests | export/import merge-over-current + reject-unknown-id behavior confirmed by 4 tests named `R15-UI-058` in their own titles | ci_pinned (keybindings.test.ts:85,94; settings.test.ts:134; SettingsPanel.test.tsx:451) |
| R15-DATA-092 | live source read (static copy + constant, no runtime branching) | `DEFAULT_REGION = "IN"`; Region hint now reads "Number formatting, plus which market's symbol resolver, trading calendar, macro/news providers and screener universe the sidecar uses."; row hint is `Defaults to ${regionConfig(DEFAULT_REGION).label}.` (derived, not hardcoded "United States") | holds |
| R15-UI-052 | live source read (static copy) | grep for the two false claims ("web research run right now", "fully private ... offline") returns 0 hits in OnboardingFlow/OnboardingBanner/ChatSidebar; surviving copy is scoped-true ("your keys, notes and portfolio stay on this machine"; web research gated behind adding a model) | holds |

Notes: the five UI/keybinding/palette entries are pure frontend logic needing a jsdom runtime to
exercise the actual dispatch; each is confirmed via source-line read of the fix_shape's exact
mechanism plus the pinned, already-committed vitest test (several explicitly tagged with the
register id in their own `it()` title) that encodes the original repro as its assertion, per the
task's ci_pinned carve-out. DATA-092 and UI-052 are pure static copy/config with no branching
logic, so they were confirmed directly by reading the shipped strings/constants at the candidate
sha (no runtime needed, no pinned-test dependency) — verdict `holds`, not `ci_pinned`.

COVERAGE: 7/7 ids raw; no raw: none.
