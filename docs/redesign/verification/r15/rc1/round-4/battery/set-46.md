# batch-10/W7-panels-marketplace — regression battery re-run (rc1-battery-11, round-4)

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad, sidecar :52351 (shared for the whole shard).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-UI-032 | `GET /sec/filings/search?q=Apple` / `?q=Nvidia` / `?q=zzqxnotacompany` | Apple -> AAPL first (Apple Inc.); Nvidia -> NVDA exact; garbage -> `[]`, no exception, HTTP 200 all three. | holds |
| R15-UI-028 | `POST /quant/option/greeks` (spot 220, strike 220, r 0.05, q 0.005, vol 0.28) + code check `src/modules/quant/units.ts` `toMarketUnits()` and `GreeksDashboard.tsx:245,446` | Backend still serves raw QuantLib units (vega 60.76/yr-vol, theta -21.66/yr) unlabelled; frontend `greekForDisplay` routes vega/theta/rho through `toMarketUnits` (÷100, ÷365, ÷100 with unit strings) at both render sites. Matches certified fix shape. | holds |
| R15-UI-018 | Code check: `ConfirmButton.tsx` used in all 6 named panels; `SettingsPanel.tsx:445-453` try/catch on `deleteSecret`. Behavioral double-click-confirm assertion is vitest (`MarketplacePanel.test`: "a single click on Remove does not remove the plugin; a second click confirms it"). | Static code matches the certified fix everywhere (ConfirmButton wired into AgentBuilderPanel/WorkspaceDialog/SettingsPanel/PortfolioPanel/ScreenerPanel/MarketplacePanel; keychain delete now try/catch with a surfaced reason). Actual click-sequence behavior needs vitest, not run by this role. | ci_pinned (MarketplacePanel.test.tsx: "a single click on Remove does not remove the plugin; a second click confirms it") |
| R15-CODE-PLATFORM-072 | `GET /data-sources` + code check `src/lib/marketplace.ts:172-236` | Live response: yfinance serves 7 keys (analyst_rating, balance_sheet, cash_flow, fundamentals, income_statement, ohlcv, quote), matching provider_registry, not the old 3-key hand literal. `fetchDataSourceDeclarations()` derives rows straight off this response's snake_case fields; `catch{}` returns `{}` on failure (no stale hand row). | holds |
| R15-DATA-077 | `GET /data-sources` (IN-region rows) + code check `src/lib/marketplace.ts:196-215` `INDIA_DATA_LANES` + `grep -ri "eodhd\|twelve"` | Only nse_direct/nse/bse (keyless EOD) carry region IN; `INDIA_DATA_LANES` renders exactly those three as informational rows once `/data-sources` confirms them. No EODHD/Twelve Data hit in sidecar or src (only unrelated "twelve months" strings). Vendor deferral remains, as designed/certified. | holds |

COVERAGE: 5/5 ids raw; no raw: none.
