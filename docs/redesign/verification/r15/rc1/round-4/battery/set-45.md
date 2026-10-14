# batch-10/W6-chart-notes-blueprint (rc1-battery-21, set-45)

Candidate sha 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sidecar :52361.

Note: the shared candidate worktree's `docs/` tree (5148 files) shows as
deleted on disk (`git status` all `D`) though `HEAD`'s git tree has every file
intact — read via `git show HEAD:<path>` instead of the working tree for the
doc-check entries below (filed as an environment finding).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-026 | `GET /history/ZZZZNOTREAL`, `GET /history/QQZZFAKE.NS` | bare unknown symbol: `reason:"unknown_symbol"`; suffixed unknown (`.NS`): `reason:null` — matches the documented rule exactly | holds |
| R15-UI-048 | not re-run (vitest, heavy lane owns it); `grep settings.ts` + `ChartPanel.test.tsx` names | `settings.ts` has a `chartDefaults` slice (persist/parse round-trip at :288-290); `ChartPanel.test.tsx:278` `"a fresh panel (no persisted view) opens on the settings chart default (R15-UI-048)"`, `:311` `'"Make default" persists...'` present | ci_pinned (`ChartPanel.test.tsx::"a fresh panel (no persisted view) opens on the settings chart default (R15-UI-048)"`) |
| R15-UI-024 | not re-run (vitest); `grep NotesPanel.tsx` + `NotesToolbar.test.tsx` names | `NotesPanel.tsx:33,129-130` imports and registers `TaskList`/`TaskItem` from `@tiptap/extension-list`; `NotesToolbar.test.tsx:84` `"the Task list button toggles a task list (extension is registered)"`, `:95`/`:109` wikilink-picker cases present | ci_pinned (`NotesToolbar.test.tsx::"the Task list button toggles a task list (extension is registered)"`) |
| R15-DOCS-004 | `git show HEAD:docs/redesign/PRODUCT_DESIGN_DECISIONS.md` head | Opens with the `SUPERSEDED (R15-DOCS-004)` banner naming both reversals (R6, R9) and which sections (§0-7,9,10 dead; §8,11-16 binding) and pointing to `VYSTED_DESIGN.md`/`R9_DESIGN_SYSTEM.md` | holds |
| R15-DOCS-005 | `git show HEAD:docs/BLUEPRINT.md` L18-20; `find src/modules -maxdepth 2 -iname index.ts*` | BLUEPRINT.md now reads "20 modules shipped in 0.9 (see §4 for the full ~37-module v1.0 roadmap)"; 21 `index.ts` files under `src/modules/*` (20 module dirs + the root barrel) — count matches | holds |
| R15-DATA-078 | `git show HEAD:docs/BLUEPRINT.md` grep alpha_vantage; `grep -rn alpha_vantage sidecar/` | BLUEPRINT.md:266 now reads "yfinance fallback (no API key needed for basic use; R15-DATA-078 — alpha_vantage was [never built])"; 0 hits for alpha_vantage anywhere in `sidecar/` (disk, intact) | holds |
| R15-CODE-PLATFORM-024 | `git show HEAD:docs/BLUEPRINT.md` grep write_text_atomic; `grep src-tauri/src/lib.rs`; `cat capabilities/default.json` | BLUEPRINT.md:77-78 now describes the atomic-write commands, not a `tauri-plugin-fs` capability, naming R15-CODE-PLATFORM-024; `lib.rs:391,422` defines `write_text_atomic`/`write_bytes_atomic` and both are registered in the invoke handler (:513-514); `capabilities/default.json` permissions list still has no `fs:*` entry (consistent — the doc no longer claims one) | holds |

COVERAGE: 7/7 ids raw.
