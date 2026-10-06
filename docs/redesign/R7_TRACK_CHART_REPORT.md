# R7 Track H — Chart Experience Report (worktree-agent-r7-chart)

The chart panel's three stacked toolbar rows of cryptic codes + the always-on
~50-entry indicator wall are gone. The surface is now ONE toolbar row — symbol
quick-load, the eight-step timeframe segmented control, four quiet disclosure
triggers (Draw / Indicators / Compare / Sync), active-state chips, and the
status cluster — with the reclaimed height handed to the canvas. Everything
the old surface could do remains reachable; nothing was amputated.
`src/lib/chart-theme.ts` was NOT touched (canvas palette stays in lockstep).

## Shipped (file:line)

| What                                                                                                          | Where                                                                            |
| ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Draw-tool catalog: full popover names + terse chip labels                                                     | `src/modules/chart/toolbar.tsx:41` (`DRAW_TOOLS`), `:55` (`DRAWING_CHIP_LABELS`) |
| `ToolbarDisclosure` — trigger + raised hairline popover, Escape (propagation-stopped) + click-outside dismiss | `src/modules/chart/toolbar.tsx:99`                                               |
| `DrawMenu` — ten tools spelled out, points-required meta                                                      | `src/modules/chart/toolbar.tsx:186`                                              |
| `IndicatorsMenu` — search input + six-category grouped `[x]`/`[ ]` toggle rows + Clear all                    | `src/modules/chart/toolbar.tsx:234`                                              |
| `CompareMenu` — symbol input + Add                                                                            | `src/modules/chart/toolbar.tsx:314`                                              |
| `SyncMenu` — Crosshair / Visible range / Symbol toggle rows                                                   | `src/modules/chart/toolbar.tsx:365`                                              |
| `menuLabel` (spelled-out name) on all 50 catalog entries                                                      | `src/modules/chart/indicators.ts:53` + catalog body                              |
| One toolbar row (symbol, timeframes, disclosures, chips, status)                                              | `src/modules/chart/ChartPanel.tsx:1048`                                          |
| Timeframe segmented control (all 8 intervals, bordered group)                                                 | `src/modules/chart/ChartPanel.tsx:1073`                                          |
| Armed-tool chip with live points-left countdown + `[x]` disarm                                                | `src/modules/chart/ChartPanel.tsx:1161`                                          |
| Comparison chip (no-data `!` flag, `%` normalize, remove)                                                     | `src/modules/chart/ChartPanel.tsx:1188`                                          |
| Earned indicator-chip row (exists ONLY when ≥1 active; carries computing/error/Retry)                         | `src/modules/chart/ChartPanel.tsx:1241`                                          |
| Indicator wall DELETED (no always-rendered grid remains)                                                      | `src/modules/chart/ChartPanel.tsx` (old lines 1322–1365 removed)                 |
| Drawings inspector — earned bottom row + `Clear drawings (n)`                                                 | `src/modules/chart/ChartPanel.tsx:1315`                                          |
| Disclosure/menu state + handlers (`handleMenuChange`, `onArmTool`, `onDisarmTool`, `clearAllIndicators`)      | `src/modules/chart/ChartPanel.tsx:232,962,981,1001,1009`                         |

Commits: `1b7012f` (catalog menuLabels), `eee0085` (toolbar + wall deletion + tests),
plus the docs commit carrying this report.

## Parity table — old control → new path

| Old control (verified live)                                                                                         | New path                                                                                                      |
| ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| Symbol input + `Load`                                                                                               | Unchanged — directly on the one toolbar row                                                                   |
| `1m 5m 15m 30m 1h 1d 1wk 1mo` buttons                                                                               | Unchanged — segmented control on the row (all 8)                                                              |
| `SYNC` `CX`                                                                                                         | Sync popover → "Crosshair" toggle (aria `Sync crosshair`)                                                     |
| `SYNC` `ZM`                                                                                                         | Sync popover → "Visible range" toggle (aria `Sync visibleRange`)                                              |
| `SYNC` `SY`                                                                                                         | Sync popover → "Symbol" toggle (aria `Sync symbol`)                                                           |
| `DRAW` `TREND`                                                                                                      | Draw popover → "Trendline" (chip stays "Trend")                                                               |
| `DRAW` `H-LINE`                                                                                                     | Draw popover → "Horizontal line"                                                                              |
| `DRAW` `V-LINE`                                                                                                     | Draw popover → "Vertical line"                                                                                |
| `DRAW` `RAY`                                                                                                        | Draw popover → "Ray"                                                                                          |
| `DRAW` `RECT`                                                                                                       | Draw popover → "Rectangle"                                                                                    |
| `DRAW` `ELLIPSE`                                                                                                    | Draw popover → "Ellipse"                                                                                      |
| `DRAW` `FIB RETR`                                                                                                   | Draw popover → "Fibonacci retracement"                                                                        |
| `DRAW` `FIB EXT`                                                                                                    | Draw popover → "Fibonacci extension"                                                                          |
| `DRAW` `CHANNEL`                                                                                                    | Draw popover → "Parallel channel"                                                                             |
| `DRAW` `TEXT`                                                                                                       | Draw popover → "Text label"                                                                                   |
| `clear (n)` drawings link                                                                                           | Drawings inspector row → `Clear drawings (n)`                                                                 |
| "click chart N more time(s)" hint                                                                                   | Armed-tool chip → "N points left" countdown + `[x]` disarm                                                    |
| `COMPARE` symbol input + `Add`                                                                                      | Compare popover → input + Add                                                                                 |
| Compare symbol readout + `!` no-data flag                                                                           | Comparison toolbar chip                                                                                       |
| `%` normalize toggle                                                                                                | On the comparison chip (aria `Normalize comparison`)                                                          |
| `×` remove comparison                                                                                               | On the comparison chip (aria `Remove comparison overlay`)                                                     |
| Indicator wall — all 50 toggles in 6 category sections                                                              | Indicators popover: search + the same 6 groups, every row a toggle with the spelled-out name (`menuLabel`)    |
| Indicator active state (pressed wall button)                                                                        | Removable chip on the earned row (terse label, `Remove <label>`) + `[x]` marker in the popover row            |
| `Clear (n)` indicators                                                                                              | Chip row `Clear all (n)` AND popover footer `Clear all indicators`                                            |
| `computing…` / error + `Retry` indicator status                                                                     | Earned chip row (aria `Retry indicators`)                                                                     |
| Status: symbol / `via provider` / staleness badge / session label                                                   | Unchanged — right-aligned cluster on the row                                                                  |
| Empty / loading / no-data states                                                                                    | Unchanged — quick-load affordance stays on the row; honest region-aware no-data message + Retry kept verbatim |
| Host command channels (symbol / indicators / comparison), sync bus, panel-context publish, drawings store reconcile | Untouched — state flow identical, only the surface changed                                                    |

Design conformance: popovers are `charcoal-875` (raised, one rung) + 1px
`--hairline-strong` border, 0 shadow; rows are 32px command rows, toolbar
controls 24px; hovers climb one luminance step (`875 → 850` inside popovers);
monochrome throughout (no peach — no live-agent activity here); ASCII `[x]`/`[ ]`
toggle markers; spelled-out words in popovers, terse chips in the toolbar.

## Verification (this worktree)

`pnpm typecheck` ✅ · `pnpm lint` ✅ (0 errors; one pre-existing warning in
equity-overview, not mine) · `pnpm vitest run src/modules/chart` ✅ 45/45
(plus the 3 external suites that reference the chart module: 29/29).

Key proofs in `src/modules/chart/ChartPanel.test.tsx`:

- `:306` wall-gone — with popovers closed, NO catalog toggle and no category
  header renders; no idle chip row.
- `:322` the popover lists the entire 50-entry catalog (enumerated from
  `INDICATOR_CATALOG`, count asserted `=== 50`) in all six groups.
- `:410` functionality-parity enumeration — every old control mapped to its
  new home (the 10 draw codes asserted against an explicit old→new table, all
  50 indicators, compare input+Add, the 3 sync flavors, 8 timeframes,
  symbol+Load).
- `:357` chip add/remove logic — adding RSI+MACD fetches `["macd","rsi"]`,
  removing the RSI chip prunes the fetch to `["macd"]`.
- `:381`/`:398` dismissal semantics — Escape closes the popover WITHOUT
  disarming the armed tool (propagation stopped); outside click closes.
- All prior data-wiring tests (Volume Profile / Parabolic SAR / Ichimoku
  attach+detach, sync bus, comparison overlay, panel-context publish) kept and
  rerouted through the popover click paths.

## For the lead to eyeball live

1. One row, no wrap at the default chart panel width; popovers overlay the
   canvas (z-order) and never clip at panel edges.
2. The canvas visibly gains the old wall's ~40% height; multi-pane indicators
   (RSI + MACD) still split panes correctly under the new layout.
3. Popover surface: raised + hairline, NO shadow; row hovers one step;
   focus lands in the Indicators search / Compare input on open.
4. Armed-tool flow on the real canvas: arm Trendline → chip counts 2→1 while
   clicking the chart → drawing commits → chip clears (jsdom can't click a
   real canvas).
5. Compare chip `%` toggle re-scales the overlay (left scale) without a blink
   (cache path), and the `!` flag on a junk symbol.
6. Earned rows appear/disappear without layout jump (indicator chips above
   the canvas, drawings inspector below).
7. Trigger count badges (`Indicators 2`, `Sync 1`) read correctly at 1920×1080
   and 2560×1440.
