# batch-28/W6-sonnet (shard rc1-battery-17)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52357 (data dir
`rc1-round-5-recheck-data-battery-17`), used only for the live/in-process probes below;
the frontend entries are pure client-side logic with no sidecar endpoint to exercise.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-053 | Frontend `captureTerminalState` panel-context-bus fan-out (no sidecar endpoint); pinned vitest `context-provider.test.ts:206` describe "captureTerminalState — otherPanels generic summary (R15-AGENT-053)" incl. the array-inline and headline-inline cases, plus `MacroPanel.test.tsx:144`. | Both test files present at HEAD, unmodified, assertions intact (`watchedSymbols=AAPL,MSFT` inlined, headline text surfaced). | ci_pinned |
| R15-AGENT-055 | Frontend layout-template/menu-mode mapping (no sidecar endpoint); pinned vitest `layout-templates.test.ts:537` describe "one plan per template id (R15-AGENT-055)". | Test present at HEAD, unmodified: `LAYOUT_TEMPLATE_IDS` disjoint from the 4 menu-mode ids, each menu payload maps to exactly one mode plan. | ci_pinned |
| R15-AGENT-096 | Frontend screener store (`applyFilters` flat-group-vs-flat-criteria); pinned vitest `screener.test.ts:494` "applyFilters: a FLAT group supersedes the caller's flat criteria (R15-AGENT-096)" + `host-actions.test.ts:1388`. | Both present at HEAD, unmodified: group leaves (`pe_ratio<20`) are what's sent, the stale flat criteria (`market_cap>1000`) are dropped. | ci_pinned |
| R15-CODE-FRONTEND-017 | Frontend stale-response-ordering (sec/earnings stores); pinned vitest `sec.test.ts:248` "I1: a late rejection for a previous issuer does not paint its error over the current one (R15-CODE-FRONTEND-017)" + `earnings.test.ts:149`. | Both present at HEAD, unmodified. | ci_pinned |
| R15-UI-015 | Pinned vitest `sec.test.ts:313` + `use-sidecar-retry.test.ts:25` describe "useRetryOnSidecarReady (R15-UI-015)"; supplementary live probe `curl :52357/macro/DGS10?provider=fred`. | Tests present at HEAD, unmodified. Live probe: still deterministic `502 {"code":"provider_error", detail:"FRED needs a free API key..."}` — the backend half of the register repro is unchanged, matching the "settles after one attempt on a keyless 502" pinned case. | ci_pinned |
| R15-UI-021 | Frontend chart-drawing keyboard-scope logic (no sidecar endpoint); pinned vitest `ChartPanel.test.tsx:968` "Backspace typed into a field outside the chart keeps the selected drawing (R15-UI-021)" + `:1002` "a locked drawing survives Delete" + 3 more cases in the same block. | All 5 cases present at HEAD, unmodified. | ci_pinned |
| R15-CODE-PLATFORM-017 | In-process call (candidate `sidecar/.venv`) to `services.workflow_nodes.code_node.evaluate_code` — the register's own repro cases (`round(2.5)`, `2^3`, ternary) plus batch-28's fresh cases (`log()` disallowed, `x/0`, `x**2+1`). | `round(x=2.5)` -> 3.0 (mathjs half-away-from-zero, not banker's rounding); `2^3` -> 8; ternary both branches correct; `log(x,10)` -> "disallowed syntax: Call" (never a mathjs answer); `x/0` -> "division by zero" (never Infinity); `x^2+1` x=3 -> 10. All match the certified evaluator; pinned vitest `code-node-inspector.test.tsx:145` also present, unmodified. | ci_pinned |

Raw: `battery/raw/set-80/<id>.txt` for all 7 ids.

COVERAGE: 7/7 ids raw; no raw: none.
