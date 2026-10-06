# UI-1 — loading a named workspace never rolls back global data; autosave persists the newer state (final-adv-maintainer, d38b5d1a)

Harness: scratch vitest jsdom, real src/lib/workspace.ts against own sidecar :52825 (workspace blobs land in my own data dir), dockview replaced by the same fake shape src/lib/workspace.test.ts uses. Evidence: UI-1/harness-workspace.json.

1. `restoreLastSessionOrDefault` settles the autosave gate.
2. v1 global data (watchlist MSFT; holding AAPL 10@180) → `saveWorkspace("FP-UI1")`; the saved blob carries every PERSISTED slice (watchlist, portfolios, notes, settings, brief, …).
3. v2: add NVDA to the watchlist and TCS 5@3500 to the portfolio.
4. `loadWorkspace("FP-UI1")` → watchlist still [MSFT, NVDA], holdings still [AAPL:10@180, TCS:5@3500] (`loadRolledBack: false`) — only layout slices applied.
5. `autosaveLayout()` → GET /workspace/__autosave__ holds the v2 watchlist and both lots (`autosaveHasV2: true`) — the rollback was never persisted.
6. Relaunch simulation (stores emptied, persistence reset, restore from the autosave blob) → v2 data back (`relaunchHasV2: true`).

VERDICT UI-1: pass
