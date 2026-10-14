# batch-2/W5-surfaces-and-math

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, own sidecar `127.0.0.1:52351`,
data dir `rc1-round-5-data-rc1-battery-11` (seed copy). Backend-testable entries
re-run via targeted `pytest -k` against the candidate's `sidecar/.venv`, or live curl.
Entries whose only feasible repro drives frontend TS rendering are `ci_pinned`
against the committed vitest test (grepped for presence, not executed).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-009 | `pytest tests/test_backtest_engine.py -k "test_multi_symbol_equity_curve_has_one_point_per_timestamp or test_multi_symbol_sharpe_does_not_scale_with_symbol_count"` | `2 passed` | holds |
| R15-DATA-010 | `pytest tests/test_backtest_engine.py -k sortino` | `2 passed` | ci_pinned (tests/test_backtest_engine.py: sortino tests, currently passing) |
| R15-DATA-011 | `pytest tests/test_quant_options.py -k "theta or gamma"` | `2 passed` | ci_pinned (tests/test_quant_options.py: theta/gamma tests, currently passing) |
| R15-DATA-007 | `GET /sec/filings?symbol=AAPL` (list), then `GET /sec/filings/0000000000-00-000000?identifier=AAPL` (fabricated accession). | List returns real AAPL filings. Out-of-range accession returns `404` `{"code":"not_found",...}` — no synthetic 10-K invented. | holds |
| R15-DATA-031 | grep `src/modules/earnings/EarningsCalendarPanel.test.tsx` for `R15-DATA-031`. | Test `"R15-DATA-031: labels EPS with currency and never interleaves currencies when sorted"` present at line 202, affix comments at 149/174 — unchanged from original repro. | ci_pinned (EarningsCalendarPanel.test.tsx:202) |
| R15-DATA-042 | grep `src/modules/portfolio/PortfolioPanel.test.tsx` for `R15-DATA-042`. | Test `"R15-DATA-042: CSV export gets a Currency column and a blank Weight % when mixed"` present at line 573. | ci_pinned (PortfolioPanel.test.tsx:573) |
| R15-CODE-PLATFORM-053 | grep `src/modules/portfolio/metrics.test.ts` for `D57`. | `"mixed-currency portfolio: per-currency subtotals, never a cross-currency sum (D57)"` present at line 90; single-currency companion at line 66. | ci_pinned (metrics.test.ts:90) |
| R15-DATA-100 | grep `src/modules/quant/BondPricerPanel.test.tsx` for `R15-DATA-100`. | Both `"R15-DATA-100: in region IN, prices render with ₹, not a hard-coded $"` (line 58) and the display-currency-select override test (line 67) present. | ci_pinned (BondPricerPanel.test.tsx:58,67) |

**Set result: 2/8 holds (live), 6/8 ci_pinned. No regressions.**
