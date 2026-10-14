# batch-13/W3-w3

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DOCS-017 | Read `docs/CURRENT_STATE.md:358-378` §3.3 screener bullet; in-process `load_india_universe('nse-all'\|'bse-all'\|'india-all')` + `sp500.json` load against the candidate's own venv; live `GET /screener/default-universe` | Doc quotes `sp500` 503 symbols (snapshot 2026-09-24), `nse-all` 3,506 (EQ 2,584 + ETF 351 + SM 571), `bse-all` 5,042, `india-all` 5,891, and documents nested AND/OR `CriterionGroup` (no longer "reserved"). Live loader counts from the candidate: `nse-all` 3506, `bse-all` 5042, `india-all` 5891, `sp500` 503 @ `2026-09-24` — exact match, no drift since batch-14's certification | holds |

Evidence: `raw/set-65/R15-DOCS-017-live-counts.txt`, `raw/set-65/R15-DOCS-017-default-universe.json`.

COVERAGE: 1/1 ids raw; no raw: none.
