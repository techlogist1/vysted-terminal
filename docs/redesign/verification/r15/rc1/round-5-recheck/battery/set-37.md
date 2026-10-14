# batch-9/W3-fundamentals-identity-earnings (shard rc1-battery-9)

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd. Sidecar: source, `127.0.0.1:52355`,
data dir `rc1-round-5-recheck-data-rc1-battery-9` (from `rc1-round-5-recheck-seed-data`).

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-LEAD-023 | in-process `_quote_time(FakeTicker)` with empty `get_history_metadata()` and empty `history(period='5d')` frame | `ProviderError("Yahoo returned a price with no trade time")` raised, not IndexError | holds |
| R15-DATA-052 | `GET /fundamentals/NAPEROL`, `GET /fundamentals/ELCIDIN` | both: `sector: "Financial Services"`, `industry: "Investment Company"`, `sector_source: "resolver"` (matches BSE truth; `field_meta.sector.provider` still says yfinance — same minor note batch-9 recorded, not a regression) | holds |
| R15-LEAD-016 | `GET /earnings/AAPL/history` | `period_end: "2026-06-30"` → `reported_date: "2026-07-30"`; `period_end: "2025-09-30"` → `reported_date: "2025-10-30"` — reported_date is the actual announcement date, distinct from period_end | holds |
| R15-DATA-069 | `GET /fundamentals/AAPL/ratings/price-target-history`, `GET /fundamentals/AAPL/ratings/individual` | history: Evercore ISI Group `target_from 365.0 → target_to 380.0` on 2026-09-18; B of A Securities `370.0` on 2026-09-23 — matches batch-9's raw-yfinance cross-check exactly. Individual table: `current_price_target` populated (370.0 / 380.0 / …), never null | holds |

Raw: `battery/raw/set-37/R15-LEAD-023.txt`, `R15-DATA-052-naperol.json`, `R15-DATA-052-elcidin.json`,
`R15-LEAD-016.txt`, `R15-DATA-069-history.json`, `R15-DATA-069-individual.json`.

COVERAGE: 4/4 ids raw; no raw: none.
