# batch-13/unassigned (rc1-battery-23, shard 23)

Candidate `949c3c9fd49d61ecadc9813a8321bcdfd81178bd`, own sidecar `:52363`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DOCS-017 | Live `GET /screener/universe?id={nse-all,bse-all,india-all,sp500}`; read `docs/CURRENT_STATE.md` §3.3 screener bullet | Live counts nse-all 3506, bse-all 5042, india-all 5891, sp500 503 — all four match `CURRENT_STATE.md` (lines 369-378) exactly (`3,506 symbols: EQ 2,584 + ETF 351 + SM 571`, `5,042`, `5,891`); doc also states "Criteria support nested AND/OR ... OR-grouping is no longer reserved/unimplemented" | holds |

COVERAGE: 1/1 ids raw; no raw: none.
