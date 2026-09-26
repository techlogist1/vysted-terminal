# batch-2/W1-fundamentals-seam

Sidecar under test: candidate `4c6dfe8c` (rc1-cand worktree), own sidecar `127.0.0.1:52340`,
data dir `rc1-data-rc1-battery-0` (seed copy). Live GETs where the register repro was live;
in-process python (candidate's `.venv`) for the two entries whose repro is code-level
(correctness gate, news date parsing) — no pytest/vitest suite run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-008 | `GET /fundamentals/SIFY` | `currency: "USD"`, `financial_currency: "INR"`; `price_to_sales` is `null`/`status: withheld`, reason "mixes bases: the listing trades in USD but reports its statements in INR ... withheld". | holds |
| R15-DATA-004 | `GET /fundamentals/DHANBANK` | `held_percent_insiders: 0.51176`, `field_meta.held_percent_insiders.status: "flagged"`, reason "yfinance insiders 51.18% disagrees with the NSE shareholding filing ... (promoter group: 0.00%) beyond 3pp ... kept, flagged". `held_percent_institutions` likewise flagged (6.02% vs NSE 0%). | holds |
| R15-DATA-013 | `GET /fundamentals/DAL` | Top-level `eps: 2.05` (exchange-filed BSE figure). `field_meta.eps.status: "ok"`, provider `bse`. `pe_ratio: 5.6044946` kept but `field_meta.pe_ratio.status: "flagged"`, reason "trailing EPS 8.9 disagrees by 77% ... kept, flagged". | holds |
| R15-DATA-006 | `GET /quotes/DAL?asset_class=equity` | `{"change":0.0,"change_percent":0.0,"market_state":"CLOSED","freshness":"stale","provider":"bse","timestamp":"2025-03-12T00:00:00Z"}` — the stale BSE date flows through with zero change and `freshness: "stale"`. | holds |
| R15-DATA-070 | In-process: `services.news_provider._parse_struct_time(None)`, `_parse_struct_time(<malformed struct_time>)`, `_parse_iso(None)`, `_parse_iso("not-a-date")`; grep of the sort-key source and `NewsFeedPanel.tsx`. | All four parse calls return `None` (never `utcnow()`). Source shows `dated.sort(key=lambda item: item.published_at, reverse=True)` — undated items are handled separately, never sorted by a fabricated date. `NewsFeedPanel.tsx:27` renders `"date unknown"` for a null `published_at`. | holds |
| R15-DATA-033 | In-process: `services.correctness_gate.validate_quote`/`validate_series` (candidate `.venv`) on a NaN-price `Quote`, an inf-price `Quote`, and an `OHLCVSeries` whose last bar's `close` is NaN. | All three raise `CorrectnessError`: `"non-positive price nan for 'TEST' from 'nse'"`, `"non-positive price inf for 'TEST' from 'nse'"`, `"non-positive last close nan for 'TEST' from 'nse'"`. | holds |

**Set result: 6/6 holds.**
