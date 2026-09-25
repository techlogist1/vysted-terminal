# batch-10/W6-chart-notes-blueprint (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 7 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-048 | test file presence: `src/modules/chart/ChartPanel.test.tsx` (cert evidence was purely this vitest — fresh-panel default, per-panel persisted view, "Make default") | file present on `4097dac4` | ci_pinned |
| R15-LEAD-026 | `GET /history/ZZQXNOTASYM` | `{"bars":[],"provider":"none","reason":"unknown_symbol",...}` — exact match to cert | holds |
| R15-UI-024 | test file presence: `src/modules/notes/NotesToolbar.test.tsx` (cert evidence was purely this vitest — TaskList toggle, wikilink wrap/picker) | file present | ci_pinned |
| R15-DOCS-004 | `grep` `docs/redesign/PRODUCT_DESIGN_DECISIONS.md` + test file presence `src/lib/design-doc-citations.test.ts` | line 3: `> **SUPERSEDED (R15-DOCS-004):** §0-§7, §9, §10 describe the "Warm Graphite" palette...` banner present; citation test file present | holds |
| R15-DOCS-005 | `grep` `docs/BLUEPRINT.md:20` + `ls src/modules` | doc: "20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap)"; 23 entries under `src/modules/` incl. the registrar `index.ts` (20 module dirs + index + 2 support files) — consistent with the doc's "20 modules" claim | holds |
| R15-DATA-078 | `grep` `docs/BLUEPRINT.md:266` | "18. yfinance fallback (no API key needed for basic use; R15-DATA-078 — alpha_vantage was [never built])" — the non-existent fallback is no longer claimed as real | holds |
| R15-CODE-PLATFORM-024 | `grep` `docs/BLUEPRINT.md:77-78` + `grep` `src-tauri/src/lib.rs` | doc names `write_text_atomic`/`write_bytes_atomic` as the export mechanism (not `tauri-plugin-fs`); both `fn write_text_atomic` (lib.rs:391) and `fn write_bytes_atomic` (lib.rs:422) exist | holds |

Raw output: `battery/raw/set-43/*`. Excluded (not certified in batch-10): R15-UI-091 (chart never consumes `suggested_indicators` — the entry's repro still holds as a defect).
