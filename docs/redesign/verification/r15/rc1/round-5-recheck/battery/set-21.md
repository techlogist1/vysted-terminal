# batch-6/W1-india-exchange-data (set-21.md) — rc1-battery-21, round 5-recheck

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-017 | Full original repro re-run: `/disclosures/shareholding\|announcements\|results?symbol=JNPR`, same 3 for `DHOOTTRANS` and `SUMAX`; `/quotes/SUMAX`; `/resolve?q=Sumax+Engineering+Limited` (exact legal name, DAT-P15-5); `/resolve?q=AMAL` + `/disclosures/results?symbol=AMAL` (DAT-P9-2). | JNPR: shareholding/announcements/results all 200 (previously 502 "not a known NSE/BSE instrument"); fii_percent 1.77 + dii_percent 5.07 = institutions_percent 6.84 (the ~44%-understated split is now correctly exposed, not folded into a single figure). DHOOTTRANS: shareholding 200 (promoter 82.78%). SUMAX: shareholding 200, `/quotes/SUMAX` 200 (price 109.15 INR, provider nse_direct). Legal-name search "Sumax Engineering Limited" now ranks SUMAX (board=SME, yahoo_symbol=SUMAX-SM.NS) as candidates[0] at confidence 1.0 — previously SUMAX wasn't in the master at all so only the 6 wrong "…Engineering Ltd" candidates showed; those 5 unrelated names still appear ranked below it (harmless — legal-name collision, not a resolver defect). AMAL: `/resolve` now returns BOTH the NSE listing (candidates[0], confidence 1.0) and the BSE listing (previously NSE-only was missing); `/disclosures/results?symbol=AMAL` 200 with 10 events across NSE+BSE (previously 502). | holds |

COVERAGE: 1/1 ids raw; no raw: none.
