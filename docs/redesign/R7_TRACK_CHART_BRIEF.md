# R7 Track H — Chart Experience Brief (worktree: worktree-agent-r7-chart)

Redesign the chart panel's surface to professional-product calm, inside THIS worktree only:
`~/Documents/dev/vysted-terminal/.claude/worktrees/r7-chart`. Branch `worktree-agent-r7-chart`.
NEVER write to the main repo path.

## Ground rules

- You OWN `src/modules/chart/**` ONLY (plus your own tests). Nothing else — not stores, not
  lib, not other modules, not globals.css, not tokens. If you need a shared change, append
  it to `docs/redesign/INTEGRATION_NOTES_R7_CHART.md` for the lead.
- Run `pnpm typecheck && pnpm lint && pnpm vitest run src/modules/chart` (worktree-local
  node_modules are installed) before each commit; `pnpm prettier --write` on changed files.
- Conventional commits per deliverable; push to `origin worktree-agent-r7-chart`.
- Design law: docs/redesign/VYSTED_DESIGN.md (read it). JetBrains Mono everywhere; surface
  ladder #0a0a0a→#242424; containers 0px, controls 4px/32px-or-24px; monochrome (peach =
  live agent activity ONLY); no shadows; type roles micro11/caption12/body13/title15/
  prose16; spacing tokens only.
- All existing functionality stays REACHABLE — this is disclosure, not amputation.

## The disease (verified live, screenshot 01-tab-Chart.png in main repo verification/r7/)

Three stacked toolbar rows of cryptic abbreviations:
`SPY | Load | 1m 5m 15m 30m 1h 1d 1wk 1mo | SYNC CX ZM SY` +
`DRAW | TREND H-LINE V-LINE RAY RECT ELLIPSE FIB RETR FIB EXT CHANNEL TEXT` +
`COMPARE | SYMBOL | Add` — and below the chart an always-visible INDICATOR WALL
(~25 indicators in a flat grid: moving averages, momentum, etc.) eating ~40% of the panel.

## The target (Cursor-grade: complex workspace, simple surface)

- ONE toolbar row: symbol + timeframe segmented control (the 8 timeframes stay — they're
  load-bearing for traders) + THREE quiet disclosure triggers: `Draw`, `Indicators`,
  `Compare` + the existing sync/status affordances consolidated.
- `Draw` opens a compact popover (raised surface, 1px hairline-strong border, command-row
  styling) listing the draw tools with their full names; selecting one arms it and shows a
  small active-tool chip in the toolbar with an [x] to disarm. Keyboard-dismissable.
- `Indicators` opens a popover with a search input + the indicator list grouped (Moving
  Averages / Momentum / Volatility / Volume...), each row a toggle; ACTIVE indicators
  render as small removable chips in the toolbar row (or a thin second row ONLY when ≥1
  active — an earned row, not idle chrome). The bottom indicator wall is DELETED.
- `Compare` opens a small popover with the symbol input + add.
- Spell words, not codes, in all popovers (the toolbar chips may stay terse: "1d", "MA 20").
- The chart canvas gets the reclaimed height. Keep `chart-theme.ts` canvas palette in
  lockstep (don't change its values).
- States: empty (no symbol) keeps the existing quick-load affordance; loading; no-data
  (the honest region-aware message stays).
- Sweat: hover states one luminance step; focus rings neutral; popovers raised+hairline,
  never shadowed; truncation never mid-word; row heights from the 32/24 ladder.

## Verification you must do yourself

This worktree can't run the live app — write/adjust component tests asserting: wall is
gone (no always-rendered indicator grid), popovers list every tool/indicator that the old
rows had (functionality parity — enumerate them in a test), active-chip add/remove logic.
Visual verification on the live app is the lead's; list what to eyeball in your final report.

## Done =

No stubs. typecheck/lint/tests green. Committed + pushed. Final report
`docs/redesign/R7_TRACK_CHART_REPORT.md`: shipped file:line, parity proof (old control →
new path table), what the lead should eyeball live.
