# Set 76 — batch-28/W3-sonnet (regression battery, shard 0, round 5)

Candidate: 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar: own boot on :52340,
data dir `rc1-round-5-data-rc1-battery-0` (copy of the round's seed data), openbb-mcp
:52153 + sec-edgar-mcp :52154 shared read-only.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-003 | `GET /disclosures/shareholding?symbol=AMAL` + `GET /disclosures/announcements?symbol=AMAL&limit=25`, header `X-Vysted-Region: US` | Both return `coverage: not_applicable`, `count: 0`, note "AMAL is not an NSE/BSE instrument; Indian exchange disclosures do not apply" — no data leak from Amal Ltd's BSE filing. | holds |
| R15-DATA-024 | `GET /disclosures/deals?symbol=KOPRAN`, header `X-Vysted-Region: IN` | 125 deals, exchanges {NSE, BSE}, 63 BSE rows, including the exact original-repro row: 2026-09-07 UNITED SHIPPERS LTD sell 700000 @234.3 on BSE (source_url present via `sources`). | holds |
| R15-DATA-038 | `GET /sec/filings/0000320193-25-000079/sections?identifier=AAPL`, `GET /sec/filings/0000320193-25-000079?identifier=AAPL`, `GET /sec/insider/AAPL?limit=50` | sections has 2+ populated entries (business 1432 words, risk_factors 1430 words, non-zero total_chars); insider returns 9 Form-4 transaction rows (not empty). | holds |
| R15-RESEARCH-022 | In-process: `KeylessSearchBackend(engines={"ddg": stub})` where stub returns one row "Unusual traffic from your computer network" / "verify you are a human" (candidate `.venv`, cwd `sidecar/`) | `search()` raises `SearchError` reason=`rate_limited` ("keyless web search has no engine available right now — DuckDuckGo: blocked (challenge page); …") instead of returning an ok empty `SearchResponse`; breaker.record_failure() fires on the block. | holds |

COVERAGE: 4/4 ids raw; no raw: none.
