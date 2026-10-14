# batch-10/W6-chart-notes-blueprint (set-45) — rc1-battery-2, gate round 5-recheck

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar `:52342` for the live
`GET /history/...` check; the other three entries are grep/source checks (TS logic, vitest
is the heavy lane's; two are pure doc/token reads via `git show HEAD:...`). Raw output:
`raw/set-45/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-026 | `GET /history/ZZZZNOTREAL`, `GET /history/QQZZFAKE.NS` (own sidecar `:52342`) | bare unknown symbol: `reason:"unknown_symbol"`; suffixed unknown (`.NS`): `reason:null` — matches the documented rule exactly | holds |
| R15-UI-048 | not re-run (vitest, heavy lane owns it); grep `settings.ts` + `ChartPanel.tsx` + `ChartPanel.test.tsx` | `settings.ts` still carries a persisted `chartDefaults` slice; `ChartPanel.tsx:278-290` reads `chartDefaultsAtMount` for a fresh (unpersisted) panel; `ChartPanel.test.tsx:278` `"a fresh panel (no persisted view) opens on the settings chart default (R15-UI-048)"` present | ci_pinned (`ChartPanel.test.tsx::"a fresh panel (no persisted view) opens on the settings chart default (R15-UI-048)"`) |
| R15-UI-024 | not re-run (vitest); grep `NotesPanel.tsx` + `package.json` + `NotesToolbar.test.tsx` | `NotesPanel.tsx:33,129-130` imports/registers `TaskList`/`TaskItem` from `@tiptap/extension-list`; `package.json` carries `@tiptap/extension-list@3.25.0`; `NotesToolbar.test.tsx:84` `"the Task list button toggles a task list (extension is registered)"` + wikilink-picker cases present | ci_pinned (`NotesToolbar.test.tsx::"the Task list button toggles a task list (extension is registered)"`) |
| R15-DOCS-004 | `git show HEAD:docs/redesign/PRODUCT_DESIGN_DECISIONS.md` head; `git show HEAD:styles/tokens.css` | Opens with the `SUPERSEDED (R15-DOCS-004)` banner naming both reversals (R6, R9) and which sections are dead (§0-7,9,10) vs binding (§8,11-16), pointing to `VYSTED_DESIGN.md`/`R9_DESIGN_SYSTEM.md`; `tokens.css` `charcoal-900=#161616`, `amber-400=#fab283` match the live pure-neutral+peach system the banner names | holds |

## Notes

- All four entries match round-4's own re-run of this same set at a prior candidate
  (`1006c6da`), read as precedent, never as this round's evidence — no regression against
  either the register's certified fix or the prior gate round's observed behaviour.
- LEAD-026's `reason:null` for a suffixed-unknown symbol is the documented, accepted
  behaviour (not a residual bug) — the register's own repro states this as the fixed shape.

COVERAGE: 4/4 ids raw; no raw: none.
