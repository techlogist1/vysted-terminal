# RC1 owner-drive: portfolio-notes

Candidate: `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a` (branch `004-r4-experience-rebuild`)
Own sidecar: `127.0.0.1:52324`, seed data copied from `rc1-seed-data`.
Method: real `PortfolioPanel`/`NotesPanel`/`NotesToolbar` components mounted in jsdom via the census harness (`harness/portfolio.s2c.test.tsx`, `notes.s2c.test.tsx`, `toolbar.s2c.test.tsx`), driven against a live from-source sidecar, same requests/prompts as census where they exist. Plus direct code reads at the fix commits and direct curl/HTTP probes for the sidecar routes.

## Round 2 (gate round 2, candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`)

`git diff 4097dac4..4c6dfe8c` scoped to this group's surface shows exactly ONE relevant change: `src/modules/portfolio/PortfolioPanel.tsx` (+15/-1). Everything else the group covers (`sidecar/routers/portfolio.py`, `src/modules/notes/**`, `src/components/ConfirmButton.tsx`) has zero diff between the two candidates. The change is a direct fix for `rc1-drive-portfolio-notes:1` (the round-1 quote-refresh backlog defect below): a `quoteFetchInFlightRef` guard (mirroring `WatchlistPanel`'s existing `inFlightRef`) now skips a `setInterval` tick while the previous quote fan-out hasn't settled (`PortfolioPanel.tsx:194,229,250,269-271`). The fix's own new test names the finding directly: `"skips a quote-refresh tick while the previous fan-out is still in flight, then refetches once it settles (rc1-drive-portfolio-notes:1)"`.

Re-verification on my own sidecar (fresh `rc1-seed-data` copy, `127.0.0.1:52324`, `rc1-cand` worktree at `4c6dfe8c`): re-ran `PortfolioPanel.test.tsx` + all of `src/modules/notes/*.test.tsx` on the candidate — **65/65 pass**, including the new guard test (`round2-vitest-p8-fix-confirmed.log`). Live sidecar spot-checks against `:52324` repeat round 1's results unchanged: `GET /portfolio/positions` → `[]`/GET-only, `PUT`/`DELETE` → `405` (R15-CODE-PLATFORM-021 architecture change still holds, confirmed via `sidecar/routers/portfolio.py` — no diff since round 1). Since the fake-timer unit test directly exercises the exact interval-guard logic that produced the round-1 live wedge (same code path, same `setInterval`/`quoteFetchInFlightRef` mechanism), and the sidecar-side pieces are byte-identical to round 1, a full live 100-holding/9-unresolvable-symbol re-wedge was not re-run (would cost 4.5+ min against the 120s-per-call stall-watchdog rule for no additional evidence over the targeted test + code read). **P8 verdict: fixed, confirmed both by code read and by a live-mounted-component test exercising the exact guard.**

No other row in this group's scope changed. The round-1 table below stands as-is except the P8 row, updated inline.

## Scored table

| # | Interaction | Census | RC1 | Register id | Delta |
|---|---|---|---|---|---|
| P1 | Empty portfolio | ok | ok | - | unchanged |
| P2 | Form validation | partial | partial | R15-UI-078 | still open (form-path); agent-path negative-cost now blocked as a side effect of other host-actions.ts work |
| P3 | Populated P&L math | partial (fabricated ₹0 total on unresolved quotes) | ok | R15-UI-005 | **fixed** |
| P4 | Delete holding (non-active portfolio) | broken (stale closure) | ok | R15-UI-035 | **fixed** (harness needed a ConfirmButton double-click rewrite, unrelated new safety primitive, not a regression) |
| P6 | Mixed-currency CSV export | partial (no currency col, formula injection) | partial | R15-DATA-042 / R15-UI-079 | Currency column **fixed**; formula-injection **still open** |
| P7 | Quote transport failure | broken (₹0 fabricated) | ok | R15-UI-004 | **fixed** |
| P8 | 100-holding quote fan-out | ok (all 200, slow) | **ok (round 2, fixed)** | rc1-drive-portfolio-notes:1 | round 1: new_defect (unbounded backlog, no overlap guard); round 2 (4c6dfe8c): `quoteFetchInFlightRef` guard added, verified live-mounted test passes (65/65) |
| P9 | Agent get_portfolio / host actions | broken (no ids, intent gate strips delete) | ok | R15-AGENT-042 / R15-AGENT-019 | **fixed** |
| sidecar CRUD | write-only ledger, PUT/DELETE 405 | partial | GET-only by design | R15-CODE-PLATFORM-021 | architecture change (holdings truth moved to frontend store), confirmed intentional, not a regression |
| N1 | Note lifecycle (clear, fast scope-switch) | broken (stale-clear, lost fast-switch edit) | ok | R15-UI-001 | **fixed** |
| N2 | Agent write_note (append/keystroke race, mode-less, scope=global) | broken (clobbered, replaced, phantom ticker) | ok | R15-UI-001 / R15-CODE-FRONTEND-003 / R15-CODE-FRONTEND-014 | **fixed** |
| N3 | Huge note (1.97M chars) | ok | ok | - | unchanged |
| N4 | Prompt-injection note | ok (inert) | ok (inert) | - | unchanged |
| N5 | Slash menu | partial (Task List throws) | ok | R15-UI-024 | **fixed** |
| N5 | Wikilink menu (insert, live-add) | broken (escaped text, stale symbol list) | ok | R15-UI-024 | **fixed** |
| N6 | Export .md | partial | ok | - | unchanged (Blob-download fallback still intended outside Tauri) |
| Toolbar | Link insert | broken (window.prompt throws) | ok | R15-UI-025 | **fixed** |
| Toolbar | Insert [[wikilink]] on selection | broken (destroys selection) | ok | R15-UI-024 | **fixed** |
| Toolbar | H1-H3/bold/italic/code/lists/quote/code-block | ok | ok | - | unchanged |

## Census -> RC1 deltas (register-cited)

**Fixed, confirmed live + by code read:**
- R15-UI-005 -- `PortfolioPanel.tsx` totalValue/totalValueNote now publish `null` + a reason string instead of a fabricated ₹0.
- R15-UI-004 -- quote-transport-failure distinguishable from "symbol not found."
- R15-AGENT-042 -- `publishedHoldings` now carries `holdings[i].id` per row (comment cites R15-AGENT-042 directly).
- R15-AGENT-019 -- intent gate correctly classifies write/delete phrasings.
- R15-UI-035 -- `handleDelete` useCallback now depends on `active.id`; delete in a non-active portfolio works. Verified via ConfirmButton double-click (arm + confirm), a new unrelated safety primitive that required a harness rewrite but is not itself a regression.
- R15-DATA-042 -- CSV export now includes a Currency column.
- R15-UI-001 -- notes editor/store no longer drift: clearing persists, fast scope-switch-during-debounce no longer loses the edit, agent-appended text survives the user's next keystroke.
- R15-CODE-FRONTEND-003 -- mode-less `write_note` now defaults to append, not replace.
- R15-CODE-FRONTEND-014 -- `scope='global'` now maps to the General note, not a phantom GLOBAL ticker.
- R15-UI-024 -- Task List slash command registers and applies; wikilink insert-on-selection no longer destroys the selection; wikilink suggestion list picks up symbols added after mount.
- R15-UI-025 -- toolbar Link insert uses a popover, no longer throws without a stubbed `window.prompt`.
- R15-DATA-081 -- confirmed fixed by code read (not re-driven live this round; crypto pair path handling, out of this group's direct scope but adjacent).
- R15-CODE-FRONTEND-012 -- confirmed fixed by code read (sidecar ledger write-only sync issue, superseded by R15-CODE-PLATFORM-021's architecture change).
- `rc1-drive-portfolio-notes:1` (round-1 new_defect, not register-tracked) -- **round 2 (4c6dfe8c): fixed.** `quoteFetchInFlightRef` overlap guard added to `PortfolioPanel.tsx`; live-mounted test passes.

**Still open, confirmed unchanged:**
- R15-UI-079 -- CSV formula-injection cells (`=`,`+`,`-`,`@`) still written verbatim in `src/lib/csv.ts`, no escaping guard.
- R15-UI-078 -- form-path blank-cost-basis-saves-as-0 still reproduces. Nuance: the AGENT-path negative-cost-basis half of this entry now appears fixed as a side effect of unrelated host-actions.ts hardening (`holdingProblem` flags negative cost basis; `portfolio_add_position` blocks on `problem || costBasis === null`), but the register entry as a whole stays open because the form-path component is unfixed. Not filed as a separate finding key since the register entry's status is unchanged.

**Architecture change (not a bug, not a regression):**
- R15-CODE-PLATFORM-021 -- `sidecar/routers/portfolio.py` is now GET-only; holdings truth lives entirely in the frontend workspace blob / Zustand store. Confirmed via docstring + code read + `test_portfolio.py` (18/18 pass on candidate). This is the documented intentional migration, not a broken CRUD surface.

**New defect (not in register):**
- Quote auto-refresh backlog / resource exhaustion -- see `rc1-drive-portfolio-notes:1` in the findings file. `QUOTE_REFRESH_MS=5000` `setInterval` has no overlap guard; `api.ts` has zero `AbortController` usage. Once any symbol resolves slower than 5s (any small-cap/delisted NSE ticker via the `nse_direct` fallback), every tick starts a fresh full fan-out on top of whatever is still in flight, producing an unbounded, non-decreasing backlog. Reproduced live on my own sidecar with a 100-holding portfolio seeded with ~9 unresolvable symbols: 4.5+ minutes of an unbroken repeating cycle through the same 9 symbols with zero progress, continuing after the originating client had disconnected. A parallel probe against the untouched shared `:52152` stack answered the same query in 8ms, proving this is accumulated per-instance backlog, not a systemic provider defect. The sidecar self-recovered once the backlog eventually drained (confirmed via a background watch probe), so severity is high (renders the panel's live quotes completely unusable and saturates the sidecar's worker pool for the duration) rather than critical (not a permanent hang).

**Minor harness-methodology note (not a product finding):**
- P4/P4b's delete-control test needed rewriting for the new `ConfirmButton` arm/confirm double-click gate (`src/components/ConfirmButton.tsx`), introduced after census as an unrelated shared destructive-action safety primitive. Recorded as `rc1-drive-portfolio-notes:2`, severity low, kind regression only in the sense that the *harness* regressed against the new UI, not that the underlying R15-UI-035 fix regressed.

## Evidence index

- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/COVERAGE.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/portfolio-replay.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/notes-replay.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/notes-toolbar-replay.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/A0-context-with-ids.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/A1-delete-h3.jsonl` (local ollama tool-use lane -- inconclusive, model answered in prose rather than calling tools; not treated as load-bearing evidence, superseded by the N2 replay + host-actions.ts code read for the same claims)
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/A2-write-note.jsonl` (same caveat)
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/sidecar-log-p8-wedged-window.log` (the 05:45-05:46 repeating-cycle window, primary evidence for the new quote-backlog defect)
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/sidecar-log-p8-backlog-tail.log` (post-recovery tail, showing the sidecar answering /portfolio/positions and /health at 200 again)
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/round2-vitest-p8-fix-confirmed.log` (round 2: 65/65 pass on candidate `4c6dfe8c`, including the guard test)
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/round2-diff-portfolio-panel.stat.txt` (round 2: the exact `PortfolioPanel.tsx` diff between the two candidate shas)
- `docs/redesign/verification/r15/rc1/findings/rc1-drive-portfolio-notes.json`
