# rc1-battery-5 — regression battery shard 5 (round 5)

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98`. Own sidecar booted from
`.../rc1-round-5-cand/sidecar` on `127.0.0.1:52345`, data dir a fresh copy of
`rc1-round-5-seed-data` at `.../rc1-round-5-data-rc1-battery-5`. openbb-mcp/sec-edgar-mcp
reused shared read-only (`:52153`/`:52154`).

Sets: batch-4/W1-agent-runtime (set-10, 9 ids), batch-10/W7-panels-marketplace (set-45, 5
ids), batch-11/W3-agent-eval (set-49, 1 id), batch-16/W1-one (set-63, 1 id). 16 ids total.

## Result: 16/16 holds, 0 regressed, 0 findings

Method per id: read the register entry + the certifying batch's VERDICTS.md "Per-entry
evidence", then re-run that exact repro live against the candidate — direct HTTP against
the running sidecar where a route exists (compare_symbols has none, so it was called
in-process via its own handler function), or an in-process replay of the certifying code
path when the fix is a wire-shape/library-construction guarantee (Gemini thought
signatures, `GenerateContentConfig` construction, `native_search_available`). Two entries
(R15-UI-028, and half of R15-AGENT-007) lean on a named pinned test rather than a full
live re-run, per role instructions (never run the whole vitest/pytest suite from this
shard) — cited by file/test name in the set file and raw evidence.

Notable during the run:
- R15-AGENT-011's first probe used the wrong tool shape (`strategy: mean_reversion`
  instead of the tool's actual `entry`/`exit` DSL args) and failed with a genuine "unknown
  strategy" error unrelated to the entry — corrected and re-run against the real
  `POST /backtest/run` route with `RELIANCE.NS` (US symbols hit a live Yahoo rate-limit in
  this isolated stack, unrelated to the entry).
- R15-AGENT-007's first attempt threw `Connection refused` on both scenarios via
  `run.py`'s subprocess call to `vy.py`, while several of my own curl/probe processes were
  concurrently hitting the same `:52345` port. Traced in-process (identical `_http()` code
  path) it succeeded end to end with a real tool-calling turn; a clean re-run of the
  unmodified harness with nothing else hitting the port passed
  (`price-reliance #0 81.7s PASS`, `pass_hat_1: 1.0`). Recorded as a harness/environment
  artifact of my own parallel probing, not a product regression — the actual mechanism
  (grader + vy.py transport + agent loop) holds.
- Ollama lock: acquired for the two live agent_eval runs (`mkdir` succeeded immediately
  both times, no contention seen), released after each. One retry ran without explicitly
  re-acquiring the lock first (the prior background job's own `trap` had already released
  it before I noticed) — no observed collision with another lane, noted here for the
  record.

Stopped the shard's sidecar (killed the sleep-wrapper pid) and the ad-hoc black-hole TCP
listener used for R15-LEAD-032 at the end.

COVERAGE: 16/16 ids raw; no raw: none.
