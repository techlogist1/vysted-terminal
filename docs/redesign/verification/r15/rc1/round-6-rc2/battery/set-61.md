# Set: lows-P1/frontend-panels-shell-chrome (set-61) — candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-075 | grep font-feature-settings in src/app/globals.css vs the tokens.css claim | globals.css:115-117 now sets "tnum" 1, "zero" 1, "calt" 0; tokens.css:109 claim matches | holds |
| R15-CODE-PLATFORM-070 | script diffing every var(--token, fallback) in globals.css against styles/tokens.css | 111 fallbacks checked, 0 colour disagreements (entry: 27); 8 non-colour remain, all generic font stacks (4) / ease / 4px==0.25rem, no retired warm/amber/590 values (grep d89a4e, 590 empty); notes-prose sizes now var(--text-*) | holds |
| R15-DOCS-007 | grep BLUEPRINT.md for the stale palette line, theming line, UC2/UC4 | 'charcoal + warm amber + sage' absent; :251 says dark-only, light deferred (FR-030); UC2 (:655) carries the openbb-mcp degrade note, UC4 (:661) carries a matching MCP caveat | holds |

COVERAGE: 3/3 ids raw; no raw: none
