# R9 Track D — Settings rebuild — report

Branch: `worktree-agent-r9-settings` (5 commits + 2 merges of
`origin/worktree-agent-r9-tiers` — Team A's commits ride with their own SHAs, so
the lead's integration dedups cleanly). Everything below is pushed.

## What shipped

### D1 — the Research surface (V9)

`ResearchSection` rebuilt as TWO radio-clear tier cards on Team A's
`tier_a | tier_b` store contract; both cards keep their controls visible at all
times (the V9 cure — the tier surface IS the controls, nothing hides behind the
selection):

- **Tier A "Unlimited (Local)"** (default): managed SearXNG flow with a designed
  status chip (`searxngChipMeta`, test-pinned vocabulary: Docker not found /
  Not set up / Pulling / Starting / Ready / Error), a container health line, and
  ONE primary action per state — Set up → Stop (teardown), Retry on error,
  nothing while transitional. Docker-missing state keeps the honest copy + a
  plain-text install hint (no external nav). Whenever not READY the card shows
  the quiet truth line "Until set up, research uses limited keyless search."
- **Tier B "Hosted research model"**: OpenRouter key state via the SAME
  `provider-keys` probe + `KeyEntryDialog` as AI Providers (presence only, the
  value never enters frontend state); three per-stop rows (Normal / Deep /
  Ultra) rendering Team A's `RESEARCH_MODEL_OPTIONS` with the verified pricing
  hints as micro-text (`priceVerified: false` picks are suffixed "· estimate";
  a persisted custom slug stays selectable and says "Custom model — pricing on
  its OpenRouter page"). With no key the card shows the key CTA only — no dead
  selects.
- **SearXNG custom URL verdict: KEPT** — it is wired end-to-end (store →
  `X-Vysted-Searxng-Url` → sidecar resolution, under either tier per Team A's
  contract); demoted to a collapsed "Advanced: custom instance URL" disclosure.
- **No third anything**: keyless-tier UI (per-engine breaker line,
  `t1EngineStatusLine`, `/search/status` poll), BYOK hosted-scraper controls,
  the Exa-direct key card, and the redundant "Deep research" explainer card are
  gone.

### D2 — proportion rebuild (V4)

- Jump-nav collapse ladder: full → designed short labels (Providers / Research /
  Region / Keys / Advanced) → one "Sections ⋯" overflow menu. Gates re-pinned to
  MEASURED row widths (578px full / 432px short in uppercase JetBrains Mono
  micro); verified live at 1280/980 (full), 900 (short), 760 (overflow) —
  zero clip/wrap at every step (the first estimate, 440px, clipped at 530 — the
  capture round caught it). An 820px window sits within scrollbar-width of the
  440px short gate and renders short OR overflow depending on the rig — both
  steps fit, neither clips, so the ladder degrades safely either way (fix-round
  correction: the original "820 (short)" claim did not reproduce on the
  reviewer's rig).
- Provider rows on one designed slot grid (name+status flex, w-16 default slot,
  w-28 key slot, w-8 remove slot); SET DEFAULT is now the short form "Default"
  (button) / check+"Default" (active state) — never wraps, one column.
- Toggle switch retuned to reference proportions: 36×20 track, 16px thumb,
  32px hit area (the old 64×32 block died with the halved tokens).
- Model selects: raw-id fallback options run through `formatModelLabel`
  ("DeepSeek V4 Flash", never "DEEPSEEK-V4-FLA…").
- Section/subsection heads went quiet (no decorative icons; hierarchy by size +
  color). One icon step (`ICON_14`, the law's 14px) with a single `tokens-ok`
  justification line; partition audit = zero violations.
- Swept all five sections at 1280 + minimum panel width; the India region row
  fits. Keybinding rows ride a uniform per-CARD collapse ladder (fix round, see
  below): label column `flex-1` keeps every row's kbd/record cluster inline on
  one aligned column while the card is ≥576px; below that ALL rows stack the
  cluster under the label as a unit — row shapes never mix at any width.

### D3 — appearance knobs: KILLED (V6)

`accentIntensity` + `density` controls, store fields, blob fields, and tests are
gone; `setAll` silently drops them from older blobs.

### D4 — stray-item audit (round-trip truth)

Every remaining Settings control demonstrably round-trips. The grep-verified
verdicts (full table appended to `verification/R9_DEFECT_CATALOGUE.md`):

| Control                                                                                                | Verdict                                                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `paletteRecentsEnabled`, `paletteScopedToPanel`                                                        | KILLED — CommandPalette never read them                                                                                                                                                                                                                                                             |
| `starterCockpitPanelIds` (FR-032 picker)                                                               | KILLED — `config/default-layout.ts` is static, never read it                                                                                                                                                                                                                                        |
| `panelDefaults` (store-only seam)                                                                      | KILLED — no writer, no reader                                                                                                                                                                                                                                                                       |
| `providerPreferenceOrder` + reorder group                                                              | KILLED — no picker consumes the order                                                                                                                                                                                                                                                               |
| Interface section + nav chip                                                                           | REMOVED — every control in it was dead                                                                                                                                                                                                                                                              |
| `defaultAgentId`                                                                                       | **FIXED** — `setDefaultAgentId` applies to `store/active-agent` immediately; the FIRST `setAll` (boot restore) seeds the lens; later restores/imports do NOT yank a live session (applies next session). Explicit raw-chat persists as `RAW_CHAT_SENTINEL`; a legacy dead `null` coerces to Copilot |
| Region / default provider / default model / key rows / keybindings / modules / layouts / export-import | round-trip verified, kept                                                                                                                                                                                                                                                                           |

## Gates (in-worktree, post-merge of Team A's branch)

- vitest: **141 files / 1386 tests, all green** (my partition:
  `SettingsPanel.test.tsx` 34 + `settings.test.ts` 12 = 46).
- `tsc --noEmit` green; eslint clean (one PRE-EXISTING warning in Team E's
  `EquityOverviewPanel.tsx`); `audit-design-tokens.mjs` — **zero violations on
  the partition** (`SettingsPanel.tsx`, `store/settings.ts`).
- Visual self-check (headless Chrome on :5175, sections at 1280 + min panel
  width + ladder states + sub-minimum squeezes):
  `docs/redesign/verification/r9/settings/`.

## Cross-partition touches (lead: prefer the owner's version on conflict)

1. `src/lib/workspace.test.ts` — settings round-trip test swapped to surviving
   fields (killed fields broke it); merged cleanly with Team A's searchSettings
   tests. Plus one type-only cast fix (`as unknown as`) in their new test.
2. `src/store/search-settings.test.ts` — same one-line type-only cast fix.
3. `src/app/page.tsx` — autosave subscription `state.tier` → `state.researchTier`
   (the legacy field died with Team A's contract; one line, tree-green unblock).

## NEEDS-MANUAL-CHECK

1. **Tier B configured-state visuals in the real shell** — headless browser has
   no OS keychain, so captures show the honest "couldn't check the keychain" +
   key-CTA branch; the configured branch (key line + three priced model rows) is
   test-pinned but needs one eyeball in the Tauri app with a real key.
2. **Orphaned Exa keychain entry** — a previously stored
   `plugin-secret:vysted-search-exa:exa_api_key` secret now has no UI delete
   path (the Exa lane is dead). Decide: one-time cleanup note in release notes,
   or a lead-owned migration sweep.
3. **`prettier --check .` fails on 8 PRE-EXISTING files** from the 004/tiers
   baseline (R9 docs + `scripts/audit-design-tokens.mjs`) — not formatted here
   to avoid cross-partition churn; the lead should format at integration.
4. **Starter-cockpit / palette preferences are gone** — if the operator wants
   them back they must arrive WITH consumers (Team E's CommandPalette /
   `config/default-layout.ts`), per the works-perfectly-or-dies rule.
5. Dev-rig note: Vite under `.claude/worktrees/` does not hot-reload (chokidar
   ignores dot-directories) — restart the server to pick up edits.

## Fix round (adversarial review blocker)

**Blocker:** at 1280 (Settings solo) the keybindings card mixed row shapes —
rows with long descriptions wrapped their kbd/Record/reset cluster onto a
second line while short rows kept it inline-right, breaking D2's row-to-row
control-column alignment. Mechanism: the row was `flex-wrap` and the label div
had no `flex-1`, so its flex base size was the description's max-content width
(~525px for the old 70-char Edit-panel copy) and the row wrapped before the
description's own `truncate` could ever engage.

**Fix (both halves of the reviewer's prescription, done uniformly per card):**

1. `SettingsPanel.tsx` — the keybindings `Card` is now a `@container`; the
   label column is `flex-1` (basis-0, so its copy never decides the wrap
   point) with `@max-[576px]:basis-full` (below 576px card width ALL rows
   stack the cluster under the label as a unit, ml-auto right-aligned). Row
   shapes are uniform at every width; `truncate` is the genuine last resort
   at sub-stack starvation. Container-query variant follows the
   `brief-blocks.tsx` precedent; audit script stays clean.
2. `store/keybindings.ts` — designed short descriptions for the four
   over-budget actions (all defaults now ≤43 chars, fitting the stacked
   min-width row with zero truncation; the old copy truncated mid-word in the
   previous min capture): "Switch to read-only Ask mode." / "Switch to
   single-panel Edit mode." / "Switch to multi-panel Build mode." / "Switch to
   autonomous Delegate mode." / "Show or fully hide the agent column."

**Pins:** `SettingsPanel.test.tsx` asserts every keybinding row's label column
is `flex-1 min-w-0`; `keybindings.test.ts` pins the copy budget (description +
non-mac formatted combo ≤56 chars for the inline state, description alone ≤43
for the stacked state).

**Evidence (headless Chrome CDP, Settings solo'd by closing the other tabs,
per-row `getBoundingClientRect` + `scrollWidth` audit):**

- 1280 (card 622px): 15/15 rows inline, clusters on one right column, zero
  truncation → `1280-keybindings.png` (REPLACES the defective capture the
  reviewer cited).
- 760 with agent column (card 377px): 15/15 rows uniformly stacked, zero
  truncation → `min-keybindings.png` (the previous capture truncated
  mid-word: "surgical chan…").
- 460, agent column hidden (card 399px): 15/15 uniformly stacked, zero
  truncation → `460-narrow-keybindings.png` (new).
