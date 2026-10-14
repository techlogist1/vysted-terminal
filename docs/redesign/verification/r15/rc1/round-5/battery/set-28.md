# batch-7/W5-agent-writes-portfolio (rc1-battery-10)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52350, data dir rc1-round-5-data-battery-10.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-032 | ChatSidebar/proposed-changes timing is frontend-only (no sidecar API); pinned vitest `ChatSidebar.test.tsx` still present and targets the exact certified string ("Couldn't apply: Open Flux ..."); source still writes `Applied: ${title}` synchronously (ChatSidebar.tsx:304) ahead of the async accept() path — mechanism unchanged | pinned test intact, mechanism matches certified fix | ci_pinned (src/modules/chat/ChatSidebar.test.tsx) |
| R15-AGENT-041 | Undo/pre-image is a proposed-changes store behaviour, no sidecar API; pinned vitest `ProposedChangesReview.test.tsx` "keeps an applied data write listed with Undo, which restores it (R15-AGENT-041)" present; source still sets `status: "undone"` on undo (proposed-changes.ts:241) | pinned test intact, mechanism matches | ci_pinned (src/modules/chat/ProposedChangesReview.test.tsx) |
| R15-AGENT-043 | Malformed criterion is dropped client-side in `parseScreenerCriterion` (host-actions.ts:440) before any sidecar call, so no live curl repro exists; pinned vitest `host-actions.test.ts` still asserts "Wrote 2 of 3 screener criteria; dropped roe: value must be a number — review and Run" | pinned test intact | ci_pinned (src/lib/host-actions.test.ts) |
| R15-AGENT-044 | Live `GET /resolve?q=MAZAGON%20DOCK` -> ok:true, resolved MAZDOCK (Mazagon Dock Shipbuilders); `GET /resolve?q=MAZAGONDOCK` (literal, no fuzzy match) -> ok:false, "No instrument matched"; `GET /resolve?q=Cochin%20Shipyard` -> ok:true, resolved COCHINSHIP, confidence 1.0 | matches batch-7 certification exactly (fuzzy name resolves, literal garbled ticker fails, no dead row created) | holds |
| R15-UI-017 | Frontend-only gate ordering; pinned vitest `ChatSidebar.test.tsx` still asserts "No API key for anthropic" with no orphan user turn; source confirms the "No API key for" message (ChatSidebar.tsx:818) is emitted before `appendUser(prompt)` (ChatSidebar.tsx:862) | pinned test intact, gate-before-mutation ordering unchanged | ci_pinned (src/modules/chat/ChatSidebar.test.tsx) |
| R15-UI-034 | Frontend-only (PortfolioPanel edit/switch/save); pinned vitest "an edit ends when the portfolio switches; Save then writes nothing silently (R15-UI-034)" present in PortfolioPanel.test.tsx | pinned test intact | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |
| R15-UI-035 | Frontend-only (stale memoised delete handler); pinned vitest "Delete works in a portfolio switched to after mount (R15-UI-035)" present | pinned test intact | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |
| R15-UI-036 | Frontend-only (quote refresh interval / as-of totals); pinned vitest "refreshes quotes on the Watchlist interval and dates the totals by the oldest quote (R15-UI-036)" present | pinned test intact | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |
| R15-UI-037 | Frontend-only (cost-basis label/unit); pinned vitest "the cost input and column say per share (R15-UI-037)" present; source still has `aria-label="Avg cost / share"` (PortfolioPanel.tsx:898) | pinned test intact, label text unchanged | ci_pinned (src/modules/portfolio/PortfolioPanel.test.tsx) |

COVERAGE: 9/9 ids raw; no raw: none.
