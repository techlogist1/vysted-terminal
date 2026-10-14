# set-79: lows-P2/frontend-panels-shell-chrome (rc1-battery-23, candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-081 | source: openPanel resolves via modules.enabledPanels(); chat module always-on in Settings; pinned test exists | enabledPanels guard at workspace.ts openPanel; SettingsPanel alwaysOn; test "disabled portfolio: openPanel returns false" present (workspace.test.ts:71) | ci_pinned |
| R15-CODE-FRONTEND-025 | pinned test present; PANEL_MIN_SIZE dead keys grep | test at PanelHost.test.tsx:198; chat-sidebar/broker-order-entry keys absent from PanelHost.tsx | ci_pinned |
| R15-LIFECYCLE-029 | pinned test present; PanelHost gate | gate on pluginsReady (PanelHost.tsx:124,194); test PanelHost.test.tsx:248 | ci_pinned |
| R15-CROSS-PLATFORM-009 | grep for glyph outside keybindings.ts | zero non-test hits; guard test source-guards.test.ts:50 | holds |
| R15-DOCS-006 | grep original false claims | no SSR-safe/static-export in PanelHost.tsx/page.tsx; no 'three-place'; no 'ONE search surface' | holds |
| R15-LEAD-027 | grep suggested:chart | no suggested:chart in command-palette.ts; only chart.open row; test command-palette.test.ts:278 | holds |
| R15-LIFECYCLE-028 | grep pagehide/flush | wireAutosaveTriggers registers pagehide -> flushPendingAutosave (workspace.ts:1188); test workspace.test.ts:1452 | holds |

COVERAGE: 7/7 ids raw; no raw: none
