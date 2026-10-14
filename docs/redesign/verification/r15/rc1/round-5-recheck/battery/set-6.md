# set-6 — batch-3/W2-agent-frontend-gate (rc1-battery-19, gate round 5-recheck)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52359 (fresh copy of
rc1-round-5-recheck-seed-data). Vitest scoped to the 9 files touching these entries
(173/173 passed) plus direct source reads where no committed test names the sub-repro.
Raw: `battery/raw/set-6/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-080 | vitest proposed-changes / proposed-change-kinds + source read of `AUTO_APPLIED_KINDS` | AUTO gate is now an allow-list (panel, chart, watchlist); data-write/settings stay pending | holds |
| R15-CODE-FRONTEND-008 | vitest ComposerPlusMenu hint test + source read | Hint copy rendered from `autoApplies`, one shared declaration, no drift | holds |
| R15-CODE-FRONTEND-003 | vitest host-actions "write_note honours the catalog-documented args" | Omitted mode defaults to append; original wipe repro no longer reproduces | holds |
| R15-CODE-FRONTEND-014 | vitest host-actions save_layout / global-scope tests | `scope:'global'` → General bucket; `save_layout {}` updates active layout | holds |
| R15-UI-001 | vitest NotesPanel + notes store, source read of `flush()`/unmount cleanup | Store authoritative; empty-clear flush and unmount-flush confirmed in source (no dedicated test for those 2 sub-repros, matches batch-3's scratch-check treatment) | holds |
| R15-UI-002 | vitest CommandPalette "always-consumed chart-command channel" | Cmd-K ticker pick routes through `loadSymbolIntoChart`, chart updates under default settings | holds |
| R15-AGENT-014 | vitest plugin-bootstrap + plugin-agents, source read of boot loop, live GET /custom-agents on own sidecar | Boot loop now calls `syncPluginAgents(pluginId, true)`; full live proof needs Tauri GUI shell (out of scope, no-GUI rule) — verified via committed test + source | holds |

COVERAGE: 7/7 ids raw.
