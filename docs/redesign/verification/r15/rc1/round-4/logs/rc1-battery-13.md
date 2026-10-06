# rc1-battery-13 — gate round 4

Candidate `1006c6da694ede5776c3dabbd27b305aeb56b5ad`. Sidecar booted from source on
`127.0.0.1:52353`, data dir `rc1-round-4-data-battery-13` (copied from
`rc1-round-4-seed-data`), MCP env pointed at the shared `:52153`/`:52154`. Sleep-wrapper pid
`93959` (stopped at end of run).

Sets owned: batch-2/W5-surfaces-and-math (set-4, 8 ids), batch-3/W3-llm-adapters-and-errors
(set-7, 6 ids), batch-6/W2-delegate-runs-runtime (set-21, 1 id), batch-25/W1 (set-71, 1 id).
16 ids total.

## Method

For each id: read the register entry + the batch's own VERDICTS.md "Per-entry evidence" to
learn how it was originally certified, then re-ran that exact repro against the candidate:

- Pure backend logic (DATA-009, DATA-010, LEAD-014) — in-process Python scripts against the
  candidate's own `sidecar/.venv`, reusing the real classes/functions the register names, not
  a re-implementation.
- Live HTTP endpoints on my own sidecar (DATA-011, DATA-007, UI-008/CODE-AGENT-003,
  RESEARCH-010 error half).
- Real SDK + MockTransport replay (AGENT-004) and literal replay of the ORIGINAL leaked-JSON
  evidence text from the surface drive's own jsonl (AGENT-018).
- Frontend-only fixes with no live sidecar surface (DATA-031, DATA-042, CODE-PLATFORM-053,
  DATA-100, CODE-PLATFORM-013): never ran vitest (heavy lane owns it); instead read the source
  guard AND confirmed the committed pinned test(s) still assert the exact register behaviour,
  verdict `ci_pinned` naming the test(s). CODE-PLATFORM-013's original certification used an
  uncommitted scratch test (`plat013.test.tsx`, per batch-25's own teardown convention, gone by
  design) — 5 DIFFERENT committed tests now cover the same drift class, one of them reproducing
  the register's own fresh case verbatim, so this is `ci_pinned` on stronger, permanent evidence.

## Result

16/16 hold. 0 regressions, 0 new defects. 8 `holds` (live/in-process re-repro), 8 `ci_pinned`
(frontend currency/plugin-flag fixes, cited against committed tests). No `needs_gui`, no
`blocked_env`, no `lock_timeout` (no Ollama call was needed for this shard — RESEARCH-010's
error half was reproduced by calling `run_research_model_brief` directly with a live OpenRouter
401, which is the code path under test regardless of which chat model wraps it, so the Ollama
lock was never required).

Two positive-key controls from batch-3 (real OpenRouter/OpenAI/DeepSeek keys validate true)
were intentionally not re-run — no real key was read or printed in this shard, and the
negative/rejected-key path is the one the register regression class is about.

Yahoo Finance was 429-rate-limiting on my sidecar port from an unrelated background universe
refresh at boot; none of my 16 ids needed a live Yahoo call, so this did not block anything.

Sidecar stopped by killing sleep pid 93959 at end of run.
