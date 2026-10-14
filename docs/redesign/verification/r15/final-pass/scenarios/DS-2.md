# DS-2 — three fresh small names, every served field vs the outside world (investor, d38b5d1a)

Names picked from the bundled masters (sidecar/services/resolver_masters, regenerated 2026-09-24), none in
r15/battery/manifest.json names:
- NSE Emerge/SME: YASHOPTICS (Yash Optics & Lens, NSE SME, listed 2024-04-08, yahoo_symbol YASHOPTICS-SM.NS)
- thin BSE-only: SUNRAJDI (Sunraj Diamond Exports, BSE 523425, group X; 121 traded days in the last year)
- 2026 listing: KARAMTARA (Karamtara Engineering, NSE/BSE 544917 mainboard, listed 2026-09-17)

Command: `python3 scratchpad/inv/ds2.py` against :52810 (clean profile, X-Vysted-Region IN): /resolve, /quotes, /fundamentals,
/history, /disclosures/{shareholding,announcements,corporate-actions,deals,results}. Raw: raw/investor/ds2.json.
Outside world: screener.in (raw/investor/ds2-screener.json): https://www.screener.in/company/YASHOPTICS/,
https://www.screener.in/company/523425/, https://www.screener.in/company/KARAMTARA/. api.bseindia.com refused this host
(Akamai "Access Denied", see DS-1), so screener is the witness.

## Read-back vs truth
| field | YASHOPTICS app / screener | SUNRAJDI app / screener | KARAMTARA app / screener |
|---|---|---|---|
| price, as-of | 135.4 eod 2026-10-01 / ₹135 | 12.44 eod 2026-10-01 (vol 10) / ₹12.4 | 410.95 eod 2026-10-01 / ₹411 |
| 52w high/low | — (fundamentals 404) / 140 / 97.5; history max 140.5 min 97.5 | 23.02 (2025-10-03) / 10.55 (2026-09-18) vs 22.6 / 10.6 | 429.35 (2026-10-01) / 320 (2026-09-17, listing day) vs 429 / 320 |
| market cap | — 404 / ₹335 Cr | 66,310,172 = ₹6.63 Cr / ₹6.63 Cr | **unavailable** "provider did not publish" / ₹13,225 Cr |
| P/E | — / 37.0 | **155.5 flagged** (reason: implied 141.1) / 55.2; served EPS 0.23 -> 54.1 | 57.6 (Yahoo EPS 7.11, NI TTM 228.8 Cr) / 104 (screener P&L stops at FY25 for this new listing — source lag, not a defect) |
| EPS | — / — | 0.23 (BSE-filed, 4 quarters to 2026-06-30) / implied 0.225 | 7.11 |
| BVPS, P/B | — / 40.2 | 1.80, 6.91 / 3.26 (equity basis differs: Yahoo other equity -4.37 Cr vs screener reserves -3.59 Cr; no filing reachable to arbitrate -> dropped) | 41.7 / blank |
| revenue TTM, NI | — / FY26 53.99 Cr, 9.05 Cr | 2.55 Cr, 0.122 Cr (BSE-filed) / TTM 2.55, 0.12 | 4,312 Cr, 228.8 Cr / FY25 3,109, 135 (lag) |
| shareholding | NSE 2026-03-31 promoter 73.19 / public 26.81 / Mar 2026 73.19 / 26.80 | BSE 2026-06-30 promoter 35.83, DII 0.17, public 64.17, pledge 0 / Jun 2026 35.83 / 0.17 / 63.99 | BSE 2026-09-16 promoter 82.01, FII 2.24, DII 5.44 / Sep 2026 82.01 / 2.25 / 5.44 |
| corporate actions | dividend ex 2026-09-15 "RE 0.50 PER SHARE" (amount_per_share null) | dividends 2011-2013, covered | none, covered |
| announcements | 50, 2025-08-21..2026-09-24 | 21, 2026-04-14..2026-09-30 | 8 since listing |
SUNRAJDI's provider ownership (insiders 54.14%, institutions 0%) is served "flagged" against the BSE filing (35.83 / 0.17) — honest.
A scrip that has not traded never reads as trading today: DAL (DS-1) quote freshness stale 2025-03-12, 52w withheld.

## Defects
**investor:2 (high, new)** — NSE Emerge has no fundamentals. GET /fundamentals/YASHOPTICS -> 404
`{"detail":"The data provider has no data for this symbol or series — check the symbol.","code":"not_found"}`; the same 404 for
SUMAX, QUALIANCE, GANESHIN, VOLERCAR (all NSE SME rows of the master). GET /fundamentals/YASHOPTICS/income and /balance -> 200
`{"symbol":"YASHOPTICS-SM.NS","periods":[],"lines":[],"gaps":[]}` (no reason); /earnings/YASHOPTICS/history -> empty.
The Equity Overview renders the 404 as "Fundamentals unavailable — ... check the symbol." (src/modules/equity-overview/
EquityOverviewPanel.tsx:1139-1147 with api.ts:90 rejectionReason) for a valid ₹335 Cr listing. Direct upstream probe with the
candidate's own yfinance (raw/investor/yf-sme.txt): `YASHOPTICS-SM.NS {'longName': None, 'marketCap': None, ... 'trailingEps': None}`,
income columns [] — Yahoo does not carry the Emerge board, and no other lane (the exchange-filings overlay used for BSE EPS)
backs it, so all 571 SME rows of the NSE master are fundamentals-less and told their symbol is wrong. Not in the register
(R15-DATA-017 fixed the SME quote/disclosure lanes; R15-DATA-001's DAT-P15-2 was the wrong-name shell this now 404s instead).

**investor:3 (medium, regression of R15-DATA-013)** — SUNRAJDI: eps 0.23 and net_income_ttm 1,220,000 are served from the BSE filing
with the reasons "the provider's 0.08 disagrees with it — not served", yet pe_ratio 155.5 (= 12.44 / 0.08, the unserved EPS) stays,
flagged with reason "... (470,000 / 5,330,400 = 0.09); the P/E it implies at the ratio price 12.44 is 141.1". Truth: screener P/E 55.2;
the payload's own served EPS gives 54.1. sidecar/services/correctness_gate.py:703-790 (`_FILED_SIZES` overlay) replaces
eps/net_income_ttm but never recomputes pe_ratio; the P/E flag at :417 reasons from the provider figures before the overlay.
R15-DATA-013's fix shape was "serve the derived EPS and recompute P/E from quote price, or flag both"; the served pair is now
inconsistent and the flag's own correction is wrong.

**KARAMTARA market cap unavailable** (₹13,225 Cr listing; payload holds eps 7.11 and NI 2,287,539,968 -> 32.2 Cr shares ->
₹13,222 Cr) is the same mechanism as investor:1 (DS-1) and is kept on that key.

Results calendar: YASHOPTICS and KARAMTARA return 0 events "covered" from NSE's event-calendar (forthcoming meetings);
SUNRAJDI's BSE board-meeting feed returns 10 past events. Not judged a defect: the NSE feed is a forthcoming calendar.

VERDICT DS-2: finding investor:2 investor:3
