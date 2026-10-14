# Set 59 — lows-P1/backtest (candidate ace7dd76)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-079 | in-process compile_rule on AND/and | both parse OK | holds |
| R15-CODE-PLATFORM-034 | in-process walk-forward run, 10 bars, 3 slices, spying slice runner | max hits per bar 1, total 10 of 10 bars (disjoint slices) | holds |
| R15-CODE-PLATFORM-035 | grep of banned scaffolding phrases in 3 files | all 0; bar_loader required param | holds |
| R15-CODE-PLATFORM-036 | count compile_rule calls on CustomDslStrategy construction | 2 (one per rule, was 4) | holds |
| R15-UI-060 | run_backtest with on_event collector, 10 bars | run-start, progress(5), progress(10), run-complete | holds |
| R15-UI-061 | frontend render; test BacktestResultView.test.tsx:88 + header "Trades (N closed, M open)" in source | vitest-only | ci_pinned |

COVERAGE: 6/6 ids raw
