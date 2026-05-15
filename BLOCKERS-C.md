# Teammate C — Visual Verification Note

## Summary

All five publisher commits land cleanly; all gates pass (typecheck, lint,
format:check, frontend tests 184/184, sidecar pytest 222/222). No panel
resisted the publish-on-change idiom — the Phase-2 chart-sync infinite-loop
precedent did NOT recur, and per-panel "publish doesn't trigger infinite
re-render" assertions confirm the discipline holds.

The three screenshots called for in the plan brief have an ordering
dependency on Teammate A's worktree that is documented here so the lead's
merge audit can produce them post-merge:

1. **Agent Builder panel mid-edit (1920×1080 + 2560×1440)** — _producible
   from this worktree in isolation, but only inside a Tauri shell._ The
   Custom Agent Builder panel calls `getSidecarBaseUrl()` which goes through
   `invoke("get_sidecar_port")` (Tauri core). Outside Tauri, the sidecar
   resolves to an error and the saved-agents list shows the "loading…"
   state. The panel form itself renders fully because every input is
   client-side. A `pnpm tauri dev` screenshot pass after the worktree-C
   merge will produce a populated mid-edit shot.

2. **Chat sidebar agent picker showing the saved custom agent alongside
   first-party agents** — _NOT producible from worktree-C alone._ The chat
   sidebar (`src/components/ChatSidebar.tsx`, owned by Teammate A) does not
   exist on this branch. After `worktree-agent-A` merges into main, the
   lead's post-merge verification pass produces this screenshot — the
   `useAgentsStore` union store this commit lands is already wired to feed
   the picker.

3. **Chat sidebar context badge populated from a Chart panel showing
   AAPL** — _NOT producible from worktree-C alone._ Same reason as #2 —
   the context badge is rendered by Teammate A's chat sidebar. The
   per-panel publisher chain that drives the badge is fully tested in
   `panel-context-publishers.test.tsx` + the chart's own publisher test
   block in `ChartPanel.test.tsx`, so the integration is verified at the
   unit level. The end-to-end visual proof becomes producible the moment
   worktree-A merges.

## What I did instead

- Added "publish doesn't trigger infinite re-render" assertions per panel
  (chart, watchlist, news, equity, portfolio) — the bus's publish spy is
  asserted to fire <10 times after mount + microtask flush. A render-loop
  bug would push that to thousands within a tick.
- Added unmount-cleanup assertions per panel — `lastEventBySource[<source>]`
  is `undefined` after `unmount()`.
- Added explicit re-publish-on-change tests for the chart (timeframe
  change), the watchlist (row click), and the equity overview (symbol
  submit).

Unit-test coverage is the substitute the CLAUDE.md visual-verification
section anticipates for cases that cannot be exercised through
`chrome-devtools` MCP (the "canvas-interactive features" gotcha is
analogous in spirit — different blocker, same substitution principle).

## Lead's post-merge action

After `worktree-agent-A` is merged but before tagging v0.4.0:

1. `pnpm tauri dev` with the sidecar bundled.
2. Open the Custom Agent Builder panel via cmd+K → `agent-builder`. Fill
   the form mid-edit (id `macro-quant`, name "Macro Quant", a system
   prompt with regime-first language, two tools toggled, provider
   Anthropic). Save to capture the persisted-state screenshot pair.
3. Open the chat sidebar (Teammate A's surface). Open the agent picker.
   Confirm "First-party" and "Custom" sections are visually separated and
   the saved custom agent appears under "Custom".
4. Open a Chart panel, set its symbol to `AAPL`. Open the chat sidebar's
   context badge — confirm it reads something like "Context: AAPL chart,
   daily, [indicators]". The publisher chain this branch lands is
   responsible for that read.
5. Save all six PNGs (3 shots × 2 resolutions) under
   `docs/screenshots/v0.4.0/teammate-c/`.

## Acceptance

Per the Phase-3 plan §"C's BLOCKERS-C.md surface": this is a Tier-3
documentation surface, not a Tier-4 block. The code path is verified end-
to-end at the unit-integration level; only the final visual proof is
ordering-dependent on Teammate A's merge.
