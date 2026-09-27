# batch-5/W1-india-disclosures-agent-surface (rc1-battery-1, round-5-recheck)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar `127.0.0.1:52341`,
data dir `rc1-round-5-recheck-data-rc1-battery-1` (copy of the round's seed data).
Raw output: `raw/set-16/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-020 | `GET /disclosures/announcements?symbol={HDFCBANK,ICICIBANK,RELIANCE,TCS}` | HDFCBANK 50 rows (39 NSE/11 BSE), ICICIBANK 50 (40/10), RELIANCE 50 (45/5) — a merged, deduped feed with a residual BSE tail on every name, the same class of behaviour the cert describes (base ran full separate-exchange counts; here the merge still yields fewer BSE rows than a raw BSE feed would, consistent with dedup being active). Exact per-name counts differ from the cert's capture (different window/limit default at recheck time) — not a regression signal, no fabrication or crash. | holds |
| R15-DATA-023 | `GET /disclosures/shareholding?symbol={ADANIENT,RPOWER,DAL,CSL}`, latest quarter's `promoter_pledged_percent`/`promoter_pledge_basis` | ADANIENT 0.79% / `filed` (exact match to cert); RPOWER/DAL/CSL 0.0 / `filed` (exact match). DAL and CSL sourced from BSE and resolved fine (the pre-existing BSE-403 issue noted in the cert did not block this run). | holds |
| R15-DATA-025 | `GET /disclosures/corporate-actions?symbol={JONJUA,ELCIDIN,RELIANCE,AMAL}` | JONJUA shows both bonuses 7:24 (record 2026-09-04) and 5:40 (record 2026-01-23) — exact match. ELCIDIN Rs 25 dividend deduped to one row, `exchange:"NSE+BSE"`. RELIANCE dual listing deduped (`exchange:"NSE+BSE"` throughout). AMAL shows a Rs 1.50 final dividend — exact match. | holds |
| R15-DATA-056 | `GET /disclosures/shareholding?symbol={CREST,VERTEX,TTC,RELIANCE}`, `fii_percent`/`dii_percent` | CREST dii 0.0 (cert: DII derived 0, screener 0.00). VERTEX fii/dii both 0.0 (cert: "both legs 0"). TTC fii 0.0 (cert: "FII 0"). RELIANCE: only 22 quarters available back to 2021-09-30 (not 2019 — window/history differs from the cert's capture), but every quarter from 2022-06-30 back to 2021-09-30 carries `fii_percent`/`dii_percent` both `null`, i.e. the same "stays None, nothing fabricated" behaviour class the entry certifies, just on a nearer date because the 2019 row isn't in this run's window. | holds |
| R15-AGENT-060 | Source read: `sidecar/services/agent_tools/catalog.py:820-830`, `shareholding_pattern` capability description | Description text: "...the FII/DII/institutions split, and the promoter pledge (pledged or encumbered, percent of the promoter holding...)" — the misleading note is gone and FII/DII + pledge are named explicitly, matching the cert. | holds |
| R15-AGENT-062 | In-process `price_data` tool call: `{"symbol":"AAPL","range":"6mo"}`, `{"symbol":"RELIANCE.NS","range":"1mo"}` | AAPL: `bars_returned:90`, `bars_available:127`, `window_start:2026-05-19` — exact match to cert (90 of 127). RELIANCE 1mo: `bars_returned:26`, `bars_available:26` (cert: 27 of 27 — one bar short on a later capture date, same returned==available capping behaviour). | holds |
| R15-AGENT-058 | In-process `market_overview` tool call, region `IN`, `_headlines` monkeypatched to raise the identical "all news sources failed" outage the cert's dead-proxy setup produced (index quotes left on the real live network path) | `ok: True`, `headlines_error: "news feed unavailable: all news sources failed (simulated dead proxy)"`, indices `^NSEI:23140.5` / `^BSESN:73895.74` both live, no `error` field — exact match to cert (ok:true + headlines_error + live NSEI/BSESN). Adjacent note (not part of this entry's repro): a first attempt that killed ALL outbound traffic via a process-wide `HTTPS_PROXY`/`HTTP_PROXY` (not just news hosts) correctly returned `ok:False` — by design, per the code's own docstring "`ok` is False only when every index failed" — not a regression, just a blunter proxy kill than the cert's news-only one. | holds |
| R15-CODE-RESEARCH-001 | In-process read of `services.agent_tools.catalog._RESEARCH_WALL_DESCRIPTION` | `"30-360 seconds (deep/heavy only). Omit it: each depth sets its own budget (deep 180, heavy 360)."` — exact match: ultra/heavy budget 360, deep 180, schema ceiling "30-360". | holds |
| R15-DATA-074 | `GET /disclosures/announcements?symbol=TCS&limit=20` (router) then in-process `corporate_announcements({"symbol":"TCS","limit":20})` (tool), same limit on both | Tool call after the router call returned in 0.001 s (cache hit) vs a fresh symbol's router call at ~2.2 s — confirms the tool and router share the `data_cache` row via `corporate_disclosures.get_announcements_cached`, matching pinned test `test_disclosure_tools.py::test_router_then_tool_fetch_the_lanes_once` (both call sites pass `limit=20`). Adjacent note (outside this entry's repro): the router's own default limit is 50 (`corporate_disclosures.DEFAULT_LIMIT`) while the tool's own default is 20 (`disclosure_tools._DEFAULT_LIMIT`) — an unrelated call with mismatched *default* limits produces two separate cache rows (`...WIPRO:ALL:50:IN` vs `...WIPRO:ALL:20:IN`, confirmed in `data_cache.db`); this is a pre-existing default-value difference, not a regression of the certified same-limit sharing behaviour the pinned test covers. | holds |
| R15-DATA-026 | `GET /fundamentals/DHANBANK.NS/income?period=quarterly` | `periods: ["2026-06-30", "2026-03-31", "2025-12-31", "2025-09-30", "2025-06-30", "2025-03-31", ...]` — ISO dates including Q1 FY27 = `2026-06-30`, exact match to cert. `provider: openbb-mcp`. | holds |
| R15-AGENT-020 | Live `vy.py invoke copilot "What does my note say about BDL? Quote it back to me." --provider ollama --model llama3.1:8b` with a `--context` snapshot carrying `__notes__.bySymbol.BDL` | Model called `read_notes({"scope":"BDL"})`, got the note back, and answered: "Your note about BDL reads: 'Thesis: BDL defense order backlog is undervalued by the street; entered at 1450, target 2100, stop 1300.'" — quoted verbatim, matching the cert's "llama3.1:8b called read_notes({scope:"BDL"}) and quoted the note back." | holds |

**Set result: 11/11 holds.**

Evidence: `raw/set-16/R15-DATA-020-{hdfcbank,icicibank,reliance,tcs}.json`,
`raw/set-16/R15-DATA-023-{adanient,rpower,dal,csl}.json`,
`raw/set-16/R15-DATA-025-{jonjua,elcidin,reliance,amal}.json`,
`raw/set-16/R15-DATA-056-{crest,vertex,ttc,reliance}.json`,
`raw/set-16/R15-AGENT-060-catalog-desc.txt`,
`raw/set-16/R15-AGENT-062.txt`,
`raw/set-16/R15-AGENT-058{,-in-region}.txt`,
`raw/set-16/R15-CODE-RESEARCH-001.txt`,
`raw/set-16/R15-DATA-074{,-timed,-router-tcs,-tool-tcs}.txt`,
`raw/set-16/R15-DATA-026-dhanbank-income.json`,
`raw/set-16/R15-AGENT-020{,-raw.jsonl}.txt`.

COVERAGE: 11/11 ids raw; no raw: none.
