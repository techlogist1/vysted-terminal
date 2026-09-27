# rc1-battery-18 (Sonnet) — gate round 5

Candidate `9bc600ece2ce6343a6aa48f130d7620b1466bb98` (verified via `git rev-parse HEAD`
against the scratch worktree). Seed data copied to
`rc1-round-5-data-battery-18`; own sidecar booted from `rc1-round-5-cand/sidecar` on
`127.0.0.1:52358` (sleep pid 63634, worker pid 63637), `/health` confirmed ok before any
probe. Both pids killed at the end (the sleep-pipe teardown didn't propagate to the
worker on macOS, so the worker was killed directly as a second step).

Sets worked: batch-3/W1-agent-runtime (7 ids), batch-10/W1-runtime-backtest (7 ids),
batch-12/W1-resolver (1 id), batch-30/WA-R15-DATA-030 (1 id) — 16 ids total, all HOLD,
zero findings.

No prior round-5 files existed for this label at start (checked
`battery/{set-5,set-39,set-55,set-84}.md`, `battery/raw/{set-5,set-39,set-55,set-84}/`,
`findings/rc1-battery-18.json`, `logs/rc1-battery-18.md` — all absent), so this was a
fresh run, not a continuation.

Method per id: read the register entry (repro/evidence) and the certifying batch's
VERDICTS.md "per-entry evidence" line, then re-ran the SAME repro against the candidate —
in-process python calls against the candidate's own venv for sidecar-side mechanisms
(`_dispatch_tool_with_progress`, `_normalise_tool_args`, `_model_facing_content`, the groq/
ollama adapters, the backtest engine, `relevance.row_relevant`), a single targeted
`pytest <file>.py` (never the suite) where the batch verifier's own proof WAS the
committed pinning test, and live `curl`/`vy.py` against the own sidecar for HTTP-surface
and live-model mechanisms (indicator validation, `.BO` provider routing, backtest 422s,
the nemotron reasoning-split live check). Two ids (UI-010, UI-011) have a genuine
frontend-only leg (vitest) that this role does not re-run per instructions — the frontend
mechanism itself was confirmed by reading the current source (AbortController wiring,
schema min/max, `costBasis` null handling) and the pinned test file's presence at the
candidate sha is cited as `ci_pinned`.

Notable checks:
- AGENT-002: reproduced the exact "tool finished = False / False" sequence (cancel a
  pending `__anext__` at 0.05s then `aclose()` on a 0.4s tool) — the task is genuinely
  cancelled, not left running.
- AGENT-003: ran `test_b3_runtime_capped_round.py` directly (not the suite) — both cases
  pass.
- AGENT-021: confirmed all 4 untrusted-text tool families (web_search/news/
  corporate_announcements/research) fence through `wrap_untrusted`, and statically
  confirmed `data-write`/`settings` are absent from `AUTO_APPLIED_KINDS` (watchlist
  staying auto-applied is the documented SC-025 design, not a regression).
- AGENT-050/LIFECYCLE-015/CODE-PLATFORM-029/030: ran the exact pinned pytest files; all
  green including the specific parametrized/named tests the batches cite.
- LEAD-018: did a real live OpenRouter free-lane run (`nvidia/nemotron-3-super-120b-a12b:
  free`, no spend — free tier) in addition to the fixture test; 238 thinking events stayed
  separate from 463 delta events, zero leak-phrase hits across the whole transcript.
- LEAD-050: ran the committed parametrized test (includes the literal GE repro) plus two
  fresh cases (CF Industries, MP Materials) not written against the fix — both correctly
  stayed relevant, matching batch-30's own "fresh case" methodology.
- DATA-115: live `.BO`/`.NS` routing on own sidecar matches batch-12's cert almost bar-
  for-bar (bar counts differ by one trading day, expected given the later run date).

COVERAGE: 16/16 ids raw; no raw: none.
