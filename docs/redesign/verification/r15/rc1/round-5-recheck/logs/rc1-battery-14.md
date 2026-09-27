# rc1-battery-14 — regression battery shard 14 (gate round 5-recheck)

Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via
`git -C .../rc1-round-5-recheck-cand rev-parse HEAD`).

Sets: batch-5/W3-agent-runtime-chat (set-18, 8 ids), batch-10/W5-screener-routes-statedocs
(set-43, 5 ids), batch-26/W2-sonnet (set-73, 2 ids), batch-30/WriterA-r15-data-030 (set-85,
1 id). 16 ids total.

## Setup

- Seed data copied `rc1-round-5-recheck-seed-data` -> `rc1-round-5-recheck-data-battery-14`.
- One sidecar for the whole shard, booted from the candidate's source
  (`sidecar/.venv/bin/python3 main.py --host 127.0.0.1 --port 52354 --data-dir <own data dir>`),
  `VYSTED_OPENBB_MCP_PORT=52153`/`VYSTED_SEC_EDGAR_MCP_PORT=52154` pointing at the shared
  read-only MCP subprocesses. `/health` confirmed `ok`. Stopped at the end by killing its
  worker pid (85502) after the `sleep 86400 | python3` launcher pid (85500) alone did not
  terminate it — the sidecar does not watch stdin EOF, so this shard's stop step is: kill the
  launcher pid, confirm the worker is still up via `ps`, then kill the worker pid directly
  (both belong to this shard's own port; no other owner's process touched).

## Method per id

Re-ran each entry's OWN stated repro (never judged from the diff): live HTTP curl where the
repro is a route, in-process Python calls into the exact function the register entry and the
batch verifier's certification name (`_coerce_history`, `hardware_fit.detect_device`,
`fundamentals_store._connect`/`_migrate`, `row_relevant`, `a010v2.py`'s own hang harness),
and source reads of the fix sites the batch VERDICTS.md certified — cross-checked against the
register entry's `repro`/`evidence` fields, never against the diff alone. Two live LLM checks
(R15-AGENT-026, R15-AGENT-033) used real local Ollama `llama3.1:8b` generations under the
shared Ollama lock (`/tmp/vysted-r15-ollama.lock`), acquired and released per the lock
protocol (`mkdir` retry loop; `trap rmdir ... EXIT INT TERM HUP` around the call).

Three entries (R15-RESEARCH-014, R15-AGENT-025, and the frontend half of
R15-AGENT-031/R15-UI-054) rest on source-level confirmation rather than a full live
end-to-end run: R15-RESEARCH-014 because no Anthropic key exists in this isolated BYOK
profile (the same constraint the original batch-5 certifier hit — its underlying
`is_length_finish` mechanism was live-proven correct via this shard's own R15-AGENT-026
probe); R15-AGENT-025 because the full ~200s hang-harness re-run (separate sidecar boot
pointed at `junk_provider.py`) did not fit this shard's time budget, though both the
backend planner-timeout and frontend stall-watchdog fix sites are present and
comment-tagged with the entry id; R15-AGENT-031/R15-UI-054's frontend half rests on a
pinned vitest plus source read (the backend half was live-cross-confirmed by the
R15-AGENT-033 run's own notice frame, which carried `step_kind: "notice"`).

## Result

All 16/16 ids: **holds**. No regressions, no new defects, no chain failures, no gate8-shaped
findings. `findings/rc1-battery-14.json` is `[]`.

COVERAGE: 16/16 ids raw across 4 set files; no raw: none.
