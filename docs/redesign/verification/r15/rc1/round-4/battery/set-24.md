# batch-6/W5-host-actions-portfolio (set-24)

All 9 entries were certified in batch-6 via vitest (`host-actions.test.ts` / `portfolios.test.ts`).
Per the stall/no-vitest rule, this shard does not execute those suites; instead each entry's fix
is re-derived by reading the current candidate source at 1006c6da694ede5776c3dabbd27b305aeb56b5ad
and confirming the code path the pinned test exercises is unchanged/present. Raw excerpts under
`battery/raw/set-24/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-012 | grep host-actions.ts for portfolio/positions network calls; grep sidecar routers/portfolio.py routes | no fetch to `/portfolio/positions` remains in host-actions.ts; sidecar route is GET-only `/positions` (no bare PUT/DELETE) | holds |
| R15-DATA-089 | grep src/ for addPosition/updatePosition/deletePosition | zero occurrences anywhere in src/ (including tests) — client fully removed | holds |
| R15-CODE-PLATFORM-022 | same grep as DATA-089 | same — dead client is gone, not merely unimported | holds |
| R15-DATA-088 | read normalizeHolding() + setAll()/addHolding()/updateHolding() | non-finite/<=0 quantity and non-finite/<0 cost both return null and are dropped by setAll's `.filter((h): h is Holding => h !== null)`; addHolding/updateHolding return null/false | holds |
| R15-CODE-FRONTEND-011 | read parseHostAction/describeHostAction/applyHostAction + proposed-changes.ts enqueue/accept | proposed-changes.ts:103 calls `parseHostAction` once at enqueue, stores `intent`; describeIntent(intent) renders the diff; accept (line 146) calls `applyIntentAsync(change.intent)` — the same bound intent, not a re-parse of raw input | holds |
| R15-CODE-FRONTEND-007 | same as CODE-FRONTEND-011 (shared fix, commit 124b316) | same evidence — accept applies the intent bound at enqueue time, immune to an active-portfolio switch afterward | holds |
| R15-AGENT-042 | read PortfolioPanel.tsx publishedHoldings + resolveHolding() | line 444 `id: holdings[i]?.id` (comment cites R15-AGENT-042 by name); resolveHolding refuses a 2+-lot ambiguous symbol match, naming each lot's id/size in the problem string | holds |
| R15-CODE-FRONTEND-009 | read `case "save_screen"` apply branch | writes the agent's recipe via `applyFilters()` before `saveScreen()`, computes `replaces` and narrates "replaced" vs `+"name"` | holds |
| R15-CODE-FRONTEND-010 | read `case "write_screener_filters"` apply branch | `if (run) { void useScreenerStore.getState().runScreener(); }` — actually invoked, not just narrated | holds |

COVERAGE: 9/9 ids raw; no raw: none.
