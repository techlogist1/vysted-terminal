# batch-9/W3-fundamentals-identity-earnings (set-37), shard rc1-battery-11, candidate ace7dd76

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-LEAD-022 | GET /quotes/{BHP.AX,0700.HK,7203.T,VOD.L,SAP.DE,BRK.B} | all 200 priced (BHP.AX 61.21 AUD, 0700.HK 421.2 HKD, 7203.T JPY, VOD.L GBp, SAP.DE EUR); BRK.B -> BRK-B 502.65 | holds |
| R15-LEAD-023 | in-process _quote_time, empty metadata + empty history | ProviderError "Yahoo returned a price with no trade time" (no IndexError) | holds |
| R15-DATA-052 | GET /fundamentals/{NAPEROL,ELCIDIN} | both Financial Services / Investment Company, sector_source resolver | holds |
| R15-LEAD-016 | GET /earnings/{AAPL,MSFT,RELIANCE.NS}/history | AAPL reported 2026-07-30/04-30/2026-01-29 vs period_end quarter ends; RELIANCE.NS 2026-07-17 | holds |
| R15-DATA-069 | GET /fundamentals/AAPL/ratings/price-target-history and /individual; UI label grep | per-firm targets (Evercore 365->380 09-18, BofA 370 09-23), individual targets non-null; timeline title "Mean of targets revised that day" in source (adjacent: Needham target 0.0 row) | holds |
| R15-UI-015 | GET /macro/DGS10?provider=fred; pinned test | 502 deterministic keyless message; src/lib/use-sidecar-retry.test.ts "settles after one attempt when the engine answered (a keyless 502)" exists (heavy lane runs it) | ci_pinned |

COVERAGE: 6/6 ids raw; no raw: none
