# Set: lows-P3/frontend-panels-data-surfaces (set-97) — candidate ace7dd76, sidecar :52346

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-109 | grep openCryptoStream over src/ sidecar/ | only a test asserting it is not exported (sidecar-client.test.ts:398) | holds |
| R15-CODE-FRONTEND-023 | grep ChartPanel for the re-render fix; pinned test | test "N crosshair moves on a lone chart cause 0 ChartPanel re-renders" exists (ChartPanel.test.tsx:1172) | ci_pinned |
| R15-UI-064 | pinned tests present | ChartPanel.test.tsx:1238 (% overlay sorted/de-duped, visible scale), :1275 (indicator colours) | ci_pinned |
| R15-CODE-FRONTEND-024 | ls/grep dead modules | fuzzy.ts, indicator-presets.ts and tests gone; no refs; dead-surface.test.ts pins | holds |
| R15-CROSS-PLATFORM-006 | node (type-stripping) calls safeFilename on NSE:RELIANCE, CON, :*?"<>| | NSE_RELIANCE, CON_, a_______b | holds |
| R15-DOCS-010 | grep 'amber' in DataTable/NotesToolbar; active class | no amber promise left; filled-pill active state; test NotesToolbar.test.tsx:128 | holds |

COVERAGE: 6/6 ids raw; no raw: none
