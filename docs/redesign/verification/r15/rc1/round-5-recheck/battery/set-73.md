# batch-26/W2-sonnet — rc1-battery-14 (gate round 5-recheck, candidate 949c3c9f)

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-AGENT-010 | Re-ran the batch-26 verifier's own `a010v2.py` (a never-answering local-socket stand-in for a hung `HTTPS_PROXY`), `cwd=sidecar`, against candidate `symbol_resolver`/`agent_tools.resolve_symbol` (`raw/set-73/R15-AGENT-010.txt`) | `'zzqx vericheck unfound co'` (US, unresolved masters miss): wall 6.09 s, `_live_lookup` bounded at 5.45 s, `max_gap_ms 27` (event loop never stalls). Fresh query `'qqzv bramblewick holdings plc'` (IN): wall 8.83 s, `_live_lookup` bounded at 5.01 s, `max_gap_ms 27`. Matches the certified range (5.34-5.69 s bounded `_live_lookup`, max gap ~21 ms, vs 30+ s / event-loop-stalling at base). | holds |
| R15-LEAD-039 | Live `GET /earnings/RDY/estimates`, `/TM/estimates`, `/SONY/estimates` on :52354, plus fresh case `/HMC/estimates` (`raw/set-73/R15-LEAD-039.txt`) | All four return 200 (not 502). EPS triple is `null` on all four; revenue triple is set (RDY mean 84.51B INR, TM mean 13.35T JPY, SONY mean 3.15T JPY, HMC mean 5.84T JPY). Exact match to the certified original + fresh (HMC) case. | holds |

COVERAGE: 2/2 ids raw; no raw: none.
