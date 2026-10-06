# batch-7/W5-agent-writes-portfolio — regression battery re-run (rc1-battery-11, round-4)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar :52351 (shared for the whole shard).
All these entries are frontend TS logic (host-actions.ts / ChatSidebar.tsx / PortfolioPanel.tsx). No GUI, and
this role does not run vitest/pytest suites (the heavy lane owns them). Where the certified behavior is
sidecar-reachable (AGENT-044's resolve step) it was re-run live; the rest are confirmed by reading the exact
certified code paths at the candidate sha and naming the committed, register-id-tagged pinned test.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-AGENT-043 | Code check: `host-actions.ts` `wroteCriteriaText`/`droppedCriteriaNote`/`write_screener_filters` apply case | Produces exactly `"Wrote N of M screener criteria; dropped ... — review and Run"`, matching the certified repro string. | ci_pinned (`src/lib/host-actions.test.ts:338` "write_screener_filters says which malformed criterion it dropped, in label and ack (R15-AGENT-043)") |
| R15-AGENT-041 | Code check: `undoPreImage`/undo path present and exported, unchanged | Undo mechanism intact. | ci_pinned (`src/lib/host-actions.test.ts:1651` "an applied holding delete can be undone: the holding is back with its id (R15-AGENT-041)") |
| R15-AGENT-032 | Code check: ChatSidebar apply/enqueue ordering | Behavioral proof needs jsdom/vitest. | ci_pinned (`src/modules/chat/ChatSidebar.test.tsx:769` "under AUTO a failing auto-apply writes no 'Applied:' line, it says why (R15-AGENT-032)") |
| R15-UI-017 | — | Behavioral proof needs jsdom/vitest. | ci_pinned (`src/modules/chat/ChatSidebar.test.tsx:609` "a send with no key leaves no orphaned user turn and keeps the prompt (R15-UI-017)") |
| R15-AGENT-044 | LIVE `GET /resolve?q=Mazagon%20Dock`, `?q=MAZAGONDOCK`, `?q=Cochin%20Shipyard` against candidate sidecar + code check `host-actions.ts` `addResolvedEquity()` | "Mazagon Dock" -> MAZDOCK (resolved); "MAZAGONDOCK" (invented, no space) -> `ok:false`, no candidates; "Cochin Shipyard" -> COCHINSHIP. `addResolvedEquity()` calls `GET /resolve` before `addSymbol`, matching the fix exactly. | holds |
| R15-UI-034 | — | — | ci_pinned (`src/modules/portfolio/PortfolioPanel.test.tsx:394,454` "R15-UI-034") |
| R15-UI-035 | — | — | ci_pinned (`src/modules/portfolio/PortfolioPanel.test.tsx:430` "Delete works in a portfolio switched to after mount (R15-UI-035)") |
| R15-UI-036 | — | — | ci_pinned (`src/modules/portfolio/PortfolioPanel.test.tsx:213` "refreshes quotes on the Watchlist interval... (R15-UI-036)") |
| R15-UI-037 | Code check: `src/modules/portfolio/metrics.ts:94` | Per-share cost basis math unchanged. | ci_pinned (`src/modules/portfolio/PortfolioPanel.test.tsx:93` "the cost input and column say per share (R15-UI-037)") |

COVERAGE: 9/9 ids raw; no raw: none.
