# set-24 — batch-7/W1-india-exchange-data (rc1-battery-21)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-014 | `GET /fundamentals/{FUSION,DAL,JONJUA}` | FUSION revenue_ttm 17,144,200,000 (1,714.42 Cr, NSE-filed) with Yahoo's 8,582,000,128 (858.2 Cr) disclosed `"not served"`; DAL 99,700,000 (9.97 Cr, BSE) vs Yahoo 27,600,000 `"not served"`; JONJUA `field_meta.revenue_ttm.status: "flagged"` ("TTM basis: the exchange filings leave a quarter of the trailing year unfiled or unparsed") | holds |
| R15-DATA-027 | `GET /fundamentals/{TCS,AAPL}` | TCS: top-level `provider: "yfinance"` but `field_meta.revenue_ttm.provider: "nse"` (exchange-derived field, 2,758,590,000,000 = 4-quarter NSE sum); AAPL: `provider: "yfinance"` unaffected (US symbols not routed to the exchange lane) | holds |
| R15-DATA-050 | `GET /disclosures/results?symbol={JONJUA,DAL,ELCIDIN,CHTR}` | all four now HTTP 200 with BSE `events` (JONJUA count 10, DAL count 10, ELCIDIN count 10, CHTR count 4) — all previously 502 | holds |
| R15-DATA-060 | `GET /disclosures/{shareholding,announcements,results}?symbol=SIFY`, `GET /disclosures/shareholding?symbol=AAPL` | SIFY shareholding: 200, `coverage:"covered"`, `provider:"sec-20f"`, 4 major_shareholders summing to **83.78%** exactly (register's SEC 20-F figure); SIFY announcements/results: 200 `coverage:"not_applicable"`; AAPL shareholding: 200 `coverage:"not_applicable"` — all previously 502 | holds |
| R15-DATA-076 | `GET /fundamentals/{FUSION,DAL}` (revenue_growth field) | FUSION `revenue_growth: 0.05464...` (5.46%, NSE-filed) with Yahoo's 128.1% `"not served"`; DAL `revenue_growth: 0.452` (45.2%, BSE-filed, matches screener 7.26/5.00-1) | holds |
| R15-LEAD-015 | `GET /fundamentals/DHANBANK/income?period=quarterly` and `?period=annual` | quarterly: `gaps: ["2025-09-30"]` (the missing quarter is now explicitly marked); annual: `periods` are ISO dates (`2026-03-31`, `2025-03-31`, ...) on the same route | holds |

Raw: `battery/raw/set-24/R15-{DATA-014-FUSION,DATA-014-DAL,DATA-014-JONJUA,DATA-027-TCS,DATA-027-AAPL,DATA-050-JONJUA,DATA-050-DAL,DATA-050-ELCIDIN,DATA-050-CHTR,DATA-060-SIFY-shareholding,DATA-060-SIFY-announcements,DATA-060-SIFY-results,DATA-060-AAPL-shareholding,DATA-076-FUSION,DATA-076-DAL,LEAD-015-DHANBANK}.txt`
