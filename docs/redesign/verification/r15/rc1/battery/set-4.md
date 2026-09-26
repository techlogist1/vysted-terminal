# batch-2/W5-surfaces-and-math

Sidecar under test: candidate `4c6dfe8c` (rc1-cand worktree), own sidecar `127.0.0.1:52340`,
data dir `rc1-data-rc1-battery-0` (seed copy). Backend-testable entries re-run via a single
targeted `pytest -k` invocation (not the full suite) against the candidate `.venv`, or live
curl. Entries whose only feasible repro drives frontend TS rendering are `ci_pinned` against
the committed vitest test (grepped for presence, not executed), per the "never run vitest
suites" rule.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-009 | `pytest tests/test_backtest_engine.py -k "test_multi_symbol_equity_curve_has_one_point_per_timestamp or test_multi_symbol_sharpe_does_not_scale_with_symbol_count"` | `2 passed` — equity curve emits one point per timestamp regardless of symbol count; Sharpe does not inflate with N. | holds |
| R15-DATA-010 | `pytest tests/test_backtest_engine.py -k sortino` (`test_sortino_uses_downside_deviation_not_loss_subset_stdev`, `test_sortino_nonzero_for_identical_losses`) | `2 passed` — `sortino == pytest.approx(6.35, abs=0.01)` (RMS-of-shortfall, not stdev-of-loss-subset); nonzero for identical-magnitude losses. | ci_pinned (tests/test_backtest_engine.py: sortino tests, currently passing) |
| R15-DATA-011 | `pytest tests/test_quant_options.py -k "theta or gamma"` | `2 passed` — binomial theta stays negative (long-call time decay), gamma matches the BS reference at an odd step count too. | ci_pinned (tests/test_quant_options.py: theta/gamma tests, currently passing) |
| R15-DATA-007 | `GET /sec/filings?symbol=AAPL` (list), then `GET /sec/filings/0000000000-00-000000?identifier=AAPL` (fabricated/out-of-range accession). | List returns 40 real AAPL filings. Out-of-range accession returns `404` `{"code":"not_found", ...}` — no synthetic 10-K invented. | holds |
| R15-DATA-031 | grep `src/modules/earnings/EarningsCalendarPanel.test.tsx`. | `it("R15-DATA-031: labels EPS with currency and never interleaves currencies when sorted", ...)` present at line 202, plus affix comments at 149/174. | ci_pinned (EarningsCalendarPanel.test.tsx:202) |
| R15-DATA-042 | grep `src/modules/portfolio/PortfolioPanel.test.tsx`. | `it("R15-DATA-042: CSV export gets a Currency column and a blank Weight % when mixed", ...)` present at line 573. | ci_pinned (PortfolioPanel.test.tsx:573) |
| R15-CODE-PLATFORM-053 | grep `src/modules/portfolio/metrics.test.ts`. | `it("mixed-currency portfolio: per-currency subtotals, never a cross-currency sum (D57)", ...)` present at line 90; single-currency companion at line 66. | ci_pinned (metrics.test.ts:90) |
| R15-DATA-100 | grep `src/modules/quant/BondPricerPanel.test.tsx`. | Both `it("R15-DATA-100: in region IN, prices render with ₹, not a hard-coded $", ...)` (line 58) and the display-currency-select override test (line 67) present. | ci_pinned (BondPricerPanel.test.tsx:58,67) |

**Set result: 2/8 holds (live), 6/8 ci_pinned.**
