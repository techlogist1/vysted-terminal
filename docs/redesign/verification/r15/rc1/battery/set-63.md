# batch-12/W8-w8 (set-63)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-63/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-010 | Live: `GET /sec/filings/0000320193-21-000105?identifier=AAPL` (no `form_type` hint), `.../sections?form_type=10-K`; fresh: `GET /sec/filings/0001564590-22-035087?identifier=MSFT` (the oldest of a 12-row 10-Q list, unhinted) | AAPL 10-K opens unhinted -> 200, `form_type:"10-K"`, `period_of_report:"2021-09-25"` (was a 404 pre-fix). `/sections?form_type=10-K` returns the Business section. Fresh: MSFT 10-Q opens unhinted -> 200, `form_type:"10-Q"`, `period_of_report:"2022-09-30"`, `sections:[]` (matches the cert's noted pre-existing residual: section parsing covers only 10-K items, not a regression). | holds |
| R15-CODE-PLATFORM-013 | Code read: `grep -rn setModuleEnabled` across `src/`; `plugin-bootstrap.ts:186,193` (`bridgePluginModule`/`unbridgePluginModule`); `SettingsPanel.tsx:1944-1952` | Only two direct callers write the `plugin:<id>` module flag, both in the lifecycle owner `plugin-bootstrap.ts` (bridge on enable, unbridge on disable) — `SettingsPanel.tsx` carries an explicit comment that a bare `setModuleEnabled` there previously desynced the two stores and now routes through the marketplace lifecycle instead. Pinned test `SettingsPanel.test.tsx:148` "toggling a bridged plugin module routes through the marketplace lifecycle, not setModuleEnabled directly" present unweakened. | ci_pinned: SettingsPanel.test.tsx:148 (+ callsite audit above) |
| R15-RELEASE-007 | Live: `node scripts/audit-design-tokens.mjs` clean run, then the entry's own negative case (inject `gap-1.5 px-[7px] text-[12px]` into `brief-blocks.tsx`, restore after) | Clean run: "design-token audit clean (372 files)", exit 0 — matches cert's file count. Negative case: 3 violations reported (`off-grid step gap-1.5`, 2x `arbitrary value`), exit code 1. File restored byte-identical afterward (`diff` clean). `package.json:10` confirms `lint` runs this audit (`eslint . && node scripts/audit-design-tokens.mjs`), matching the cert's chain wiring. | holds |

Summary: 2 holds, 1 ci_pinned, 0 regressions.

COVERAGE: 62/62 ids raw; no raw: none — every assigned id has a raw evidence file under `raw/set-{10..14,56..63}/`, including duplicate id R15-UI-090 (independently probed for both set-13 and set-62) and the corrected re-probes noted inline for R15-DATA-059 (TCI/META region param) and R15-AGENT-027 (humanize `detail=` kwarg).
