# batch-7/W3-unattended-chart-workspace

All 10 entries are `open`+`low` in the register — never certified as fixed, so there is nothing
to regress. Each is re-confirmed present and unchanged via source inspection against the
candidate worktree (`4c6dfe8c`); all are frontend-only, so none were re-run under vitest per the
role's rules.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-062 | Read `src/modules/backtest/BacktestPanel.tsx`. | `const DEFAULT_END = "2025-12-31";` still hard-coded (today is 2026-09-26) — default runs still silently omit the most recent ~9 months. Unchanged. | holds (unchanged known-open) |
| R15-UI-064 | Read `src/modules/chart/ChartPanel.tsx` indicator-color assignment. | `indicator.lines.forEach((line, lineIndex) => ...)` resets `lineIndex` to 0 for every indicator, so two different single-line indicators (SMA, EMA) both land on `INDICATOR_COLORS[0]` — still shares one color. `priceScaleId: compareNormalize ? "left" : "right"` for the `%`-normalize overlay is unchanged. | holds (unchanged known-open) |
| R15-UI-066 | `grep role=alert\|role=status` over `src/components/EmptyState.tsx`. | No match — an upstream-failure empty state and a genuinely-empty state still share icon/tones with no `role=alert`/`role=status` distinction. Unchanged. | holds (unchanged known-open) |
| R15-UI-068 | Read `src/components/DataTable.tsx`; `grep <table` over Screener/Watchlist/Earnings modules. | `ScreenerResultsTable.tsx`, `WatchlistPanel.tsx`, `EarningsCalendarPanel.tsx` still hand-roll their own `<table>` instead of the shared `DataTable` primitive. Unchanged. | holds (unchanged known-open) |
| R15-UI-070 | `grep vysted-workspace` over `src/components`, `src/modules`; read `SettingsPanel.tsx` export. | Settings Export still writes only `vysted-settings.json` ("no secrets included") — no control anywhere reads or writes a `.vysted-workspace` file. Unchanged. | holds (unchanged known-open) |
| R15-UI-072 | Read `src/modules/chat/ModelControl.tsx`'s model-selector button. | Still only a `Cpu` icon or plain text label plus `aria-haspopup="listbox"` (screen-reader only) — no chevron/visual affordance that it opens a menu. Unchanged. | holds (unchanged known-open) |
| R15-UI-074 | `grep` for a prose line-length cap (`max-w-…ch`, `65ch`/`75ch`) over `src/modules/research`, `src/modules/equity-overview`. | No match — no reading surface caps its line length. Unchanged. | holds (unchanged known-open) |
| R15-UI-076 | Read `src/store/symbols.ts` `DEFAULT_SYMBOLS`. | Still `[SPY, QQQ, BTC/USDT, ETH/USDT, NVDA, AAPL]` regardless of an India-first region setting. Unchanged. | holds (unchanged known-open) |
| R15-UI-078 | Read `src/modules/portfolio/PortfolioPanel.tsx` form validation and `src/lib/host-actions.ts` agent-path validation. | Form path: `Number("")` is `0` (finite, non-negative) so a blank cost-basis field is still silently saved as `0`; `Number("1e20")` passes the same checks with no upper bound on quantity either — both sub-defects reproduce exactly as documented. Agent path: `costBasisProblem()`/the `portfolio_add_position` case now gate on a `problem` string and `fail()` a negative cost basis instead of applying it silently — that one sub-path looks improved, but the entry is a 3-part compound and 2 of 3 parts are unchanged, so `open`/`low` remains an accurate status for the whole entry. | holds (unchanged known-open; one sub-path improved but not enough to close the entry) |
| R15-UI-080 | Read `src/modules/research/BriefPanel.tsx` `SourceRow`. | No `vysted://` scheme special-case in `SourceRow`; a structured-provenance source still renders as an external `<a>` with `ExternalLink` and a Google S2 favicon lookup for synthetic providers like `nse_direct`/`yfinance`. Unchanged. | holds (unchanged known-open) |

Raw output: `raw/set-27/UI-062.txt` … `UI-080.txt`.
