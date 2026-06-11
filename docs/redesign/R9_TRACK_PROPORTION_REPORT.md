# R9 Track E — Proportion sweep report

Branch `worktree-agent-r9-proportion`. Partition: every visual surface except
`src/modules/chat/**`, `src/modules/research/**` (Team C) and
`SettingsPanel.tsx`/`settings.ts` (Team D). All work re-tunes to the restored
standard Tailwind spacing semantics (R9_DESIGN_SYSTEM.md §0) — the old look was
the bug.

## Gate snapshot (in-worktree, at close)

| Gate                                   | Result                                                                                                          |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `node scripts/audit-design-tokens.mjs` | **clean for the E partition** — every remaining violation (62) lives in chat/research/SettingsPanel (Teams C/D) |
| vitest (full suite)                    | **141 files / 1378 tests, all green**                                                                           |
| `pnpm lint`                            | green                                                                                                           |
| `pnpm format:check`                    | green (one chore commit prettied pre-existing doc warns from the foundation commits)                            |
| `pnpm typecheck`                       | green                                                                                                           |
| Captures                               | headless Chrome (CDP-driven palette) at 1280 + 960 → `verification/r9/proportion/`                              |

## Per-surface checklist

Conventions used throughout: h-6 chrome / h-7 toolbar / h-8 form control rungs;
12px icons in h-6, 14px in h-7/h-8 (16px stays composer-only); micro chips
`px-1 py-0.5`; 28px data rows (`py-1` cells); 8px-grid gaps; scroll caps and
canvas heights carry `tokens-ok` layout justifications.

### E1 — Chart toolbar (prior session, V3)

- [x] One h-7 row at every width; fixed `w-[8.5rem]` symbol input; labeled Load;
      segmented timeframe; Draw/Indicators/Compare/Sync on one 14px ladder.
- [x] Declared collapse ladder: segmented→dropdown (1020), labels→icons (800),
      overflow ⋯ (460). Captures: `chart-toolbar-*.png`.

### E2 — Surfaces (this session unless noted)

- [x] **Notes** (prior session, V5) — one h-7/14px icon ladder; `notes-1280.png`.
- [x] **Shell chrome + dockview tabs** (prior session, V7) — `minimumTabWidth`,
      `dockview-tabs-overflow-*.png`.
- [x] **Data surfaces** (prior session) — watchlist, screener, equity overview,
      macro, sec, news, earnings, analyst ratings: 28px rows, button-guard icons.
- [x] **Portfolio** — header switcher/rename join the h-7 toolbar rung beside the
      size-7 icon buttons (no staggered header); Briefcase drops 16px→14px; the
      Add/Save submit + cancel join the h-8 form inputs; error dismiss is a real
      icon-xs button. Visible in `default-cockpit-1280.png` / `order-entry-1280.png`.
- [x] **Backtest** — trade-log cells on the py-1 28px rung with 12px sort glyphs;
      rail gaps to the 8px grid; strategy cards py-2; Run joins the h-8 rung.
      `backtest-1280.png`, `backtest-960.png` (no clipped text at either).
- [x] **Node editor** — workflow-name input joins the h-7 toolbar; inspector
      Apply/Delete join its h-8 form; textarea min-heights snap to grid steps
      (`min-h-12/16/20/24`); palette cards 28px; run-overlay chips px-1; Run-again
      a 28px control. `node-editor-1280.png`, `node-editor-960.png`.
- [x] **Quant** (option pricer, bond pricer, yield curve, greeks) — submit
      buttons join the h-8 form rung; chart canvas + skeleton carry tokens-ok;
      date inputs ride full-width rail rows (never the 2-col grid — at the grid
      step the native calendar indicator clipped the year's last digit; the
      earlier px-2 inset was not enough and is reverted to the uniform px-3),
      with Volatility joining the full-width stack so the grid stays a clean
      2×2. Verified by live DOM measure: every date field ≥180px of text room
      for a ~51px dd/mm/yyyy. `option-pricer-1280.png`, `bond-pricer-1280.png`,
      `yield-curve-1280.png`, `greeks-dashboard-1280.png`.
- [x] **Broker connect + order entry** (visual only, §6.5 untouched) — status/
      mode/read-only/provenance chips on the px-1 py-0.5 micro pattern (the
      off-grid `py-[1px]` dies); kite banner icons on a shared 14px constant.
      Order-entry was already on the h-8 rung. `broker-connect-1280.png`,
      `order-entry-1280.png`.
- [x] **Marketplace** — action cluster + credential footer gap-2; state badge on
      the chip pattern; explicit icon sizes drop to the button guard;
      Save/Cancel join the h-8 credential inputs; skeletons on-grid.
      `marketplace-1280.png`, `marketplace-960.png`.
- [x] **Agent builder** — Save/Cancel join the h-8 form; prompt editor min-height
      snaps to the 96px step; spinner takes the guard's 14px.
      `agent-builder-1280.png`.
- [x] **Platform dialogs** — WorkspaceDialog inputs + footer actions on the h-8
      dialog-form rung; list gap-2 with a tokens-ok scroll cap.
      `workspace-dialog-1280.png`.
- [x] **Safety surfaces** — DisclaimerFlow TOS scroll cap justified;
      OrderConfirmationDialog + AuditLogViewer were already on the law
      (untouched — §6.5). `audit-log-1280.png`.
- [x] **tradesa-v2 plugin** (all ten components) — dead 12/14px sizes mapped to
      the §2 roles; containers sharp; chips on rounded-control px-1 py-0.5;
      confidence/cost bars h-1 sharp neutral tracks; table cells py-1 28px rows;
      settings dialog rebuilt on the form rung with shared Button primitives
      (amber CTA + shadow die); status-strip refresh icon 12px in its h-6 hit
      target. Tradesa panels need live Supabase creds — headless shows the
      PanelShell state UX only (see NEEDS-MANUAL-CHECK).
- [x] **ui primitives** (prior session) — button on the xs h-6 / sm h-7 /
      default h-8 three-rung ladder with 12/14px icon guards; dialog max-h
      viewport clamp justified.
- [x] **PanelHost min sizes re-checked** — the chart entry was re-tuned in the
      prior session (480→360 under the one-row toolbar); all other entries'
      rationale comments (aside widths w-72/w-80, criteria grid, tracks) still
      hold because the sweep changed control rungs and paddings, not structural
      widths. One observation filed under NEEDS-MANUAL-CHECK below.

### E3 — FRED copy (prior session, V8)

- [x] Keyless error is product copy (free key + where to get it + keyless
      alternatives); the env-var name never reaches the user; test asserts it.

### E4 — Stray-item audit

- [x] Wiring audit across the partition: every `opensPanel` target resolves;
      `PanelSpec.component` ⟷ `panelComponents` maps are complete both ways;
      every marketplace `pluginId` resolves to a bundled plugin. No dead menu
      entries / orphaned panels / drift-class commands found.
- [x] Kill-or-fix table appended to `verification/R9_DEFECT_CATALOGUE.md`
      (Team E section): 4 fixed (accent misuse ×2, dead type sizes, off-grid
      chips), 2 kept-on-record (documented seams, not UI debris).

## NEEDS-MANUAL-CHECK (live app)

1. **Tradesa-v2 populated states** — headless has no Supabase creds, so the
   captures show the PanelShell unauthenticated/empty UX. The table rows,
   confidence bars, cost rollup, and settings dialog need one live-app pass.
2. **dockview minimum enforcement below viewport budget** — at 1280 wide with
   the default cockpit + an extra quant tab, the active group renders ~460px,
   under option-pricer's declared 640 minimum (dockview lets groups compress
   when the sum of minimums exceeds the viewport). Inputs survive (the rail is
   fixed-width and date fields ride full rows) but the results column starves. Worth a
   lead-level look at whether minimums should clamp harder or the quant panels
   should declare a collapse ladder for the results column.
3. **Sidecar-dependent populated states** (screener results, audit-log rows,
   broker reads, backtest results/equity curve) — empty-state proportions are
   verified headless; populated-row rhythm needs the live rig per the standing
   "populated screenshots" rule.
4. **Reference side-by-side verdict** — per §6 of the design system, the
   fresh-context verifier judges these captures against Cursor/Linear; this
   report records implementation claims only.

## Commits (this session)

| Commit    | Surface                                     |
| --------- | ------------------------------------------- |
| `13be233` | portfolio                                   |
| `d51a153` | backtest                                    |
| `d39b1ee` | node editor                                 |
| `d25a9fb` | quant submit rungs + canvas tokens-ok       |
| `52bd93f` | broker-connect visual                       |
| `800bece` | marketplace                                 |
| `2800df1` | agent builder                               |
| `987eede` | platform dialogs + safety                   |
| `e4f1ec9` | tradesa-v2 (all components)                 |
| `c78235c` | chore: prettier over pre-existing doc warns |
| `de48fca` | quant date inset + capture pack             |
