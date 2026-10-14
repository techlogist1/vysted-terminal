# batch-10/W7-panels-marketplace (set-46.md)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Shard rc1-battery-3. Own sidecar
`:52343`. Raw output: `battery/raw/set-46/<id>.txt`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-032 | `GET /sec/filings/search?q=Apple`, `?q=Tesla` (own sidecar); source check of `SecFilingsPanel.tsx`/`sec.ts` | Apple returns CIK `0000320193` first among 6 hits, Tesla returns CIK `0001318605` — `sec_filings_provider.search_companies` no longer swallows `edgar.search()` to `[]`; the panel has a debounced `searchCompanies` autocomplete wired at line 117 (batch-9's "still dead end to end" note is resolved) | holds |
| R15-UI-028 | Source read of `src/modules/quant/units.ts` (`toMarketUnits`/`greekForDisplay`), wiring check in `GreeksDashboard.tsx`/`OptionPricerPanel.tsx`; manual arithmetic on the register's own numbers | `vega/100=0.30627`, `theta/365=-0.1087`, `rho/100=0.135565` — vega, theta AND rho now convert to market units with labels ("per 1 vol pt"/"per day"/"per 1%"); both panels render `{unit}` beside the value; comment explicitly cites R15-UI-028 for the rho fix (the batch-9 "Rho still unlabelled" residual is closed too) | holds |
| R15-UI-018 | Source check of all 5 named sites (`AgentBuilderPanel.tsx`, `WorkspaceDialog.tsx`, `SettingsPanel.tsx` reset/layouts/provider-remove, `PortfolioPanel.tsx`) + `keychain.ts` | Every named site now wraps its destructive action in `<ConfirmButton>`; `ProvidersSection.handleRemove` wraps `deleteSecret` in try/catch and renders `removeError` inline (`text-negative` line) instead of an unhandled rejection | holds |
| R15-DATA-077 | Source check of `src/lib/marketplace.ts` (`INDIA_DATA_LANES`), `MarketplacePanel.tsx` wiring, `ChartPanel.tsx` empty-state copy | `INDIA_DATA_LANES` (nse_direct/nse/bse) is defined, comment-tagged R15-DATA-077, and rendered by `MarketplacePanel.tsx:129`; chart empty-state copy reads "No EOD data for this symbol. BSE/NSE serve end-of-day data only..." with no Kite/Upstox/Dhan mention (D81 copy half + the marketplace-row vendor half both present) | holds |

COVERAGE: 4/4 ids raw.
