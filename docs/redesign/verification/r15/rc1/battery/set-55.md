# batch-11/W8-frontend-visual (rc1-battery-1, candidate 4c6dfe8c)

Note: all 4 ids closed in batch-11 per `closure_evidence` (matches the task's own set label).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-085 | grep `text-charcoal-600`/`text-charcoal-700` unprefixed usage outside tests; presence of `design-contrast.test.ts` | `design-contrast.test.ts` computes WCAG ratios from `tokens.css` for every text token on charcoal-900/950 (present, unchanged); a fresh grep of `src/**/*.tsx` outside tests turns up no unprefixed readable use of the low-contrast tokens, matching the certified state | ci_pinned |
| R15-UI-091 | live `GET /indicators/suggested?timeframe=5m&asset_class=equity`, `...1d&crypto`, `...1d&equity`; live `GET /indicators/AAPL?indicators=ema:9,ema:21` on own sidecar (:52341) | (5m, equity) → `["ema:9","ema:21","vwap","rsi"]`; (1d, crypto) → `["ema:50","ema:200","vwap:week","rsi"]`; (1d, equity) → `["ma","volume","rsi","macd"]` — exact match to the spec's named combos and batch-11's certified output | holds |
| R15-CODE-PLATFORM-023 | presence of `src/modules/portfolio/metrics.ts` + `metrics.test.ts`, `backtest.test.ts`, `PortfolioPanel.test.tsx` | all present, covering per-currency buckets, null-under-30-days, and the Risk section's loading/insufficient states per batch-11's cert. The independent Python-vs-metrics.ts numerical cross-check (agreement to 1e-15 on live TCS.NS/^NSEI data) is a one-off already performed by batch-11's fresh verifier and was not repeated this shard (frontend-only computation, no server-side behaviour to independently regress beyond the pinned vitest suite) | ci_pinned |
| R15-CODE-PLATFORM-025 | `sed -n '249p;322p' docs/BLUEPRINT.md` | line 249: "Multi-tab layout (dockview, shipped); multi-window (v1.0 roadmap, deferred — R15-CODE-PLATFORM-025)"; line 322: "Drag-drop panel layout (resize, hide; pop-out to a second window is v1.0 roadmap — R15-CODE-PLATFORM-025)" — byte-identical to the certified text; BLUEPRINT §2 untouched (confirmed unmodified, per the never-edit-unilaterally list) | holds |

COVERAGE: 4/4 ids raw; no raw: none.
