# Battery shard 17 — set-54 (batch-11/W7-preferences)

Candidate 1006c6da694ede5776c3dabbd27b305aeb56b5ad.

| id | repro run | observed | verdict |
|---|---|---|---|
| R15-UI-087 | node re-run of orderedProviders (pure fn, verbatim) + source-confirmed fallback wiring in ChatSidebar.tsx / settings.ts / errors.py | ordering correct; fallback consumer present and gated on classified pre-output failure | holds |

COVERAGE: 1/1 ids raw; no raw: none. Note: batch-11's own palette/start-layout sub-claims were
vitest-only and not independently re-run here (pytest/vitest suites are out of scope for this
role); the core ordering + fallback-wiring mechanism was independently re-executed.
