# rc1-battery-22 — regression battery shard 22 (Sonnet)

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd, worktree confirmed via
`git -C <cand> rev-parse HEAD`. Own sidecar booted from candidate source on
:52362, data dir copied from `rc1-round-5-recheck-seed-data` to
`rc1-round-5-recheck-data-rc1-battery-22`; sleep pid 3769 (sh wrapper) / 3771.
Shared read-only stack (:52152) used only for the two ephemeral
`/agents/{id}/invoke` GET-shaped probes (R15-UI-012); every state-mutating
POST (delegate run start/cancel, backtest run) went to my own :52362 instance.

Sets covered (all 15 ids, no restart from a prior attempt — no
`rc1-battery-22` files existed in this round before this run):

- batch-8/W1-sidecar-lifecycle-transport (set-30): R15-UI-012, R15-UI-014,
  R15-CODE-PLATFORM-011, R15-RESEARCH-032, R15-LIFECYCLE-011,
  R15-LIFECYCLE-010, R15-LIFECYCLE-023 — all holds, via live curl against the
  register's exact repro payloads plus direct reads of the exact evidence
  lines cited in the register/batch-8 VERDICTS.md (source parity, no drift).
- batch-10/W1-runtime-backtest (set-40): R15-AGENT-050, R15-LEAD-018,
  R15-CODE-PLATFORM-029, R15-LIFECYCLE-015, R15-UI-010 — holds (live
  in-process python probes against the candidate's sidecar venv, standalone
  scripts mirroring the pinned tests' own fixtures/harnesses, never pytest
  itself); R15-UI-011 — ci_pinned (BacktestPanel.test.tsx: "swaps Run for Stop
  while a backtest is streaming", "Stop aborts the live stream, idles the run,
  and Retry runs on a fresh controller") — the register's own repro is a live
  UI rail-control-state observation with no curl/python equivalent, and
  batch-10 certified it purely via these two vitest cases; source (the
  AbortController + Stop button wiring) confirms the fix is present but I did
  not run vitest to prove the runtime behaviour myself (role restriction).
- batch-11/W2-runtime-schema (set-50): R15-CODE-AGENT-009 — holds (live AST
  line-span count of invoke_agent/_dispatch_round + grep census of
  test_runtime_phases.py's 9 direct phase tests; pytest itself not run).
- batch-12/W4-research-verdict-parse (set-60): R15-RESEARCH-002 — holds (the
  register's exact python -c command against _parse_verdict for all 3 cited
  UNVERIFIED strings; the register's own note already records this exact
  own-stated-repro holding at gate round 5, and this shard independently
  reconfirms it at candidate 949c3c9f; the broader labelled/bracketed/
  numbered-verdict class claim, filed separately as R15-LEAD-060, is out of
  scope per gate rule change 1).

One notable methodology deviation worth flagging: R15-LEAD-018's register
repro is a live OpenRouter nemotron network call. No free-tier OpenRouter key
was available to this shard within the role's remit (the account lane is
shared across concurrently-running battery shards), so I instead replayed the
register/batch-10-cited captured fixture (tests/fixtures/llm/nemotron_cot.jsonl)
through the real production `ReasoningSplitter` module in-process — a live
code-path exercise on real captured data, not a static source read, but not
the live network call the register's repro literally names. Marked holds on
that basis; flagging the substitution rather than silently treating it as
equivalent.

No regressions found. No new defects found (nothing beyond the register's own
scope was probed). No chain (ci-local/smoke) issues — that lane is out of
this shard's remit. No trading/Gate-8-relevant surfaces touched (no D81
material in any of these 15 ids).

Stopped my own sidecar (sleep pid 3769) at the end of the run.

COVERAGE: 15/15 ids raw; no raw: none.
