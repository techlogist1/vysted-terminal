# batch-3/W2-agent-frontend-gate (set-6), shard rc1-battery-16, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-080 | scratch vitest, real proposed-changes gate, autonomy=auto, 7 data/settings kinds + 3 control kinds | portfolio add/update/delete, write_note, save_layout, save_screen, set_region all pending/'staged'; set_chart_symbol, add_to_watchlist, open_panel accepted/applied; INFY note untouched; AUTO_APPLIED_KINDS [panel,chart,watchlist] | holds |
| R15-CODE-FRONTEND-008 | same AUTO probe + hint copy | same statuses; ComposerPlusMenu hint now '<instant kinds> changes apply instantly; <staged> ... ' | holds |
| R15-CODE-FRONTEND-003 | write_note {scope:NVDA,text} no mode, NVDA='my long thesis' | 'Appended to the NVDA note' -> 'my long thesis\n\nnew line' | holds |
| R15-CODE-FRONTEND-014 | write_note scope global; save_layout {} with active layout | global -> General ('keep me\n\nhello'), no GLOBAL key; save_layout {} -> 'Research Desk' (default -> 'Agent layout') | holds |
| R15-UI-001 | full TipTap editor interaction (no headless probe outside the suite) | pinned by src/modules/notes/NotesPanel.test.tsx ('shows an agent write_note into the open note, and the next keystroke keeps it', 'a scope switch inside the debounce window saves each scope's own text'); source has flush on scope switch + unmount | ci_pinned |
| R15-UI-002 | real CommandPalette, live /resolve/autocomplete of own sidecar, type RELIANCE, click Tickers row | chart command null -> {symbol:RELIANCE, region:IN, seq:1} via loadSymbolIntoChart | holds |
| R15-AGENT-014 | real bootstrapPlugins() against fresh-data sidecar, GET /custom-agents | before: []; after: ['custom:vysted-lenses-quant-tutor'] | holds |

COVERAGE: 7/7 ids raw; no raw: none
