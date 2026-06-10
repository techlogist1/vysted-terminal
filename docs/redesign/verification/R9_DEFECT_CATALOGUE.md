# R9 Defect Catalogue

Numbered, with owner team and root cause where known. Baseline captures (pre-token-flip):
`verification/r9/00-baseline/`. The operator's evidence pack (R9 brief) is the source for
V2–V9; planning-session live observation confirmed V2/V3 on screen.

| # | Defect | Root cause / evidence | Team |
|---|--------|----------------------|------|
| V1 | **Spacing convention split** — h-6=12px, h-7=28px, h-8=16px rendered simultaneously; 1,897 halved vs 51 standard call sites | R4 `--spacing-N` overrides (D26, fixed in tokens at 5636e7b); every surface must re-tune | ALL (E sweeps non-chat/settings) |
| V2 | Composer: five-chip strip below input; dot-touches-pill on NORMAL; cramped depth selector; bloated meta row | ComposerMetaRow.tsx (R8 design, now off-reference); halved tokens distorted every chip | C |
| V3 | Chart toolbar: symbol input flex-greedy (~250px for "SPY"), Load button h-6-tiny, timeframe dropdown oversized, two-row sprawl at panel widths | ChartPanel.tsx:200-260 toolbar row; mixed conventions + no fixed symbol width | E |
| V4 | Settings: section chips clip/wrap (AI PROVIDERS / RESEARCH / REGION & LOCALE); India region field clips; dropdown text truncates mid-word; SET DEFAULT wraps; model rows truncate ("DEEPSEEK-V4-FLA…") | SettingsPanel.tsx; h-8 controls rendered 16px under halved tokens → clipped descenders; no designed short forms at some collapse steps | D |
| V5 | Notes toolbar icon ladder broken (giant pencil vs tiny printer) despite R8 "one ladder" claim | h-8 (16px rendered) vs h-6 (12px rendered) buttons mixing both conventions — V1 expression | E |
| V6 | Appearance "accent intensity" + "density" knobs are dead UI — written to store/blob, read by nothing | src/store/settings.ts:33-50; no render consumer (verified by grep) | D (verdict: kill — see brief) |
| V7 | Dockview tab fragments: squeezed tab renders 2–3 chars beside overflow chip | R8 known-remaining; needs minimumTabWidth-class fix in PanelHost/globals dockview block | E |
| V8 | FRED keyless error copy names `FRED_API_KEY` env var — dev-flavored | R8 NEEDS-MANUAL-CHECK #4 | E |
| V9 | Research tier controls undiscoverable post-R8 (operator could not find them); three-tier model is settings noise | Settings Research section; architecture defect — R9 collapses to two tiers | A (contract) + D (surface) |
| V10 | SAKSOFT deep run: Q4 FY26 figures "not parsed" from primary board-outcome filing while secondary sources carried them | extract.py page-selection/format gap; live diagnosis agent running — findings to Team B at dispatch | B |
| V11 | Off-entity sources leak at low rates: Coromandel + Tea Post DRHP in SAKSOFT list; Nestle/Zomato cluster in ROUTE's | relevance.py entity gate scores partial-token matches above floor | B |
| V12 | ROUTE brief reported only the ₹2 final dividend from the filing, missed assembling ₹11/share FY total carried by its own secondary sources | iter.py synthesis transcribes primary filing literally; no cross-source assembly step | B |
| V13 | Keyless scraping + BYOK hosted-scraper visible as user tiers (settings noise; hand-rolled scrape loop can't beat research models) | R7 three-tier architecture — R9 model: two tiers, keyless = invisible bootstrap fallback with nudge banner | A |
| V14 | ULTRA cross-check can exceed its 240s lane on slow chat models and skips (honestly) | depth.py ultra profile wall; Tier B obsoletes for hosted runs; Tier A keeps honest skip + B may rebalance walls | B |
| V15 | Layout actions are template-static; "arrange my windows" ignores content (long brief ≠ dominant panel) | layout-templates.ts planLayout/planCustom have no content signals | Lead |

Kill-or-fix sweep (stray/vestigial items) runs per-partition during the pass; kill list
appended to this file by each team, verified live by the lead at gates.

## Kill list (appended during the pass)

### Team D (Settings) — settings-truth sweep

Verdict basis: a control that does not round-trip (change → persist → reload →
APPLIED) is theater. Each entry below was verified written-never-read by grep
over `src/` before the kill; old blob values are silently dropped on restore
(`settings.setAll` merges only surviving keys).

| Item | Evidence | Verdict |
|---|---|---|
| `themeKnobs.accentIntensity` + `themeKnobs.density` (Appearance group) | V6 — store fields written, zero render consumers | KILLED (controls, store fields, blob fields, tests) per brief D3 |
| `paletteRecentsEnabled` ("Show recent commands") | CommandPalette renders recents unconditionally from `store/command-palette`; never reads the flag | KILLED — wiring lives in Team E's CommandPalette.tsx (out of partition); control was theater |
| `paletteScopedToPanel` ("Scope to the focused panel first") | zero consumers anywhere | KILLED |
| `starterCockpitPanelIds` (Starter cockpit picker, FR-032) | `config/default-layout.ts` composes a static panel set; never reads the preference | KILLED — the picker promised a composition nothing honored |
| `panelDefaults` (store field, no UI) | no writer, no reader — stray store surface | KILLED |
| `providerPreferenceOrder` ("Provider preference order" group) | no picker consumes the order (ComposerMetaRow + Settings selects render the live provider list directly) | KILLED — resurrect only WITH a consuming picker |
| Interface section + nav chip | every control in it was dead after the above | REMOVED (section now: AI Providers · Research · Region & locale · Keybindings · Advanced) |
| `defaultAgentId` ("Default agent" select) | was written-never-read (active-agent store seeded statically) | FIXED, not killed — `settings.setDefaultAgentId` now applies to `store/active-agent` immediately and the boot restore seeds the lens; explicit raw-chat persists as a sentinel so a legacy dead `null` coerces to Copilot |

