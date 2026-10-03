# Final pass: OWNER-DRIVE panels-layouts (candidate d38b5d1a)

Driver: final-drive-panels-layouts (claude-opus-5-5, effort high), Sat 3 Oct 2026, 16:28-17:30 IST.
Method: PROMPT_surface_s2.md OWNER-DRIVE. Reads went to the shared :52800 (GET only). Writes and the
write-family routes (/workspace, /custom-agents, /workflow, /backtest, /quant) went to my own sidecar on
:52843 (final-cand/sidecar source, seed-copy data dir, 0 secrets). Layouts and workspace were driven through
the real `src/lib` code against a real dockview grid in a scratch vitest + jsdom harness (no GUI, no :5173).

Evidence: `docs/redesign/verification/r15/surface/panels-layouts/final/`
- `P-http-replay.jsonl`: all 299 census calls replayed. `P-census-vs-final.txt` is the per-call status diff.
- `P-http-extra.jsonl` + `F-*.txt`: extra probes, with full bodies.
- `L-layouts-probe.json`: templates, fit, menu modes, research space and agent arrange. `L-workspace-roundtrip.json`: the workspace round trip. `L-layouts.probe.test.tsx.txt`: the harness.

## Scored table (census -> rc1 -> final)

| Row | Census | RC1 | Final | Delta | Evidence |
|---|---|---|---|---|---|
| panel-chart | broken | ok | **ok** | holds | 30m now returns bars: SPY 43 KB, AAPL 43 KB, RELIANCE.NS 39 KB (census 0 bars); all 8 timeframes 200 for US and IN (replay 000-027) |
| charts-timeframe | broken | ok | **ok** | holds | same rows; indicators SPY rsi 30m 200 (census 502, replay 032) |
| panel-watchlist | broken | ok | **ok** | holds | 25-name mixed list 83 s cold, 0-2 ms warm (rc1 87.7 s / 0.01 s); junk symbols dropped |
| panel-news | broken | ok | **ok** (residual attached) | holds | BDL -> Bharat Dynamics (F-news-BDL.txt). RELIANCE.NS bare-alias over-match attached to R15-DATA-030 (F-news-RELIANCE.NS.txt) |
| panel-equity-overview | partial | (carried) | **partial** | narrower | every section 200 for RELIANCE, KAYNES and AAPL; junk income/ratings now an honest 404 (census 200 with an empty body). Local-model narrative driven for the first time (census NOT TESTED): 200 in 32.6 s, verified, but the typed sections collapse (reg-1, regression of R15-UI-094) |
| panel-agent-builder | partial | (carried) | **ok** | improved | CRUD/409/422 paths as census; /custom-agents/tool-ids returns the full catalog list (F-custom-agents-tool-ids.txt) |
| panel-backtest | partial | (carried) | **ok** | improved | mixed good+junk carries a warning (R15-DATA-040); short_window 999 -> 422 with message (R15-UI-010, census 200/None); start-after-end gives an honest error |
| panel-macro | broken | ok | **ok** | holds | IMF WEO India GDP 200 with real data (F-macro-imf-IND-gdp.txt); FRED keyless gives an honest message |
| panel-sec-filings | broken | ok | **ok** (residual attached) | holds | AAPL detail 20 KB of sections, insider rows present, junk accession 404 not fabricated (R15-DATA-007/038). IN/junk symbol filings now 502 'unexpected response' (census 200 empty), attached to R15-DATA-061 |
| panel-earnings-calendar | broken | ok | **ok** | holds | IN default calendar populated (R15-DATA-028); fiscal_period null (R15-DATA-067); WIT USD/INR split (R15-DATA-113); RELIANCE and INFY.NS estimates 200 (census 502) |
| panel-analyst-ratings | broken | ok | **ok** | holds | RELIANCE.NS consensus + target 200 (F-ratings-RELIANCE.NS.txt) |
| panel-option-pricer | broken | ok | **ok** | holds | binomial gamma about BS at every step count, theta negative (R15-DATA-011); RELIANCE option chain 200 |
| panel-greeks-dashboard | ok | (carried) | **ok** | same | matches census values |
| panel-bond-pricer | ok | (carried) | **ok** | same | matches census values |
| panel-yield-curve | partial | broken | **ok** | fixed | duplicate pillar -> 400 'more than one instrument with pillar ...' (census/rc1 bare 500; R15-UI-077) |
| panel-context-publishers | (unit) | (carried) | **ok** | same | covered by the candidate's own vitest; not re-driven |
| panel-broker-connect / panel-broker-order-entry | NOT TESTED | removed | **removed_with_feature** | scope (D81) | no module on candidate |
| panel-audit-log | partial | removed | **removed_with_feature** | scope (D81) | /audit-log, /audit/export, kill-switch, disclaimer-status -> 404 (replay 244-248) |
| panel-node-editor (API) | partial | (carried) | **ok** (API) / NEEDS-GUI (canvas) | improved | save/load ok; invalid-edge, cycle and unknown-type now stream run-error frames (CODE-PLATFORM-065, census 0 frames) |
| node-editor-run-overlay | partial | (carried) | **ok** (API frames) | improved | F-wf-run-*.txt |
| node-editor-code-node | partial | (carried) | **ok** | improved | `7 ** 10 ** 7` -> node-error 'power result too large' in 0.15 ms (CODE-PLATFORM-066, census stalled the sidecar); `2 ^ 10 + 1` = 1025 (F-wf-code-node.txt) |
| node-editor-palette / node-editor-save-dialog | NEEDS-GUI | (carried) | **NEEDS-GUI** | same | native drag and dialog paint; not drivable headlessly |
| layouts-arrange-templates | partial | (carried) | **partial** | improved, one new defect | all 4 templates plan correctly; research-cockpit -> chart+brief below 1180, macro-scan -> single-focus below 1080; agent arrange applies synchronously with correct labels (R15-AGENT-078 holds). New: custom arrange with unresolvable tokens reports success with nothing done (nd-1) |
| layouts-macos-menu-bridge | partial | (carried) | **ok** (dispatch) / NEEDS-GUI (native click) | improved | dispatchLayoutMenuCommand fundamental/technical/macro/compare-desk each clear and tile; bogus and no-api return false |
| layouts-workspace-save-load | partial | ok | **ok** (one new low) | holds | save/list/load/export/import/migrate round trip ok (L-workspace-roundtrip.json); `Research: X`, `a/b` (stored percent-encoded), unicode -> 200; 300-char -> honest 400; corrupt file quarantined + restored from .bak (R15-DATA-090); `__` names refused (R15-UI-046). New: delete leaves the .bak, which resurrects deleted content (nd-2) |
| charts-toolbar-draw-menu | NEEDS-GUI | (carried) | **NEEDS-GUI** | same | canvas draw gesture |
| charts-toolbar-indicators-menu | ok | (carried) | **ok** | same | catalog 200; empty list 400; unknown key 400 naming the key |
| charts-toolbar-sync-menu | (browser) | (carried) | **not re-driven** | same | no register entry touches it |
| market-session-indicator | (unit) | (carried) | **not re-driven** | same | unit-covered |
| comparison-surface | partial | (carried) | **ok** (layout) | improved | compare template + compare-desk mode tile and maximize correctly in the probe |

Totals across 32 rows: ok 20, partial 2 (equity-overview, arrange-templates), broken 0, NEEDS-GUI 3 (palette/save-dialog, draw menu, plus the canvas halves of node-editor and menu-bridge), removed_with_feature 3, not re-driven 2 (unit/browser-only rows untouched by the register), plus panel-context-publishers covered by unit tests.

## Census-to-final deltas
- **Regressions vs rc1:** none in the scored rows. The SEC IN/junk-symbol 502 and the RELIANCE.NS news over-match are attached to open blocked_tier4 entries (R15-DATA-061, R15-DATA-030), not filed as regressions.
- **Fixed since rc1:** yield-curve duplicate pillar (R15-UI-077).
- **Replay status diffs that are harness artifacts:** bt-run-get 404 (census run_id does not exist on my sidecar); ab-create-huge 201 vs 422 (census body was elided and rebuilt at 500 KB, and the model has no max length); BTC/USDT chart under asset_class=equity (the frontend sends crypto for any "/" symbol; crypto 1d/30m/1mo 200 under asset_class=crypto); ws-delete-R15 Corrupt 404 (the file had already been quarantined).
- **New findings:** nd-1 (medium), nd-2 (low), reg-1 (low, regression of R15-UI-094).
- **Observed, not filed:** IN 30m bars are stamped 09:00+05:30 (Yahoo-direct bucket alignment, upstream); IN 1wk/1mo history covers about 13 months (same as census); a backtest with no closed trades reports winRate 0.0; the shared stack's Yahoo circuit opened repeatedly under cross-lane load (environment).
- **Not driven:** a partial-unknown custom arrange (`["chart","fundamentals"]`). The planCustom code read says it applies the known subset and labels both names.
