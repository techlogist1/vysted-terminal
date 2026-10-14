# set-0 — batch-2/W1-fundamentals-seam (rc1-battery-22, round-4, candidate 1006c6da)

Sidecar :52362, own data dir `rc1-round-4-data-battery-22`. Raw per-id files under `battery/raw/set-0/`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-008 | `GET /fundamentals/SIFY` | `currency:"USD"`, `financial_currency:"INR"`, `revenue_ttm` still the raw INR-magnitude number (46.5B) but `price_to_sales`/`ev_to_ebitda` now `status:"withheld"` with reason "mixes bases: trades in USD, reports in INR ... withheld". Matches cert exactly. | holds |
| R15-DATA-004 | `GET /fundamentals/DHANBANK`, `/JONJUA` | DHANBANK `held_percent_insiders` 0.51176 flagged "disagrees with the NSE shareholding filing ... promoter group: 0.00% ... beyond 3pp". JONJUA 0.46623 flagged against 29.67%. Matches cert exactly. | holds |
| R15-DATA-013 | `GET /fundamentals/DAL` | `eps` field now `status:"ok"` sourced `bse` = 2.05 (exchange-filed, an improvement beyond the batch-2 cert snapshot). `pe_ratio` stays `status:"flagged"`, reason states the disagreement and the correct P/E ("... implies P/E 24.5 ... kept, flagged") — never silently `ok`. The defect class (silent pass-through) does not reproduce. | holds |
| R15-DATA-006 | `GET /quotes/DAL?asset_class=equity` | `timestamp:"2025-03-12T00:00:00Z"`, `change:0.0`, `freshness:"stale"`, `provider:"bse"`. Matches cert exactly (no fresh-looking stale print). | holds |
| R15-DATA-070 | in-process: `_parse_struct_time(None/malformed)`, `_parse_iso(None/malformed)` on candidate's `services/news_provider.py`; source read of `fetch_news` sort | Both parsers return `None` (never `_utcnow()`) for missing/malformed dates; `fetch_news` sorts only the dated subset newest-first and appends undated items after — matches cert's "dated items newest first, then undated". `NewsFeedPanel.test.tsx` still present. | holds |
| R15-DATA-033 | in-process: `correctness_gate.validate_quote`/`validate_series` on candidate's `services/correctness_gate.py` with NaN price, Inf price, NaN last close | All three raise `CorrectnessError` ("non-positive price nan/inf", "non-positive last close nan") — `math.isfinite` guard confirmed present and firing. | holds |

COVERAGE: 6/6 ids raw; no raw: none.
