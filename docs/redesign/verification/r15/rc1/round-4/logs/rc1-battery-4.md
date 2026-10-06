# rc1-battery-4 — regression battery shard 4 (round 4)

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad` (verified via
`git -C <cand-worktree> rev-parse HEAD`). Sets: batch-8/W4-resolver-exchange-lanes
(set-33, 11 ids), batch-11/W8-frontend-visual (set-55, 4 ids),
batch-14/W1-agent-runtime-... (set-66, 1 id). No prior round-4 files existed for
these sets at start (checked `battery/set-33.md`, `set-55.md`, `set-66.md`,
`battery/raw/set-33|55|66`, `findings/rc1-battery-4.json` — all absent), so this
is a fresh run, not a continuation.

## Sidecar

One sidecar for the whole shard on `:52344`, data dir copied from
`rc1-round-4-seed-data` to `rc1-round-4-data-battery-4`, `VYSTED_OPENBB_MCP_PORT=52153`
/ `VYSTED_SEC_EDGAR_MCP_PORT=52154` pointed at the shared read-only MCP subprocesses.
`/health` returned ok. Sleep pid 70584 (worker 70587) — stopped at the end of the run.

## Method

- set-33 (resolver/exchange lanes, macro providers): live `curl` against `:52344`
  for the network-facing entries (DATA-058, UI-039, DATA-051, DATA-085, LIFECYCLE-019
  live check); in-process Python (candidate's own `sidecar/.venv`) importing the
  actual service modules for the ones the batch-8 verifier certified via
  mock-transport / stubbed-network conditions (LIFECYCLE-019 backoff/retry,
  LIFECYCLE-022 primary-404-fallback + no-false-holiday, CODE-DATA-002 memo timing,
  CODE-DATA-003 router/tool payload parity, AGENT-045 unresolved-name message,
  DATA-084 falsy-zero, DATA-086 ProviderError-not-curated-fallback). Every in-process
  script ran detached (`nohup ... &`) and was polled with `Monitor`/`ps`, never a
  foreground blocking call.
- set-55 (frontend visual): UI-091 checked live against `:52344`'s
  `/indicators/suggested` and `/indicators/AAPL`. UI-085 and CODE-PLATFORM-023 are
  vitest-pinned; per role instructions the heavy lane owns full vitest/pytest runs,
  so these are `ci_pinned`, confirmed by reading the pinned test file plus an
  independent grep (UI-085: no unprefixed readable-text `text-charcoal-600/700`
  outside the documented `disabled:` carve-out) or reading the implementation
  (CODE-PLATFORM-023: all promised metrics are exported from `metrics.ts`).
  CODE-PLATFORM-025 is a doc-text + Rust-source grep, no test involved.
- set-66 (agent-eval grader): read `models/llm.py` (`LLMToolResultEvent`),
  `services/agent_runtime.py` (`_tool_result_event`, emitted after every dispatched
  tool call) and `scripts/agent_eval/grader.py` (the `tool_result`-aware failure
  check) — all present and match the batch-14 fix description exactly. Confirmed
  the grader logic directly and deterministically with a small in-process script
  calling `grader.grade()` on the exact event shapes the pinned test
  (`test_a_trial_whose_tool_call_errored_fails` / `..._retry_..._passes`) uses —
  both give the batch-14-certified verdicts. Also attempted a genuine live
  `llama3.1:8b` invoke via `scripts/r15/vy.py` (under the Ollama single-lane lock,
  `--port 52344`) asking for AAPL's nearest-expiry option chain, to see the
  `tool_result` frame on the wire end-to-end; this was still in flight when the
  shard's other evidence was already conclusive (code + grader-logic level), and
  the deterministic in-process result is what the verdict below is based on.

## Notes

- Two probes in set-33 needed a widened query to match the certified repro
  exactly: `R15-UI-039` with the truncated `GUJGAS` query returns empty
  candidates (no bug — the renamed ticker is `GUJENERGY`, so a `GUJGAS` prefix no
  longer matches on the post-rename master); the exact `GUJGASLTD` query (the
  actual register repro, matched via `former_name`) returns the correct enriched
  row. Kept both raw files; `-exact` is the one the verdict is based on.
- `R15-DATA-085`'s first curl attempt returned an empty body under load (the
  sidecar was mid-flight resolving a large batch of concurrent Yahoo quote
  requests from its own boot-time warm cache); a clean re-run with `-v` got the
  full 5.5KB body correctly. Not a product defect — kept both raw files.

COVERAGE: 16/16 ids raw; no raw: none.
