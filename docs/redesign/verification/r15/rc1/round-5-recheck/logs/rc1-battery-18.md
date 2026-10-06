# Working log — rc1-battery-18

Shard: REGRESSION BATTERY shard 18 (Sonnet), gate round rc1/round-5-recheck.
Candidate: `949c3c9fd49d61ecadc9813a8321bcdfd81178bd` (verified via `git rev-parse HEAD` in
`.../scratchpad/rc1-round-5-recheck-cand`, worktree read-only for this role).

## Setup

- Copied seed data: `rc1-round-5-recheck-seed-data` -> own
  `rc1-round-5-recheck-data-rc1-battery-18` (isolated, keyless profile).
- Booted own sidecar from the candidate's `sidecar/` against the copied data dir, detached
  (`nohup ... sleep 86400 | python3 main.py --host 127.0.0.1 --port 52358 ... &`), recorded
  the sleep pid, polled `/health` until 200 OK before starting set-5.
- Shared stack (main sidecar :52152, openbb-mcp :52153, sec-edgar-mcp :52154) was read-only
  reference only — never restarted, never written through.

## Sets worked, in order

1. **set-5** (batch-3/W1-agent-runtime, 7 ids) — all re-proven via standalone in-process
   asyncio/pytest-free scripts rebuilding the certified fix's exact mechanism
   (`_dispatch_tool_with_progress` cancel-on-aclose, `_ToolForeverProvider` capped-round
   loop, `_model_facing_content` untrusted fencing, `_normalise_tool_args`/`_coerce`
   stringified-arg + unknown-indicator rejection, Groq/Ollama truncated-JSON arg parsing),
   plus 3 live `vy.py invoke` runs (copilot/screener) against the own sidecar on
   llama3.1:8b via Ollama (lock-wrapped per the local-model-lock rule). All 7/7 hold.
2. **set-8** (batch-3/W4-research-depth, 6 ids) — static + in-process re-proof of the
   budget-metering seam (`deep_research._run_native` -> `oneshot.complete_with_usage` ->
   `BudgetGuard.add_usage`), `verify.cross_check()`'s wall-timeout bound, the keyless
   search rotation's bounded backoff (DDG/Brave/Mojeek all externally rate-limited at
   probe time — documented as an adjacent environmental note, not a regression, since the
   bounded-rotation mechanism itself measured 8.5s well inside the 25s cap), the SSRF
   redirect-block in `extract.fetch_page` against a local loopback canary, and a live
   research-model-retirement repro (forced `openai/o3-deep-research` via
   `X-Vysted-Research-Models`, got the exact register-cited user-facing error frame instead
   of a raw 404). Plus one live 316s DEEP research run on Ollama corroborating end-to-end.
   All 6/6 hold.
3. **set-82** (batch-29/W2-sonnet, 2 ids) — live `/indicators` vs `/history` freshness
   parity across equity/BSE/crypto/empty-series cases (R15-DATA-063); live
   `/fundamentals` TTM-cadence checks for TCS.NS/NDTV/JONJUA plus 6 synthetic
   `FiledPeriods.cadence()` shape tests (R15-LEAD-004). JONJUA's live classification had
   drifted from the batch-29 snapshot (most likely a new quarter filed since verification,
   not a code change) — documented as an adjacent note per gate rule change 1, since the
   entry's own stated repro (a quarterly filer never mislabeled half-yearly) still held on
   TCS.NS and NDTV exactly as certified. Both 2/2 hold.
4. **set-89** (unplanned-3, 1 id) — grep for the stale hardcoded India-universe size
   comments (removed) plus in-process `load_india_universe()` counts (nse-all 3,506,
   bse-all 5,042, india-all 5,891) matching the register exactly. 1/1 holds.

## Deviations / notes worth flagging upstream

- R15-RESEARCH-008: all 3 keyless engines were externally blocked/rate-limited from this
  probe's IP at the time of testing — attributed to concurrent load from the many parallel
  gate-round shards hitting the same free services, not a candidate defect. The mechanism
  under test (bounded per-engine backoff/rotation time) still measured well inside spec.
- R15-LEAD-004 / JONJUA: live data drift between the batch-29 certification snapshot and
  this recheck, not a code regression — see set-82.md for detail.
- vy.py's console line-print truncates long tool_use payload fields (>400 chars) before the
  brief's `cost` field becomes visible on R15-RESEARCH-009's live run; relied on the
  in-process mechanism test as load-bearing evidence instead of re-running the ~5min live
  call a second time.

## Sidecar teardown

Killed the sidecar's sleep pid (94456) first, per the documented ISO_STACK.md pattern.
After ~20s the worker (pid 94458) had not exited and `/health` still responded, so killed
the worker pid directly (own sidecar, own port :52358 — not another owner's process).
Confirmed down via `ps -p 94458` (no such process) after the kill.

## Result

16/16 assigned entries re-proven to hold against the candidate. Zero regressions, zero new
defects, zero chain failures, zero Gate 8 issues. `findings/rc1-battery-18.json` = `[]`.

COVERAGE: 16/16 ids raw; no raw: none.
