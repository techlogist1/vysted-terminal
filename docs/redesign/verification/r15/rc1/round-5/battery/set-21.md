# set-21 — batch-6/W3-unattended-platform-chart (rc1-battery-8)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. No browser session available this run
(NO GUI per role rules) — these four entries' repros are GUI-driven (focus a panel, click a
tab); verified instead by direct source inspection of the exact mechanism the register/batch-6
verifier cited, at the candidate sha.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-051 | source read: `sidecar/services/agent_runtime.py` `_render_terminal_preamble` | resolves `focused_chart` via `panelId == ts["focusedPanel"]` before falling back to `charts[0]`; labels "Focused chart" only on a real match (comment cites R15-AGENT-051 explicitly) | holds |
| R15-AGENT-052 | source read: `PanelHost.tsx`, `EquityOverviewPanel.tsx`, `BacktestResultView.tsx`, `ChartPanel.tsx` | focus bus (`setFocusedSource(panel?.id)`) and all three named publishers now key off the same dockview panel id (`chart`, `equity-overview`, `backtest`) — the prior `'equity'`/`'backtest-panel'`/`'chart-<id>'` mismatches are gone | holds |
| R15-CODE-FRONTEND-015 | same source read as AGENT-052 | same mechanism, same fix | holds |
| R15-LEAD-012 | `sidecar/.venv/bin/python3 --version`; bare `python3 --version`; `which python3.13`; `grep` `scripts/build-python.mjs` | bare `python3` still resolves to 3.14.5 (reproduces the Homebrew-moved scenario) but `build-python.mjs` now explicitly probes for/requires `python3.13` (`WANT="3.13"`, throws if absent) rather than trusting bare `python3`; candidate's own sidecar venv confirmed 3.13.13 | holds |

Raw: `battery/raw/set-21/R15-{AGENT-051,AGENT-052,CODE-FRONTEND-015,LEAD-012}.txt`
