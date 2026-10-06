# batch-12/W7-w7 (set-62)

Candidate 4c6dfe8c. Own sidecar :52342, data dir rc1-data-battery-2. Raw output: `raw/set-62/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-002 | Live: `GET /history/AMAL?range=1mo` under `X-Vysted-Region: US` vs `IN`; code read `chart-command.ts:25,43,65` (optional `region` on the command), `sidecar-client.ts:235,254` (`value !== undefined` drops an unset per-call region) | US region -> `provider:yfinance`, last close 47.58 USD (Amalgamated Financial). IN region -> `provider:nse_direct`, last close 674.4 INR (Amal Ltd) — the SAME symbol resolves to two different real listings by region, matching the cert's own live figures (47.21/687.65 from a different snapshot date — normal drift). `chart-command.ts` carries the region through the store; an unset region is dropped, not coerced to a default, so the session region still applies elsewhere. | holds |
| R15-UI-090 | Live (independent re-run for this set) at 07:05 IST Sat — both NSE and US closed: `GET /quotes/AAPL` and `/quotes/RELIANCE.NS` each under `X-Vysted-Region: IN` and `US` | Both symbols return the SAME `freshness:"eod"` regardless of the region header (AAPL: eod/eod; RELIANCE.NS: eod/eod, `market_state:"CLOSED"`) — confirms the region-invariant, instrument-based freshness labeling holds independently of which header is sent. The live/eod flip itself needs a market-hours window this run (Saturday) didn't have; same residual noted in set-13's row for this id. | holds |

Summary: 2 holds, 0 regressions. UI-090 is a duplicate id already verified independently in set-13 under the same weekend market-closed constraint; both runs agree.
