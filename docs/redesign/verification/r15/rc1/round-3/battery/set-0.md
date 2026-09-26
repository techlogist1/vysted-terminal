# batch-2/W1-fundamentals-seam + batch-2/W2-instrument-identity — rc1-battery-0

Candidate sha 01d6920a300b016ab1ad8aa436ee4e4586f8e336, own sidecar :52340 (data dir
`rc1-round-3-data-rc1-battery-0`, copy of the seed profile).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-004 | `GET /fundamentals/DHANBANK` | `held_percent_insiders`/`held_percent_institutions` now `status:"flagged"` with a reason citing the NSE/BSE shareholding disagreement (>3pp) instead of plain `ok` | holds |
| R15-DATA-006 | `GET /quotes/DAL?asset_class=equity` | `timestamp:"2025-03-12T00:00:00Z"`, `freshness:"stale"` — the true 556-day-old print date, not today | holds |
| R15-DATA-008 | `GET /fundamentals/SIFY` | top-level `financial_currency:"INR"` now distinct from `currency:"USD"`; `price_to_sales` withheld with a currency-mismatch reason; frontend (`EquityOverviewPanel.tsx:833`, `metrics.ts:19`, `brief-blocks.tsx:336`) consumes `financial_currency ?? currency` and is unit-tested | holds |
| R15-DATA-013 | `GET /fundamentals/DAL`, `/fundamentals/SMR` | DAL `eps` now sourced from BSE exchange filing (2.05) not Yahoo's stale 8.9; SMR `eps`/`pe_ratio` both `status:"flagged"` citing the 58% net-income/shares disagreement | holds |
| R15-DATA-033 | in-venv `correctness_gate.validate_series/validate_quote` on NaN close/price | both now raise `CorrectnessError` ("non-positive last close/price nan") — `x <= 0` replaced by `not math.isfinite(x) or x <= 0` at correctness_gate.py:161,199 | holds |
| R15-DATA-070 | read `sidecar/services/news_provider.py` | `_parse_struct_time`/`_parse_iso` return `None` (never `_utcnow()`); `NewsItem.published_at: datetime \| None`; `fetch_news` sorts dated items desc then appends undated items last | holds |
| R15-CODE-DATA-001 | `GET /resolve?q=FOCUS`, `GET /disclosures/shareholding?symbol=FOCUS` | resolver now returns `needs_disambiguation:true` with two distinct candidates (NSE Focus Lighting: isin/bse_code null; BSE Focus Business Solution: its own isin/bse_code) — no more merged ISIN/BSE-code; shareholding `split_source:null` | holds |
| R15-CODE-DATA-005 | grep `is_applicable`/`_is_blocked`/`is_india_target` under `sidecar/services` | `market_cap_witness.py`, `ownership_check.py`, `research/range_check.py` each now `is_applicable = is_india_listing` imported from new `services/witness.py`; `research/disclosures.py` imports `is_india_target` from `relevance.py` instead of holding its own copy | holds |
| R15-DATA-001 | `GET /fundamentals/DAL/income` | `symbol:"DAL.BO"`, periods FY-end 2026-03-31 etc, `operating_revenue` ~20.6M (matches Dynamic Archistructures' scale), not Delta's multi-billion figures | holds |
| R15-DATA-003 | `GET /disclosures/shareholding?symbol=AMAL` (route) + read `services/witness.py`, `services/ownership_check.py`, `services/research/fast.py:376` | new `services/witness.is_india_listing` decides on the RESOLVED listing suffix (`.NS`/`.BO`), not bare-ticker master membership; docstring names this exact AMAL case; `ownership_check.get_exchange_ownership` is called with the resolved `listing` (fast.py:376) so a US AMAL (no suffix) is skipped — the raw India-only `/disclosures/shareholding` HTTP route itself is unchanged by design (bare-ticker lookup), the research-layer applicability gate is what was fixed and holds | holds |

COVERAGE: 12/12 ids raw; no raw: none.
