# rc1-battery-22 — regression battery shard 22 (round 4)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Sets: batch-7/W1-india-exchange-data (set-25),
batch-2/W1-fundamentals-seam (set-0), batch-11/W2-runtime-schema (set-49). 15 ids total, all
previously `status: fixed` and `certified` in their batch VERDICTS.json.

Own sidecar booted at :52362 (sleep pid 10892, worker 10895), data dir
`rc1-round-4-data-battery-22` (copy of seed data), used for sets 25 and 0 (live GET regression
checks against real NSE/BSE/SEC upstreams, no stubs). Set 49 (batch-11) needed no sidecar boot —
verified via ast inspection and in-process python calls against the candidate's `sidecar/.venv`
(a second scratch copy `rc1-round-4-lifecycle-test` for the schema-migration/backup repro, since
that repro mutates a data dir's build marker and stores).

Result: all 15 ids hold. No regressions found.

Notable:
- R15-DATA-013 (DAL EPS/P/E): the `eps` field is now sourced from BSE exchange-filed data as `ok`
  (an improvement beyond what the batch-2 cert snapshot showed), while `pe_ratio` stays correctly
  `flagged` with the true P/E stated in its reason — the silent-pass-through defect class does not
  reproduce.
- R15-DATA-060 (SIFY 20-F shareholding): the live SEC fetch succeeded this run (cert had fallen
  back due to a transient `browse-edgar` 503) and returned the exact 83.78% family-control figure.
- R15-CODE-AGENT-009: `invoke_agent` measured 101 lines this run vs the cert's 95 — a small,
  non-regressive drift, still far under the pre-fix ~488-line baseline; the split-loop structure
  and the 9 pinned phase tests are intact.
- R15-DATA-027's agent/MCP-tool-specific wrapper was not separately round-tripped through an
  LLM/Ollama call (to avoid holding the shared Ollama lock for a wrapper that calls the identical
  underlying `provider_registry` fundamentals path already confirmed live via direct GET) — scoped
  down, documented in set-25.md.

Sidecar stopped at end of run (kill of sleep pid 10892). Scratch data dirs
(`rc1-round-4-data-battery-22`, `rc1-round-4-lifecycle-test`) left under the scratchpad, not
touched under docs/.

COVERAGE: 15/15 ids raw; no raw: none.
