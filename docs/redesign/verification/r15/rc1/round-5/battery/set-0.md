# batch-2/W1-fundamentals-seam

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`, own sidecar `127.0.0.1:52351`,
data dir `rc1-round-5-data-rc1-battery-11` (seed copy). Live GETs where the register
repro was live; in-process python (candidate's `sidecar/.venv`) for the two entries
whose repro is code-level (correctness gate, news date parsing) — no pytest/vitest
suite run.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-008 | `GET /fundamentals/SIFY` | `currency: "USD"`, `financial_currency: "INR"`; `price_to_sales` is `null`/`status: "withheld"`, reason "Yahoo's price/sales ... divides or states a USD listing value against INR statements ... withheld" — same mechanism as the original repro. | holds |
| R15-DATA-004 | `GET /fundamentals/DHANBANK` | `held_percent_insiders: 0.51176`, `field_meta.held_percent_insiders.status: "flagged"` (yfinance 51.18% vs NSE promoter group 0.00%). `held_percent_institutions: 0.0602`, `field_meta.held_percent_institutions.status: "flagged"` (yfinance 6.02% vs BSE institutional 14.26% this run — the exact percentage the exchange filing carries has moved day-to-day, but the flagging mechanism is unchanged). | holds |
| R15-DATA-013 | `GET /fundamentals/DAL` | Top-level `eps: 2.05` (exchange-filed BSE figure), `field_meta.eps.status: "ok"`, provider `bse`. `pe_ratio: 5.6044946` kept but `field_meta.pe_ratio.status: "flagged"`, reason "trailing EPS 8.9 disagrees by 77% ... kept, flagged". | holds |
| R15-DATA-006 | `GET /quotes/DAL?asset_class=equity` | `{"change":0.0,"change_percent":0.0,"market_state":"CLOSED","freshness":"stale","provider":"bse","timestamp":"2025-03-12T00:00:00Z"}` — same stale BSE date, zero change, `freshness: "stale"`. | holds |
| R15-DATA-070 | In-process: `services.news_provider._parse_struct_time(None)`, `_parse_struct_time(<malformed struct_time>)`, `_parse_iso(None)`, `_parse_iso("not-a-date")`; grep of the sort-key source and `NewsFeedPanel.tsx`. | All four parse calls return `None` (never `utcnow()`). `sort(key=lambda item: item.published_at, reverse=True)` unchanged at news_provider.py:470. `NewsFeedPanel.tsx:28` renders `"date unknown"` for a null `published_at` (line shifted 27→28, same text). | holds |
| R15-DATA-033 | In-process: `services.correctness_gate.validate_quote`/`validate_series` (candidate's `.venv`) on a NaN-price `Quote`, an inf-price `Quote`, and an `OHLCVSeries` whose last bar's `close` is NaN. | All three raise `CorrectnessError`: `"non-positive price nan for 'TEST' from 'nse'"`, `"non-positive price inf for 'TEST' from 'nse'"`, `"non-positive last close nan for 'TEST' from 'nse'"` — verbatim match to the original repro. | holds |

**Set result: 6/6 holds. No regressions.**
