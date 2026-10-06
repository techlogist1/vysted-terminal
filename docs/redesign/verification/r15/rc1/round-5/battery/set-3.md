# batch-2/W4-workspace-persistence (shard rc1-battery-17)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar booted from candidate source
on :52357, data dir `rc1-round-5-data-rc1-battery-17` (copy of the round-5 keyless seed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-001 | Live sidecar workspace save/load not applicable (frontend-only rollback logic); pinned vitest `workspace.test.ts:603 "loading a named workspace never rolls back portfolios or notes (R15-CODE-FRONTEND-001)"` present and matches the register repro (per-workspace vs global-store split). | Test present, unmodified, asserts portfolios/notes survive a `loadWorkspace` call. | ci_pinned |
| R15-CODE-FRONTEND-004 | Live `curl` POST/GET/DELETE `:52357/workspace` for `Research: NVDA`, `Research: RELIANCE.NS`, `Research: M&M`, `My Layout (2)`, `../escape`, `a/b\c`. | All 6 names save 200, GET/DELETE round-trip 200/204; `ls` on the data dir's `workspaces/` shows each name percent-encoded to a filename inside the dir (e.g. `%2E%2E%2Fescape.vysted-workspace`) — no traversal above the data dir. No 400s. | holds |
| R15-CODE-FRONTEND-005 | Pinned vitest `workspace.test.ts:660 "round-trips chart drawings through workspace JSON"` + the gated-autosave describe block (line 1317) covering drawings/keybindings triggering `autosaveLayout`. | Test present, unmodified, matches register repro (drawings/keybindings serialized and now wired to autosave triggers). | ci_pinned |
| R15-CODE-FRONTEND-018 | Pinned vitest `workspace.test.ts:1584 "saved screens survive serialize, a fresh store and deserialize"`. | Test present, unmodified: `saveScreen` -> `serializeWorkspace` -> reset store -> `deserializeWorkspace` restores `savedScreens` incl. universe. | ci_pinned |
| R15-LIFECYCLE-002 | Pinned vitest `workspace.test.ts:1001` + `:1084 "restores holdings, notes and watchlist even when the saved layout has an unregistered panel (R15-LIFECYCLE-002)"`. | Test present, unmodified, asserts every data slice restores and 0 autosave POSTs fire when a layout panel id is unregistered (the broker-panel-removal trigger case). | ci_pinned |
| R15-LIFECYCLE-003 | Pinned vitest describe `workspace.test.ts:1317 "persisted-slice registry + gated autosave (R15-LIFECYCLE-003, CODE-FRONTEND-005/018)"`, incl. `:1406 "autosaves nothing during the launch restore; the first save after it carries the research space"`. | Test present, unmodified: restore issues 0 POSTs, first post-restore save carries `researchSymbol`/research archive. | ci_pinned |
| R15-LIFECYCLE-009 | Pinned vitest `workspace.test.ts:1681 "imports the ledger once into a blob that never carried portfolios, and saves the import"` (RELIANCE.NS/TCS.NS/BTC-USDT fixture matches register repro exactly); supplementary live probe `GET :52357/portfolio/positions` -> 200 `[]` (seed data carries no legacy ledger rows, endpoint itself reachable/functional). | Test present, unmodified, asserts holdings import once, no duplicate on relaunch, ledger skipped once portfolios exist. | ci_pinned |

Raw: `battery/raw/set-3/<id>.txt` for all 7 ids.

COVERAGE: 7/7 ids raw; no raw: none.
