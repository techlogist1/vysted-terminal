# Regression battery — set-45 (batch-10/W7-panels-marketplace)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar on `:52345`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-CODE-PLATFORM-072 | Live `GET /data-sources` on the running sidecar | `yfinance` now serves all 7 keys (`analyst_rating, balance_sheet, cash_flow, fundamentals, income_statement, ohlcv, quote`), matching `provider_registry.py`; `nse_direct/nse/bse/ccxt` each have an entry with rank+region; `src/lib/marketplace.ts:172-236` derives rows from this same fetch, not a hand-written catalog | holds |
| R15-DATA-077 | Live `GET /data-sources`, filtered to `nse_direct`/`nse`/`bse` | All three carry `region: ["IN"]`, keyless, stable ids; pinned by `marketplace.test.tsx::"declares the three India keyless lanes with a stable id (matches the resolver)"` | holds |
| R15-UI-018 | `grep -rl ConfirmButton src` (all 6 non-test surfaces) + live read of `ConfirmButton.tsx` (arm/confirm, 4s window) + `SettingsPanel.tsx:446-452` `handleRemove` | `ConfirmButton` now guards SettingsPanel, ScreenerPanel, WorkspaceDialog, MarketplacePanel, AgentBuilderPanel, PortfolioPanel (all 5 original repro surfaces); `deleteSecret` is wrapped in try/catch, sets `removeError` on failure (was an unhandled rejection) | holds |
| R15-UI-028 | Read `src/modules/quant/units.ts` (`toMarketUnits`) + `GreeksDashboard.tsx:108,144` (renders `${value} ${unit}`) + pinned `units.test.ts` | `vega: value/100 "per 1 vol pt"`, `theta: value/365 "per day"`, `rho: value/100 "per 1%"` — all three now unit-labelled (rho was the batch-10 residual fix); rendering path shows the unit string next to the value | holds |
| R15-UI-032 | Live `GET /sec/filings/search?q=Apple` / `q=Nvidia` / `q=zzqxnotacompany` on the running sidecar | Apple → 6 real hits incl. exact ticker AAPL first; Nvidia → NVDA only; nonsense query → `[]` (no swallowed exception) | holds |

COVERAGE: 5/5 ids raw.
