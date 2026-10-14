# rc1 gate round 4 - adversarial sample verifier shard 1 (rc1-vshard-1, Opus)

Checkout: 68d5573aff9a579af084dcbb124843f2aecff6e8 (candidate worktree, read-only). Own sidecar :52601 booted from worktree source with its own data dir; loopback forwarder 52397->52601 for vy.py. Evidence: `verifier/shard-1/`. Log: `logs/rc1-vshard-1.md`. Environment: Yahoo returning 429 throughout (screener rows skip as rate_limited); no Gemini key.

Result: 24 checked, 24 holds, 0 refuted, 0 inconclusive. 7 adjacent defects filed in `findings/rc1-vshard-1.json`.

| id | verdict | entry repro / command | evidence | fresh variant |
|---|---|---|---|---|
| LIFECYCLE-006 | holds | vy.py agent chat, research model openai/o3-deep-research pinned, tier_b | each research call -> research_step status error "The research model openai/o3-deep-research is no longer available on OpenRouter; pick another in Settings > Research." + tool_result ok:false; assistant text still written (lifecycle006-retired-model.jsonl). RESEARCH_MODEL_OPTIONS drops the retired slugs; all 6 listed slugs in the live catalog; Settings badges "(unavailable)" | perplexity/sonar-reasoning at DEEP stop on TCS -> same honest error (lifecycle006-fresh-sonar-reasoning.jsonl) |
| RESEARCH-009 | holds | in-process deep_research ULTRA, openrouter, stubbed usage (scratchpad vshard1/test_v_metering.py) | cost 873200 tokens / $7.8588 over 236 calls accumulated via budget.add_usage | 5000-token ceiling -> "abort->synthesize: token ceiling 5000 reached" |
| AGENT-012 | holds | same run as RESEARCH-009 | BudgetGuard ceilings from the depth profile fire and abort to synthesis | ULTRA breach (see adjacent: brief note None) |
| RESEARCH-013 | holds | in-process stubs of the filings leg | NSE-only -> "nse", BSE-only -> "bse", both -> "nse+bse" | - |
| DATA-019 | holds | curl /disclosures/announcements?symbol=JUMBO | JUMBO 18 (was 0), BSE window 2026-03-31..2026-09-27 disclosed; AttachLive/AttachHis PDFs 200 | TTC 16, AMAL 21 |
| DATA-021 | holds | curl /disclosures/shareholding?symbol=SIL | split_as_of == each quarter; NSE XBRL 2023-09 confirms FII 38.86 / DII 4.05 (flat history is real) | in-process: _SPLIT_MERGE_MAX_DAYS=100 leaves splits None beyond one quarter; DAL |
| AGENT-009 | holds | real _screener_run on a live bse-all roe run (2857 skip rows) | 25 KB payload, skip_summary {rate_limited 2587, missing_field:roe 270} + 5 examples | - |
| AGENT-006 | holds | in-process fake Gemini stream, parallel calls, signature on first only | provider_meta carried, survives JSON round-trip, re-attached per function_call part | no Gemini key: live call not possible |
| LEAD-007 | holds | GenerateContentConfig validation of full catalog | 56 tools + google_search validate via parameters_json_schema | server-side acceptance of int enums / list types unverifiable (no key) |
| DATA-030 | holds | news matcher on entry cases (RELIANCE.NS, HDFCBANK, SBIN, BAJFINANCE, TCS.NS) | all tag; single-letter A/T/F/C prose does not (data030-matcher.txt). Live empty RELIANCE.NS/HDFCBANK feeds = upstream (Yahoo .NS RSS 0 items) | KOTAKBANK.NS, LT.NS, INFY.NS tag |
| AGENT-015 | holds | live workflow ai.agent_invoke on llama3.1:8b (Ollama lock held+released) | reply about "Pineapple" = typed prompt reached the agent (agent015-run.sse) | brace-bearing prompt (adjacent) |
| CODE-PLATFORM-002 | holds | live palette-shaped graphs via /workflows run | json_path, branch true/false_path, compare neq/lte, notify message_template, sleep seconds (1.0 s), indicator_id + 5 sidecar kinds emit declared ports (platform002-run*.sse) | FRED node needs a key (expected) |
| DATA-083 | holds | stub isError / non-JSON / no-content MCP results | lastToolCallOk False for openbb; sec same except non-JSON passes as prose by design | - |
| DATA-038 | holds | curl SEC sections / insider | AAPL 10-K Business + Risk Factors ~10k chars each; AAPL insider 9 rows | MSFT insider 20; NVDA 10-Q [] because upstream get_filing_sections returns only has_financials (checked direct) |
| DATA-039 | holds | curl SEC filings INFY | 40 rows incl 6-K x16 and 20-F | AAPL limit 10 -> 10; TSM 6-K present |
| DATA-035 | holds | in-process bhavcopy with _cache_dir redirected to scratchpad | HTML-200 caches nothing; 404 / header-only CSV for today reads back None; post-publish 858112 chars cached (data035-inproc.txt) | - |
| DATA-036 | holds | curl /history 1y twice | warm KSE.BO 0.34 s (was 8.7 s), provider bse | JUMBO.BO 0.34 s, TTC.BO 0.38 s |
| DATA-016 | holds | curl fundamentals DAL | 52w high/low withheld, reason "no trades in 52 weeks (last trade 2025-03-12)"; no flat forward-filled line | see adjacent (52w change 0.0, empty history no reason) |
| UI-006 | holds | screener india-all P/E 0-40 asc limit 200 | matched 2799, small caps first; header "N matched · showing top K", Show more, server sort in TSX | nse-all dividend_yield desc: same top rows at limit 20 and 1000 (matched 1382) |
| UI-007 | holds | fresh vitest (ui007-fresh.v.test.tsx.txt) | preset "High insider holding" after nested OR group + advanced + formula 'roe > 0.3' sends no formula, no dividend_yield; store group null, advanced false (ui007-vitest-fresh.log) | - |
| DATA-044 | holds | nse-all pe_ratio<20 criteria vs formula 'pe < 20' | identical results, missing_field:pe_ratio 279 itemized | bse-all price_to_book<1 itemizes 177 missing |
| DATA-020 | holds | repo RELIANCE 2026-06-09 fixtures through _dedup_key / _pair_cross_feed | NSE+BSE copies collapse (keys equal True) | live INFY/LT residual pairs (adjacent) |
| DATA-023 | holds | curl /disclosures/shareholding | promoter_pledged_percent basis "filed": SPICEJET 39.77, JPPOWER 79.2, GMRAIRPORT 16.44, CSL/DAL/RELINFRA 0.0; types/data.ts mirrors | GMRAIRPORT NSE XBRL 2026-06 EncumberedShareUnderPledgedAsPercentageOfTotalNumberOfShares 0.1644 = 16.44 |
| DATA-024 | holds | `grep -rniE 'bulk.?deal\|block.?deal\|\bsast\b' sidecar src types` (was 0 hits) | hits in routers/disclosures.py (GET /deals), catalog `exchange_deals` read_handler, copilot.json allow-list, test_b5_india_deals.py. Live KOPRAN 62 (48 bulk, 14 sast); ADANIENT 34 incl 2026-09-25 block rows | CCDL (BSE-only) 106 BSE rows; JUMBO kind=sast -> venue_not_covered with note; AAPL -> not_applicable |

## Adjacent (not refutations)

1. DATA-024 medium: a dual-listed name reads only the NSE lane; BSE-venue bulk/block deals are silently absent. KOPRAN BSE bulk sell 700000 by UNITED SHIPPERS LTD on 2026-09-07 (in-process `_bse_deals(KOPRAN, 524280, bulk)`, data024-bse-dual-listed-inproc.txt) is missing from /disclosures/deals (only the NSE 500000 row). The capability description does not disclose this.
2. DATA-030 medium: bare-ticker/company alias over-matches different listed companies: 'Reliance Power' / 'Reliance Infrastructure' -> RELIANCE.NS, 'LT Foods' -> LT.NS, 'ITC Hotels' -> ITC.NS (data030-matcher.txt).
3. DATA-020 low: cross-exchange copies still unpaired live: INFY 2026-09-18 ESOP allotment on BSE and NSE at the same minute; LT 3 pairs (2026-09-09 allotment, 09-08 newspaper, 09-01 scheme of arrangement) (data020-INFY.json, data020-LT.json).
4. DATA-016 low: DAL fifty_two_week_change 0.0 served status ok despite no trades in 52 weeks; DAL.BO 1y /history returns 0 bars, provider "none", reason null (silent empty chart).
5. AGENT-015 low: `_render_template` blanks non-context braces in a typed prompt ('Compare {sym} vs peers' -> 'Compare  vs peers'; '{1,2}' -> '').
6. RESEARCH-009 low: ULTRA budget breach leaves brief note None (DEEP sets BUDGET_STOP_NOTE); known residual that the delegate BudgetGuard does not receive research-leg spend still present.
7. DATA-023 low: CSL shareholding serves two rows with quarter_end 2026-08-20 (submissions 08-20 and 08-25), quarter_end equal to a submission date rather than a quarter end.

Housekeeping: my DATA-035 first in-process run wrote one 0-byte marker into ~/Library/Caches/bse-bhavcopy; I removed that single file (logged) and reran with the cache redirected. data024-upstream-bse-KOPRAN-bulk.json is a 403 body from a direct BSE curl (kept as record; the in-process path was used instead).
