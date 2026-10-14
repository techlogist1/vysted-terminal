# Batch-28 fresh-context verification (Opus)

**Merge target:** `worktree-agent-batch-28-int@c780c5161e26ab2366d991df64503eaf5d384dc6`.

**Verdict: approve.**
- The chain is green: integrator `ci-2.log` ends `CI_EXIT=0` (3751 passed, 1 skipped), and `smoke.log` has `SMOKE_EXIT=0`.
- 25 entries certify, and none of them is a regression.
- 5 entries are not certified. Each is a partial improvement over base, not a regression.
- R15-LEAD-046 is concurred as not-a-defect.

**Rig**
- A scratch worktree of the integration head ran the main sidecar from source on 127.0.0.1:52310, with a copied data dir and MCP on :52153/:52154.
- A second instance on :52311 used an empty data dir for the cold-cache cases.
- Local model: llama3.1:8b via `scripts/r15/vy.py`. No OpenAI-direct spend.
- Frontend checks ran as scratch `B28V_*` vitest files in the scratch worktree; the CODE-PLATFORM-017 case called the live sidecar. All were deleted afterwards.
- Every certification uses at least one fresh case that the fix was not written against.

**R15-DATA-030** was not marked fixed. The integrator reverted its alias half in c780c516 because it broke single-word company names, so DATA-030 stays open and was not verified here.

## Certified

| id | original repro (live or in-process) | fresh case |
|---|---|---|
| DATA-003 | Under US, AMAL is not_applicable on shareholding, announcements, corporate-actions, deals and results, even right after an IN request warmed the cache. Under IN or with no header: 104 patterns, promoter 71.35. AMAL.BO under US is still served. | PNC: not_applicable under US, served under IN. HAL under US: not_applicable. HAL.NS under US: served. llama answers the PNC shareholding question honestly: "not a listed instrument on the NSE or BSE". |
| DATA-024 | KOPRAN bulk sources ["NSE bulk","BSE bulk"], with 60 BSE rows (incl. 2026-09-07 UNITED SHIPPERS sell 700000). | RELIANCE: 331 BSE rows at about 1383.9. SAKSOFT: BSE lanes present, no errors. |
| LEAD-022 | 2222.SR is SAR, SAP.F EUR, GGAL.BA ARS. | BMW.DE EUR, 005930.KS KRW, NESN.SW CHF, BHP.AX AUD. BRK.B maps to BRK-B and BF.B to BF-B. |
| DATA-038 | AAPL 10-Q 0000320193-23-000077: total_chars 49985 ("Filing Content"). AAPL 8-K: 4430. | MSFT 8-K 0001193125-26-380280: 4382. NVDA 10-Q 0001045810-26-000075: 49997. |
| DATA-053 | INFY.BO volume 812000 vs history 811562. INFY.NS, ELCIDIN and SAKSOFT (nse_direct) carry open/high/low/prev_close, with low <= price <= high. | SBIN.BO 234000 vs 233720. HDFCBANK.BO 843000 vs 842939. ICONIKSPEV 81000 vs 81042. |
| DATA-008 | INFY.NS: financial_currency null (currency INR); revenue_ttm 1.8458e12 served from NSE with a "USD basis ... not compared" reason; FCF withheld with a reason naming both currencies. | HCLTECH.NS shows the same pattern. SIFY is unchanged (USD / financial INR). AAPL, WIPRO and DRREDDY are normal. |
| LEAD-014 | Probe over all 54 tools: (B) type-name placeholder echo accepted 0 times; (E) returns the sentinel. | The controls repair normally. |
| AGENT-094 | Every arrange_layout row in the probe is OK (union-typed value left to the validator). | llama "watchlist on top, chart below" produces `{"pattern":"custom","panels":["watchlist","chart"]}`, ok:true, staged. The llama custom chart/news case self-corrects to ok:true after a stringified-array retry. |
| AGENT-095 | llama SIFY ADS prompt: the dated sourced sentence "2026-06-26: One SIFY ADS represents six equity shares." is kept. | In-process `_guard_ratio_claims` on 5 unseen date shapes ("2026.06.26", "Jun 26, 2026", "(26-06-2026)", "26 Jun", "26/6/26"): all kept against the depositary result and all replaced against the bare one. Dated fabrications (5 and 4 shares) are still replaced. |
| AGENT-092 | CASE1: brief None before dispatch. CASE2: 'dispatched brief'. | The control is OK. |
| AGENT-001 | COCHINSHIP in-process gives dividend_yield '0.82%', revenue_growth '2.40%', earnings_growth '-19.37%'. The llama answer quotes 0.82% / 2.40% / -19.37%. | KPITTECH in-process gives '1.44%' and similar. llama quotes ROE 16.45%, operating margin 12.25%, profit margin 8.84% (percent, not fraction). |
| DATA-114 | Scenario C: results ['2026-09-18' x3], network ['2026-09-22','2026-09-21']. | Fresh scenario D is also OK. |
| RESEARCH-022 | Live Mojeek serves a captcha today. The keyless path raises SearchError rate_limited, and the breaker goes 1 then 2 (open) instead of returning an empty answer. | This was a live outside-world case the fix was not written against. |
| RESEARCH-027 | Stall probe: Saksoft 8.1 s, Tata Elxsi 8.4 s, with "Web search did not answer within 8s". | KPIT 6.7 s, Persistent 8.6 s. |
| LEAD-045 | Fresh data dir: sp500 under IN gives 503 rows, skipped 0, not throttled, basis live. | In-process curl_cffi batch transport: 16 rows, failures {}. |
| LEAD-044 | Fresh data dir: sp500 under IN gives 0 INR rows (HAL is Halliburton/USD; PNC, PTC and IT are US names). | nifty50 under US gives 49 INR rows. In-process fallback: CCL/IEX/TECH resolve to their USD names in an IN session; SAIL resolves to Steel Authority INR in a US session. |
| DATA-113 | PDD CNY, NVO DKK, TSM USD, AAPL USD, INFY.NS INR, BIDU null. | BABA surprises CNY. The EpsEstimateGrid scratch test shows a null currency renders no code or symbol anywhere ("Mean1.50 ... High1.60"), and DKK renders its affix. |
| DATA-055 | Live NAVN first_trade_date 2025-10-30, MDLN 2025-12-17, SAIL 2025-02-13, all with listing_date null. | EquityOverview scratch test: first_trade_date 300 days ago gives "since listing" with no 1Y row; 400 days ago gives "52w"; a listing_date 100 days ago wins over first_trade_date 2001. |
| AGENT-053 | Live NewsFeedPanel publishes focusedHeadline and topHeadline (writer test). | With 7 NSE symbols and nothing hovered, the summary is `watchedSymbols=RELIANCE,TCS,HDFCBANK,INFY,ICICIBANK,+2 more, topHeadline=<full headline>`. Hovered, with a 40-hex id, the headline reaches the agent but is cut at the 200-char cap (see issues). |
| AGENT-055 | Scratch test: mode ids are disjoint from LAYOUT_TEMPLATE_IDS. | The 4 palette items (Fundamental / Technical / Macro / Compare Desk) each dispatch exactly one mode plan. All 4 legacy template payloads return false. |
| AGENT-096 | OR flat group of 3 leaves with a stale [market_cap, roe] flat list. | runScreener body: criteria = [pe_ratio<12, dividend_yield>0.04, price_to_book<1] with group `or`; market_cap and roe are not sent. |
| CODE-FRONTEND-017 | Scratch test with deferred mocks. A late SUCCESS for a superseded insider leaves the current load untouched, and its later error shows. | Three detail loads resolving C, then A-reject, then B-reject: activeAccession C, status ready, error null. |
| UI-015 | Scratch test: a TypeError("Failed to fetch") search failure keeps its message, and clearSearch clears it. | A late 'app' rejection after 'apple' resolved does not paint an error. |
| UI-021 | Scratch ChartPanel test with three charts. Select in A, then pointerdown inside C, then body Delete: counts stay [1,1,1]. | pointerdown inside A, then Backspace removes it. A locked drawing survives. |
| CODE-PLATFORM-017 | The inspector preview calls the real sidecar at :52310: `log(x, 10)` with x=1000 shows "disallowed syntax: Call" (never "= 3"). | `x / 0` shows "division by zero" (never Infinity). `x ** 2 + 1` with x=3 shows "= 10". A direct POST /workflow/run agrees on each. |

## Not certified

| id | holds | unfixed claim + fresh repro |
|---|---|---|
| UI-090 | No false-live for foreign listings. | The audit fix_shape's exchange tz/session table was skipped (the writer failed closed instead). 7203.T at 2026-09-23T02:00Z, during the Tokyo session, with a tick at 02:00Z reads 'eod'. |
| RESEARCH-001 | The IT/Gartner and ALL cases show 0 region-feed items. | Common-word ticker ON (US): 7 off-entity region-feed items with rr=True reach DEEP (AP bond market, Lockheed, On Holding buyback, Nvidia, Innate Pharma). |
| DATA-063 | The IndicatorResponse field and its mirror exist. | Live /indicators/TCS (rsi) returns freshness null while /history gives 'eod'. INFY.NS (ema) and AAPL (sma) are also null. get_history never sets series.freshness. |
| LEAD-004 | NDTV is fixed; JONJUA stays half-yearly. | An unfiled Oct-Dec quarter with no 6-month context, and an Oct-Mar H1 with Oct-Dec filed inside it, both still come out 'half-yearly'. |
| LIFECYCLE-020 | 3 warm cycles stay closed. | Warm weight accumulates with no reset; the circuit opens at warm cycle 10 (ct 3.0), and the user batch then returns rate_limited with 0 HTTP calls. |

## Not-a-defect: R15-LEAD-046 (concur)

Fresh counter-probe on 27 Sep, `yfinance .info`:
- HDB: forwardEps 1.3915 from 4 analysts. HDFCBANK.NS: 63.07 from 41.
- WIT: 0.14989 from 7 analysts. WIPRO.NS: 13.8994 from 40, which is about 0.145 USD per ADS at about 95.9 INR/USD. That agrees within 3%.
- The sidecar's `/fundamentals/HDB` gives forward_pe 16.536 = 23.01 / 1.3915, with forward_pe_fiscal_year 2027-03-31.

Vysted computes each listing's figures correctly. The HDB gap comes from two independent consensus sets (4 analysts vs 41), not from a code or currency-basis error.

## Issues noticed (not filed as verdicts)
- `/layout <unknown word>` (including the mode names, such as `/layout fundamental`) silently resets to the default layout through arrange_layout. This predates the batch.
- SEC search: `clearSearch` does not bump `searchGeneration`. If the user types "Apple" and then clears the field before a slow rejection arrives, "Company search unavailable: ..." appears under the empty field (scratch F5 printed `error sec-edgar-mcp is not available`).
- AGENT-053: while a row is hovered, the 40-hex `focusedArticleId` still uses about 58 of the 200 summary chars. A long focused headline is truncated and topHeadline is dropped.
- TATAMOTORS.NS/.BO are not_found (post-demerger symbol) in nifty50 and quotes.
