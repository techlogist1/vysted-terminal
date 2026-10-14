# Set: batch-4/W5-panels-screener (set-14) — rc1-battery-10, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-004 | test pin check (jsdom; vitest owned by heavy lane) | api.ts returns {error} not null; test `R15-UI-004: a failed live-quote fetch shows the banner and Retry re-fetches` exists (PortfolioPanel.test.tsx:117) | ci_pinned |
| R15-UI-005 | test pin check | "no live quotes resolved" note + tests PortfolioPanel.test.tsx:141,175 | ci_pinned |
| R15-UI-006 | live POST /screener/run india-all 0<PE<40 limit 200 sort pe asc | result_count 200, matched_count 3057, evaluated 4231, ascending from PRITI.NS 0.0005 / SATCH.BO (small caps lead) | holds |
| R15-UI-007 | test pin check | `R15-UI-007: a preset resets a nested group + formula, not just criteria` (ScreenerPresets.test.tsx:33) | ci_pinned |
| R15-DATA-044 | live nse-all pe_ratio<20 vs formula 'pe < 20' | coverage 'screened 2,686 of 3,506 — 820 unavailable'; 567 missing_field:pe_ratio itemized; formula identical coverage | holds |
| R15-DATA-093 | live custom_symbols RELIANCE TCS INFY HDFCBANK COCHINSHIP (bare) | 5/5 evaluated as RELIANCE.NS...; circuit not forced open (adjacent: pinned by test_screener.py:784) | holds |
| R15-UI-003 | live GET /custom-agents/tool-ids + POST/PUT custom agent openrouter + [research,web_search,price_data] | 56 ids == catalog 56 incl. research/web_search/publish_brief; PUT keeps tools+openrouter; UI half pinned by agent-builder.test.tsx:111,273 | holds |
| R15-CODE-FRONTEND-020 | test pin check | agent-builder.test.tsx:342 brand_new_tool live-catalog test + sidecar test_custom_agents_router.py tool-ids route | ci_pinned |
| R15-LIFECYCLE-007 | env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin; _resolve_docker_binary + _run_docker --version | resolved /usr/local/bin/docker; rc 0 'Docker version 29.4.0' | holds |

Note: own sidecar died once mid-set (unattributed external kill, log has no trace); restarted on :52350, all probes below it re-run.
