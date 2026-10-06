# rc1-battery-12 log

Role: REGRESSION BATTERY shard 12. Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad.
Sidecar booted from candidate source on :52352, data dir rc1-round-4-data-battery-12 (copy of seed).
Sets: batch-8/set-31, batch-11/set-48, batch-6/set-20, batch-18/set-70.

## Results

- set-31 (batch-8): 4/9 hold via live curl + ollama-lock probes (R15-UI-013, R15-AGENT-028,
  R15-UI-057, R15-CODE-AGENT-006); 5/9 ci_pinned — frontend-only logic with no HTTP/GUI
  surface, confirmed present via static source read against the exact certified mechanism
  (R15-UI-049, R15-UI-019, R15-AGENT-055, R15-AGENT-056, R15-AGENT-081).
- set-48 (batch-11): 5/5 hold (scripts-build, all verified via direct node module calls +
  static source read, no vitest suite run).
- set-20 (batch-6): 1/1 holds (R15-DATA-017, live NSE calls).
- set-70 (batch-18): 1/1 holds (R15-LEAD-034, live quotes + in-process correctness_gate call
  with fresh symbols not used by the original writer/verifier).

No regressions found in this shard. Sidecar :52352 stopped (worker pid 87219, after sleep
pid 87216 exit did not propagate EOF fast enough — killed directly, this shard's own sidecar
only, no other owner's port touched).

COVERAGE: 16/16 ids raw; no raw: none.
