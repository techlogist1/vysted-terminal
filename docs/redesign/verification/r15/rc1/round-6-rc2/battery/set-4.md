# batch-2/W5-surfaces-and-math (set-4), shard rc1-battery-7, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-009 | in-process seeded 200-date random walk, N=1,2,4 buy-and-hold via run_backtest | 200 curve points for every N; engine sharpe == date-sampled sharpe (0.4852/1.1897/1.1375) | holds |
| R15-DATA-010 | _compute_metrics on [+0.02]*10+[-0.05,-0.051] | sortino 6.3521 == textbook 6.3521 (pre-fix 261.93); mixed identical-loss series nonzero | holds |
| R15-DATA-011 | POST /quant/option/price binomial vs BS, steps 50..500, american put | binomial theta -39.81 vs BS -39.68; gamma 0.01835-0.01861 vs 0.01833 at all step counts incl. 201; put theta -30.8 | holds |
| R15-DATA-031 | pure panel (vitest) | EarningsCalendarPanel.test.tsx "R15-DATA-031: labels EPS with currency and never interleaves currencies when sorted" exists | ci_pinned |
| R15-DATA-042 | CSV export (vitest) | PortfolioPanel.test.tsx "R15-DATA-042: CSV export gets a Currency column and a blank Weight % when mixed" exists | ci_pinned |
| R15-CODE-PLATFORM-053 | buildPortfolioSummary mixed-currency (vitest) | metrics.test.ts:86,108 pin concentration null/mixedCurrencies | ci_pinned |
| R15-DATA-043 | POST /screener/run custom [AAPL,RELIANCE.NS,MSFT,TCS.NS] | coverage "spans INR, USD - ranked within each currency"; order RELIANCE,TCS (INR) then AAPL,MSFT (USD) | holds |
| R15-DATA-100 | POST /quant/bond/price (currency-free) + panel test | route currency-free; BondPricerPanel.test.tsx "R15-DATA-100: in region IN, prices render with rupee, not $" exists | ci_pinned |
| R15-DATA-007 | GET /sec/filings/0000320193-23-000077?identifier=AAPL; and -26-000020 | real identity: 10-Q, Apple Inc., filed 2023-08-04 (not 10-K/today/''); 26-000020 -> 10-Q 2026-07-31 | holds |

COVERAGE: 9/9 ids raw; no raw: none
