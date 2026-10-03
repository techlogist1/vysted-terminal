# batch-10/W7-panels-marketplace (set-46), shard rc1-battery-7, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-053 | panel->agent context (frontend); grep of pinned tests + consumer branch | context-provider.test.ts:250/294/305 exist; context-provider.ts:408 pushes every other publisher into otherPanels | ci_pinned |
| R15-UI-032 | GET /sec/filings/search?q=Apple/Nvidia/AAPL/zzq... | Apple -> Apple Inc. AAPL first (+5 more); Nvidia -> NVDA; AAPL -> AAPL; junk -> [] (was empty for all) | holds |
| R15-UI-028 | Greeks panel units (frontend); grep + live route | units.test.ts pins vega per 1 vol pt / theta per day / rho per 1%; OptionPricerPanel.test.tsx:70; route still returns raw QuantLib partials by design | ci_pinned |
| R15-UI-018 | destructive-action confirms (frontend); grep | ConfirmButton used in Settings, Screener, AgentBuilder, Marketplace, WorkspaceDialog, Portfolio; MarketplacePanel test "a single click on Remove does not remove the plugin" exists | ci_pinned |
| R15-DATA-077 | GET /data-sources + marketplace grep | providers list nse_direct/nse/bse (region IN); marketplace.ts declares India keyless lanes; marketplace.test.ts:121 pins them | ci_pinned |

COVERAGE: 5/5 ids raw; no raw: none
