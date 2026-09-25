# batch-10/W7-panels-marketplace (rc1-battery-7)

Candidate `4097dac4`. Own sidecar on `:52347`. 7 certified entries re-run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-053 | test file presence: `src/modules/chat/context-provider.test.ts` (cert evidence was purely this vitest) | file present on `4097dac4` | ci_pinned |
| R15-UI-032 | `GET /sec/filings/search?q=Apple`, `q=Nvidia`, `q=zzqxnotacompany` | Apple → `[AAPL, APLE, MLP, AAPI, PAPL]` (exact ticker first); Nvidia → `[NVDA]`; unknown → `{"results":[]}`, no exception | holds |
| R15-UI-028 | test file presence: `src/modules/quant/units.test.ts` (cert evidence was purely this vitest — rho per-1% labelling) | file present | ci_pinned |
| R15-UI-018 | test file presence: `src/modules/marketplace/MarketplacePanel.test.tsx` (cert evidence was purely this vitest — single click doesn't remove, second confirms) | file present | ci_pinned |
| R15-CODE-PLATFORM-072 | `GET /data-sources` | provider rows with `keys`/`rank`/`asset_classes` for ccxt/openbb-mcp/nse_direct/nse/bse/yfinance — matches the shape `marketplace.ts` derives from | holds |
| R15-DATA-077 | same `/data-sources` fetch | `nse_direct` (rank 15), `nse` (rank 20), `bse` (rank 25) all listed as distinct keyless India lanes | holds |
| R15-DATA-068 | test file presence: `src/modules/analyst-ratings/AnalystRatingsPanel.test.tsx` (UI leg — as-of chip; the sidecar leg was re-verified live in set-40) | file present | ci_pinned |

Raw output: `battery/raw/set-44/*`.
