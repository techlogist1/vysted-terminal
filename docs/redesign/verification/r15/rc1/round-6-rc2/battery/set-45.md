# Set: batch-10/W6-chart-notes-blueprint (set-45) — rc1-battery-21 @ ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-048 | UI repro is a ChartPanel mount; confirmed named vitest cases + settings.chartDefaults slice exist at candidate | ChartPanel.test.tsx:287 'opens on the settings chart default (R15-UI-048)', :298, :320 'Make default'; settings.ts chartDefaults:91/118 | ci_pinned (src/modules/chart/ChartPanel.test.tsx R15-UI-048) |
| R15-LEAD-026 | GET /history/ZZQXNOTASYM, QQZZFAKE.NS on own sidecar | ZZQXNOTASYM -> 200 bars [] provider none reason 'unknown_symbol'; suffixed QQZZFAKE.NS reason null by documented rule (verifier note) | holds |
| R15-UI-024 | UI repro (editor); confirmed TaskList/TaskItem registration + named tests at candidate | NotesPanel.tsx:33,130-131 registers TaskList/TaskItem; NotesToolbar.test.tsx:84 Task list button, :95 wikilink WRAPS selection, :109 no-selection picker | ci_pinned (src/modules/notes/NotesToolbar.test.tsx R15-UI-024) |
| R15-DOCS-004 | read docs/redesign/PRODUCT_DESIGN_DECISIONS.md:1-12 (the entry's own repro) | opens with SUPERSEDED (R15-DOCS-004) banner naming R6/R9 reversals and the binding sections; design-doc-citations.test.ts:38 guards dead citations | holds |

COVERAGE: 4/4 ids raw (battery/raw/set-45/); no raw: none
