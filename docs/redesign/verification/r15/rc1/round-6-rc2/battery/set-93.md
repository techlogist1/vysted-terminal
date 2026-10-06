# Set: lows-P3/backtest (set-93) — rc1-battery-17, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-062 | stated repro is the Backtest panel End default; read BacktestPanel.tsx + src/lib/date-defaults.ts (GUI/vitest not run) | BacktestPanel.tsx:51 `useState(() => backtestDateDefaults().endDate)` (today, local date; no 2025-12-31 literal left in the panel source). Pinned by src/modules/backtest/BacktestPanel.test.tsx "defaults the date range to today and today - 2y, not a frozen literal" (fake clock 2026-09-25 -> 2024-09-25 / 2026-09-25) | ci_pinned |

COVERAGE: 1/1 ids raw; no raw: none
