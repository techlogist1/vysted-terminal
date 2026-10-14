# DS-5 — screener over mixed currencies, nulls and thresholds (investor lens)

Stack: own sidecar :52810 (d38b5d1a built binary), POST /screener/run, 15:09 IST. Raw: `raw/investor/ds5.json`.

| run | universe | criteria / sort | result |
|---|---|---|---|
| mixed_mcap_desc | custom: AAPL, MSFT, RELIANCE.NS, TCS.NS, SIFY, INFY, INFY.NS, AMAL, AMAL.BO, SUNRAJDI, YASHOPTICS, KARAMTARA, GSTL, BTC-USD | market_cap desc | 10 rows; INR block (RELIANCE … SUNRAJDI.BO, then AMAL.NS and KARAMTARA.NS with null market cap) then USD block (AAPL, MSFT, SIFY). Coverage: "screened 10 of 14 — 3 unavailable · spans INR, USD — ranked within each currency". |
| mixed_pe_lt_30 | same | pe_ratio < 30, asc | 6 rows; SIFY skipped `missing_field:pe_ratio` (null counted as unavailable, R15-DATA-044 holds). |
| mixed_mcap_gt_1e11 | same | market_cap > 1e11 | 5 rows; AMAL.NS, KARAMTARA.NS skipped `missing_field:market_cap`. |
| nifty50_mcap_desc | nifty50 | market_cap desc | 50/50, all INR, monotone; TMPV.NS null P/E present. |
| nifty50_pe_asc | nifty50 | pe_ratio asc | ONGC 6.43 first; TMPV.NS (null P/E) last (R15-DATA-112 / UI-006 missing-last holds). |
| sp500_mcap_gt | sp500 | market_cap > 5e11 | 19 of 503 matched, result_count == matched_count == rows (R15-UI-006 holds). |

Checks:
- No interleaving of currencies (R15-DATA-043 holds). The custom-universe threshold is labelled "listing currency" in the criteria builder (`CriterionGroupEditor.universeMoneyUnit`), so a single number applied per listing currency is disclosed, not hidden.
- Nulls sort last in both directions and count as unavailable in the coverage line.
- Header counts equal the match count in every run.
- Carry-overs, not new: SUNRAJDI.BO shows P/E 155.5 here too (same value as investor:3, which now also reaches the screener); YASHOPTICS-SM.NS and GSTL-SM.NS are `not_found` (investor:2 class); AMAL.NS and KARAMTARA.NS null market cap (investor:1 class).
- BTC-USD in a custom list under region IN becomes BTC-USD.NS `not_found`: by design in `yfinance_provider._yahoo_symbol` case (c) (a name in neither master keeps .NS so Yahoo 404s it honestly); crypto has its own universe. Not filed.

VERDICT DS-5: pass
