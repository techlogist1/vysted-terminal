# batch-6/W3-unattended-platform-chart (rc1-battery-6, gate round 5-recheck, candidate 949c3c9f)

Own sidecar :52346 (candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, seed-data copy `rc1-round-5-recheck-data-rc1-battery-6`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-012 | `node -e "import('./scripts/build-python.mjs').then(m=>m.resolveBuildPython())"` in the candidate repo with bare `python3` on `PATH` at 3.14.5 (exact repro condition — Homebrew still has `python3` -> 3.14 on this Mac) | `resolved: python3.13` — `resolveBuildPython()` skips the bare `python3` and picks `python3.13` explicitly | holds |
| R15-AGENT-052 | Source: `PanelHost.tsx` `onDidActivePanelChange` -> `setFocusedSource(panel?.id)`; `ChartPanel.tsx` publishes `source: panelId` (via `usePanelId`); `EquityOverviewPanel.tsx` `busSource = props.api?.id`; `BacktestResultView.tsx` `BUS_SOURCE = "backtest"` | All three publishers now key their bus `source` by the dockview panel id, matching what `PanelHost` focuses — closes the `chart-${panelId}` / `'equity'` / `'backtest-panel'` mismatch | holds |
| R15-AGENT-051 | In-process `sidecar/services/agent_runtime._render_terminal_preamble(ts)` with a synthetic `TerminalState`: two chart panels (`chart-a`=TSLA, `chart-b`=INFY), `focusedPanel='chart-b'`, `focusedSymbol='INFY'` | `"Focused chart: INFY (1d, no indicators)."` followed by `'When the user says "this" or "it", they mean INFY...'` — both lines name INFY, no contradiction (source comment cites R15-AGENT-051 directly at the `focused_chart = next(...)` lookup) | holds |
| R15-CODE-FRONTEND-015 | Same source probe as R15-AGENT-052 (shared root cause: bus-key/dockview-id convention) | Same evidence — all three panel-context publishers now share one dockview-id key convention with `PanelHost`'s `focusedSource` | holds |

Evidence: `raw/set-22/R15-LEAD-012.txt`, `raw/set-22/R15-AGENT-052.txt`, `raw/set-22/R15-AGENT-051.txt`, `raw/set-22/R15-CODE-FRONTEND-015.txt`.

COVERAGE: 4/4 ids raw; no raw: none.
