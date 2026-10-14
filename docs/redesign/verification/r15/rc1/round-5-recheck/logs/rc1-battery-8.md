# rc1-battery-8 (Sonnet) — regression battery shard 8

Candidate: 949c3c9fd49d61ecadc9813a8321bcdfd81178bd (verified via git rev-parse HEAD in the shared worktree at start).

Sidecar: booted from source at `<candidate>/sidecar`, port 52348 (within the 52100-52399 range), data dir
`rc1-round-5-recheck-data-rc1-battery-8` (cp -R from the seed data). Booted 19:37 IST, /health OK <1s. Killed at
end of run (pid 73233 sleep-wrapper, then pid 73235 main.py directly — the sleep-pipe EOF did not cause a prompt
exit, so the python process was killed directly; confirmed /health unreachable afterward).

Sets worked in order (batch-7 set-27, batch-9 set-36, batch-28 set-78), one battery/<file>.md written per set
before starting the next.

## batch-7/W3-unattended-chart-workspace (set-27.md)

- R15-AGENT-023: two attempts. First attempt used the wrong workflow-node config key (`ref` instead of
  `secret_ref`) and the wrong edge port (`in`/`in` instead of `quote`->`value`), confirmed via source read of
  `sidecar/services/workflow_nodes/builtin.py:392-416`; the schedule fired but the node errored
  (`lastStatus: "error"`). Deleted and recreated correctly; a one-off `/workflow/run` validated the fix, then a
  5-min interval schedule was created and left running while other set-27/set-36/set-78 entries were probed.
  Confirmed two unattended fires exactly 5:00 apart (19:50:18, 19:55:18 IST), both ok, webhook URL never
  persisted (0 occurrences in sidecar.log or workflows.db).
- R15-CODE-PLATFORM-018: live 20k-step American binomial via `/workflow/run` while polling `/health`
  concurrently — confirmed sub-7ms health throughout a 9.9s run backed by a spawned ProcessPoolExecutor worker
  at 98% CPU.
- R15-UI-020/023/031/026: permanent pinned tests confirmed present (all four literally named "(R15-UI-0xx)" in
  the test file); NOT executed — this role never runs vitest suites. Verdict ci_pinned, naming the exact test.
- R15-CODE-FRONTEND-019, R15-DATA-090, R15-UI-046: all live-reproduced against the sidecar's workspaces
  directory (chmod 555, truncation, raw listing) plus source confirmation of the frontend legs.

## batch-9/W2-research-search-news (set-36.md)

- R15-LIFECYCLE-018: the ORIGINAL batch-9 certification was itself a source read (no live timed race), so this
  was re-verified the same way — `warm_detect()` at `app.py:144` lifespan startup, and the double-checked-lock
  fix at `searxng_manager.py:533-558` (flag set in `finally` after `refresh()`, under `_detect_lock`).
- R15-DATA-094: live-reproduced exactly (unauthorized status, RSS-only fallback header, 0 key leakage).
- R15-UI-033: no permanent pinned test survives for this one (checked `MarketplacePanel.test.tsx` — only 3
  unrelated `it`s). Re-verified via the live network leg the fix depends on (same unauthorized response as
  DATA-094) plus a full source read of the call chain (probe -> throw -> configure() re-throw before setSecret
  -> panel's `.catch(setValidationError)`).
- R15-CROSS-PLATFORM-002: ran the ONE permanent class-pin test file directly —
  `sidecar/tests/test_tests_encoding.py` (3 tests, including a fresh tmp_path case the fix was not written
  against) — not the full pytest suite. All 3 passed.

## batch-28/W4-sonnet (set-78.md)

- R15-DATA-008: live HCLTECH.NS matches the fresh case exactly; SIFY unchanged (matches what batch-28 itself
  recorded as the expected non-regression); AAPL/WIPRO.NS/DRREDDY.NS normal.
- R15-LEAD-022: all 6 fresh-case symbols (BMW.DE, 005930.KS, NESN.SW, BHP.AX, BRK.B, BF.B) priced correctly live.
- R15-DATA-055: NAVN/MDLN matched the fresh case exactly; SAIL's bare-ticker resolution now hits a different
  (older, established) company than the fresh case recorded — noted as resolver/master-data drift, not a code
  regression (its own per-field dates are correctly populated); DHOOTTRANS's per-field dates confirmed live;
  frontend threshold logic pinned at a named permanent test, not re-executed.

## Findings

None. All 16 ids verified holds or ci_pinned (with the exact test named); zero regressions, zero new defects,
zero chain failures, zero trading-path hits. `findings/rc1-battery-8.json` is `[]`.

## Coverage

16/16 ids have a raw file under `battery/raw/set-{27,36,78}/`; no NOT-RUN placeholders anywhere in this shard's
output.

## Local-model lock

Not needed — every probe in this shard reached the sidecar directly via curl or the candidate's own venv
(pytest on one file); no Ollama/vy.py call was made, so the `/tmp/vysted-r15-ollama.lock` was never touched.
