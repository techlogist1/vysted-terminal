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

## Teardown (round 1)
- Stopped only my own sidecar: `kill 85020` (the sleep pid), verified via `ps -p 85020`
  showing no process. Never touched any other owner's port.

## Round 2 (gate round 2, candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`)

- Confirmed `rc1-cand` scratch worktree HEAD == `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`,
  `sidecar/.venv/bin/python3` present.
- `git diff 4097dac4..4c6dfe8c --stat` scoped to this group's files: only
  `src/modules/portfolio/PortfolioPanel.tsx` (+15/-1) and its own test file changed.
  `sidecar/routers/portfolio.py`, `src/modules/notes/**`, `src/components/ConfirmButton.tsx`:
  zero diff. (Two unrelated files also changed -- `src/lib/host-actions.ts` and
  `src/lib/sidecar-client.ts`, both adding an optional `region` param to
  `loadSymbolIntoChart`/`history()` for a chart/research cross-market disambiguation fix,
  D57/R15-DATA-002-adjacent -- out of this group's scope, not portfolio/notes surface.)
- Read the `PortfolioPanel.tsx` diff directly: adds `quoteFetchInFlightRef` (a `useRef(false)`),
  sets it `true` at the start of the quote-fetch effect, `false` in a new `.finally()`, and the
  `setInterval` tick now does `if (quoteFetchInFlightRef.current) return;` before bumping
  `quotesNonce` -- exactly the WatchlistPanel-style overlap guard `rc1-drive-portfolio-notes:1`
  named as the smallest fix shape. The new test in the same diff is literally titled
  `"...(rc1-drive-portfolio-notes:1)"`.
- Booted a fresh own sidecar: `cp -R rc1-seed-data ->
  vysted-iso/rc1-drive-portfolio-notes-r2/data`, then
  `cd rc1-cand/sidecar && VYSTED_OPENBB_MCP_PORT=52153 VYSTED_SEC_EDGAR_MCP_PORT=52154
  sleep 86400 | ./.venv/bin/python3 main.py --host 127.0.0.1 --port 52324 --data-dir <r2 data>`
  detached via `nohup ... &`; sleep-pipe pid 63682 (worker pid 63685). `/health` returned 200
  on the first poll.
- Ran `node_modules/.bin/vitest run src/modules/portfolio/PortfolioPanel.test.tsx
  src/modules/notes --reporter=verbose` in `rc1-cand` (detached via `nohup`, read back after):
  **4 files / 65 tests, all passed**, including
  `"skips a quote-refresh tick while the previous fan-out is still in flight, then refetches
  once it settles (rc1-drive-portfolio-notes:1)"`. Saved full output to
  `surface/portfolio-notes/rc1/round2-vitest-p8-fix-confirmed.log`.
- Live sidecar spot-check against my fresh `:52324`: `GET /portfolio/positions` -> `[]`,
  `PUT`/`DELETE /portfolio/positions` -> `405` -- byte-identical to round 1's finding
  (R15-CODE-PLATFORM-021 still holds; router file has zero diff since round 1).
- Did **not** re-run the full live 100-holding/9-unresolvable-symbol wedge scenario (the one
  that took 4.5+ minutes in round 1): the fix is a synchronous ref-guard on the exact
  `setInterval` call site that produced the round-1 backlog, the fix's own fake-timer test
  exercises that exact guard end-to-end (fetch pending across 3 ticks -> 0 extra calls ->
  fetch resolves -> next tick refetches, call-count asserted), and the sidecar-side code that
  produced the backlog (`api.ts`'s lack of `AbortController`, the provider fallback walk) is
  unchanged -- a live re-wedge would re-prove the same guard logic at ~150x the cost and risk
  the 120s-per-tool-call stall-watchdog rule for zero additional evidentiary value. Code read
  + targeted live-mounted-component test is the correct-weight verification here.
- Updated `surface/portfolio-notes/rc1/COVERAGE.json` (panel-portfolio row:
  `driven` partial -> ok, `quote auto-refresh...` state broken -> ok with round-2 evidence),
  `rc1/drives/portfolio-notes.md` (P8 row, new Round 2 section, deltas list), and
  `rc1/findings/rc1-drive-portfolio-notes.json` (added `status: "fixed"` +
  `fix_evidence` to item 1; nothing deleted, item 2 unchanged as it never described an
  open product defect).

## Teardown (round 2)
- Stopped only my own round-2 sidecar: `kill 63682` (the `sh -c` pipe pid) exited the shell
  but left its `sleep 86400` (63684) and `python3 main.py` (63685) children running detached
  (no process group was set on the `nohup` launch) -- caught this via `lsof -i :52324` still
  showing LISTEN after the first kill, then `kill 63684 63685` directly. Verified fully down:
  `ps -p 63684 63685` empty, `curl :52324/health` connection-refused, `lsof -i :52324` empty.
  Never touched `:52152-54`, the census-round sidecar, or any other owner's port.
