# batch-2/W5-surfaces-and-math

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`, sidecar `127.0.0.1:52353`
(source, data dir `rc1-round-4-data-battery-13`, seeded from `rc1-round-4-seed-data`).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-009 | In-process `_run_single_slice` with a seeded random walk, N=1/2/4 symbols, 200 dates | curve points = 200 for N=1, 2 and 4 (independent of symbol count) | holds |
| R15-DATA-010 | In-process `_compute_metrics` on `[+0.02]*10 + [-0.05,-0.051]` | engine sortino 6.3521 == textbook downside-deviation sortino 6.3521 (pre-fix 261.93); identical-loss case gives 6.4807, not 0.00 | holds |
| R15-DATA-011 | Live `POST /quant/option/price` european call, S=K=220, method=binomial vs black-scholes | binomial theta -39.81 vs BS -39.68 (same sign, matches cert); gamma 0.01840 (200 steps) vs BS 0.01833 | holds |
| R15-DATA-031 | Source + pinned test read (`EarningsCalendarPanel.test.tsx` `R15-DATA-031`, `EarningsSurpriseChart.tsx:69-89`) | pinned test asserts currency-affixed EPS + no cross-currency sort interleave; surprise-chart title now `Surprise (EPS ${prefix}{suffix})` | ci_pinned (EarningsCalendarPanel.test.tsx: "R15-DATA-031: labels EPS with currency and never interleaves currencies when sorted") |
| R15-DATA-042 | Source + pinned test read (`PortfolioPanel.test.tsx` `R15-DATA-042`) | pinned test asserts Currency column + blank Weight% under mixed currencies; source confirms `mixedCurrencies` guard on export | ci_pinned (PortfolioPanel.test.tsx: "R15-DATA-042: CSV export gets a Currency column and a blank Weight % when mixed") |
| R15-CODE-PLATFORM-053 | Source + pinned test read (`metrics.test.ts` mixed-currency case) | `concentration` and `weight` both null when `mixedCurrencies` is true; source guard at metrics.ts:158-171 | ci_pinned (metrics.test.ts: mixed-currency case asserting `concentration` null) |
| R15-DATA-100 | Source + pinned test read (`BondPricerPanel.test.tsx` `R15-DATA-100`) | pinned test: region IN renders ₹, not hard-coded $; display-currency select overrides region default | ci_pinned (BondPricerPanel.test.tsx: "R15-DATA-100: in region IN, prices render with ₹, not a hard-coded $") |
| R15-DATA-007 | Live `GET /sec/filings/0000320193-23-000077?identifier=AAPL` (the original repro accession) + a genuinely nonexistent accession | real accession: resolves to real metadata (form_type 10-Q, filed 2023-08-04, company_name "Apple Inc.") — no fabricated 10-K/today/empty-name; nonexistent accession: honest 404 not_found | holds |

COVERAGE: 8/8 ids raw; no raw: none.
