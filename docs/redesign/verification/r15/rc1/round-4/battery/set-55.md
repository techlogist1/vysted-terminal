# set-55 — batch-11/W8-frontend-visual (rc1-battery-4, round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. UI-091 checked live against
the round's own sidecar (`:52344`); UI-085/CODE-PLATFORM-023 are vitest-pinned —
per role instructions the heavy lane owns full vitest/pytest runs, so these are
verified by reading the pinned test + an independent grep/doc check, not by
executing vitest. CODE-PLATFORM-025 is a doc-text + rust-source check. Raw:
`battery/raw/set-55/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-085 | `grep -rn 'text-charcoal-600\|700' src --include=*.tsx` outside tests; read `src/lib/design-contrast.test.ts` | Only 3 hits remain, all `disabled:text-charcoal-600` (the documented carve-out — border/disabled-fg token), zero unprefixed readable-text use; the pinned test computes WCAG ratios for every text token against both panel surfaces and asserts the floor | ci_pinned (`src/lib/design-contrast.test.ts`) — grep corroborates the code-side half live; the numeric WCAG assertion itself was not re-executed (vitest suite is the heavy lane's) |
| R15-UI-091 | Live `GET /indicators/suggested?timeframe=5m&asset_class=equity`, `...1d&asset_class=crypto`, `...1d&asset_class=equity`; `GET /indicators/AAPL?indicators=ema:9,ema:21` | 5m/equity → `["ema:9","ema:21","vwap","rsi"]`; 1d/crypto → `["ema:50","ema:200","vwap:week","rsi"]`; 1d/equity → `["ma","volume","rsi","macd"]`; AAPL ema:9/21 request returns real EMA(9)/EMA(21) line data (non-null once past the warmup window) | holds |
| R15-CODE-PLATFORM-023 | Read `src/modules/portfolio/metrics.ts` (dailyReturns/annualizedVolatility/sharpeRatio/sortinoRatio/maxDrawdown/calmarRatio/historicalVaR95/correlation/beta/computeCurrencyRisk all exported) and `src/modules/portfolio/metrics.test.ts` (`describe("risk metric primitives (R15-CODE-PLATFORM-023)"...)`, `describe("computeCurrencyRisk (R15-CODE-PLATFORM-023)"...)`) | All 7 promised metrics + VaR/beta/correlation are implemented client-side over the tracked portfolio's own return series (not just inside backtest_engine.py), with a dedicated pinned test suite covering per-currency buckets, the `MIN_RISK_HISTORY_DAYS` null-guard and zero-length-series safety | ci_pinned (`src/modules/portfolio/metrics.test.ts`) — implementation presence confirmed by reading the module; the numeric agreement-to-1e-15 claim was not re-executed |
| R15-CODE-PLATFORM-025 | `sed -n docs/BLUEPRINT.md` around the Multi-window bullet + pop-out line; `grep -rln WebviewWindowBuilder src-tauri/src/*.rs` | BLUEPRINT.md:249 "Multi-tab layout (dockview, shipped); multi-window (v1.0 roadmap, deferred — R15-CODE-PLATFORM-025)"; pop-out line also scoped to v1.0 roadmap; no `WebviewWindowBuilder` in the Rust core (still correctly unbuilt, not silently promised) | holds |

COVERAGE: 4/4 ids raw; no raw: none.
