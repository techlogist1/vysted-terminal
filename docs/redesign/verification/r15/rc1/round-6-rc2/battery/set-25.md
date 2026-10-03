# Set: batch-7/W1-india-exchange-data (set-25) — rc1-battery-17, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd, sidecar :52357 (own openbb-mcp :52390, sec-edgar-mcp :52391)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-014 | GET /fundamentals/{DAL,FUSION,JONJUA} | DAL revenue_ttm 99.7M (9.97 Cr, = screener) provider bse, "standalone, sum of 4 filed quarters to 2026-06-30", Yahoo's 27.6M "not served"; FUSION 17,144.2M (1,714 Cr, NSE filed) with Yahoo 8,582M disclosed not served (screener 1,699); JONJUA half-yearly filer status "flagged" ("TTM basis ... quarter unfiled or unparsed; kept, flagged") not stated as fact | holds |
| R15-DATA-027 | GET /fundamentals/{DAL,AAPL,TCS IN} | DAL/FUSION/TCS revenue_ttm provider bse/nse (exchange-filed lane ahead of yfinance); AAPL stays yfinance | holds |
| R15-DATA-076 | GET /fundamentals/{DAL,FUSION} | DAL revenue_growth 0.452 provider bse, "period to 2026-06-30 vs the same period to 2025-06-30"; FUSION 0.0546 nse with Yahoo's 128.1% "not served" | holds |
| R15-LEAD-004 | GET /fundamentals/{DHANBANK,TCS} (quarterly filers) | no "half-yearly" text anywhere in either response; both "sum of 4 filed quarters to 2026-06-30" | holds |
| R15-DATA-050 | GET /disclosures/results?symbol={JONJUA,DAL,ELCIDIN,CHTR} | all HTTP 200: 10/10/10/4 events (JONJUA Results 2026-08-12; ELCIDIN Results 2026-08-13, sources NSE+BSE); were 502 | holds |
| R15-DATA-060 | GET /disclosures/{shareholding,announcements,results}?symbol=SIFY, shareholding AAPL, 20-F lane via SIFY/WIT | all HTTP 200 coverage not_applicable with note (was 502); 20-F lane (region US, fresh cache key): SIFY coverage covered provider sec-20f, holders 67.98+7.90+7.56+0.34 = 83.78; WIT covered sec-20f | holds |
| R15-LEAD-015 | GET /fundamentals/DHANBANK/income?period=quarterly and annual | quarterly gaps ["2025-09-30"], every line null at that period; annual periods ISO ['2026-03-31', ...], gaps [] | holds |

COVERAGE: 7/7 ids raw; no raw: none
