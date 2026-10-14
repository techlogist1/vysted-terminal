# batch-6/W3-unattended-platform-chart

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-012 | live: `python3 --version` on PATH (repro condition) then `node -e "import('./scripts/build-python.mjs').then(m=>{...m.resolveBuildPython()...})"` | PATH `python3` is 3.14.5 (matches the repro's "Homebrew moved python3 to 3.14" condition); `resolveBuildPython()` still resolves `python3.13` → interpreter reports `3.13.13` | holds |
| R15-AGENT-052 | code read (`EquityOverviewPanel.tsx:550` `busSource = props.api?.id ?? "equity-overview"`; `ChartPanel.tsx:1030` `source: panelId`; `PanelHost.tsx:286` `setFocusedSource(panel?.id)`) + `vitest run src/modules/panel-context-publishers.test.tsx` (`"is found under the dockview id PanelHost focuses (R15-AGENT-052)"`) and `src/modules/chart/ChartPanel.test.tsx` (`"with two charts, the focused second chart is the snapshot's focus (R15-AGENT-052)"`) | bus source now literally the dockview panel id in every publisher checked; both named tests pass | holds (ci_pinned) |
| R15-AGENT-051 | code read (`context-provider.ts:404` `charts.find(c => c.panelId === focusedPanel) \|\| charts[0]`; `agent_runtime.py:438-441` `shown = focused_chart or charts[0]`, label only "Focused chart" when `focused_chart is not None`) + `pytest tests/test_b5_runtime_focus.py` (2 tests, one literally `test_the_focused_second_chart_is_the_one_rendered`) | both pass; the preamble's "Focused chart" label and the deixis line now derive from the SAME `focused_chart`, not `charts[0]` unconditionally | holds (ci_pinned) |
| R15-CODE-FRONTEND-015 | `vitest run src/modules/chat/ChatSidebar.test.tsx` (`"a focused Equity Overview's ticker drives the badge, the chips and the snapshot (R15-CODE-FRONTEND-015)"`) + code read of the single `focusedSymbolFromBus()` derivation (`context-provider.ts:243`) now used for badge/chips/snapshot alike | test passes; one function, one derivation, no more 3-way disagreement | holds (ci_pinned) |
| R15-UI-021 | `vitest run src/modules/chart/ChartPanel.test.tsx` (`"Backspace typed into a field outside the chart keeps the selected drawing"`, `"a locked drawing survives Delete"`, `"Delete with nothing focused still deletes"`, all named R15-UI-021) | 51/51 passed | holds (ci_pinned) |

Runs: `npx vitest run src/modules/panel-context-publishers.test.tsx src/modules/chat/ChatSidebar.test.tsx
src/modules/chat/context-provider.test.ts` → 3 files, 66/66 passed. `sidecar/.venv/bin/python3 -m pytest
tests/test_b5_runtime_focus.py -v` → 2/2 passed. `npx vitest run src/modules/chart/ChartPanel.test.tsx` →
1 file, 51/51 passed.

Note: batch-6's own certification for these three (AGENT-052/051/CODE-FRONTEND-015/UI-021) leaned on a
scratch file `zz-b6v-verify.test.tsx` that was explicitly "not kept" — I did not try to resurrect it;
instead I located the permanent pinned tests + read the fixed source directly, which independently
confirm the same class of fix.

Raw: `battery/raw/set-22/*.txt`.
