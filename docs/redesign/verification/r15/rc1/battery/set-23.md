# batch-7/W1-india-exchange-data

Own sidecar: candidate `4097dac4`, `127.0.0.1:52345`, data dir `rc1-data-rc1-battery-5` (seed
copy). All 7 entries are live HTTP/in-process re-runs against the running candidate sidecar
(never vitest/pytest suites).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-014 | `GET /fundamentals/DAL` (register/VERDICTS repro symbol). | `revenue_ttm` 99,700,000 (9.97 Cr), `field_meta.revenue_ttm.provider="bse"`, label "standalone, sum of 4 filed quarters to 2026-06-30", reason states the provider's 27,600,000 disagrees and is not served — matches VERDICTS.md's certified figure exactly. | holds |
| R15-DATA-027 | In-process `services.agent_tools.fundamentals._fundamentals({"symbol":"DAL.BO"})` and `{"symbol":"AAPL"}` (candidate venv). | DAL: `revenue_ttm=99700000.0`, `provider="bse"`. AAPL: `revenue_ttm` stays `provider="yfinance"`, no exchange-lane call — same split VERDICTS.md certified for the agent tool path. | holds |
| R15-DATA-050 | `GET /disclosures/results?symbol=JONJUA\|DAL\|ELCIDIN`. | All three return HTTP 200 `coverage:"covered"` with BSE/NSE results events (JONJUA 4 BSE events incl. Results 2026-04-23; DAL Results 2025-11-10/08-11; ELCIDIN Results 2025-08-08 etc.) — the register's prior-502 symbols now 200. | holds |
| R15-DATA-060 | `GET /disclosures/shareholding?symbol=SIFY\|AAPL`. | AAPL: 200 `coverage:"not_applicable"`, note "not an NSE/BSE instrument". SIFY: 200 `provider:"sec-20f"`, 4 major holders 67.98+7.90+7.56+0.34=83.78%, `source_url` a live sec.gov Archives 20-F — matches the register's "83.78% family control" and VERDICTS.md's certified SIFY figures (the 20-F lane worked live this run, unlike the verifier's session where sec-edgar-mcp timed out — data.sec.gov direct path unaffected either way). | holds |
| R15-DATA-076 | `GET /fundamentals/DAL` (same response as DATA-014). | `revenue_growth=0.452`, `field_meta.revenue_growth.provider="bse"`, label "standalone, period to 2026-06-30 vs the same period to 2025-06-30" — matches VERDICTS.md's certified 0.452. | holds |
| R15-LEAD-004 | `GET /fundamentals/TCS`. | `field_meta.revenue_ttm`: `provider="nse"`, label "consolidated, sum of 4 filed quarters to 2026-06-30", `reason=null` — the exchange lane resolves cleanly with no "half-yearly" mislabel (consistent with the fix; the lane answered rather than exercising the no-lane fallback text VERDICTS.md also covered). | holds |
| R15-LEAD-015 | `GET /fundamentals/DHANBANK/income?period=quarterly`. | Response carries `"gaps": ["2025-09-30"]` and the `2025-09-30` period's values are `null` in every line (operating_revenue, total_revenue, …); periods are ISO dates. Matches VERDICTS.md's certified gap row exactly. | holds |

Raw output: `raw/set-23/DATA-014.txt`, `DATA-027.txt`, `DATA-050-{JONJUA,DAL,ELCIDIN}.txt`,
`DATA-060-{SIFY,AAPL}.txt`, `LEAD-004-tcs.txt`, `LEAD-015-dhanbank-income.txt`.
