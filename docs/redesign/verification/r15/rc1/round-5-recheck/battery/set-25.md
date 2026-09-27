# set-25 — batch-7/W1-india-exchange-data (rc1-battery-19, gate round 5-recheck)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Own sidecar :52359 (fresh copy of
rc1-round-5-recheck-seed-data). Every id re-run live against the own sidecar, HTTP-level,
same routes the register's repro names. Raw: `battery/raw/set-25/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-027 | GET /fundamentals/TCS, /fundamentals/AAPL | TCS provider=nse, consolidated, sum of 4 filed quarters; AAPL stays yfinance | holds |
| R15-DATA-014 | GET /fundamentals/{DAL,FUSION,JONJUA} | DAL 9.97 Cr (bse, exchange-filed, provider's own value disclosed "not served"); FUSION 1,714.42 Cr (nse); JONJUA TTM explicitly flagged, not asserted as fact | holds |
| R15-DATA-076 | GET /fundamentals/DAL | revenue_growth=0.452 (bse), matches screener 7.26/5.00-1 | holds |
| R15-DATA-050 | GET /disclosures/results?symbol={JONJUA,DAL,CHTR,ELCIDIN} | all 200 (were 502), correct BSE results dates | holds |
| R15-DATA-060 | GET /disclosures/{shareholding,announcements,results}?symbol=SIFY, /disclosures/shareholding?symbol=AAPL | non-IN symbols answer 200 not_applicable; SIFY shareholding covered via sec-20f, 83.78% total matches register | holds |
| R15-LEAD-015 | GET /fundamentals/DHANBANK/income?period={quarterly,annual} | gaps=["2025-09-30"]; annual periods ISO on both providers | holds |

COVERAGE: 6/6 ids raw.
