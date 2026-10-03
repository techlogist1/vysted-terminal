# Set: batch-6/W3-unattended-platform-chart (set-22) — candidate ace7dd76, sidecar :52345

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-012 | `python3 --version` then node `resolveBuildPython()` from scripts/build-python.mjs (the repro condition: bare python3 is 3.14) | python3 = 3.14.5, resolveBuildPython -> `python3.13` = 3.13.13; sidecar-specs.mjs calls ensureBuildVenv | holds |
| R15-AGENT-052 | source check: publishers' bus keys vs dockview ids | Backtest `BUS_SOURCE="backtest"`, Chart `source: panelId`, Equity `busSource`; layout ids chart/equity-overview; pinned by panel-context-publishers.test.tsx (vitest, heavy lane) | ci_pinned |
| R15-AGENT-051 | in-process `_render_terminal_preamble` with two charts, second (INFY) focused | "Focused chart: INFY (1d, ema:9)." and deixis "they mean INFY" - consistent; equity-overview focus case prints "Chart: SPY" + "Focused panel: equity-overview." | holds |
| R15-CODE-FRONTEND-015 | source check of `focusedSymbolFromBus` used by badge, chips and snapshot | one derivation shared (context-provider.ts:264, SuggestionChips.tsx:8,51); pinned by ChatSidebar.test.tsx:600 (vitest) | ci_pinned |
| R15-UI-021 | source/test check of ChartPanel keydown scope | TEXT_ENTRY_SELECTOR guard present; tests ChartPanel.test.tsx:977 (composer/symbol Backspace), :1011 (locked survives Delete), :1106 (body Backspace) | ci_pinned |
