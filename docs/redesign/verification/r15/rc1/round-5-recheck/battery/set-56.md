# set-56 — batch-11/W8-frontend-visual (rc1-battery-0, gate round 5-recheck)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar `:52340` (shard-shared
with set-26). UI-091 checked live against this shard's own sidecar; UI-085 is
vitest-pinned (grep + pinned-test read, per role instructions the heavy lane owns full
vitest runs); CODE-PLATFORM-023/025 are grep/doc/config checks matching the entries' own
stated repros verbatim. Raw: `battery/raw/set-56/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-085 | `grep -rn "text-charcoal-600\|700" src --include=*.tsx` outside tests; read `src/lib/design-contrast.test.ts` | Only 3 hits remain, all `disabled:text-charcoal-600` (the documented disabled-fg carve-out), zero unprefixed readable-text use (the original 19 non-test hits are gone); the pinned test computes WCAG ratios for every text token against both panel surfaces and asserts the 3:1/4.5:1 floors | ci_pinned (`src/lib/design-contrast.test.ts`, both `R15-UI-085` describe blocks) — grep corroborates the code-side half live; the numeric WCAG assertion was not re-executed |
| R15-UI-091 | Live `GET /indicators/suggested?timeframe=5m&asset_class=equity`, `...1d&asset_class=crypto`, `...1d&asset_class=equity`; `GET /indicators/AAPL?indicators=ema:9,ema:21` | 5m/equity → `["ema:9","ema:21","vwap","rsi"]`; 1d/crypto → `["ema:50","ema:200","vwap:week","rsi"]`; 1d/equity → `["ma","volume","rsi","macd"]` — all match the FR-092 sets exactly, distinct per timeframe/asset class; the EMA request returns real non-null EMA(9)/EMA(21) values past the warmup window | holds |
| R15-CODE-PLATFORM-023 | The entry's own literal sidecar greps (`value_at_risk\|VaR\|def.*beta\|correlation_matrix` over `sidecar/services`+`sidecar/routers`; `sharpe\|sortino\|calmar` over `sidecar/services/*.py`; risk fields in `portfolio_db.py`/`models/portfolio.py`), plus a read of `src/modules/portfolio/metrics.ts` + `PortfolioPanel.tsx` render sites | Sidecar-side greps are byte-identical to the original defect (0 hits outside `backtest_engine.py`, no risk fields in the portfolio DB/model — the sidecar was never the fix's location); all 7 promised risk functions (`sharpeRatio`, `sortinoRatio`, `calmarRatio`, `historicalVaR95`, `correlation`, `beta`, `maxDrawdown`) exist client-side in `metrics.ts` and are rendered at `PortfolioPanel.tsx:1098-1160` | holds — the promised analytics are implemented and wired into the Portfolio & Risk panel; the sidecar-only grep is an adjacent fact, not a regression |
| R15-CODE-PLATFORM-025 | `python3 -c` parse of `tauri.conf.json` `app.windows`; grep for `WebviewWindowBuilder`/pop-out spawn code; grep `docs/BLUEPRINT.md` for the multi-window/pop-out scoping language | `app.windows` is still exactly 1 entry (Tier-1 §2 untouched); 0 hits for any pop-out spawn code anywhere; `BLUEPRINT.md:249,322` scope multi-window/pop-out as v1.0-roadmap/deferred and cite the entry directly at both mentions | holds |

Summary: 3 holds, 1 ci_pinned. No regressions.

COVERAGE: 4/4 ids raw; no raw: none.
