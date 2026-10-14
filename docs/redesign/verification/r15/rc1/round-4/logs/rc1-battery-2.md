# rc1-battery-2 — gate round 4, regression battery shard 2

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`, worktree
`/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand`
(verified via `git rev-parse HEAD` before starting).

Sidecar: own copy of the seed data at `rc1-round-4-data-rc1-battery-2`, booted on
`:52342` (`VYSTED_OPENBB_MCP_PORT=52153`, `VYSTED_SEC_EDGAR_MCP_PORT=52154` against
the shared read-only stack), sleep pid 61543, stopped at the end of the shard
(confirmed `/health` connection refused afterward).

Sets worked in order: batch-7/W4-research-funnel (set-28, 12 ids) → batch-10/W8-plugins-dock
(set-47, 2 ids) → batch-12/…sec-filing-lookup (set-63, 2 ids).

## set-28 (batch-7)

9 of 12 ids are sidecar/python and were re-run as direct in-process calls against the
candidate's fixed code (`services/search/extract.py`, `base.py`, `keyless.py`,
`services/research/relevance.py`, `services/research/iter.py`) via
`scratchpad/probe_set28.py` — all 9 hold; raw per-id output under
`battery/raw/set-28/`. The remaining 3 (R15-UI-038, R15-UI-092, R15-RESEARCH-026) are
frontend TS/TSX logic with no live/curl-able repro and no in-process JS runtime in the
candidate worktree besides vitest (checked `node_modules/.bin` — no `tsx`/`ts-node`);
running vitest is the heavy lane's job per this role's rules, so these are `ci_pinned`
naming their exact tests, after confirming via grep that the tests exist at the cited
lines.

## set-47 (batch-10)

Both ids (R15-CODE-PLATFORM-012, R15-AGENT-057) are frontend-only (plugin manager
panel / plugin runtime / plugin-agents fetch) and were certified in batch-10 only via
vitest. Same constraint as above (no vitest in this shard) → `ci_pinned`, after a
source-level grep confirming the fix shape (`handleToggle` now routes through
`useMarketplaceStore`; `plugin-agents.ts` now checks `response.ok` and PUTs on 409) is
present in the candidate.

## set-63 (batch-12)

R15-LEAD-010: live `curl` against my own sidecar's `/sec/filings/{accession}` route,
which reaches the real SEC EDGAR MCP on the shared stack (`:52154`) — the exact AAPL
10-K accession from the register 404-repro now returns 200 with the right form_type
and dates. Holds.

R15-RELEASE-007: `package.json`'s `lint` script now chains the audit
(`eslint . && node scripts/audit-design-tokens.mjs`), and running the audit script
directly against the candidate exits 0 clean on 373 files. The negative injection case
was skipped — it needs an edit inside the read-only candidate worktree, which this role
may not do. Holds.

## Deviations / things skipped and why

- No vitest run anywhere in this shard (5 ids: UI-038, UI-092, RESEARCH-026,
  CODE-PLATFORM-012, AGENT-057) — explicit rule for this role ("never run vitest or
  pytest suites... an entry certified only through a pinned test → ci_pinned").
- RELEASE-007's negative case and LEAD-010's second (MSFT) case were not re-run — the
  positive case for each already reproduces the register's exact named repro and is
  sufficient to confirm the fix holds; no edit was made to the read-only candidate
  worktree.

COVERAGE: 16/16 ids raw; no raw: none.
