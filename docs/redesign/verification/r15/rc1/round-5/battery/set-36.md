# batch-9/W3-fundamentals-identity-earnings (round 5, candidate 9bc600ec, rc1-battery-3)

Own sidecar :52343 (candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, seed-data copy `rc1-round-5-data-battery-3`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DATA-052 | Live `GET /fundamentals/ELCIDIN`, `GET /fundamentals/NAPEROL` | ELCIDIN: `sector:"Financial Services"`, `industry:"Investment Company"` (was empty). NAPEROL: `sector:"Financial Services"`, `industry:"Investment Company"` (was "Basic Materials"/"Chemicals") — exact match to cert | holds |
| R15-DATA-069 | Live `GET /fundamentals/AAPL/ratings/price-target-history` | 972 per-firm/per-day rows across 60 distinct firms and 527 distinct dates, not one "Consensus" snapshot — far exceeds cert's "10+ distinct rows" bar | holds |
| R15-LEAD-016 | Live `GET /earnings/AAPL/history` | `reported_date` (e.g. `2026-07-30`) is ~1 month after `period_end` (`2026-06-30`) on every row, not equal to it | holds |
| R15-LEAD-023 | In-process `yfinance_provider._quote_time(FakeTicker)` with metadata carrying no `regularMarketTime` and an empty 5-day history frame | Raises typed `ProviderError("Yahoo returned a price with no trade time")`, not `IndexError` — source (`yfinance_provider.py:508-533`) docstring explicitly cites R15-LEAD-023 as the terminal case | holds |

Evidence: `raw/set-36/R15-DATA-052-{ELCIDIN,NAPEROL}.json`, `raw/set-36/R15-DATA-069.json`, `raw/set-36/R15-LEAD-016.json`, `raw/set-36/R15-LEAD-023.txt`.

COVERAGE: 4/4 ids raw; no raw: none.
