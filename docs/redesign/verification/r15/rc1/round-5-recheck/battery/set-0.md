# Set 0 — batch-2/W1-fundamentals-seam (rc1-battery-24)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`. Own sidecar on `127.0.0.1:52364`, data dir copied from `rc1-round-5-recheck-seed-data`. Every id re-run live: 4 via HTTP against the running sidecar, 2 via in-process python against the candidate's own `sidecar/.venv`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-004 | `GET /fundamentals/DHANBANK` (X-Vysted-Region: IN) on :52364 | `held_percent_insiders=0.51176`, `field_meta.held_percent_insiders.status="flagged"`, reason "yfinance insiders 51.18% disagrees with the NSE shareholding filing... (promoter group: 0.00%)... kept, flagged"; `held_percent_institutions` also flagged | holds |
| R15-DATA-013 | `GET /fundamentals/DAL` on :52364 | `eps=2.05` served from BSE exchange filing (not raw yfinance 8.9); `field_meta.eps.reason`="exchange-filed (BSE) figure served; the provider's 8.90 disagrees with it — not served"; `pe_ratio.status="flagged"` naming the implied 24.5 P/E | holds |
| R15-DATA-006 | `GET /quotes/DAL?asset_class=equity` on :52364 | `timestamp=2025-03-12T00:00:00Z`, `freshness="stale"`, `market_state="CLOSED"`, `change=0.0` — the 556-day-stale print is labelled stale, not presented as today's +4.99% | holds |
| R15-DATA-070 | in-process: `_parse_struct_time(None)`, `_parse_iso("not-a-date")`, `_parse_iso(None)`, then the real `fetch_news` merge/sort logic on a dated+undated pair | all three parsers return `None` (never `_utcnow()`); sort order `['a'(dated), 'b'(undated)]` — undated sorts LAST, `published_at=None` | holds |
| R15-DATA-033 | in-process: `validate_quote`/`validate_series` on NaN price, Inf price, NaN last-close via the real `correctness_gate.py` + `models/market.py` | all three raise `CorrectnessError` ("non-positive price nan/inf", "non-positive last close nan") — `math.isfinite` gate catches what bare `<= 0` missed | holds |

COVERAGE: 5/5 ids raw; no raw: none.
