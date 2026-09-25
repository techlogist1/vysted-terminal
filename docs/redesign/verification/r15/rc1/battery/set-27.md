# batch-7/W5-agent-writes-portfolio

Own sidecar: candidate `4097dac4`, `127.0.0.1:52345` (same shard sidecar as sets 23-26),
data dir `rc1-data-rc1-battery-5`. Per `PLAN.md` §"File ownership" this writer set's fixes
live almost entirely in frontend TypeScript (`host-actions.ts`, `proposed-changes.ts`,
`ChatSidebar.tsx`, `PortfolioPanel.tsx`) — `portfolio_delete_position`/`add_to_watchlist`/
`save_screen` are `kind="host_action"` capabilities the sidecar only advertises, never
executes; the apply/undo/parse/ack logic all runs client-side. Never ran vitest per the
role's rules, so those reduce to `ci_pinned`. `R15-AGENT-044` is the one entry with a live,
sidecar-side half (`GET /resolve`, the resolution policy the fix routes model-supplied
symbols through) — re-run live below.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-044 | `GET /resolve?q=Mazagon%20Dock`, `?q=MAZAGONDOCK`, `?q=Cochin%20Shipyard` against the live sidecar. | "Mazagon Dock" → `ok:true`, `resolved.symbol:"MAZDOCK"` (confidence 0.92). "MAZAGONDOCK" → `ok:false`, `message:"No instrument matched 'MAZAGONDOCK'."`, `resolved:null`. "Cochin Shipyard" → `ok:true`, `resolved.symbol:"COCHINSHIP"` (confidence 1.0) — exact match to VERDICTS.md's certified figures. This is the resolution policy the AGENT-044 fix makes `add_to_watchlist` route through instead of trusting a model-invented symbol directly; the frontend host-action consumption of this response (`applyHostActionAsync`) is only exercised by its vitest suite. | holds (backend `/resolve` policy); frontend consumption not re-run — `src/lib/host-actions.test.ts` |
| R15-AGENT-041 | Frontend-only (`proposed-changes.ts` apply/pre-image/Undo, `host-actions.ts`, `ProposedChangesReview.tsx`); no sidecar counterpart (`portfolio_delete_position` is `kind="host_action"`, applied client-side against the Zustand portfolio store). Not re-run (vitest). | Pinned: `src/store/proposed-changes.test.ts`, `src/lib/host-actions.test.ts`, `src/modules/chat/ProposedChangesReview.test.tsx` — apply `portfolio_delete_position` then Undo restores the holding with its original id; a note replace + Undo restores the prior text. | ci_pinned (src/store/proposed-changes.test.ts) |
| R15-AGENT-043 | Frontend-only (`host-actions.ts` `parseScreenerCriterion`); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/lib/host-actions.test.ts` — a malformed leaf (`pe_ratio lt "cheap"`) yields "Wrote 1 of 2 screener criteria; dropped pe_ratio: value must be a number — review and Run", ack carries `dropped: [...]`. | ci_pinned (src/lib/host-actions.test.ts) |
| R15-AGENT-032 | Frontend-only (`ChatSidebar.tsx` apply-outcome write, `proposed-changes.ts` `enqueue`/`accept` resolving to `applied\|staged\|failed`); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/modules/chat/ChatSidebar.test.tsx` — under AUTO, a failing auto-apply writes "Couldn't apply: …", never "Applied:", and the change stays pending. | ci_pinned (src/modules/chat/ChatSidebar.test.tsx) |
| R15-UI-017 | Frontend-only (`ChatSidebar.tsx` `appendUser`/key-resolution ordering); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/modules/chat/ChatSidebar.test.tsx` — a send with no key leaves no user turn, keeps the prompt, shows "No API key for …"; the keyless-Ollama branch also returns before `appendUser`. | ci_pinned (src/modules/chat/ChatSidebar.test.tsx) |
| R15-UI-034 | Frontend-only (`PortfolioPanel.tsx` edit/switch/Save); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/modules/portfolio/PortfolioPanel.test.tsx` — edit, switch portfolio, then Save gives "are required" and the portfolios are unchanged. | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |
| R15-UI-035 | Frontend-only (memoised delete-column closure over a stale portfolio target); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/modules/portfolio/PortfolioPanel.test.tsx` — delete works correctly in a portfolio switched to after mount. | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |
| R15-UI-036 | Frontend-only (quote refresh interval, totals as-of label); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/modules/portfolio/PortfolioPanel.test.tsx` — quotes refetch on the 5 s interval; totals title reads "Oldest quote in these totals: …". | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |
| R15-UI-037 | Frontend-only (label/column copy); no sidecar counterpart. Not re-run (vitest). | Pinned: `src/modules/portfolio/PortfolioPanel.test.tsx` — labels read "Avg cost / share" (placeholder "per share"), column "Avg cost". | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |

Raw output: `raw/set-27/AGENT-044-mazagon-dock.txt`, `AGENT-044-mazagondock-nospace.txt`,
`AGENT-044-cochin-shipyard.txt`.
