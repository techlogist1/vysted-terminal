# R15 rc1 gate: workflow plan

Script: `docs/redesign/verification/r15/tooling/rc1-gate.js`. Run it once the Stage C batches (8, 9) are merged on `004-r4-experience-rebuild`, one workflow at a time.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/rc1-gate.js", args: {sha: "<candidate sha on 004>", max_fix_rounds: 2, skip_gui: false}})
```

Optional args: `scratch` (the scratch root, if this session's scratchpad is gone), `gui_wait_min` (default 60), and `drive_groups` (default: the 8 census owner-drive groups).

## Phases

| # | Phase | Agents (model, effort) | What it does |
| - | ----- | ---------------------- | ------------ |
| 1 | Preflight | 1 Sonnet medium | Resolves the sha and runs a clean `ensure-all-sidecars --force` in the scratch worktree `rc1-cand`. Takes a seed snapshot of the ISO data, restarts the shared stack (:52152-54) from the candidate, and records Ollama, SearXNG, disk, idle time and register counts. A failed build returns `blocked`, and the script stops. |
| 2 | Gate 8 | 1 Opus high | Checks the OpenAPI paths, the catalog and MCP tool lists, `test_no_trading_surface.py`, and grep sweeps over src/, sidecar/, src-tauri/, plugins/ and docs/, with every hit classified. Then runs the tracked portfolio end to end, including a gated agent write on llama3.1:8b. |
| 3 | Regression | Sonnet medium: 1 heavy lane, 1 battery index, 1 data pack, 1 collator. Sonnet high: 8 owner-drives (≤3 at once) and one battery agent per writer set (≤2 at once; about 30 sets from batches 2-7, plus 8/9). Opus high: 1 scenarios agent. | Five lanes run in parallel. A barrier follows, because the fix loop needs every finding. |
| 4 | Fix (≤ `max_fix_rounds`) | Each round, all Opus high: 1 triage, ≤4 writers (isolated worktrees), 1 integrator, 1 recheck | Triage splits the regressions and the critical/high/medium new defects into disjoint writer sets. Writers push `worktree-agent-rc1-fix-r<N>-<name>`. The integrator merges into `worktree-agent-rc1-fix-int` in the scratch `rc1-fix-int` and needs ci-local and smoke green. Recheck re-runs only the failed items. Anything left open is logged and becomes a blocker. |
| 5 | GUI | 1 Sonnet medium presence gate, then 1 Opus high | Runs only if some entry is `needs_gui`, `skip_gui` is false, and idle time is ≥ 1500 s within `gui_wait_min`. The app is a `tauri build --debug` bundle launched with `HOME=` an isolated profile. The idle check runs before every batch. A frontmost surprise stops the batch and discards the capture. |
| 6 | Verify | ⌈sets/8⌉ Opus xhigh sample shards, then 1 Opus xhigh final verifier | The shards try to refute 3 certified entries per writer set. Entries are picked by index, `(7i+3) mod n` and the next two. The final verifier re-proves Gate 8 on its own and reads only raw evidence before forming each verdict. It writes the gate sheet. |

Concurrency: a global limiter holds the workflow to 6 agents whatever the CPU count. Lane caps: drives 3, battery 2, heavy 1, GUI 1. Every `agent()` call names its model and effort. No Haiku, no fast tier. The same COMMON text as the batch script, stall rule included, is prepended to every prompt, followed by the rc1 facts block.

Ports: shared stack :52152-54 (read-only for drives). Own sidecars on:

- :52310 Gate 8
- :52311 scenarios
- :52312 final verifier
- :52313 data pack
- :52320+i drives
- :52330+r triage
- :52335+r recheck
- :52340+i battery sets
- :52600+k shards

`rc1-cand` is read-only except for preflight, the heavy lane, and the GUI agent's debug build in phase 5.

## Evidence (all under `docs/redesign/verification/r15/rc1/`)

| File | Proves |
| ---- | ------ |
| `PREFLIGHT.md` | The candidate built clean. Shows the stack and environment state and the register counts at gate start. |
| `GATE8.md`, `gate8.json`, `gate8/*` | Zero order, broker, kill-switch or audit-order routes, tools or MCP names. Every grep hit is explained. The tracked portfolio round-trips, and an agent write is gated. |
| `REGRESSION.md`, `logs/ci-local.log`, `logs/smoke.log` | `pnpm ci-local` is green from a clean sidecar build at the sha, with per-stage counts. The built binaries boot. |
| `SCENARIOS.md`, `scenarios/*.jsonl` | Read-back-before-claim, skepticism and self-consistency, per model. Model weakness is kept separate from product defects. |
| `OWNER_DRIVE.md`, `drives/<group>.md`, `../surface/<group>/rc1/` | Every census-driven control is re-driven, with census→rc1 deltas. |
| `BATTERY.md`, `battery/INDEX.json`, `battery/set-<i>.md` | Every certified entry's original repro still holds against the fresh build, grouped by writer set. |
| `DATAPACK.md`, `battery/collected/` | The 24 names are re-collected, without overwriting the census baseline. The fields fixes touched are re-diffed, and no census match has regressed. |
| `FINDINGS.json` / `.md` | Every finding from every lane, with its kind and severity. |
| `fix-r<N>/PLAN.md`, `INTEGRATION.md`, `RECHECK.md` | Shows how each regression was fixed and certified again, or why it was not. |
| `GUI_ROUND.md`, `docs/screenshots/vr15-rc1/` | The presence log per batch, a verdict per needs_gui entry, and populated dark-theme proof shots. |
| `verifier/shard-*.md`, `VERDICT.md`, `../R15_GATE_RC1.md` | The adversarial sample, the evidence behind each gate line, and the sheet: PASS/FAIL/DEFERRED per item, blockers, remaining needs_gui ids, and the sha to tag. |

## After the workflow (the lead)

1. Read `R15_GATE_RC1.md`. A FAIL means a fix batch, then the gate runs again. Tag nothing.
2. If fixes landed, audit `origin/worktree-agent-rc1-fix-int` and fast-forward 004 to the verified head (the sheet's sha). If 004 has moved past the candidate, the tagged tree must be the verified sha or the gate runs again.
3. Tag `r15-rc1` at that sha and push the tag. The script never tags, merges to main, pushes main, opens a PR or force-pushes.
4. Update the register: the GUI round's certified ids go from `needs_gui` to `fixed`. Deferred ids stay `needs_gui` and are recorded with the idle rule.
5. Hygiene: prune dead worktree registrations, the `rc1-*` scratch worktrees, and local branches fully merged into 004. Never main, 004, the remote default, registered branches or this run's branches. Nothing on the remote.

## Assumptions

- The script is authored for the harness's 6-agent cap. The `~2,500`-char prompt limit is read as applying to each role text; COMMON and the facts block (about 2.4k each) are prepended on top. The final verifier is longer.
- Owner-drive groups are the 8 from `PROMPT_surface_s2.md`. New critical/high/medium defects found at the gate go through the fix loop. Lows go to rc2 and are logged.
- The brief grants computer-use for `com.vysted.desk`, but the Tauri identifier is `com.vysted.terminal`. If the built app is not already granted, the GUI agent defers rather than requesting access while the operator is away.
- The screenshot folder follows `docs/screenshots/v<tag>/` literally: `vr15-rc1/`.
