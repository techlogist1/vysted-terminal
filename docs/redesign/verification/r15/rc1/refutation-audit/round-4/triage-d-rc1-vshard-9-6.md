# triage-d / rc1-vshard-9:6 (tie R15-DATA-113) -> partial on R15-DATA-113, severity raised to critical

Audited 07:23-07:26 IST, HEAD bed3b166 (code == 01015033; `sidecar/services/earnings_provider.py` and `src/modules/earnings` are untouched by the fix round).

## Entry
R15-DATA-113 (currency-mislabel, medium, fixed, certification failures so far: 1). root_cause: "earnings_provider.py sets currency from the trading/ADR currency (info['currency']) for every money field". fix_shape: "Carry financialCurrency separately for statement-size fields (revenue_estimate_mean) vs per-share fields (eps_estimate_mean) ... and label the panel per field". The fix added a scale-checked `revenue_currency` and left every EPS field on `currency` = info['currency'], assuming per-share EPS is always in the trading currency (true for WIT, which the entry was filed on).

## Live at HEAD (:52435)
```
PDD est {'eps_estimate_mean': 18.84143, 'eps_estimate_high': 21.22954, 'eps_estimate_low': 16.789, 'revenue_estimate_mean': 115643262410.0, 'currency': 'USD', 'revenue_currency': 'CNY'}
NVO est {'eps_estimate_mean': 5.0045, ..., 'currency': 'USD', 'revenue_currency': 'DKK'}
TSM est {'eps_estimate_mean': 4.4614, ..., 'currency': 'USD', 'revenue_currency': 'TWD'}
AAPL est {'eps_estimate_mean': 1.98124, ..., 'currency': 'USD', 'revenue_currency': 'USD'}
WIT est {'eps_estimate_mean': 0.035, ..., 'currency': 'USD', 'revenue_currency': 'INR'}
PDD history eps_actual 19.33 / 9.51 / 17.69, currency USD; NVO history 6.18 / 6.63 / 6.04, currency USD
PDD surprises: eps_actual 19.33, eps_estimate_mean 18.3495, currency USD
```
Scale sweep. Quarterly `eps_estimate_mean` x4 is compared with `/fundamentals` trailing `eps`, which Yahoo gives in the trading currency per ADS (PDD trailingPE 8.36 = 77.57 / 9.28):
```
NVS 1.35  SAP 1.1  ASML 1.46  HDB 1.09  IBN 0.94  INFY.NS 1.06  TSM 1.33 (AAPL, WIT consistent)   -> EPS genuinely in the trading currency
PDD 18.84*4/9.28 = 8.1   NVO 5.0045*4/3.99 = 5.0   JD 17.34   TCOM 6.36   BIDU 8.20 vs trailing -2.34 (sign flip)  -> EPS in the reporting currency (CNY/DKK), labelled USD
```
If PDD's 18.84 were USD, its forward P/E would be about 1.0 against a trailing 8.4. In CNY (about 2.65 USD) it is about 7.3, consistent. NVO: about 1.9 in USD vs about 12 in DKK. JD and TCOM: forward P/E about 1-2 if the figure were USD. Raw sweep: `<scratch>/refaudit4-triage-d/adr-eps-sweep.txt`.

## Code
- `sidecar/services/earnings_provider.py:219` and `:253`: payload `currency = info['currency']`.
- `:345` (EarningsEvent, the Earnings Calendar Consensus EPS column), `:462`/`:488` (history entries, and the surprises built from them at `:528`), `:576` (EarningsEstimateDetail): every EPS field is labelled with that trading currency. Only revenue gets `_revenue_currency` (`:118-146`).
- `src/modules/earnings/EpsEstimateGrid.tsx:26-30`: `eps(value, currency)` formats EPS with `estimate.currency`, so the grid shows "$18.84" for PDD.

## Class decision
Same class, so partial and not a new entry. It is the same seam (earnings_provider's per-field currency), the same surface (estimates/history/surprises/calendar), the same mechanism (a reporting-currency money figure labelled with the ADR's trading currency), and the same defect_class (currency-mislabel). The entry's root_cause ("sets currency from the trading/ADR currency for every money field") still holds verbatim for the EPS fields. The fix_shape's stated split, which assumed per-share fields are in the trading currency, is exactly the part that fails for CNY/DKK reporters. The entry's own repro (WIT revenue_currency INR) holds, and so do the round-2 cases (INFY/INFY.NS INR).
Severity: critical, raised from the shard's medium. This is wrong data presented as right. PDD/JD/BIDU/TCOM/NVO EPS estimates, actuals and surprises are shown and handed to the agent as USD while overstated about 7x in USD terms. That is 5 of 16 ADRs sampled. It reaches the Earnings Calendar Consensus EPS column, the estimate grid, the surprise chart and the agent's earnings tools. The register rated the identically shaped SIFY INR-as-USD mislabel (R15-DATA-008) critical.
Certification failures: register clause "certification failures so far: 1". With this partial the count is 2.

End-of-audit (07:33 IST): own sidecar pid 90459 on :52435 stopped by pid (health now 000); no child processes; the repo working tree is unchanged apart from these output files.
