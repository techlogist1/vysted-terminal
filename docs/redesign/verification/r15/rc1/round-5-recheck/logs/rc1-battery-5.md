# rc1-battery-5 — regression battery shard 5

Role: REGRESSION BATTERY shard 5 (Sonnet), stage-c batch-4 + batch-28 + batch-11 + batch-18.
Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd (verified via `git rev-parse HEAD` at start).

## Setup

- Candidate worktree: `.../scratchpad/rc1-round-5-recheck-cand` (read-only source).
- Data dir: copied seed → `.../scratchpad/rc1-round-5-recheck-data-battery5`.
- Own sidecar booted from candidate source on port **52345**, sleep pid **66879**,
  `VYSTED_OPENBB_MCP_PORT=52153` / `VYSTED_SEC_EDGAR_MCP_PORT=52154` (shared read-only MCPs).
  `/health` returned ok in <10s.

## Sets worked (one at a time, battery/<file> written before moving on)

1. `battery/set-11.md` — batch-4/W1-agent-runtime (9 ids): AGENT-008, AGENT-009, AGENT-006,
   LEAD-007, LEAD-008, RESEARCH-005, DATA-041, DATA-046, AGENT-011. All **holds** except
   RESEARCH-005 **ci_pinned** (3 tests in test_research_synthesis_timeout.py; live repro needs
   a test-only 3s-forced-timeout monkeypatch the original cert also used, real DEEP/ULTRA is
   168-262s+). AGENT-008 and AGENT-001-style live checks used the Ollama lock; DATA-046 and
   DATA-079 hit live external APIs (World Bank, NSE F&O) from my own booted sidecar.
2. `battery/set-75.md` — batch-28/W1-opus (5 ids): AGENT-001 (critical), AGENT-092, AGENT-094,
   AGENT-095, LEAD-014. All **holds** except AGENT-092 **ci_pinned** (test_run_manager.py,
   the register's own repro is the exact shape of the pinned test's mocked provider).
   AGENT-001 needed 2 live Ollama attempts — attempt 1 hit real provider timeouts
   (environmental, yfinance rate-limiting visible throughout this session's sidecar.log,
   unrelated to the defect); attempt 2 got real numbers through and confirmed correct scaling.
3. `battery/set-54.md` — batch-11/W6-options-chain (1 id): DATA-079 **holds** — this is new
   feature work since the last check (a real option-chain endpoint with exchange OI now exists
   and returns live NIFTY data with 18 expiries), not a narrow bug fix.
4. `battery/set-67.md` — batch-18/unassigned (1 id): LEAD-034 **holds** — the `-SM.NS` symbol-
   mismatch defect is fixed at the exact gate (`correctness_gate._SUFFIX_RE`/`symbols_match`),
   confirmed by direct unit calls. Adjacent, unrelated note (not a regression, not filed): the
   outer `provider_registry.get_fundamentals('INSPIRE')` call still errors for these 3 specific
   thin NSE-Emerge micro-caps, but via a DIFFERENT gate (`fallback_ok` rejecting an all-null
   "unusable shell") — legitimately sparse yfinance data, not a symbol mismatch.

## Ollama lock discipline note

First lock-acquire attempt (AGENT-008/009 shared screener prompt) was botched: my first
`nohup sh -c 'trap ...; <cmd>' &` invocation's trap fired (releasing the lock) without the
underlying `vy.py` process having exited, and a second `mkdir` then succeeded, producing two
concurrent live Ollama calls. Caught it via `ps aux`, killed both (pids 72114/72115/73057/73058),
`rmdir`'d the lock, and re-ran cleanly via the Bash tool's own foreground→auto-background
promotion (which correctly serializes: the lock-holding command and its trailing `rmdir` are
one background job, polled via the task-notification, never overlapping). All later Ollama
calls used that pattern instead. No lock was held past its actual process's lifetime after
this was fixed, and no other-agent Ollama call was interrupted (checked `ps aux` before and
after; the pre-existing `ollama runner` process seen at 7:27PM predates my first attempt and
outlived my cleanup — plausibly another shard's call, never touched).

## Findings

None. All 16 register entries in this shard's 4 sets hold at candidate 949c3c9f (or are
ci_pinned to an existing, correctly-scoped regression test). `findings/rc1-battery-5.json` is `[]`.

## Teardown

Stopped my sidecar by killing sleep pid 66879 only.

COVERAGE: 16/16 ids raw across all 4 sets; no raw: none.
