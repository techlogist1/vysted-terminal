# batch-4/W5-panels-screener (rc1-battery-6, gate round 5-recheck, candidate 949c3c9f)

Own sidecar :52346 (candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, seed-data copy `rc1-round-5-recheck-data-rc1-battery-6`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-004 | jsdom render is this entry's own repro; vitest owned by the heavy lane in this shard — read the pinning test | `PortfolioPanel.test.tsx:116` "R15-UI-004: a failed live-quote fetch shows the banner and Retry re-fetches" asserts `/Couldn't refresh live quotes/` banner + Retry re-fetch and clear | ci_pinned |
| R15-UI-005 | jsdom render; read the pinning tests | `PortfolioPanel.test.tsx:138` (partial: totalValue 2000, note names ZZZNOTREAL) and `:180` (all-unresolved: totalValue null, no fabricated 0.0%) | ci_pinned |
| R15-UI-006 | Live `POST /screener/run` india-all, `0<pe_ratio<40`, sort pe_ratio asc, limit 200 vs limit 1000 | limit=200 → `result_count 200, matched_count 3046`, strictly ascending PE from 0.0005; limit=1000 → `result_count 1000` (same `matched_count 3046`) — matched_count distinct from the page cap, raising limit surfaces more rows | holds |
| R15-UI-007 | jsdom store+component render; read the pinning test | `ScreenerPresets.test.tsx:33` "R15-UI-007: a preset resets a nested group + formula, not just criteria" | ci_pinned |
| R15-DATA-044 | Live `POST /screener/run` nse-all, `pe_ratio<20` | `evaluated_count 2738, skipped_count 768`; skip reasons `{missing_field:pe_ratio: 508, rate_limited: 260}` — NULL pe_ratio itemized, not silently counted; `coverage: "screened 2,738 of 3,506 — 768 unavailable"` | holds |
| R15-DATA-093 | Live `POST /screener/run` custom bare Indian tickers `[RELIANCE,TCS,INFY,HDFCBANK,COCHINSHIP]` (no `.NS`) | `evaluated_count 5, skipped_count 0`, all 5 resolved to `.NS` INR rows in 14ms (served warm) — bare-ticker resolver fix confirmed without needing to force the circuit open | holds |
| R15-UI-003 | Live backend: `GET /custom-agents/tool-ids`, then `POST`+`PUT /custom-agents` round-trip with `tools:[research,web_search,price_data]`, `default_provider:openrouter` | Backend: 56 tool ids (incl. research/web_search/publish_brief); create+PUT round-trips the full tool array and `openrouter` unchanged — API layer was never the limiting factor. Core defect is frontend-only (`form.tsx` hardcoded fallback array); verifying the UI truncation itself needs jsdom, not run here | ci_pinned |
| R15-CODE-FRONTEND-020 | jsdom render; read the pinning test | `agent-builder.test.tsx:331` "case not written against: a tool id the sidecar lists but the fallback array lacks is selectable" — fresh case beyond `KNOWN_TOOL_IDS`, proving the render is no longer tautological | ci_pinned |
| R15-LIFECYCLE-007 | In-process, exact repro PATH: `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin` calling `services.searxng_manager._resolve_docker_binary()` directly against the candidate's sidecar venv | `resolved: /usr/local/bin/docker` (OrbStack's docker, found via the `_KNOWN_DOCKER_LOCATIONS` fallback after `shutil.which` misses the minimal launchd PATH) — the exact repro condition no longer reports `cli_present:false` | holds |

Evidence: `raw/set-15/R15-UI-004.txt`, `raw/set-15/R15-UI-005.txt`, `raw/set-15/R15-UI-006.txt`, `raw/set-15/R15-UI-007.txt`, `raw/set-15/R15-DATA-044.txt`, `raw/set-15/R15-DATA-093.txt`, `raw/set-15/R15-UI-003.txt`, `raw/set-15/R15-CODE-FRONTEND-020.txt`, `raw/set-15/R15-LIFECYCLE-007.txt`.

COVERAGE: 9/9 ids raw; no raw: none.
