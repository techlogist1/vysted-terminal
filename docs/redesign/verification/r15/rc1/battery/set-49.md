# unplanned-4

Candidate 4097dac4. Raw output: `raw/set-49/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DOCS-005 | `grep -c '^import' src/modules/index.ts`; `grep -n "modules in v1\|Module Catalog" docs/BLUEPRINT.md` | 21 imports; `docs/BLUEPRINT.md:238`: "Module Catalog (20 shipped in 0.9.0; the full list below is the v1.0 roadmap, ~37 modules)" — shipped-vs-roadmap counts are now distinguished, no longer a single misleading "~38 modules in v1.0" claim | holds |
| R15-UI-085 | `grep -rn text-charcoal-600 src --include=*.tsx` (excluding tests) | 2 hits (`SettingsPanel.tsx:530,539`, `ChatSidebar.tsx:2158`), all `disabled:text-charcoal-600` state variants — down from the register's 19 base-text hits; no readable-label contrast violation remains | holds |
| R15-UI-087 | `grep -n "R15-UI-087\|fallback order" src/components/SettingsPanel.tsx`; `src/components/SettingsPanel.test.tsx` ("the provider fallback order is live: the arrows reorder the rows and the store (R15-UI-087)") | `SettingsPanel.tsx:82,89,434` — a live, reorderable fallback-order UI with a "Move one provider to position `to`" function; pinned test present | holds |

Summary: 3 holds. No regressions.
