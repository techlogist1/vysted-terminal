# batch-26/W2-r15-agent-010-r15-lead-039 (set-77)

Live re-runs against the candidate sidecar on :52350 (candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad).

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-010 | (a) masters-hit `GET /resolve?q=infosys` timed; (b) code read of `resolve_symbol.py`/`symbol_resolver.py` for the to_thread/bound fix; (c) concurrent test: a live-miss resolve fired in the background while 5x `/health` were curled during it | (a) 0.28s (batch-26's fresh case measured 0.35s — consistent); (b) `resolve_async` now runs `resolve` on a dedicated `_RESOLVE_POOL` (4 workers, comment cites "R15-LEAD-040") instead of the shared to_thread pool, and `_LIVE_SEARCH_TIMEOUT_SECONDS = 5.0` bounds the yfinance Search call (was unbounded/30s default); (c) miss resolved in 0.92s and all 5 concurrent `/health` calls returned in 0.07-0.08s each — no event-loop stall | holds |
| R15-LEAD-039 | `GET /earnings/{RDY,TM,SONY,HMC}/estimates` | all four return 200 with `eps_estimate_*` fields null and `revenue_estimate_mean` populated (RDY 84.51B, TM 13.35T, SONY 3.15T, HMC 5.84T) — HMC is the exact fresh case batch-26 certified against, reproduced here again; a further fresh symbol (NSANY) 502s, but with the distinct "no upcoming earnings event" ProviderError branch (by design, not this entry's class) rather than a crash on missing EPS fields | holds |

Note (rule 9, three-failure watch): R15-AGENT-010 is at "certified after two failures" per the lead note — this run found no refutation, so no third failure is recorded.

COVERAGE: 2/2 ids raw; no raw: none.
