# batch-2/W4-workspace-persistence — rc1-battery-0

Candidate sha 01d6920a300b016ab1ad8aa436ee4e4586f8e336. `src/lib/workspace.ts` code reads
(plus live curl against my own sidecar :52340 for the sidecar-side entry).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-FRONTEND-001 | read `workspace.ts` `PersistedSlice.scope`, `loadWorkspace`, `applyLayoutSlice`, `restoreSlices` | every slice now tagged `scope: "layout"` or `"global"`; `loadWorkspace(name)` → `applyLayoutSlice` → `restoreSlices(workspace, "layout")` ONLY — never restores portfolios/notes/research-spaces/settings/keybindings (all `scope: "global"`); doc comment names R15-CODE-FRONTEND-001 directly | holds |
| R15-CODE-FRONTEND-004 | live `POST /workspace` on :52340 with `name:"Research: NVDA"` and `"Research: M&M"` | both `200 {"status":"saved",...}` (was 400); GET/DELETE round-trip clean | holds |
| R15-CODE-FRONTEND-005 | read `workspace.ts` `PERSISTED_SLICES` entries for `chartDrawings`/`keybindings`/`researchSpaces`/`savedScreens` + `wireAutosaveTriggers()` | each now has a `subscribe: onChange(...)` entry; `wireAutosaveTriggers()` maps every `PERSISTED_SLICES.subscribe` to `autosaveLayout` — single registry, no more per-store hand-wiring gaps | holds |
| R15-CODE-FRONTEND-018 | read `workspace.ts` `savedScreens` slice | now a full `PERSISTED_SLICES` entry (key/read/restore/subscribe) and a `SerializedWorkspace.savedScreens` field | holds |
| R15-LIFECYCLE-002 | read `deserializeWorkspace`, `stripUnknownPanels`, `restoreSession` | `stripUnknownPanels` now prunes only the unknown panel (not the whole layout); `deserializeWorkspace`'s own docstring names R15-LIFECYCLE-002 ("neither a garbled slice nor a layout that cannot be restored costs the user the rest of their data"); global slices restore independent of + before the layout slice | holds |
| R15-LIFECYCLE-003 | read `autosaveLayout`/`flushAutosave`/`restoreSettled`/`autosaveTimer`/`autosaveInFlight`/`autosaveQueued` | `autosaveLayout` no-ops until `restoreSettled`; trailing-edge `AUTOSAVE_DEBOUNCE_MS=500` debounce; `flushAutosave` is single-flight (`autosaveInFlight`/`autosaveQueued` re-run) — comment explicitly names the debounce+gate+single-flight design | holds |
| R15-LIFECYCLE-009 | read `restoreSession`'s `importLegacyPositions()` + `fetchLegacyPositions()`; live `GET /portfolio/positions` on :52340 | when the blob never carried `"portfolios"`, `importLegacyPositions()` reads `GET /portfolio/positions` (confirmed live, 200) and seeds the default portfolio via `seedDefaultPortfolio` | holds |

COVERAGE: 7/7 ids raw; no raw: none.
