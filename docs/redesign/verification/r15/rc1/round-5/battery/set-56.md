# batch-12/W2-screener (rc1-battery-10)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar :52350.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-043 | Live `POST /screener/run` custom [AAPL, RELIANCE.NS, MSFT, TCS.NS], market_cap desc, limit 2 -> [RELIANCE.NS INR, AAPL USD], coverage "spans INR, USD — ranked within each currency". Fresh case: 6 mixed symbols asc, limit 3 -> [INFY.NS, TCS.NS, MSFT], round-robin per currency, coverage note present | matches batch-12 certification exactly | holds |
| R15-DATA-112 | Live `POST /screener/run` custom [MANIKA.NS, RELIANCE.NS, TCS.NS] (MANIKA has null market_cap): desc -> [RELIANCE.NS, TCS.NS, MANIKA.NS]; asc -> [TCS.NS, RELIANCE.NS, MANIKA.NS]. Null-market_cap row sorts last both directions | matches batch-12 certification exactly | holds |
| R15-DOCS-018 | `docs/CURRENT_STATE.md:331-338` still describes the preference-rank resolver: nse_direct rank 15, nse (jugaad) rank 20, bse rank 25, region IN, ahead of yfinance rank 50; `sidecar/services/provider_registry.py:167,184,203,219` confirm ranks 15/20/25/50 unchanged | doc still matches provider_registry.py ranks, no regression | holds |

COVERAGE: 3/3 ids raw; no raw: none.
