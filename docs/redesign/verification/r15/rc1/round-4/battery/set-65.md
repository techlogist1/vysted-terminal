# set-65 — batch-13/W3-docs-017-india-universe-counts (rc1-battery-3)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad, own sidecar :52343.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DOCS-017 | Live `GET /screener/universe?id={nse-all,bse-all,india-all,sp500}` + code read (models/screener.py CriterionGroup) + doc read | nse-all 3506, bse-all 5042, india-all 5891, sp500 503 — matches CURRENT_STATE.md §3.3's stated counts and batch-13's cert exactly; `CriterionGroup` on `ScreenerRequest.group` confirms nested AND/OR ships (not "reserved") | holds |

Separate new_defect (outside this entry's scope, filed as `rc1-battery-3:1`): `docs/CURRENT_STATE.md:356-358` still describes earnings `fiscal_period` as "inferred from calendar month" and EPS stddev as "an approximation (high−low)/4" — stale since the DATA-032/067 fix (set-19 above confirms both are now `null`, not fabricated/inferred).

COVERAGE: 1/1 ids raw; no raw: none.
