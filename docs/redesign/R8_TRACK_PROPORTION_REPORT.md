# R8 Track D — Proportion sweep report

Branch: `worktree-agent-r8-proportion`. Enforces `docs/redesign/R8_PROPORTION_LAW.md`
across every panel EXCEPT chat, settings, and research (other tracks own those).
Defect anchors: `R8_DEFECT_CATALOGUE.md` §D (D3, D5, D6, D10) + the mission's live
evidence at 1396px and 850–960px.

## Verification snapshot (run from this worktree)

- `pnpm test` — 1298 passed (0 failed)
- `pnpm lint` — 0 errors; 1 pre-existing warning (`EquityOverviewPanel.tsx`
  command-consumption effect, confirmed present at base `0171f65` — that block is
  owned by another track, untouched)
- `pnpm typecheck` — clean
- `pnpm format:check` — clean

## Commits

| sha       | scope                                                                                                                             |
| --------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `bc58953` | shared primitives — instrument-currency formatters, provider short forms, width hook, button icon ladder, DataTable caption cells |
| `63e1a72` | watchlist + portfolio + news — column tracks + drop ladders                                                                       |
| `a1c967b` | chart toolbar — symbol input floor, descender-safe timeframes, narrow collapse, canvas 11px floor                                 |
| `9b6b282` | notes — one 14px icon ladder, hairline group rules, chrome scope bar                                                              |
| `4242494` | equity overview — currency-by-instrument + autocomplete stuck-open fix                                                            |
| `e288aa7` | shared chrome — dockview tab token, tab ellipsis, overflow affordance                                                             |
| `a9210a7` | sweep — audit-log micro/uppercase fix, node param inputs                                                                          |
| `819c8c8` | prettier pass                                                                                                                     |
| `cb41a57` | watchlist chip-drop threshold correction + chip wrap fallback                                                                     |

## Per-surface change list

### Shared primitives (`bc58953`, `819c8c8`)

- `src/lib/format.ts:45` — `resolveCurrency()`; `formatMoney` (:65),
  `formatCompactMoney` (:102), `formatSignedMoney` (:114), `currencyAffix` (:79)
  accept the INSTRUMENT's ISO-4217 code (law §6); omitted → region default,
  byte-identical for legacy call sites.
- `src/lib/format.ts:250` — `providerShortLabel()` designed short forms
  (yfinance→YF, sec.gov→SEC, …; law §3.1 — fixed at the formatter, not CSS).
- `src/lib/use-container-width.ts` — ResizeObserver width seam for the §3.2/§3.4
  collapse ladders (integer-snapped, null until first measure).
- `src/components/DataBadges.tsx:24,46` — ProvenanceBadge renders the short form,
  `shrink-0 whitespace-nowrap` (drops/wraps whole, never clips); full provider id
  stays in the tooltip.
- `src/components/ui/button.tsx:13` — default svg size in the 32px tier 16→14px
  (law §2 icon ladder); the 24px tier was already 12px; explicit `size-4` still
  wins for primary actions. NOTE: shared component — chat/settings buttons render
  14px icons too unless they pass an explicit size (law-intended).
- `src/components/DataTable.tsx:169` — body cells `text-body`→`text-caption`
  (law §1 data-cell step). Applies to every DataTable consumer (watchlist,
  portfolio, screener, equity statements/fundamentals, SEC, greeks, earnings,
  analyst).

### Watchlist (`63e1a72`, `cb41a57`)

- `src/modules/watchlist/WatchlistPanel.tsx:27-43` — explicit tracks: price
  6.5rem / change 5.25rem / action 3rem, symbol = the one flexible track; the
  cells' px-3 padding is the ≥8px gutter. Price/change collision impossible by
  construction (table-fixed + px tracks + nowrap numerics).
- `:269-272` — measured drop ladder: provenance/freshness chips drop whole
  <340px, change% drops <300px, price always survives (law §3.2 priority).
- `:69-77` (SymbolCell) — chips row `flex-wrap` + whole-chip drops; symbol at the
  caption data step.
- `:328-339` — "Add symbol" placeholder shortened + `truncate` (honest ellipsis);
  the add affordance was already an icon button (Plus, 24px).
- Skeleton colgroup mirrors the live tracks (`:434-441`).

### Portfolio (`63e1a72`)

- `src/modules/portfolio/PortfolioPanel.tsx:50-62` — px tracks
  (`HOLDING_TRACKS`) + drop ladder: weight <680, cost <620, price <540, qty <460;
  symbol/mkt-val/P&L/actions always survive.
- `:744-770` — the `min-w-[680px]`-inside-`overflow-x-hidden` clip contradiction
  removed; columns drop whole instead.

### News (`63e1a72`)

- `src/modules/news/NewsFeedPanel.tsx:126` — meta row `flex-wrap` + `gap-y-1`:
  wraps to a second line instead of clipping vertically; source truncates
  honestly with a flex-basis floor.
- `:68-90` — sentiment chip `shrink-0 whitespace-nowrap`, dot `shrink-0`, score
  `tabular-nums` — aligned and shrink-proof.

### Chart (`a1c967b`)

- `src/modules/chart/ChartPanel.tsx:1081` — symbol input h-6 w-24 → **h-7
  `w-[7.5rem] min-w-[7.5rem]`** ("SAKSOFT.NS" never clips — law §2).
- `:1092-1140` — timeframes: segmented buttons move from fixed `h-6` to
  `min-h-6 px-2 py-1` (descender-safe by construction, law §3.3); below 700px
  measured toolbar width (`:78`, `:246`) the control collapses to a compact h-7
  dropdown (law §3.4) so the toolbar never starves into a third row.
- `src/modules/chart/toolbar.tsx:258,335` — indicator-search + compare inputs to
  the h-7 toolbar-field rung; compare "Add" stays a nowrap h-6 chrome button.
- `src/modules/chart/drawings/renderers.ts:184,219` — canvas fib labels 10px→11px
  (the floor applies to canvas text).
- Session label / status cluster verified: no fixed height, `min-w-0` + truncate
  on user content only.

### Notes (`9b6b282`)

- `src/modules/notes/NotesToolbar.tsx:109` — ONE icon ladder: all toolbar icons
  14px inside 32px controls; `:118-122` hairline `GroupRule` between groups;
  `:153` `min-h-12` + wrap (second row, never clip).
- `src/modules/notes/NotesPanel.tsx:263` — header pencil reconciled to 14px;
  export buttons ride the Button default (now 14px).
- `:314` — scope-chip bar on the §4 chrome rhythm (`gap-1.5`).

### Equity Overview (`4242494`)

- `src/modules/equity-overview/EquityOverviewPanel.tsx:55-58, 712-715` — money
  fields format in `fundamentals.currency ?? quote.currency` (no ₹ on AAPL —
  D10), fixed at the formatter seam, threaded through `formatField`.
- `:518-522, 586-598, 607, 761-770` — autocomplete can no longer stick open:
  (a) re-open is focus-gated (a debounced response landing after blur stays
  closed), (b) a programmatic draft write (selection / quick-load / external
  open-company command) suppresses the next autocomplete pass — this was the
  actual stuck-open mechanism: picking a candidate re-queried its own symbol and
  re-opened the list. Escape/blur/selection all close. The command-consumption
  `useEffect` (now `:715-726`) was NOT modified (other track owns it; `doLoad`
  internals carry the fix).
- Metric tables: ride DataTable → caption data cells per §4; statement tables and
  fundamentals unchanged structurally (already px/percent tracks + honest
  truncation on the label column only).

### Shared chrome (`e288aa7`)

- `src/app/globals.css:370` — `--dv-tab-font-size: var(--text-caption)` (token,
  not a literal).
- `:394-399` — dockview's tab label node gets `overflow:hidden` +
  `text-overflow:ellipsis` (the library sets text-overflow on the parent only,
  so squeezed tabs hard-clipped "Portfol"); the 96px tab min-width floor stays.
- `:401-431` — tabs-overflow control is a real affordance: 24px chip, micro
  token, chevron + count + `" more"` (`::after`), hover step, pointer cursor —
  not the bare ">18".

### Sweep (`a9210a7`) — marketplace, screener, backtest, macro, greeks, node editor, agent builder, broker, SEC, pricers, audit

- `src/modules/safety/AuditLogViewer.tsx:155` — the audit table inherited
  `text-micro` (11px + the utility's forced UPPERCASE — payload JSON rendered
  uppercase); body → caption data step, headers keep micro; `:145-150`
  filter-miss state → shared dense EmptyState. ch-based column tracks + honest
  payload truncation verified (`:147-163, 206`).
- `src/modules/node-editor/code-node-inspector.tsx:129` — sample-value inputs
  micro→caption (micro's uppercase transform was rewriting typed values).
- **Backtest trade-table price clip: verified still dead** —
  `src/modules/backtest/BacktestResultView.tsx:236-238` (auto table layout +
  per-cell `whitespace-nowrap` + `overflow-x-auto`; no fixed colgroup).
- Verified compliant, no change needed: marketplace (micro chips/captions ≥11px,
  h-8 credential inputs, EmptyState-pattern states), screener (h-8 criteria
  controls; results on px tracks with honest horizontal scroll at min-w-920),
  macro (EmptyState everywhere, h-8 picker), greeks/option/bond/yield pricers
  (h-8 aside forms, h-8 segmented controls, DataTable results), node editor
  (h-8/h-7 controls, micro truncation only on user content), agent builder
  (h-8 ladder, micro eyebrow labels + caption hints, error strings honest),
  broker connect/order entry (h-8 forms, micro eyebrows, FR-041 badges),
  SEC filings (DataTable tracks + honest truncation), plugin manager (tokens,
  h-8 toggle, micro state chips).
- Repo-wide sub-11px audit in scope: only the two canvas 10px labels (fixed
  above). `text-[10px]` exists ONLY under `plugins/tradesa-v2/**` — outside this
  track's scope (see NEEDS-MANUAL-CHECK).

## Formatter tests

- `src/lib/format.test.ts` — 30 tests total; **8 new**: 4 currency-by-instrument
  (`formatMoney`/`formatCompactMoney` with USD/INR/EUR/JPY, the D10 ₹4.27T case,
  null/blank/garbage fallback, lowercase normalisation), 1 signed-money currency
  threading, 3 `providerShortLabel` (designed short forms, case/whitespace
  insensitivity, unknown pass-through).
- `src/components/DataBadges.test.tsx` — +1 (short form renders, full id in
  title).
- `src/modules/equity-overview/EquityOverviewPanel.test.tsx` — +2 (INR
  instrument renders ₹ magnitudes; selection closes the dropdown and it STAYS
  closed across the debounce window).
- `src/modules/watchlist/WatchlistPanel.test.tsx` — provenance assertion updated
  to the short form + tooltip.

## Panel × width verification matrix (for the lead's live-rig pass)

Drive each at the listed widths (panel width = the dockview leaf, not the
window; the 850–960px window puts the rail panels in the tight bands).

| Panel           | ~1396px window                  | 850–960px window                                     | Extra-narrow drag                   | Expect                                                                                          |
| --------------- | ------------------------------- | ---------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------- |
| Watchlist       | full: chips + change            | panel 300–340: chips gone, change present            | panel <300: change gone; <264 floor | price NEVER touches change; chips read "YF"/"EOD" whole                                         |
| Portfolio       | all 8 columns                   | panel 540–680: weight/cost drop                      | <540 price, <460 qty drop           | P&L + Mkt val always present; no horizontal clip                                                |
| News            | one-line meta                   | narrow: meta wraps to 2 lines                        | —                                   | sentiment chip whole + aligned; no vertical clip                                                |
| Chart           | segmented timeframes            | toolbar <700: timeframe dropdown                     | —                                   | "SAKSOFT.NS" fully visible in the symbol input; no descender clip on 1wk/1mo                    |
| Equity overview | AAPL → $ market cap             | RELIANCE → ₹                                         | —                                   | type "saksoft", click candidate → dropdown closes and stays closed; blur while loading → closed |
| Notes           | one toolbar row                 | toolbar wraps to 2 rows                              | —                                   | every icon 14px incl. header pencil                                                             |
| Tab strip       | full labels                     | squeezed: ellipsis ("Portfo…"), then "⌄ N more" chip | —                                   | no bare ">18"; tab font = caption                                                               |
| Audit log       | mixed-case payload JSON at 12px | same                                                 | —                                   | headers micro, cells caption                                                                    |
| Backtest        | trade table prices whole        | horizontal scroll if needed                          | —                                   | no mid-number clip                                                                              |

## NEEDS-MANUAL-CHECK

1. **`plugins/tradesa-v2/**`is saturated with`text-[10px]`** (≈30 instances
across MetaAgentsPanel/HealthPanel/PositionsPanel/BrainDecisionsPanel/
SentinelPanel/TradeHistoryPanel/SettingsPanel/TradesaBotStatusStrip) — below
the 11px floor, but `plugins/\*\*` is outside this track's declared scope.
   Needs an operator decision/own pass.
2. **Screener market-cap currency** — `ScreenerResultRow` carries no per-row
   currency, so cross-region screens render the region default symbol. Fixing
   honestly needs the sidecar to ship row currency; out of this track's reach.
3. **Backtest header money** (`BacktestResultView.tsx:60-67`) hardcodes USD —
   backtest capital is a synthetic USD-denominated input today; flagged, not
   changed.
4. **Button icon-size ladder is a shared-chrome change** — chat/settings (other
   tracks) will see 14px icons in 32px buttons unless they pass explicit sizes.
   Law-intended, but the lead should eyeball both surfaces after merge.
5. **Dockview overflow chip live render** — the "N more" affordance is CSS over
   the library's `[chevron][count]` markup (dockview-core 6.2.2,
   `tabOverflowControl.js`); verify on the rig that the chevron+text chip reads
   correctly with many tabs.
6. **Earnings + analyst-ratings panels** were NOT in this track's scope list and
   carry two hand-rolled `table-fixed` tables
   (`EarningsCalendarPanel.tsx:212,274`) — they looked law-clean on read, but
   nobody owns them this pass.
