# R15-LEAD-004 (rc1-verifier:6) — refutation audit round 4, group data

Verdict: **regression_confirmed** (the missing-quarter case was never fixed). Severity: medium (kept).

Audited 06:58 IST on own sidecar :52400 + in-process with sidecar/.venv. Code tree == 01015033 (see data-R15-DATA-003.md header).

## Entry
- repro: GET /fundamentals for a quarterly Indian filer; the TTM field meta carries the half-yearly-filer label.
- fix_shape: derive the label from the observed filing cadence (statement period lengths), not from the region; pin one quarterly and one half-yearly case.
- batch-7 (e81c9e7) certified on TCS (no lane: provider-gap wording) and DHANBANK (four filed quarters). No quarterly filer with a hole in its exchange-filed chain was tested.

## 1. Entry's repro / verifier's refutation: live /fundamentals (X-Vysted-Region: IN)
```
06:50 IST
### GET /fundamentals/NDTV (X-Vysted-Region: IN)
symbol NDTV.NS name New Delhi Television Limited revenue_ttm 5378679808.0
  revenue_ttm reason= TTM basis: the exchange filings do not cover the trailing year in four quarters (a half-yearly filer) — annual, not trailing-4Q; kept, flagged
  net_income_ttm reason= TTM basis: the exchange filings do not cover the trailing year in four quarters (a half-yearly filer) — annual, not trailing-4Q; kept, flagged
### GET /fundamentals/TCS.NS (X-Vysted-Region: IN)
symbol TCS.NS name Tata Consultancy Services Limited revenue_ttm 2758590000000.0
  revenue_ttm reason= None
  net_income_ttm reason= None
### GET /fundamentals/JONJUA (X-Vysted-Region: IN)
symbol JONJUA.BO name Jonjua Overseas Limited revenue_ttm 239033504.0
  revenue_ttm reason= TTM basis: the exchange filings do not cover the trailing year in four quarters (a half-yearly filer) — annual, not trailing-4Q; kept, flagged
  net_income_ttm reason= TTM basis: the exchange filings do not cover the trailing year in four quarters (a half-yearly filer) — annual, not trailing-4Q; kept, flagged
### GET /fundamentals/DHANBANK (X-Vysted-Region: IN)
symbol DHANBANK.NS name Dhanlaxmi Bank Limited revenue_ttm 18710600000.0
  revenue_ttm reason= exchange-filed (NSE) figure served; the provider's 7,759,600,128 disagrees with it — not served
  net_income_ttm reason= None
```

## 2. The exchange-filed periods behind the label (in-process exchange_financials.get_filed_periods)
```
NDTV.NS nse consolidated cadence= half-yearly trailing= None
    2026-04-01 2026-06-30 months= 3 rev= 1172300000.0
    2026-01-01 2026-03-31 months= 3 rev= 1479600000.0
    2025-10-01 2025-12-31 months= 3 rev= 1504100000.0
    2025-04-01 2025-09-30 months= 6 rev= 1222700000.0
    2025-04-01 2025-06-30 months= 3 rev= 1076500000.0
JONJUA.BO bse standalone cadence= half-yearly trailing= None
    2026-04-01 2026-06-30 months= 3 rev= 43520000.0
    2026-01-01 2026-03-31 months= 3 rev= 163570000.0
    2025-10-01 2025-12-31 months= 3 rev= 15400000.0
TCS.NS nse consolidated cadence= quarterly trailing= [('2026-04-01', '2026-06-30', 3), ('2026-01-01', '2026-03-31', 3), ('2025-10-01', '2025-12-31', 3), ('2025-07-01', '2025-09-30', 3)]
    2026-04-01 2026-06-30 months= 3 rev= 722750000000.0
    2026-01-01 2026-03-31 months= 3 rev= 706980000000.0
    2025-10-01 2025-12-31 months= 3 rev= 670870000000.0
    2025-07-01 2025-09-30 months= 3 rev= 657990000000.0
    2025-04-01 2025-09-30 months= 6 rev= 1292360000000.0
    2025-04-01 2025-06-30 months= 3 rev= 634370000000.0
```

## 3. NDTV's Sep-2025 Integrated Filing XBRL carries only the Apr-Sep context
```
row 30-SEP-2025 Consolidated 29-Oct-2025 20:56:11 https://nsearchives.nseindia.com/corporate/xbrl/INTEGRATED_FILING_INDAS_1560711_29102025085611_WEB.xml
   parsed 2025-04-01 2025-09-30 6 rev 1222700000.0 np -741100000.0
   contexts(start/end): [('OneD', '2025-04-01', '2025-09-30'), ('OneI', '2025-04-01', '2025-09-30'), ('OneExpenses2D', '2025-04-01', '2025-09-30'), ('OneExpenses3D', '2025-04-01', '2025-09-30'), ('D_ItemsThatWillNotBeReclassifiedToProfitAndLoss11', '2025-04-01', '2025-09-30')]
   RevenueFromOperations facts: []
```

## 4. The JONJUA pin's fixture shape (tests/test_b7_exchange_financials.py::_JONJUA)
```
# cmd: PYTHONPATH=. ./.venv/bin/python l004_jonjua_fixture.py (replays tests/fixtures bse/filed_results_542446_jonjua_20260924.json via the test module _replay, then exchange_financials._fetch("JONJUA.BO"))
JONJUA fixture cadence= half-yearly
   2026-04-01 2026-06-30 3
   2026-01-01 2026-03-31 3
   2025-10-01 2025-12-31 3
```

## Code at HEAD
- sidecar/services/exchange_financials.py:114-121 FiledPeriods.cadence(): 'quarterly' only when trailing() returns four 3-month periods; ANY hole in the trailing chain (trailing() None, :97-112) returns 'half-yearly' — the docstring says so ('or a quarter the exchange holds no filing for').
- sidecar/services/correctness_gate.py:581-585 _ttm_basis turns cadence 'half-yearly' into 'the exchange filings do not cover the trailing year in four quarters (a half-yearly filer) — annual, not trailing-4Q; kept, flagged'.

## Reasoning
NDTV is a mainboard LODR quarterly filer, and the lane's own periods show it: 3-month filings for Apr-Jun 2025, Oct-Dec 2025, Jan-Mar 2026 and Apr-Jun 2026. Only its Sep-2025 filing is exposed as a 6-month Apr-Sep period (the XBRL carries only 2025-04-01..2025-09-30 contexts), so trailing() finds a hole and cadence() calls NDTV 'a half-yearly filer' and describes Yahoo's figure as 'annual, not trailing-4Q'. By period lengths, which is what the fix_shape asks for, NDTV is quarterly: a half-yearly filer never files a 3-month quarter inside the half that holds the hole, and NDTV filed Apr-Jun 2025 inside Apr-Sep 2025. The fix derived the label from 'can a trailing-4Q chain be built', not from period lengths, so any quarterly filer with one unfiled or unparsed quarter gets the false label. The entry's own repro reproduces at HEAD; the verifier's refutation holds. TCS (four quarters) and DHANBANK stay correct, so the certified cases were real but did not cover this shape. The JONJUA pin keeps its label under the proposed rule because its fixture holds no 3-month period inside Apr-Sep 2025.

## Certification failures
Baseline 0: the register note has no 'certification failures so far' clause; not in any stage-c not_certified list (batch-7 certified); no earlier REFUTATION_AUDIT regression_confirmed/partial verdict. Plus this verdict = 1.
