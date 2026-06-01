# Polish sweep report — the systematic bug-hunt (Pass A item 1)

_The primary pass: drive every surface like a senior product designer, find the whole class
of jank a user would hit, and fix it. Branch `001-agent-native-redesign`._

## Method + scale

A 17-agent read-only bug-hunt workflow (one agent per surface, ~1.12M tokens) judged every
panel, dialog, the agent dock, the command palette, and the panel-layout host against a
senior-designer bar (overlap / double-scroll / clipping / truncation that loses data /
mislabels / dead controls / weak empty-loading-error states / theme stragglers / responsive
breakage). It produced **202 findings (55 high, 92 medium, 55 low)**. The high + medium set
was then applied by **6 implementation teammates** over disjoint file clusters (core panels /
analysis panels / tools / dialogs / PanelHost / settings+dock) plus the lead, each verified
to tsc + eslint + the relevant tests; the lead integrated, fixed the cross-cutting test
fallout, and re-ran the full gate.

**Result: every high + the vast majority of medium findings fixed; the full suite is green
(tsc + eslint + prettier clean, vitest 744/744) and the app loads healthy with all fixes.**

## Seed bugs from the brief (all fixed + verified live)

| Seed                         | Root cause                                                                                   | Fix                                                                          | Verified                      |
| ---------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------- |
| Settings double-scroll       | dockview leaf `.dv-view` set `overflow:auto` at (0,3,0) specificity; the panel ALSO scrolled | a (0,4,0) themed selector forces `.dv-view` `overflow:hidden` → one scroller | live: `dvViewsScrolling=0`    |
| Panel-overlap not everywhere | only 5 panels had host-side min sizes                                                        | `PANEL_MIN_SIZE` expanded to 24 panels; post-restore snap on both axes       | min map covers every panel    |
| Stale `llama3.1:8b` model    | the model-override blob captured the then-default with no validation                         | trust-marker drop of legacy overrides on restore + known-model pruning       | live: dock reads `qwen2.5:7b` |
| Chart Retry no-op            | `setSymbol(s => s)` is an `Object.is` bail-out                                               | a `retryNonce` in the fetch-effect deps                                      | unit + the fetch reruns       |

## Headline fixes (highest-impact)

- **Working error recovery everywhere.** Dozens of panels had errors that dead-ended (or a
  Retry that did nothing). Every data panel now has a Retry that actually re-runs the fetch
  (chart, watchlist, news, equity-overview, portfolio, SEC ×3, screener, macro, earnings,
  marketplace, plugin-manager, backtest, node-editor) + the §6.5 dialogs (confirm-error Retry,
  ack-failure callout) + WorkspaceDialog.
- **Real empty + loading states.** Bare grey instruction lines → inviting empty states (icon
  - what-it-is + one action) and skeleton/“waiting” loading states (never a blank), across the
    panels that failed the standing requirement.
- **No data-loss collisions.** Dense numeric tables got `table-fixed` + an explicit `<colgroup>`
  - truncation (watchlist, portfolio, SEC insider, screener, backtest) — the "73,618.0256%"
    class of overlap can't recur. Three-way P&L coloring (0.0 is no longer rendered green).
- **Command palette (Raycast bar).** Title-over-subtitle ranking + a kind weight so typing
  "market" surfaces **Marketplace** above the Howard **Marks** / Mr. **Market** personas;
  character-level match highlighting; keyboard nav scrolls into view; better empty states.
- **Settings (Linear bar).** The Integrations broker list (a duplicate of the Marketplace)
  collapses to a CTA — one source of truth; distinct section icons; keybinding recorder can't
  strand; loading guard on the agent picker.
- **Agent dock.** The 4px drag-handle dead-zone is now a ~12px hit-target; the proposed-changes
  review can't push the composer off-screen; the "no key" badge is now an actionable button;
  transcript errors offer Retry.

## Per-surface disposition (high + medium)

| Surface cluster                                                   | Fixed | Notably skipped (reason)                                                               |
| ----------------------------------------------------------------- | ----- | -------------------------------------------------------------------------------------- |
| Chart / Watchlist / News / Equity / Portfolio                     | ~26   | — (chart min-height → PanelHost teammate)                                              |
| SEC / Screener / Macro / Earnings                                 | ~30   | YieldCurvePanel (in `quant/`, separate owner); a macro search-status (store change)    |
| Marketplace / Plugin Mgr / Agent Builder / Node Editor / Backtest | ~30   | PanelHost min-sizes (host teammate); node-editor canvas-interaction (needs Playwright) |
| Command palette + dialogs                                         | ~13   | WorkflowSaveDialog ESC (out of the dialog cluster's fence)                             |
| PanelHost min-sizes + placement                                   | full  | placement policy implemented by the lead in `store/workspace.ts:openPanel`             |
| Settings + agent dock + Tradesa V2                                | ~18   | settings min-size (host teammate, done)                                                |

## Guardrails during the sweep

- **§6.5 safety surfaces were PRESENTATION-only.** `OrderConfirmationDialog` and
  `DisclaimerFlow` got an elevated background, field truncation, a confirm-error Retry, and an
  ack-failure callout — the **mandatory review checkbox, the disabled-until-checked Confirm
  gate, the `data-testid`s, the ack/kill-switch wiring are untouched** (the teammate confirmed;
  vitest's safety-UI tests stay green). The Python §6.5 audit is independent and stays 9/9.
- **No LOCKED file touched.** Panel min-sizes stayed HOST-SIDE (`PanelHost`), never `PanelSpec`.
- No emoji introduced; the two stray emoji lock icons (🔒/🔓) were replaced with lucide icons.

## Evidence

- Gates: **tsc clean, eslint clean, prettier clean, vitest 744/744** after integration.
- Live (bridge, the display was asleep so verified via DOM — see PASS_A_REPORT §Verification
  constraint): app loads with **no Next error overlay**, all panels render, **0 ion-blue
  stragglers**, the kill-switch absent, the autonomy toggle present, Settings single-scroll.

## Deferred / follow-ups (ranked)

1. **Pixel screenshots** at 1920×1080 / 2560×1440 of the polished surfaces — capture when the
   display is awake (the rig can't paint an occluded webview). The app + rig are left running.
2. A small set of low-severity findings + the explicitly out-of-fence ones above (YieldCurve
   in `quant/`, WorkflowSaveDialog ESC, a macro search-status flag, node-editor canvas
   interactions needing Playwright). None are user-blocking.
3. A frontend⟺catalog parity check for `HOST_ACTION_NAMES` (noted in EXTENSION_SEAMS) so a new
   host-action can't silently miss the diff gate.
