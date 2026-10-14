# triage-c — rc1-vshard-2:5 (tie R15-CODE-FRONTEND-015)

Auditor: triage-c, rc1 gate round 4. Written 07:27 IST. HEAD is 7c450c8e, and its code tree equals 01015033.

**Verdict: verifier_error. Severity of the residual: low (was medium in the shard).**

## Shard claim

rc1-vshard-2:5 says: "bus keys and dockview panel ids still differ for Earnings Calendar ('earnings' vs 'earnings-calendar') and Screener ('screener' vs 'screener-panel'), **so a focused Earnings Calendar falls back to the chart symbol**". Its evidence is a vitest asserting that the published key equals the dockview id.

## Tied entry

R15-CODE-FRONTEND-015 is fixed (batch 6) and has class `context-bus-key-drift`. The defect it describes is: "The agent is told the wrong focused symbol: focus source ids and panel-context bus keys never match". Its repro is a focused Equity Overview on INFY that is reported as SPY.

Its fix_shape is "One exported focusedSymbolFromBus ... and a single key convention (publish under the dockview panel id)". The pinned test for it is "focus equity-overview publishing {ticker:'INFY'} -> badge, chips and snapshot all report INFY".

A related entry is R15-AGENT-052 (fixed, focus-identity-mismatch), which re-keyed chart, equity-overview and backtest to `props.api.id`. The Earnings and Screener publishers came later, from the R15-AGENT-053 generic-summary fix, and they use literal keys.

## Facts at HEAD

The key mismatch is real:
- src/modules/earnings/EarningsCalendarPanel.tsx:178 publishes `source: "earnings"`, but src/modules/earnings/index.ts:20 registers the panel as `id: "earnings-calendar"`.
- src/modules/screener/ScreenerPanel.tsx:216 publishes `source: "screener"`, but src/modules/screener/index.ts:20 registers `id: "screener-panel"`.

Every other literal publisher matches its dockview id: news, macro, portfolio, sec-filings, analyst-ratings, option-pricer, greeks-dashboard, watchlist and backtest. Chart and equity-overview key by `api.id`.

The mismatch cannot change the focused symbol, for three reasons:
- `focusedSymbolFromBus` (src/modules/chat/context-provider.ts:243-252) reads only `payload.symbol ?? payload.ticker`.
- The Earnings payload is `{symbols, windowDays, expandedSymbol}` (EarningsCalendarPanel.tsx:176-182). The Screener payload is `{universe, resultCount, partial}` (ScreenerPanel.tsx:214-224). Neither carries a `symbol` or `ticker`.
- When the focused panel has no symbol, `captureTerminalState` falls back to the chart, then to the watchlist (context-provider.ts:398-409, commented "a panel with none falls back to a chart"). That fallback happens whichever key the panel publishes under.

## Re-run at HEAD (with a counterfactual)

This is a scratch vitest over a `git archive HEAD` copy of src (`$S/fe`; test saved as `$S/TRIAGEC_FE015.test.tsx.txt`). It renders the real EarningsCalendarPanel, has a chart publishing SPY, and focuses `earnings-calendar` as PanelHost.tsx:286 would. It then republishes the same event under the dockview id, which is what the fix_shape's convention would produce.

```
cd $S/fe && ./node_modules/.bin/vitest run src/modules/earnings/TRIAGEC_FE015.test.tsx   -> 1 passed, EXIT=0
PANEL_IDS {"earnings":["earnings-calendar"],"screener":["screener-panel"]}
AT_HEAD (publish key 'earnings', focus 'earnings-calendar') {"busKeys":["chart-chart","earnings"],"focusedSource":"earnings-calendar","focusedSymbolFromBus":null,"snapshotFocusedPanel":"earnings-calendar","snapshotFocusedSymbol":"SPY","otherPanels":[{"source":"earnings","summary":"symbols=1 item, windowDays=7"}]}
COUNTERFACTUAL (published under 'earnings-calendar') {"busKeys":["chart-chart","earnings-calendar"],"focusedSource":"earnings-calendar","focusedSymbolFromBus":null,"snapshotFocusedPanel":"earnings-calendar","snapshotFocusedSymbol":"SPY","otherPanels":[{"source":"earnings-calendar","summary":"symbols=1 item, windowDays=7"}]}
SAME_FOCUSED_SYMBOL_EITHER_WAY true {"atHead":"SPY","fixed":"SPY"}
```

The focused symbol is SPY both at HEAD and with the convention applied. The badge (ChatSidebar.tsx:2268-2287 `describeContext`) reads "Context: earnings-calendar" either way, because there is no symbol. The chips are empty either way. The sidecar's `_planner_context` and `_render_terminal_preamble` (agent_runtime.py:110-128, 433-446) key only on symbol/ticker and on chart panelId, so they are unaffected too.

The only observable difference is one label. In the `__terminal__` snapshot the agent receives via get_terminal_state, the panel's summary sits in `otherPanels` under `source: "earnings"`, while `focusedPanel` and `openPanels` say `earnings-calendar`.

## Duplicate search

I grepped the register for the publish keys, "screener-panel" and "earnings-calendar". Hits: R15-CODE-FRONTEND-015, R15-AGENT-052 (the same class, fixed) and R15-AGENT-053 (coverage). None of them records the Earnings/Screener literal keys.

## Classification

**verifier_error.** The shard tested a structural property (published key == dockview id) and attributed the chart-symbol fallback to it. That attribution is wrong. The entry's defect is a symbol that is present on the focused panel but lost, so the agent gets the wrong one. It cannot occur for panels that publish no symbol. The counterfactual shows an identical `focusedSymbol` with matching keys, and the fallback the shard observed is the designed behaviour at context-provider.ts:398-409.

What remains is a label inconsistency in the agent snapshot (`earnings` / `screener` vs `earnings-calendar` / `screener-panel`). It has no effect on the badge, chips, deixis or planner. It is **low (cosmetic)** at most, below the c/h/m bar, so the tie is not reopened.

Optional cleanup, not required for rc1: key both publishers (and their `unregisterSource`) by the dockview id (`props.api?.id ?? "earnings-calendar"` / `"screener-panel"`), as EquityOverviewPanel.tsx:550 does.

## Certification-failure count

The verdict does not land on a register entry: **0**, n/a. For reference, R15-CODE-FRONTEND-015's own baseline is 1 (batch-5 not_certified), and this verdict leaves it unchanged.
