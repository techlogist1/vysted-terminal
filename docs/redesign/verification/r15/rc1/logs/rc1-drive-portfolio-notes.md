# Working log: rc1-drive-portfolio-notes

Role: OWNER-DRIVE 'portfolio-notes'. Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`.

## Setup
- Read `PROMPT_surface_s2.md`, `COMMON.md`, census `EVIDENCE.md` + `COVERAGE.json`, and the register entries matching my 8 census raw findings + adjacent portfolio/notes entries.
- Booted own sidecar per `stage0/ISO_STACK.md` recipe on port 52324 against a copy of `rc1-seed-data`; sleep pid 85020 (parent bash 85018, python 85021), log at `.../scratchpad/rc1-portfolio-notes-sidecar.log`.
- Copied census harness (`harness/portfolio.s2c.test.tsx`, `notes.s2c.test.tsx`, `toolbar.s2c.test.tsx`, `sym100.json`, `vitest.s2c.config.mjs`) into scratch dir `s2c-pn/`, symlinked `node_modules` from the read-only candidate worktree (never wrote into it).

## Fixes applied to the ported harness
- `sed` port 52221 -> 52324 across all three test files (one instance in `notes.s2c.test.tsx` was hardcoded and missed by the first pass; caught on ECONNREFUSED, fixed).
- `sed` aria-label `"Cost basis"` -> `"Avg cost / share"` in `portfolio.s2c.test.tsx` (candidate renamed the field label).
- Rewrote P4/P4b delete assertions for the new `ConfirmButton` arm/confirm double-click gate: P4 now does Edit-then-Delete and double-clicks the same delete control element for both TCS.NS and RELIANCE.NS; P4b re-adds a TCS.NS holding to the "Second" portfolio before its own delete-control assertion since P4 now legitimately consumes the original one.
- Dropped the invalid `--reporter=basic` vitest flag (not a valid reporter name on this vitest version); ran with the default reporter.

## Static verification (code read at fix commits)
Confirmed via `git log --oneline --all | grep -i "<id>"` plus direct file reads:
R15-AGENT-019, R15-UI-005, R15-AGENT-042, R15-DATA-081, R15-UI-024, R15-UI-035,
R15-CODE-FRONTEND-003, R15-CODE-FRONTEND-012, R15-CODE-FRONTEND-014, R15-UI-001,
R15-DATA-042, R15-UI-004, R15-CODE-PLATFORM-021 -- all show consistent fix evidence
in both the diff and the current HEAD.
R15-UI-078, R15-UI-079 -- code read shows the described defect pattern still present
(`src/lib/csv.ts` has no formula-injection guard; the form-path blank-cost-basis
`Number('') -> 0` still saves as a valid finite value).

## Live verification
- `sidecar/tests/test_portfolio.py`: 18/18 passed on candidate.
- Ran the ported vitest harness against my sidecar; P1-P7 and P9 passed; P8 (100-holding
  quote fan-out, 9 of the 100 symbols have no EOD data anywhere) timed out at 240000ms;
  P9 (chained after P8 in file order but logically independent) failed on an empty `<div/>`
  render -- diagnosed as cascading pollution from the still-running P8 fetch storm, not an
  independent defect (P9's own logic, re-verified via a targeted single-test rerun after
  isolating it, passes).
- Notes/toolbar suites: full pass, `notes-replay.json` and `notes-toolbar-replay.json`
  captured N1-N6 and all toolbar buttons with concrete before/after HTML+store snapshots.
- A1/A2 agent-invoke lane (local ollama `llama3.1:8b` free lane via `vy.py`): both runs
  returned prose deltas without emitting a tool call (matches the known "qwen/local-model
  tool-use inconsistency" gotcha from MEMORY.md) -- not treated as load-bearing evidence;
  the same claims (agent write_note append/mode/scope semantics) are instead confirmed via
  the N2 harness replay (a controlled synthetic invocation, not an LLM-driven one) and via
  direct `host-actions.ts` code read.

## New defect investigation (quote auto-refresh backlog)
- P8's 240s timeout prompted investigation: is this the known-slow-100-symbols case from
  census (which passed, just slow, all 200) or something new?
- Direct 20-symbol concurrent curl/urllib probe against my sidecar: all timed out at 60s.
- Single RELIANCE.NS probe against my sidecar: timed out completely. Same query against
  the separate shared `:52152` stack (same candidate code, no seeded backlog): 8ms.
  -> rules out a systemic provider/code bug; this is accumulated per-instance backlog.
- Read `sidecar/services/provider_registry.py` `get_quote`/`_resolve_sync`: confirmed a
  single linear provider fallback walk, no internal retry loop within one call -- rules out
  "retry storm inside one request" as the mechanism.
- Read my sidecar's own log over a 4.5+ minute window (05:45:07-05:50+): an unbroken,
  non-decreasing repeating cycle through the exact same ~9 unresolvable NSE symbols
  (ABAN, ABINFRA, ABMINTLLTD, ACCURACY, ACSTECH, 3IINFOLTD, AARNAV, AARTECH, AARTISURF),
  continuing even after the originating vitest process had fully exited (`ps aux` showed
  no vitest/node process; `lsof -i :52324 -sTCP:ESTABLISHED` showed no established
  connections at 05:50).
- Read `src/modules/portfolio/PortfolioPanel.tsx`: `QUOTE_REFRESH_MS = 5000` `setInterval`
  has no in-flight/overlap guard (line ~255-259); the fetch effect's `cancelled` flag
  (line ~224-248) only gates the state-update callback, never aborts the underlying fetch.
- Read `src/modules/portfolio/api.ts`: grepped for `AbortController`/`signal` -- zero
  matches in the file. Confirms there is no cancellation mechanism at all.
- Left a background Monitor watch polling the quote endpoint for recovery rather than
  blocking on it (per the stall-watchdog rule: no single tool call over 120s). It reported
  `RECOVERED` (relianceQuote http=200 took=0s) after the backlog eventually drained on its
  own, without any restart -- so this is a temporary resource-exhaustion/DoS-shaped bug
  (severity: high), not a permanent hang.
- Filed as `rc1-drive-portfolio-notes:1`, new_defect, high, not tied to any existing
  register id (not a regression of a previously-scored item; the 5s-interval refresh
  mechanism itself appears to be new work since census, part of the R15-UI-036 area).

## Deliverables written
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/COVERAGE.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/{portfolio-replay,notes-replay,notes-toolbar-replay}.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/{A0-context-with-ids,A2-context-notes}.json`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/{A1-delete-h3,A2-write-note}.jsonl`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/sidecar-log-p8-wedged-window.log`
- `docs/redesign/verification/r15/surface/portfolio-notes/rc1/sidecar-log-p8-backlog-tail.log`
- `docs/redesign/verification/r15/rc1/findings/rc1-drive-portfolio-notes.json` (2 findings)
- `docs/redesign/verification/r15/rc1/drives/portfolio-notes.md`

## Teardown
- Stopped only my own sidecar: `kill 85020` (the sleep pid), verified via `ps -p 85020`
  showing no process. Never touched any other owner's port.
