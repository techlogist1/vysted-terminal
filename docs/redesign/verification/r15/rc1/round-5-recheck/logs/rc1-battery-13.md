# rc1-battery-13 (shard 13) — working log

Candidate 949c3c9fd49d61ecadc9813a8321bcdfd81178bd confirmed via
`git -C .../rc1-round-5-recheck-cand rev-parse HEAD`.

Own sidecar booted from `sidecar/main.py` (candidate source, own `.venv`) on
:52353, data dir copied from the seed snapshot to
`.../scratchpad/rc1-round-5-recheck-data-battery-13`. Sleep pid (kill target)
recorded at `logs/rc1-battery-13-sidecar.pid` (82903). Health confirmed
(`{"status":"ok",...}`).

Sets covered (stage-c batch-4 + batch-6 + batch-25 + batch-29):

- batch-4/W4-market-data-gate → `battery/set-14.md` (8 ids) — all holds.
- batch-6/W4-research-funnel → `battery/set-23.md` (5 ids) — all holds.
- batch-25/W4-sonnet → `battery/set-70.md` (2 ids) — all holds.
- batch-29/W4-sonnet → `battery/set-84.md` (1 id) — holds.

## Method notes

- set-14: mostly direct GET against the own sidecar for `/fundamentals/*`,
  `/quotes`, `/history`; two in-process probes reused/adapted
  `docs/redesign/verification/r15/lifecycle/L2-rot/harness/parser_drift.py`
  (repointed at the candidate's sidecar dir) for R15-LIFECYCLE-004, and a
  fresh temp-cache probe against `bse_provider._bhavcopy_for`/
  `_marker_after_day` for R15-DATA-035 (this touched the real OS cache dir
  `~/Library/Caches/bse-bhavcopy`, not scoped by `VYSTED_DATA_DIR` — cleaned
  up same-day/after-day marker files after each check; left a correct,
  current `2026-09-23.csv` from the final live-download step, which is
  harmless).
- set-23: all in-process, direct calls into `services.research.fast.
  snapshot_structured`, `services.agent_tools.deep_research._run_loop`,
  `services.research.deep._run_researcher`, and `services.research.
  disclosures.gather_floor` — matching batch-6's own certification method
  (real functions, monkeypatched faults / stubbed tool_call+llm_call, no
  vitest/pytest suite). R15-RESEARCH-017's mechanism changed since batch-6
  (the `_single_pass_fallback` cert described no longer exists — both DEEP
  and ULTRA now share one `_loop_failed` honest-failure path per a later
  fix, docstring cites R15-CODE-RESEARCH-003) but the entry's OWN stated
  repro (an exception escaping `_run_loop` uncaught) does not reproduce, so
  verdict holds per gate rule change 1. R15-RESEARCH-016 was ALSO re-run
  live (not just code-traced) via a full `run_deep_brief(depth="ultra")`
  call under the Ollama lock — see below.
- set-70: R15-DATA-116 via direct GET; R15-CODE-AGENT-034 via a live
  `fastmcp.Client("http://127.0.0.1:52353/mcp")` HTTP round trip (not just
  the in-process pinned test) calling the real `list_workspaces`/
  `get_workspace` tools against the sidecar's real saved `__autosave__`
  workspace.
- set-84: `node_modules/.bin/vitest run src/lib/host-actions.test.ts -t
  "R15-LEAD-048"` — a single targeted test file/pattern, not the full
  vitest suite (the heavy lane owns that). 5/5 passed.

## Ollama lock

Acquired via `mkdir /tmp/vysted-r15-ollama.lock` before the live ULTRA
`run_deep_brief` probe for R15-RESEARCH-016. The lock directory was
observed GONE a few seconds after the detached process started (before the
process could have exited/released it itself) — likely removed by another
shard's stale-lock cleanup or a race; noted here as a harness observation,
not a product defect. The ULTRA probe was already in flight at that point
and was left to run to completion rather than interrupted (finished 332.9s,
`ok:true`, `n_sources:0` — inconclusive on source count, see
`battery/raw/set-23/R15-RESEARCH-016.txt`).

Re-acquired the lock a second time (`mkdir` → LOCK ACQUIRED) for a more
targeted follow-up: `iter_research.run_heavy_research(...)` called directly
with a pre-bound `target=AMAL (BSE), bound=True`, bypassing free-text symbol
resolution, to get an unambiguous read on whether filing-floor rows are
recorded as citations. This run did not finish inside the shard's remaining
time budget; it was terminated cleanly (`kill -TERM` on the wrapper +
worker pids), its release trap fired, and the lock directory confirmed gone
immediately after (`mkdir`/`ls` round trip, no dangling lock left for other
shards). Its (nonexistent) output is not counted as evidence for
R15-RESEARCH-016 either way; the entry's "holds" verdict rests on the code
trace of the named guard plus the completed first live run.

COVERAGE: 16/16 ids raw across all 4 sets; no raw: none.
