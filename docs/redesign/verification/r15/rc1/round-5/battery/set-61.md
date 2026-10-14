# batch-13/W3-DOCS-017 (rc1-battery-2, round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar `:52342`, data dir
`rc1-round-5-data-battery-2`. Raw output: `raw/set-61/`.

| id | repro run | observed | verdict |
| --- | --- | --- | --- |
| R15-DOCS-017 | grep `docs/CURRENT_STATE.md` §3.3 screener bullet; in-process `screener_universe_india.load_india_universe("nse-all"/"bse-all"/"india-all")` + `screener_universes/sp500.json` symbol count/`snapshot_date`, against the LIVE running loader; grep `models/screener.py` for `CriterionGroup`/`combinator` | doc reads: sp500 "503 symbols, a static snapshot dated 2026-09-24"; nse-all "3,506 symbols: EQ 2,584 + ETF 351 + SM 571"; bse-all "5,042 symbols"; india-all "5,891 symbols"; nested AND/OR via `CriterionGroup` (`combinator: "and"\|"or"`). Live loader: `nse-all=3506`, `bse-all=5042`, `india-all=5891`, `sp500=503` @ `2026-09-24` — all four counts match the doc exactly (the doc's own acceptance criterion: quote the loader's live counts, not a stale module docstring). `CriterionGroup` class + `combinator: Literal["and","or"]` confirmed at `models/screener.py:170-181` | holds |

Summary: 1 hold. No regressions.

COVERAGE: 1/1 ids raw; no raw: none.
