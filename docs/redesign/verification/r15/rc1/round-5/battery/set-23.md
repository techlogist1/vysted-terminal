# set-23 — batch-6/W5-host-actions-portfolio (rc1-battery-8)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. All 9 entries are frontend (host-actions.ts
/ portfolios.ts) or portfolio-sidecar-router mechanisms with no direct HTTP repro path and no
GUI available this run (NO GUI role rule; vitest is the heavy lane's, not run here). Verified by
tracing the exact runtime mechanism the register named through the current source, at the call
sites the register/batch-6 verifier cited.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-042 | source: `resolveHolding`/`applyIntent` (host-actions.ts:683-706, 1917-1927) + sidecar portfolio router dump | exact-id match first; ambiguous multi-lot symbol REFUSES (names each lot) instead of guessing the first lot; the numeric sidecar-ledger PUT path is gone entirely (grep: 0 hits) | holds |
| R15-CODE-FRONTEND-007 | source: describe/apply/undo all key off `intent.portfolioId`/`preImage.portfolioId` (bound at parse time) | active-portfolio switch between diff and Accept can no longer redirect the mutation | holds |
| R15-CODE-FRONTEND-009 | source: `save_screen` apply case (host-actions.ts:1853-1880) | writes the agent's own recipe via `applyFilters` before `saveScreen`; refuses on all-malformed criteria | holds |
| R15-CODE-FRONTEND-010 | source: `write_screener_filters` apply case (host-actions.ts:1806-1826) | `run:true` now calls `runScreener()` (previously narrated only) | holds |
| R15-CODE-FRONTEND-011 | source: `describeHostAction`/`applyHostAction` (host-actions.ts:1472-1474, 2036-2038) | both call the same `parseHostAction` once, then `describeIntent`/`applyIntent` on the one `HostIntent` — no independent re-parse | holds |
| R15-CODE-FRONTEND-012 | source: `sidecar/routers/portfolio.py` full dump + grep host-actions.ts | router is GET-only by design (docstring cites R15-CODE-PLATFORM-021); zero references to sidecarPositionId/portfolioUrl/syncPositionToSidecar in host-actions.ts | holds |
| R15-CODE-PLATFORM-022 | `grep addPosition\|updatePosition\|deletePosition src/store/portfolios.ts` + tree-wide importer grep | 0 matches in either — the dead 68-line client was deleted, not left unused | holds |
| R15-DATA-088 | source: `normalizeHolding` (portfolios.ts:72-97) + `setAll` (198-215) | non-finite/zero/negative quantity or negative cost basis now returns null and is filtered out of `setAll`'s workspace-restore path | holds |
| R15-DATA-089 | same evidence as CODE-FRONTEND-012 | the sidecar-ledger write path (NaN id -> 405 -> discarded) no longer exists; portfolio writes resolve entirely against the frontend store | holds |

Raw: `battery/raw/set-23/R15-{AGENT-042,CODE-FRONTEND-007,CODE-FRONTEND-009,CODE-FRONTEND-010,CODE-FRONTEND-011,CODE-FRONTEND-012,CODE-PLATFORM-022,DATA-088,DATA-089}.txt`

COVERAGE: 9/9 ids raw; no raw: none.
