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

### Team E (proportion track) — partition sweep, 2026-06-11

Wiring audit over the whole E partition (every module except chat/research; all
`src/components` except SettingsPanel; plugins): every `opensPanel` target
resolves to a registered panel id, every `PanelSpec.component` has a
`panelComponents` mapping (and vice versa), and every marketplace catalogue
`pluginId` resolves to a bundled plugin. No dead menu entries, orphaned panels,
or commands registered to missing panel ids found (the R7 "screener" drift
class is clear).

| Item | Verdict | Rationale |
|---|---|---|
| Tradesa amber CTA (`bg-amber-500` Open Settings / Save & Connect) + `shadow-sm` | **Fixed** (replaced) | Accent is reserved for live agent activity (R9 §4); CTAs now ride the shared monochrome Button primitive |
| Tradesa LLM-cost div-bar `bg-amber-500` fill | **Fixed** (neutral `charcoal-500`) | Data-vis bar shouting in the scarce accent — R9 §4 misuse |
| Tradesa dead type sizes (`text-xs/sm/base/lg/[11px]`, 35+41+15 call sites) | **Fixed** (mapped to §2 roles) | 12/14px die under the one-scale law |
| `broker-connect` chips `py-[1px]` (off-grid arbitrary) | **Fixed** (`py-0.5` micro-chip pattern) | §1 quarter-step is for optical gaps only |
| `TradesaSettingsDialog.openSettingsDialog` export (never imported) | **Kept, on record** | Documented future-glue seam (docstring: slash-command path deferred to v0.6.6, lead owns index.ts); not rendered UI, zero user-facing surface |
| `useMarketplaceStore.stateFor` selector (read only by tests) | **Kept, on record** | Test seam, not UI debris; killing it breaks the store contract tests for nothing |

No UI control in the partition is rendered without a working handler; nothing
further to kill.
