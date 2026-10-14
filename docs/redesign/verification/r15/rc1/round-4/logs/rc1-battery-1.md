# rc1-battery-1 — regression battery shard 1, gate round 4

Candidate: 1006c6da694ede5776c3dabbd27b305aeb56b5ad. Own sidecar on :52341, own data dir
`rc1-round-4-data-rc1-battery-1` (copy of `rc1-round-4-seed-data`) for the live-HTTP checks
(set-73, plus the UI-040 GET /runs shape check). For the delegate-run set (set-26) and the
research-tier pure-function set (set-64) I used candidate-venv in-process scripts instead of
the HTTP sidecar — the register's own repro evidence for those entries is written that way
(fake providers monkeypatched at `agent_runtime.get_provider`/`oneshot.get_provider`, never a
real LLM call), and it avoids needless load on the shared Ollama lane for entries that don't
need it.

Sets worked, in order: set-73 (batch-25/W4, 3 ids) -> set-64 (batch-13/W2, 1 id) -> set-26
(batch-7/W2, 12 ids, the largest/riskiest set, done last).

## set-73 (batch-25/W4 — DATA-113, DATA-116, CODE-AGENT-034)

- DATA-113: `GET /earnings/WIT/estimates` now carries `revenue_currency: "INR"` separate from
  `currency: "USD"` (EPS); `EpsEstimateGrid.tsx:71` formats revenue with the new field. Holds.
- DATA-116: all 6 register-repro BSE symbols (AMAL/DAL/NAPEROL/JUMBO/ELCIDIN + fresh TCS) return
  200 with populated shareholding patterns over `/disclosures/shareholding?symbol=`. Holds.
- CODE-AGENT-034: in-process FastMCP `Client` against the candidate's own `mcp_server` —
  `list_workspaces` returns `{'workspaces': [...]}` (bare-list wrap present), `get_workspace`
  returns the full doc, no `is_error`. REST `GET /workspace` 200 vs `/workspaces` 404 (prefix
  correctly stayed `/workspace`). Holds.

## set-64 (batch-13/W2 — RESEARCH-007)

- `domain_tier()` in-process on the register's exact URLs (medium.com/investor-diary, a
  wordpress `/ir/` post) now both rank GENERAL, not PRIMARY; Reuters ranks PRESS above both; a
  genuine `ir.somecompany.com` subdomain still ranks PRIMARY (the fix didn't break real IR
  hosts); `investors.com` (a host that IS its own registrable domain, not a subdomain) ranks
  GENERAL, matching the docstring's stated guard. `rank_sources` puts Reuters first. Holds.

## set-26 (batch-7/W2 — the 12-entry delegate-runs set)

Worked as one continuous fake-provider session (no Ollama lock needed — every entry's original
repro either used a scripted fake provider already, per the register's own evidence text, or is
a pure state-machine/pricing/checkpoint check that doesn't need a real model call). One gotcha
worth logging: my first AGENT-038 attempt used a tool-call-bearing fake provider and got a
false "regression" reading (status=error) — the register's actual repro is a bare
delta+done ONE-SHOT provider with no tool call at all; re-run with the correct provider shape
gave the certified `done`/"completed (step ceiling …)" result. Lesson: matching the EXACT
fake-provider shape the original repro used matters as much as matching the budget config.

All 12 held: CODE-AGENT-010 (terminal-state guards, DB-level `TRANSITIONS` table), AGENT-034
(cleared budget gets the floor, never unbounded), AGENT-037 (breach halts before dispatch, no
2nd provider call), AGENT-038 (final-round completion is `done` not `error`), AGENT-074
(pricing uses the resolved provider's real rate), AGENT-036 (checkpoint prompt/turns never
corrupt across two answer cycles), AGENT-035/LIFECYCLE-013 (resume reuses launch-time
provider/model without re-supply), UI-040 (frontend cancel checks `response.ok`; adopt pulls
live sidecar runs), CODE-AGENT-011 (ask_user pause/answer round-trips), AGENT-039 (delegate
launches now plan-first on a capable provider, parks `planned`, `start_run` executes it),
LIFECYCLE-012 (checkpoint written mid-round; a killed process's `running` row flips to `error`
"interrupted by sidecar restart" on the next process's first DB connection; resumes cleanly).

No regressions, no new defects, nothing needs GUI, nothing blocked on the outside world.

COVERAGE: 16/16 ids raw; no raw: none.
