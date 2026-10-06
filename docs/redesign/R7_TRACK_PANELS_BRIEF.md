# R7 Track P — Panels Polish Brief (worktree: worktree-agent-r7-panels)

Bring every remaining panel to the design law with real product taste, inside THIS
worktree only: `~/Documents/dev/vysted-terminal/.claude/worktrees/r7-panels`. Branch
`worktree-agent-r7-panels`. NEVER write to the main repo path.

## Ground rules

- You OWN: `src/modules/{equity-overview,quant,macro,sec,earnings,analyst-ratings,news,marketplace,plugin-manager,portfolio,notes}/**` and `src/components/SettingsPanel.tsx` (+ its test). NOTHING else — chat/chart/screener/backtest/node-editor/watchlist belong to other tracks; shared components (DataTable, EmptyState, ui/\*, StatusChrome, PanelHost) are the lead's. Shared needs → `docs/redesign/INTEGRATION_NOTES_R7_PANELS.md`.
- Gates per commit: `pnpm typecheck && pnpm lint && pnpm vitest run <your modules>` + prettier on changed files. Full `pnpm test` at the end.
- Conventional commits per panel/deliverable; push to `origin worktree-agent-r7-panels`.
- Design law: docs/redesign/VYSTED_DESIGN.md — read it FULLY first. Mono everywhere; ladder #0a0a0a/#101010/#161616/#1d1d1d/#242424; containers 0px, controls 4px at 32/24px heights; monochrome (peach = live agent activity ONLY); P&L green/red only; type roles micro11/caption12/body13/title15/prose16/section18/overview22 ONLY (no text-[..] arbitrary); spacing tokens only; numerics right-aligned tabular via the shared format helpers; NO shadows; composed EmptyState (the shared component) for every empty/error state — never bare prose, never a spinner-as-empty-state.

## Verified defects to kill (from the live walkthrough — verification/r7/\*.png in the main repo)

- Greeks dashboard (quant): a small table stranded in a sea of dead space. REDESIGN the
  layout: inputs left rail, results as a proper metric grid that uses the width (per-greek
  cards or a full-width DataTable + a sensitivity read), composed empty state.
- Equity overview: instructional placeholder copy renders as primary content; header
  baseline mismatches; bring statements/sections to DataTable rhythm; composed empty state
  with the quick-load chips.
- Earnings + analyst-ratings: loading spinners masquerading as empty states; sparse grids.
- Marketplace + plugin-manager: micro-text (~8.8px chips) → text-micro 11px minimum;
  install rows to the 32/24 ladder; composed empty states.
- Settings panel: provider rows inconsistent (status text + buttons misaligned row to
  row); "OpenRouter (broker)" label is WRONG — it's not a broker; the page is a wall —
  group into sections with clear hierarchy (AI Providers / Web search / Research /
  Region & locale / Advanced), consistent 32px rows, readable toggles (no micro
  checkboxes). Keep every existing setting reachable and its store wiring intact.
- News/portfolio/macro/sec/notes: sweep for off-scale text, off-grid spacing, rounded
  containers, key-value dumps that should be tables, dead empty states, truncations.
- quant module broadly (option-pricer, bond-pricer, yield-curve): mixed input heights →
  32px standard; labels consistent; results tables right-aligned tabular; honest
  validation errors inline.

## Approach

Work panel by panel (one commit each): read the component fully, fix to the law, update
its tests. Where a surface needs real redesign (Greeks, Settings), sketch the layout in a
comment block at the top of the component first — structure, then polish. Preserve all
behavior and store contracts; presentation-only unless a defect is behavioral.

## Done =

All owned panels law-clean (run the binary audit greps from the design doc §16 on your
changed files: text-[ count 0, rounded-[ 0, shadow-\* 0, off-grid spacing reviewed), tests
green, committed + pushed, final report `docs/redesign/R7_TRACK_PANELS_REPORT.md` with
per-panel before/after notes + what the lead should eyeball live + NEEDS-MANUAL-CHECK.
