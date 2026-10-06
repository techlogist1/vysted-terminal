# set-24 (rc1-battery-7) — batch-6/W5-host-actions-portfolio

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. All 9 entries are frontend-only
(`src/lib/host-actions.ts`, `src/store/portfolios.ts`); no sidecar route and no GUI
exercises them, so no vitest suite was run (per the shard's rule) — each id was
checked against its own COMMITTED, named pinned test on the candidate (a fresh
grep + read of the exact test body, never the diff), with one live re-run of the
register's own grep-based repro for CODE-PLATFORM-022.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-011 | grep for the named pinned test in host-actions.test.ts | `describe("describe/apply parity over one parsed intent (R15-CODE-FRONTEND-011)", …)` present at line 1559, full describe/apply-parity table over every HOST_ACTION_NAMES entry | ci_pinned |
| R15-CODE-FRONTEND-007 | same pinned test (shares fix commit 124b316 + bound-intent mechanism) | same describe block at line 1559 covers the stale-target-at-accept-time class | ci_pinned |
| R15-CODE-FRONTEND-009 | grep for the named pinned test | `it("save_screen saves the agent's recipe, not the on-screen draft, and says when it replaces (R15-CODE-FRONTEND-009)", …)` at line 1314 | ci_pinned |
| R15-CODE-FRONTEND-010 | grep for the named pinned test | `it("write_screener_filters writes the recipe and run:true runs it once (R15-CODE-FRONTEND-010)", …)` at line 1356 | ci_pinned |
| R15-AGENT-042 | grep for the named pinned test | `it("two lots of one symbol: an id picks its lot; the symbol alone refuses, naming both (R15-AGENT-042)", …)` at line 1208 | ci_pinned |
| R15-DATA-088 | grep for the named pinned test (store + host-action level) | `describe("holding validation (R15-DATA-088)", …)` in portfolios.test.ts:49; also host-actions.test.ts:1188 | ci_pinned |
| R15-CODE-FRONTEND-012 | grep for the named pinned test | `it("add/update/delete write only the store — no sidecar ledger call (R15-CODE-FRONTEND-012)", …)` at line 1127 | ci_pinned |
| R15-DATA-089 | grep for the pinned test (shared commit f37543d) + live grep for the removed helper | `sidecarPositionId`/`syncPositionToSidecar` no longer exist anywhere in `src/` | ci_pinned |
| R15-CODE-PLATFORM-022 | LIVE re-run of the register's own grep repro | `addPosition`/`updatePosition`/`deletePosition`/`refresh` absent from `src/` entirely (stronger than the original "no importer" finding); real apply path uses `addHolding`/`updateHolding`/`removeHolding` | holds |

Raw output for every id: `battery/raw/set-24/<id>.txt`.
