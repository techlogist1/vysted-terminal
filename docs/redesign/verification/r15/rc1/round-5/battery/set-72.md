# set-72 — batch-26/W2-sonnet (rc1-battery-21)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98, own sidecar :52361.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-010 | source read `symbol_resolver.py` (`_live_lookup`) + live `GET /resolve?q=zzqxnonexistentco9999` + pinned tests | `_LIVE_SEARCH_TIMEOUT_SECONDS = 5.0` passed into `yf.Search(...)`, AND the caller waits via `_LIVE_SEARCH_POOL.submit(...); future.result(timeout=_LIVE_SEARCH_TIMEOUT_SECONDS)` — a wall-clock deadline independent of whether yfinance's own cookie/crumb leg honors the kwarg (the exact round-2-refutation gap); live miss resolved in 1.10s; two pinned tests present: `test_live_lookup_passes_an_explicit_short_search_timeout` (kwarg recorded ≤10s) and `test_live_lookup_is_wall_clock_bounded_when_search_hangs` (wall-clock bound even when Search hangs) | holds (ci_pinned: `sidecar/tests/test_symbol_resolver.py::test_live_lookup_passes_an_explicit_short_search_timeout`, `::test_live_lookup_is_wall_clock_bounded_when_search_hangs`) |
| R15-LEAD-039 | `GET /earnings/{RDY,TM,SONY}/estimates` | all three now HTTP 200 (was 502 "incomplete estimate fields"): `eps_estimate_mean/high/low` are `null` (EPS fields absent from yfinance's calendar, as documented) while `revenue_estimate_mean/high/low` and `revenue_analyst_count` are populated per symbol | holds |

Raw: `battery/raw/set-72/R15-{AGENT-010,LEAD-039-RDY,LEAD-039-TM,LEAD-039-SONY}.txt`
