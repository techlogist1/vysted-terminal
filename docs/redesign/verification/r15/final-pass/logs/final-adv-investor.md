# final-adv-investor working log

Head under test d38b5d1a. Stack booted from final-cand/src-tauri/binaries (built artifact).
- openbb-mcp :52811, sec-edgar-mcp :52812, main :52810 (clean stranger profile final-stranger-investor, keystore {"secrets":{},"migrated":true}), main2 :52815 (final-adv-investor-data, seed copy).
- pids: scratchpad/inv/pids.txt (stop = kill sleep pids only). Launch t0 = epoch 1791018975.
cold boot: t0+239s to /health 200 on 52810 and 52815 (4 onefile sidecars + 2 other adversary stacks extracting concurrently; XprotectService scanning _MEI .so files at 51% CPU)

## DS-1 / DS-2 (done; see scenario files)
- Filed investor:1 (AMAL.NS market cap unavailable while AMAL.BO serves it; regression R15-DATA-048), investor:2 (NSE Emerge SME /fundamentals 404), investor:3 (SUNRAJDI P/E 155.5 beside filed EPS 0.23; regression R15-DATA-013).
- Dropped, with reasons:
  - DAL 52w dates and 1Y change 0.0: literally accurate for the window served, not rendered as a claim.
  - SUNRAJDI BVPS disagreement: no authoritative filing to arbitrate between sources.
  - KARAMTARA P/E gap vs screener.in: the witness lags on a new listing.
  - NSE results calendar empty: it is a forthcoming-events feed, not history.
- Outside access: api.bseindia.com Akamai "Access Denied"; screener.in used as witness. stockanalysis.com SIFY forecast 404.

## DS-3 (partial)
- SIFY: revenue_ttm carries financial_currency INR; P/S, BVPS, P/B withheld with reasons (DATA-008 holds). EPS -0.13 is USD per ADS; no adr_ratio stated. Estimate revenue mislabelled INR -> investor:4.
- WIT / IBN fundamentals: Yahoo 429 at first attempt (retry later).
- KPIT brief run attempt 1 (15:02:18) was killed with its parent shell at a context compaction; the lock trap released the lock (no EXIT line). Relaunched under nohup at 15:07:48.

## DS-4 (done)
- investor:5 GSTL cross-company ISIN stamp (regression R15-CODE-DATA-001); ratio 0.826 >= 0.75 at symbol_resolver.py:1510.
- investor:6 autocomplete hides the BSE company of every same-ticker collision.
- DATA-002 attachment written to ATTACHED.json (bare AMAL under IN).

## DS-5
- 6 POST /screener/run at 15:09 (custom mixed INR/USD list, nifty50, sp500). Mixed list ranked within each currency, coverage names both; nulls last; result_count == matched_count == rows; null pe_ratio itemized as missing_field. Custom-universe threshold label is "listing currency" (ScreenerCriteriaBuilder universeMoneyUnit) — disclosed, not a defect.

## 15:20-15:31 IST — DS-6/7, RS, AC-1, free
- DS-6: RELIANCE.BO earnings two quarters stale vs .NS, analyst count/target differ -> investor:7.
- DS-7: ownership reconcile correct on 9 names; zero-mismatch witness says "beyond 3pp" -> investor:8.
- RS-1: openai grounded; ollama normal kl-2; ollama deep 259 s vs 180 s wall -> investor:11; figures kl-1.
- RS-2: FOCUS deep brief kept "Focus on flying" / "focus on inflation data" headlines; root cause relevance._entity_signals + IN-skipped
  COMMON_WORD_TICKERS gate -> investor:12 (regression R15-RESEARCH-001; overlaps open R15-LEAD-056). Flagged P/E 71.18 shown as fact (class of investor:3/9).
- RS-3: pass (keyless search breaker honest). RS-4: FAST budget, attached to DECISIONS 4.1.
- AC-1: openai p2 investor:9, p3 investor:10, rest pass; no-key/bad-key humanized; OpenRouter (ling 404, gemma pool 429) and DeepSeek (402)
  environment; ollama grounded except p4 -> kl-4.
- free-investor-1: low-P/E screen, IDEA 3.62 genuine (one-off income), negatives on the row, rate-limit skip disclosed -> pass.
- Ollama lock: the final rmdir in olrun found the lock already gone (15:29:19) — my last hold ended at 15:29:19 with EXIT=0; no lock left behind.
