# rc1 adversarial verifier — shard 1 (rc1-vshard-1, round 2)

Candidate: `81fbfe910d472ecd154fa62e42d86bce213a697e` (worktree `rc1-4c6dfe8-fix-int`, read-only).
Own sidecar :52601 booted from the candidate source (data dir `rc1-data-rc1-vshard-1-r2`); the shared :52152 was used for GET and read-only openrouter research runs only.
Scratch evidence was copied to `verifier/shard-1-evidence/` (no secrets). Findings: `findings/rc1-vshard-1.json`.

Tally: 20 holds, 4 refuted (2 of them are register-open entries that were never certified), 0 inconclusive. DATA-029 has one sub-part (live estimates) that was first blocked by a Yahoo 429 and then passed on retry.

## Verdicts

| id | verdict | command (short) | evidence |
|---|---|---|---|
| RESEARCH-016 | holds | `r016.py`: live `run_heavy_research("Jonjua Overseas outlook")` with real tools | 13 sources, including 5 bseindia filing-floor rows. iter.py always runs `_record_web` on the floor rows (`r016-jonjua.txt`) |
| RESEARCH-020 | holds | 40-row stub backend, numResults 3/1/12/25, plus dispatch with 5 | Exact counts every time (`research020.txt`) |
| RESEARCH-024 | holds (web rows) | research brief with a web lane | livemint.com row has its host plus published_at. The news-lane gap is adjacent finding 5 (`research024.txt`) |
| DATA-021 | holds | `d021diag.py` for SIL and DIXON | No years-old split is copied, and splits are all None. The reason is that the BSE SHP lane is dead (adjacent finding 1, HIGH) |
| DATA-024 | holds | GET exchange deals: KOPRAN, SUZLON, YESBANK, JONJUA, NAPEROL | KOPRAN bulk 48 / sast 14; SUZLON sast; YESBANK sast+block; BSE-only JONJUA bulk 145; NAPEROL bulk+block. exchange_deals is in the copilot and researcher tools |
| DATA-029 | holds | in-process `_yahoo_symbol`; GET /news IN; GET /earnings/{INFY,SBIN,RELIANCE.NS}/estimates | RELIANCE.NS / 532540.BO / BDL.NS / INFY.NS / JONJUA.BO map correctly. No Flanigan's items. INFY now resolves to INFY.NS with INR EPS 19.58. First try hit Yahoo 429; the retry returned 200. Adjacent finding 2: the INFY revenue estimate is INR but labelled USD |
| AGENT-010 | **refuted (not certified)** | `a010.py`; `sed -n 1574p sidecar/services/symbol_resolver.py` | The stall is fixed: loop lag 17 ms with a 1 s blocking stub, and a raising resolver gives ok:false. The fix_shape also asks for an explicit yf.Search timeout, and `yf.Search(query, max_results=5, news_count=0)` still has none (yfinance default 30 s) |
| AGENT-013 | holds | `delegate.sh`: live delegate run (copilot, llama3.1:8b, under the ollama lock) then GET /runs/{id} | 2784-char answer, untruncated, plus a persisted brief. The frontend delivery path is in delegate-runs.ts (`a013-deleg.txt.run.json`) |
| AGENT-016 | holds | POST :52601 /workflow/run: strategy_critic with no key; researcher with provider=ollama | No-key case: node-error "Something went wrong with Anthropic." and run-error "failures in nodes: ['crit']". Fresh case: researcher on ollama completed in 47.7 s and was answered by the local model, not the openai default (`wf2.out`) |
| CODE-PLATFORM-014 | holds | code read of plugin-runtime.ts, marketplace.ts and their tests | `reloadPlugin` = unload then load. loadPlugin re-resolves secrets and runs initialize. configure() calls reloadPlugin after the grant persists, and a disabled plugin stays stopped. Tests plugin-runtime.test.ts:175 and marketplace.test.ts:122 pin it |
| LIFECYCLE-004 | holds | `l004.py` on a live TCS window, plus a BSE bhavcopy | Renaming each of O/H/L/V makes nse_direct raise ProviderError, and the registry falls through to jugaad with 27 real bars. A BSE bhavcopy with a renamed volume column raises ProviderError |
| LIFECYCLE-006 | holds | `vy.py` researcher on :52152 with o3-deep-research (literal); fresh perplexity/sonar-reasoning | Both produce an error research_step with the named message. The live catalog has all 6 static options and none of the 3 retired slugs (`l006-*.jsonl`, `or-models.json`) |
| CODE-AGENT-016 | holds | load agent JSONs with defaultProvider openrouter/xai/deepseek/bogus | The three load; bogus gives a schema violation (`cagent016.txt`) |
| CODE-AGENT-018 | **refuted** (register status open) | `python3 -c '...print(a._STAGEABLE_PLAN_ACTIONS == a._READ_SAFE_PANEL_ACTIONS)'` | `True`: the two sets are still identical, with no stated relation and no pinning test (`cagent018-020.txt`) |
| CODE-AGENT-020 | **refuted** (register status open) | `grep -n "GeminiProvider(\|GroqProvider(" sidecar/services/llm/__init__.py` | Lines 114 and 116 construct the providers with no base_url, so the override is dropped |
| DATA-036 | holds | `d036.sh`: GET /history 1y, cold and warm | BSE-only JONJUA: 0.45 s cold, 0.33 s warm, 244 bse bars. DAL 0.56 s |
| UI-090 | **refuted (not certified)** | `ui090.py` (in-process, frozen clock) | The literal case (AAPL at NSE hours under IN) gives eod, and the IN indices give live under IN and US. Fresh cases: BHP.AX with the ASX closed and VOD.L with the LSE closed, both during US hours, read `live` because `instrument_region` sends every non-IN symbol to the US calendar. The live app serves both via yfinance |
| DATA-016 | holds | GET fundamentals and history for DAL; fresh cases NAPEROL and ELCIDIN | DAL 52-week high/low are withheld ("no trades in 52 weeks (last trade 2025-03-12)") and history returns 0 bars, so no flat line is drawn. Adjacent finding 7 covers the stray dates and change fields |
| UI-006 | holds | POST /screener/run: india-all pe 0..40, sort pe asc, limit 200; nse-all roe>0.25, sort mcap asc, limit 20 | matched 2707 > result 200, and 215 > 20. Both sorts are monotonic with 0 nulls, and the true lowest P/E (ZSOUTGAS.BO 0.03) surfaces. The header renders "N matched · showing top K by <field>" and Show more. Pinned in test_screener.py:335/650 and ScreenerResultsTable.test.tsx |
| UI-008 | holds | `curl -X POST :52601/llm/keys/validate '{"provider":"openrouter","api_key":"sk-or-v1-000…"}'`, and the key `hello-not-a-key` | Both give `ok:false, reason:invalid`. validate_key probes `/key`. Onboarding, Settings and KeyEntryDialog all go through validateProvider |
| UI-012 | holds | `curl -X POST :52601/agents/nope/invoke -d '{"prompt":"hi"}'` (404 string detail) and `-d '{}'` (422 array) | streaming.ts:343-348 parses the body and runs `extractSidecarDetail`, which handles string details and 422 arrays. Sibling consumers are adjacent finding 8 |
| DATA-067 | holds | GET /earnings/upcoming | 60 events, none with fiscal_period, and no producer sets it |
| DATA-020 | holds | GET disclosures for DIXON and TATASTEEL | DIXON: 36 NSE / 4 BSE items with 0 residual pairs. TATASTEEL: 2 residual pairs, both the documented category-mismatch known limitation |
| DATA-044 | holds | POST /screener/run nse-all with pe_ratio<20 as a criterion vs formula `pe < 20`; fresh price_to_book<1 and dividend_yield>0.03 | Criterion and formula agree: matched 853, skipped 1176, NULL rows listed as `missing_field:pe_ratio`. The fresh fields are itemized the same way (983 and 2178 skipped). Pinned in test_screener.py:687 |

## Adjacent findings (not refutations)

1. **HIGH, near DATA-021.** `bse_provider._fetch_shp_index` uses plain httpx against `api.bseindia.com/.../SHPQNewFormat/w` and gets 403 "Access Denied". `_api_json` (curl_cffi) returns 200 with data for the same call. As a result there is no FII/DII split for any name, and BSE-only shareholding (ELCIDIN 503681) returns provider_error.
2. **MEDIUM, near DATA-029 (and DATA-113).** The INFY.NS estimate reports revenue_estimate_mean 491,180,745,790 with `revenue_currency: USD`. Yahoo gives financialCurrency USD (quarterly revenue 5.08e9 USD), but the calendar "Revenue Average" is in INR, the trading currency. `_revenue_currency` applies financialCurrency to the calendar figure, so the grid shows about $491B.
3. **MEDIUM, near RESEARCH-024.** News-lane research sources have no published_at, and their domain is a feed label ("Yahoo! Finance: DIXON News"). Filing-floor rows carry their date only inside the excerpt.
4. **LOW, near RESEARCH-020.** The web_search category never reaches a backend: dispatch passes `category`, SearXNG reads `categories`, and the other backends ignore it.
5. **LOW, near DATA-016.** DAL still ships 52-week high/low dates of 2025-09-25 (a forward-filled bar) and fifty_two_week_change 0.0, both with status ok, while the range itself is withheld.
6. **LOW, near UI-012.** Two other stream consumers still show raw FastAPI errors. `workflow.ts runWorkflow` throws the raw error text (a 422 on `{"spec":{}}`). The `screener.ts` stream puts a 422 detail array into the error string, giving `[object Object],…`.

## Notes

- Local-model fabrication was not treated as a finding (known limitation, DECISIONS 4.9-4.12). No GUI entries were checked.
- The ollama lock was taken with mkdir and released by the trap for each held call; the lock is absent at the end.
