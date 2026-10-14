# rc1-battery-16 — regression battery shard 16 (batch-8 + batch-10 + batch-25 + batch-29)

Candidate 9bc600ece2ce6343a6aa48f130d7620b1466bb98. Sidecar booted from candidate source on
:52356, data dir copied from rc1-round-5-seed-data (own copy: rc1-round-5-data-battery-16).

## Sets
- set-30 (batch-8/W2-provider-readiness-host-actions): 8/8 holds/ci_pinned, 0 regressions.
- set-42 (batch-10/W4-screener-routes-statedocs): 5/5 holds, 0 regressions.
- set-69 (batch-25/W4-sonnet): 2/2 holds, 0 regressions.
- set-80 (batch-29/W1-opus): 1/1 holds, 0 regressions.

## Method notes
- Frontend-only entries (AGENT-056, AGENT-081, UI-019, UI-049) have no HTTP surface; verdict
  ci_pinned naming the exact pinned vitest test, cross-checked against a live re-probe of the
  same underlying readiness/validate endpoint the component/store consumes. Never ran vitest
  myself (heavy lane owns the suite).
- R15-CODE-AGENT-034 (MCP workspace tools) verified live end-to-end via a real FastMCP
  in-memory Client over `_build_server()` pointed at my own sidecar (:52356), not source-only.
- R15-RESEARCH-001 verified via in-process `row_relevant`/`gate_news` fed real live `/news`
  data, plus source confirmation that `deep.py` calls both at HEAD. Did not spend the shared
  hosted-lane budget on a full paid DEEP research run (gpt-4o-mini) — the gate mechanism itself
  is what the fix touched and was proven end-to-end against live data through the real
  functions the fix wired in.

COVERAGE: 16/16 ids raw; no raw: none.
