# batch-10/W4-screener-routes-statedocs

Candidate `4c6dfe8c` (rc1-cand worktree). Own sidecar `127.0.0.1:52340`.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-DATA-071 | Read `sidecar/services/bse_provider.py` (`get_history`, `_assemble_history`); live `GET /history/CREST.BO?range=1y`. | Comment cites R15-DATA-071 directly: `partial`/`coverage_start` are now real fields on `OHLCVSeries`, computed from `gaps` (`partial = bool(gaps) and gaps[0] >= wanted_from`) — a cold-cache range that ran out of the 8-download budget is now marked partial with the honest coverage-start date, not silently returned as if it were the full range. Live CREST.BO/1y returned 240 bars, `partial:false` (this symbol's cache was already warm). | holds |
| R15-DATA-087 | `GET /macro/CPIAUCSL` (no provider). | `422 {"detail":"provider is required for a series id"}`. | holds |
| R15-DATA-095 | In-process: built a `fundamentals` table missing `seed_updated_at`/`eod_updated_at`/`provider` via `fundamentals_store._ALL_COLUMNS` minus those 3, then called the real `_connect()`. | All 3 columns present after `_connect()` (the general `_migrate` ALTERs every column in `_ALL_COLUMNS`, not a hand-picked subset); comment cites R15-DATA-095 directly. | holds |
| R15-DOCS-016 | grep `docs/CURRENT_STATE.md` + in-process `catalog.CAPABILITY_CATALOG` count. | Doc states "19 host actions ... no order action exists, D81 — none auto-apply"; live catalog has exactly 19 `kind='host_action'` capabilities, no order-shaped id. | holds |
| R15-DOCS-017 | grep `docs/CURRENT_STATE.md:358-372` (screener universes bullet). | Doc now reads "sp500 ... 503 symbols, a static snapshot dated 2026-09-24", "nse-all ... 3,506 symbols: EQ 2,584 + ETF 351 + SM 571", "bse-all ... 5,042", "india-all ... 5,891", "nested AND/OR via `CriterionGroup`" — no "R15-LEAD-013 open" text anywhere. This differs from the OLDER cert snapshot ("506 symbols, 2026-06-04") because R15-LEAD-013's own fix (batch-11) regenerated the sp500 pack to 503/2026-09-24, which this doc entry's LATEST certification (batch-14, register note) explicitly re-pinned to the loader's live counts — the current text matches that final certified state exactly. | holds |
| R15-DOCS-018 | grep `docs/CURRENT_STATE.md:93-94,320` + `GET /data-sources`. | Doc: "resolves by standard model key + preference order (not the asset-class chain); every result carries its serving provider"; live `/data-sources` returns per-provider `keys`/`rank`/`asset_classes` rows matching that model. | holds |

**Set result: 6/6 holds.**
