# Battery set-28: batch-7/W4-research-funnel (candidate ace7dd76, shard rc1-battery-3)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-RESEARCH-019 | run_iter_research with real visit_for_research vs live investing.com + 127.0.0.1 SSRF URL | step "error visit failed: https://www.investing.com/... (HTTP 403)"; SSRF visit returns reason 'blocked non-public or non-http(s) URL' | holds |
| R15-DATA-075 | real BSE AttachLive URL (curl 404) with AttachHis twin 200, fetch_page(AttachLive) | curl Live 404 / His 200; fetch_page ok=True with PDF text | holds |
| R15-RESEARCH-033 | run_heavy_research, explorer 2 of 3 raises | error step "explorer angle 2 ... failed: RuntimeError: explorer boom", emitted + logged | holds |
| R15-RESEARCH-023 | _filter_results on Route Mobile "All rights reserved" row | row kept (1), challenge row still blocked | holds |
| R15-RESEARCH-038 | KeylessSearchBackend, one engine failing both attempts | after 1 failed search: 2 engine calls, breaker closed, failures 1; opens after 2nd search | holds |
| R15-RESEARCH-024 | stub SearXNG row with publishedDate through web_search._dispatch and record_web | domain reuters.com, published_at 2026-07-17T10:05:00 on citation and ResearchSource | holds |
| R15-UI-038 | real brief-ingest.deriveSourceType (node strip-types), legacy "sec.gov (via Perplexity Sonar)" | filing; reuters news; blog web | holds |
| R15-RESEARCH-020 | SearxngBackend 40-row stub, options numResults 3 | 3 results, 3 citations (register: 40/8). ddg._coerce_limit helper no longer exists (refactored to base.result_limit); not part of the behaviour | holds |
| R15-RESEARCH-021 | entity_match on 'BAJFINANCE 200 DMA breakout...' | 1.0, row_relevant True (also '52-week high', KPITTECH 200 DMA) | holds |
| R15-UI-092 | real sanitizeCitationMarkers/countBrokenCitations | "[47]" -> "[?]" flagged, count 1; zero-source [3] -> [?] | holds |
| R15-RESEARCH-026 | real deriveMetrics (vite ssr bundle) market cap, no currency | "4.48T · currency unknown"; USD "$4.48T"; INR "₹4.48T" | holds |

COVERAGE: 11/11 ids raw; no raw: none
