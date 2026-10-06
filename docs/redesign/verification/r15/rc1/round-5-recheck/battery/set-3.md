# batch-2/W4-workspace-persistence (shard rc1-battery-17)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar booted from candidate source
on :52357, data dir `rc1-round-5-recheck-data-battery-17` (copy of the round-5-recheck keyless seed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-001 | Frontend-only rollback logic (no sidecar endpoint to exercise); pinned vitest `workspace.test.ts:603 "loading a named workspace never rolls back portfolios or notes (R15-CODE-FRONTEND-001)"` present and unmodified, matches the register repro. | Test present at HEAD, same line as prior certification. | ci_pinned |
| R15-CODE-FRONTEND-004 | Live POST/GET/DELETE `:52357/workspace` for `Research: NVDA`, `Research: RELIANCE.NS`, `Research: M&M`, `My Layout (2)`, `../escape`, `a/b\c`. | All 6 names: POST 200, GET 200, DELETE 204. `ls workspaces/` shows each name percent-encoded (`%2E%2E%2Fescape.vysted-workspace.bak`, `a%2Fb%5Cc...`, etc.) — no path traversal above the data dir, no 400s. | holds |
| R15-CODE-FRONTEND-005 | Pinned vitest `workspace.test.ts:660 "round-trips chart drawings through workspace JSON"` + gated-autosave describe block (line 1317) covering drawings/keybindings triggering `autosaveLayout`. | Test present at HEAD, unmodified. | ci_pinned |
| R15-CODE-FRONTEND-018 | Pinned vitest `workspace.test.ts:1584 "saved screens survive serialize, a fresh store and deserialize"`. | Test present at HEAD, unmodified. | ci_pinned |
| R15-LIFECYCLE-002 | Pinned vitest `workspace.test.ts:1001` + `:1084 "strips an unregistered panel from the saved layout and restores the rest, with every data slice and no autosave (R15-LIFECYCLE-002)"`. | Test present at HEAD, unmodified. | ci_pinned |
| R15-LIFECYCLE-003 | Pinned vitest describe `workspace.test.ts:1317 "persisted-slice registry + gated autosave (R15-LIFECYCLE-003, CODE-FRONTEND-005/018)"`. | Test present at HEAD, unmodified. | ci_pinned |
| R15-LIFECYCLE-009 | Pinned vitest `workspace.test.ts:1602 "legacy positions import (R15-LIFECYCLE-009)"` (RELIANCE.NS/TCS.NS/BTC-USDT fixture matches register repro); supplementary live probe `GET :52357/portfolio/positions` -> 200 `[]` (keyless seed carries no legacy ledger rows, endpoint reachable/functional, unchanged from round-5 cert). | Test present at HEAD, unmodified. Live probe 200 `[]`. | ci_pinned |

Raw: `battery/raw/set-3/<id>.txt` for all 7 ids.

COVERAGE: 7/7 ids raw; no raw: none.
