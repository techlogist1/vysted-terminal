# Set 55 — batch-11/W8-frontend-visual (rc1-battery-22, candidate ace7dd768c3b809b0e72b20b20cfc94eea2368bd)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-085 | entry's grep `text-charcoal-600` over src/**/*.tsx + WCAG ratio from styles/tokens.css | 19 non-test hits -> 3, all `disabled:`-prefixed (SettingsPanel:531,540; ChatSidebar:2195), none readable text; token ratios: charcoal-600 1.98:1 (disabled/border only), charcoal-500 5.24, sage-500 3.98 (adjacent note); src/lib/design-contrast.test.ts exists | holds |
| R15-UI-091 | live GET /indicators/suggested + /indicators/AAPL | (5m,equity) ema:9,ema:21,vwap,rsi; (1d,crypto) ema:50,ema:200,vwap:week,rsi; (1d,equity) ma,volume,rsi,macd; ema:9,ema:21 return EMA(9)/EMA(21) lines; vwap:week -> 'VWAP (week)' | holds |
| R15-CODE-PLATFORM-023 | metrics.ts run under node on fresh real data (INFY.NS vs ^NSEI 1y, 246 aligned days) vs independent Python statistics | vol 0.30686, Sharpe -0.96824, Sortino -1.32422, maxDD -0.41691, Calmar -0.71264, corr 0.30029, beta 0.68945 match reference to 1e-15; VaR95 0.03088 vs index-quantile 0.03118 (convention); PortfolioPanel wires computeCurrencyRisk | holds |
| R15-CODE-PLATFORM-025 | tauri.conf.json windows count + BLUEPRINT :249,:322 | app.windows has 1 entry (unchanged); BLUEPRINT now states 'multi-window (v1.0 roadmap, deferred — R15-CODE-PLATFORM-025)' and pop-out as v1.0 roadmap | holds |

COVERAGE: 4/4 ids raw; no raw: none
