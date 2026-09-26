# rc1-battery-7 working log

Role: regression battery shard 7 (Sonnet), stage-c batch-9 + batch-18 + unplanned. This is
a **second, distinct** run of the `rc1-battery-7` label: an earlier session's log (below,
kept for history) covered a *different* scope — batch-9 + batch-10 (sets 33-45) against an
older candidate `4097dac4`. This run's task assignment is batch-9 W1-W5 + batch-18 W1/W2 +
unplanned-1, against the current gate-round-2 candidate `4c6dfe8c2d939ce3557e977a3ddcf802931ac2a2`.

## Task entry-list discrepancy (logged, not filed as a finding)

The task's per-file entry lists for **all five batch-9 sets** did not match any real batch-9
writer set:

- `set-35.md` (batch-9/W1-agent-runtime): task gave `AGENT-046, AGENT-091, AGENT-094,
  AGENT-096, AGENT-098`. `AGENT-091` is real but register-status `open` (never certified,
  so out of scope for a regression check); `AGENT-094/096/098` do not exist in the register
  at all.
- `set-36..39.md` (W2-W5): task gave sequential-looking ids (`RESEARCH-074/076/078`,
  `DATA-116..126`, `DATA-128..140`, `UI-092..104`) that don't belong to batch-9 in
  `battery/INDEX.json`, batch-9's own `PLAN.md`, or the register at all.
- By contrast `set-69`/`set-70`/`set-71` (batch-18 W1, W2, unplanned-1) entries
  (`LEAD-033`, `LEAD-034`, `CODE-DATA-023`) matched the authoritative `INDEX.json` exactly.

This reads as a harness task-computation error (a garbled/pattern-generated id list), not a
product issue — no finding filed. Per instructions ("never speculate about code you have
not opened", "the register is the source of truth"), all five batch-9 sets were worked from
`battery/INDEX.json` + batch-9's own `PLAN.md`/`VERDICTS.md` roster instead of the task's
copied list. Every id actually re-verified is named in each set's `.md` table below.

Also note: `battery/INDEX.json`'s own shard grouping (shard 5 = batch-9+batch-16+batch-6;
shard 7 = batch-2+batch-18; batch-10 = shard 0) does not match this role's shard-7 grouping
(batch-9+batch-18+unplanned) either — a second, independent sharding-plan drift, most
likely from `INDEX.json` being regenerated/rebalanced after this role's assignment was cut.
Flagging both drifts for the lead; neither affected the actual verification work, which
re-ran against the authoritative register regardless of which shard/file number carried it.

## Rig

- Own sidecar booted from `rc1-cand/sidecar` (source, candidate `4c6dfe8c`) on
  `127.0.0.1:52347`, data dir `rc1-data-battery-7` (pre-existing copy of `rc1-seed-data`
  from an earlier attempt at this run — reused, not recopied). MCP env vars point at the
  shared `:52153`/`:52154` stack (confirmed live before boot).
- Sleep-pid wrapper: **11497** (`sh -c` wrapper around `sleep 86400 | ./.venv/bin/python3
  main.py --port 52347 ...`), sidecar log at `<scratchpad>/battery7-sidecar.log`. Stopped at
  end of shard via `kill 11497`.
- Models: `llama3.1:8b` via Ollama through `scripts/r15/vy.py` and direct `curl` to
  `/agents/copilot/invoke` (for the history-injection repro `_coerce_history` needs, which
  `vy.py invoke` has no flag for). Both live-model calls held `/tmp/vysted-r15-ollama.lock`
  for their duration and released it in a `trap ... EXIT` on the detached process. No
  OpenRouter/OpenAI spend needed (`CODE-AGENT-005`'s repro is a deliberately-invalid key,
  so it never leaves the auth-check step).

## Method

Per role instructions: for each certified entry, re-ran the batch's own certification
mechanism (from that batch's `VERDICTS.md` "Per-entry evidence") live against the fresh
candidate — curl/in-process-python where the cert was a live sidecar route or an in-process
probe; grep-confirmed source-fix-presence + (for a genuinely committed guard) a single
targeted `pytest`/test-file-presence check where the cert was frontend-vitest-only or a
scratch (never-committed) test with no permanent pin. Never ran a full vitest/pytest suite.

One live `vy.py`/ollama run ("Research NVDA briefly.") covered three W1 entries in one shot
(AGENT-046's minted tool-call id, CODE-AGENT-008's decoded `structured` payload shape,
RESEARCH-027's 6s-timeboxed-leg timing) — same technique the batch-9 verifier itself used.

## Sets completed (8/8)

set-35 (batch-9/W1), set-36 (W2), set-37 (W3), set-38 (W4), set-39 (W5), set-69 (batch-18/
W1), set-70 (batch-18/W2), set-71 (unplanned-1). All in `battery/set-*.md`, raw output in
`battery/raw/set-*/`.

## Corrections made in-pass (not findings)

- `R15-DATA-065`: first probe parsed the wrong JSON level (`bar.freshness` instead of the
  series-level `freshness` field) and briefly looked like a regression (`None` instead of
  `"eod"`); re-checked the actual response shape (`{symbol, timeframe, bars, provider,
  freshness, reason, partial, coverage_start}`) and found the top-level field correctly set
  to `"eod"`. Corrected before judging — see `set-38.md`.
- `R15-CROSS-PLATFORM-002`: an initial `sed` range cut off the fix line; the actual
  `fixture.read_text(encoding="utf-8")` call (line 467) was one line past the checked
  range. Re-grepped the full function and confirmed the fix is present.

## No findings

No regression, new defect, chain failure, gate-8 issue, or environment outage proven by a
direct probe was found in this shard's 8 sets (all 32 entries: **holds**).
`findings/rc1-battery-7.json` is `[]`.

COVERAGE: 32/32 ids raw; no raw: none.

---

## Prior run's log (different scope: batch-9+batch-10, candidate `4097dac4` — superseded)

Role: regression battery shard 7 (Sonnet), stage-c batch-9 + batch-10, 13 writer sets
(set-33..set-45). Candidate `4097dac423bd6d6fb49245e7ee9e0ab2bc64f18a`.

### Rig

- Own sidecar booted from `rc1-cand/sidecar` (source) on `127.0.0.1:52347`, data dir
  `rc1-data-battery-7` (copy of `rc1-seed-data`). MCP env vars point at the shared
  `:52153`/`:52154` stack.
- sleep-pid wrapper: 20557 (bash -c wrapper around `sleep 86400 | ./.venv/bin/python3
  main.py --port 52347 ...`), sidecar log at `<scratchpad>/battery7-sidecar.log`.
- Models: `llama3.1:8b` via Ollama through `scripts/r15/vy.py`. No OpenRouter/OpenAI spend
  needed this shard.

### Sets completed (13/13)

set-33, set-34, set-35, set-36, set-37 (batch-9); set-38, set-39, set-40, set-41, set-42,
set-43, set-44, set-45 (batch-10). batch-9's W3/W4/W5 content (old set-35/36/37) was reused
as the *substance* for this run's set-37/38/39 (same entries, same mechanisms), each
re-verified fresh against candidate `4c6dfe8c` rather than copied verbatim. batch-10's
content (old set-38/39) is out of this run's scope (batch-10 is not in this run's
assignment) and was left in place under its raw dirs, superseded by whichever shard now
owns batch-10.
