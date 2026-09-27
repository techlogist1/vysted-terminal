# Regression battery — batch-4/W5-panels-screener (set-14)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Sidecar `rc1-battery-6` on `:52346`
(candidate source, isolated data copy `rc1-round-5-data-rc1-battery-6`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-044 | `POST /screener/run` nse-all, `pe_ratio<20`, limit 1000 | `coverage: "screened 2,684 of 3,506 — 822 unavailable"`; `skip_details` breakdown `missing_field:pe_ratio: 552`, `not_found: 270` (was "0 unavailable" pre-fix) | holds |
| R15-DATA-093 | `POST /screener/run` custom universe, bare `RELIANCE TCS INFY HDFCBANK COCHINSHIP` | `evaluated_count:5, skipped_count:0`, all five rows resolved to `.NS` symbols with live quotes (`coverage: "screened 5 of 5 — 0 unavailable"`) | holds |
| R15-LIFECYCLE-007 | in-process `services.searxng_manager._resolve_docker_binary()` under `env -i PATH=/usr/bin:/bin:/usr/sbin:/sbin` (Finder/Dock-launch PATH) | resolved `/usr/local/bin/docker` (the operator's real OrbStack symlink) instead of failing `shutil.which` | holds |
| R15-UI-003 | `GET /custom-agents/tool-ids` (56 ids incl. research/web_search/publish_brief); source read of `form.tsx`/`AgentBuilderPanel.tsx` | backend catalog live-fetched and used as source of truth; `KNOWN_TOOL_IDS` is fallback-only comment-annotated R15-UI-003; provider is an open string, no `KNOWN_PROVIDER_IDS` gate | ci_pinned — `src/modules/agent-builder/agent-builder.test.tsx:266,331`; backend half live-verified above |
| R15-UI-004 | source read `src/modules/portfolio/api.ts` + `PortfolioPanel.tsx` | `fetchPositionQuote` returns `{quote}\|{error}` union (no swallowed null); `PortfolioPanel` sets `quotesError = failed > 0`, banner + Retry wired at :1184-1195 | ci_pinned — `PortfolioPanel.test.tsx:117` ("a failed live-quote fetch shows the banner and Retry re-fetches") |
| R15-UI-005 | source read `metrics.ts` + `PortfolioPanel.tsx` | `totalValue`/`totalValueNote` computed from `mixedCurrencies`/resolved buckets, no bare `0` fallback path found | ci_pinned — `PortfolioPanel.test.tsx:141,175` |
| R15-UI-006 | `POST /screener/run` nse-all, `0<pe_ratio<40`, `sort_by=pe_ratio&sort_dir=asc`, limit 200 | `result_count:200, matched_count:1918, evaluated_count:2684`; rows strictly ascending by `pe_ratio` (`0.0005..0.407..`) | holds |
| R15-UI-007 | source read `ScreenerPresets.tsx:127-137` + `store/screener.ts` | preset apply path (`applyFilters`) explicitly resets `group:null, advanced:false, formula:""` before writing preset criteria (comment cites R15-UI-007) | holds (source); test `store/screener.test.ts:475,494` covers `applyFilters` behavior directly |
| R15-CODE-FRONTEND-020 | source read `agent-builder.test.tsx` + `sidecar/tests/test_custom_agents_router.py` | test now asserts against a mocked live-fetched `brand_new_tool` id absent from the fallback array (:331-346); pytest `test_tool_ids_equals_agent_selectable_tool_ids` pins route == catalog parity | ci_pinned — `agent-builder.test.tsx:331`, `test_custom_agents_router.py:77` |

Raw output: `battery/raw/set-14/*.txt`.

COVERAGE: 9/9 ids raw; no raw: none.
