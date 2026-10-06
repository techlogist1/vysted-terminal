# R15 rc1 gate: workflow plan

Script: `docs/redesign/verification/r15/tooling/rc1-gate.js`. Run it once the Stage C batches (8, 9) are merged on `004-r4-experience-rebuild`, one workflow at a time.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/rc1-gate.js", args: {sha: "<candidate sha on 004>", round: 4, max_fix_rounds: 2, skip_gui: true, drive_limit: 3, batt_limit: 4, batt_shards: 25, note: "<the round note>"}})
```

`round` is required: the gate round, an integer ≥ 1. The script throws without it. Every per-round path carries `round-<N>`: evidence under `r15/rc1/round-<N>/`, drive evidence under `r15/surface/<group>/rc1/round-<N>/`, shots under `docs/screenshots/vr15-rc1/round-<N>/`, scratch trees `rc1-round-<N>-*`, branches `worktree-agent-rc1-round-<N>-<sha7>-*`. `R15_GATE_RC1.md` stays at its fixed path. No agent continues from, reuses or cites an earlier round's files, and none deletes evidence its own label did not create this round. `max_fix_rounds` defaults to 2 (0 disables the fix loop); `skip_gui` must be the boolean `true` (or `"true"`) to skip. Optional args: `scratch` (the scratch root, if this session's scratchpad is gone), `gui_wait_min` (default 60), `drive_groups` (default: the 8 census owner-drive groups), and `drive_limit` / `batt_limit` (defaults 3 / 2, integers 1..16): static wave widths, where drive i waits for drive i−drive_limit and battery shard k for shard k−batt_limit. `batt_shards` (integer 1..64, round 4): the battery shard count, the lead's ⌈fixed/16⌉ from the register at the candidate (25 at 392 fixed ids); it overrides the count derived from preflight. All four integer args are checked before preflight, so a bad value spawns nothing. The battery index must hold exactly preflight's fixed count, and no shard may exceed 24 ids; otherwise the script throws `BATTERY PLAN INVALID (harness): …` (see `RC1_GATE_R4_CHANGES.md`).

Return: `{status: 'blocked' | 'PASS' | 'FAIL', gate8, regression (with fix_rounds), scenarios (with hosted, properties), drives, harness {battery_raw_missing, drive_raw_missing, scenarios}, battery {shards, of, sets, entries, by_verdict, missing, regressed, datapack}, gui, verifier, tag_sha, candidate_sha, blockers, deferred_needs_gui}`. A blocked preflight returns the same keys with `status: 'blocked'` and nulls, without spawning anything else.

## Phases

| # | Phase | Agents (model, effort) | What it does |
| - | ----- | ---------------------- | ------------ |
| 1 | Preflight | 1 Sonnet medium | Resolves the sha and runs a clean `ensure-all-sidecars --force` in the scratch worktree `rc1-round-<N>-cand`. Takes a seed snapshot of the ISO data (keyless `dev-keystore.json` with `migrated: true`), restarts the shared stack (:52152-54) from the candidate, and records Ollama, SearXNG, disk, idle time and register counts. A failed build returns `blocked`, and the script returns `status: 'blocked'` with no other agent spawned. |
| 2 | Gate 8 | 1 Opus high | Checks the OpenAPI paths, the catalog and MCP tool lists, `test_no_trading_surface.py`, and grep sweeps over src/, sidecar/, src-tauri/, plugins/ and docs/, with every hit classified. Then runs the tracked portfolio end to end, including a gated agent write on llama3.1:8b. |
| 3 | Regression | Sonnet medium: 1 heavy lane, 1 battery index, 1 data pack, 1 collator. Sonnet high: 8 owner-drives (≤`drive_limit` at once) and ⌈fixed/16⌉ battery shards (≤`batt_limit` at once; 25 at 391 fixed ids). Opus high: 1 scenarios agent. | Five lanes run in parallel. The script packs whole writer sets, largest first, into the least-loaded of the ⌈fixed/16⌉ shards (a pure function of INDEX.json, so a resume re-derives it); the shard count comes from preflight's register count, so it is fixed before any agent returns. Round 4: the index return is validated before planning (register ids, no duplicates, count = fixed_total = preflight's fixed count), with one redo `rc1-battery-index-redo` at a fixed position, and planning asserts that every id is in exactly one shard of ≤24; an unplannable battery throws by name before any shard runs. Each shard boots one sidecar on :52340+k and re-runs the original repro of every certified entry in its sets, returning one result per entry (holds / regressed / ci_pinned / needs_gui / blocked_env). Entries with no result are logged and handed to the verifier. A barrier follows, because the fix loop needs every finding. |
| 4 | Fix (≤ `max_fix_rounds`) | Each round, all Opus high: 1 triage, ≤4 writers (isolated worktrees), 1 integrator, 1 recheck (≤7 per round) | Triage gets only the findings still open and splits the regressions and the critical/high/medium new defects into disjoint writer sets. Writers push `worktree-agent-rc1-round-<N>-<sha7>-fix-r<r>-<name>`. The integrator merges into `worktree-agent-rc1-round-<N>-<sha7>-fix-int` in the scratch `rc1-round-<N>-<sha7>-fix-int` and needs ci-local and smoke green. Branch names carry the candidate sha, and a restarted writer or integrator continues from its own pushed branch, so nothing ever needs a force-push. Recheck re-runs only the items that round worked on. The loop stops early if triage, every writer or the integration fails. Anything left open is logged and becomes a blocker. |
| 5 | GUI | 0-2: 1 Sonnet medium presence gate, then 1 Opus high | Runs only if some entry is `needs_gui` and `skip_gui` is false. The presence gate needs HIDIdleTime ≥ 1500 s within `gui_wait_min`; otherwise the round is deferred, not failed. The GUI agent first calls `list_granted_applications`: the run's grant is for `com.vysted.desk`, and if the built app is not in the list it defers with that reason and never requests access. The app is a `tauri build --debug` bundle launched with `HOME=` an isolated profile whose keystore reads `migrated: true`. The operator's real data dir, caches, WebKit store and keychain are never touched, and the data dir's mtime is checked before launch and after quit. The idle check runs before launch and before every batch. A frontmost surprise or returning operator stops the batch, discards the capture, and defers the rest. |
| 6 | Verify | ⌈sets/8⌉ Opus xhigh sample shards, then 1 Opus xhigh final verifier | The shards try to refute 3 certified entries per writer set. Entries are picked by index, `(7i+3) mod n` and the next two. The final verifier re-proves Gate 8 on its own. It reads only raw evidence files, the register, the running app and the outside world, and never another agent's conclusions (the verdict prose files listed in the script), not even after forming its own verdict. It writes the gate sheet. |

Concurrency (round 3): the script has no completion-driven limiter. The harness keys each `agent()` call on the key of the previously invoked call, so every call is issued through `step()` in one static sequence and paced by the harness cap (CPUs−2, 6 on this Mac), which queues after the key is taken. Lane caps: drives `drive_limit`, battery shards `batt_limit`, heavy 1, GUI 1. See `RC1_GATE_R3_CHANGES.md`. Every `agent()` call names its model (opus or sonnet) and its effort. No Haiku, no fast tier. Total agents: at most 26, plus 7 per fix round, plus ⌈sets/8⌉ sample shards. All 17 prompts start with COMMON, which is the batch script's text plus two additions: the never-tag/merge-to-main/push-main/PR/force-push prohibition, and a stall-rule list that also covers `pnpm install`, `tauri build`, the smoke test and `vy.py` runs. Most prompts add the rc1 facts block. The preflight, heavy lane, battery shards, writers, integrator and GUI agent also get a role-level STALL line.

Routing change 5 (25 Sep 2026): Sonnet is the default model for any task with a clear spec and checkable output (preflight, the heavy lane, scenarios, owner-drives, the battery index and shards, the data pack, collate, GUI presence); Opus at effort high judges refutation, root-causing, risk-adjacent implementation, integration, review and fresh-context certification (Gate 8, fix triage, the fix integrator, recheck, the GUI round, the adversarial sample shards, the final verifier). The fix writers get a per-writer model from the triage's `model` field: Sonnet by default, Opus only for a risk-adjacent or root-cause fix. Fable is not used anywhere in this workflow. The `run()` retry stays a single same-tier retry (label suffix `-retry`, never a third try), now retrying on whichever model the call used rather than hardcoded to Fable. The global limiter is 32 (was 16), per the operator's concurrent-agent ceiling.

Ports: shared stack :52152-54 (read-only for drives). Own sidecars on:

- :52310 Gate 8
- :52311 scenarios
- :52312 final verifier
- :52313 data pack
- :52320+i drives
- :52330+r triage
- :52335+r recheck
- :52340+k battery shards (k < ⌈fixed/16⌉, 25 at 391 fixed ids)
- :52600+k verifier sample shards

`rc1-round-<N>-cand` is read-only except for preflight, the heavy lane, and the GUI agent's debug build in phase 5.

## Round 2 tuning (25 Sep 2026)

Round 1 failed partly on harness causes (`R15_GATE_RC1.md`, `rc1/FINDINGS.md`). Changes, with phases, models, efforts, labels, paths and the fix loop unchanged:

- Lane limits are args: `drive_limit` (default 3) and `batt_limit` (default 2), integers 1..16. The global limiter stays 32.
- Local-model lock (in COMMON): every Ollama call takes `mkdir /tmp/vysted-r15-ollama.lock`, retried every 5 s for up to 15 min (a lock dir older than 20 min is stale), and releases it via an EXIT trap. A call that cannot get the lock is `lock_timeout`, a harness cause. The scenarios agent runs its Ollama scenarios one at a time and records `ran` / `lock_timeout` / `upstream_5xx` per scenario.
- Battery coverage: the indexer reads the register at the candidate (`git show <sha>:…/vysted-r15-register.json`), puts every `fixed` id in exactly one set and every set in one shard, and returns `shard` per set plus the id→shard map. The script uses those shard numbers when they are contiguous from 0 (≤8), else it shards by batch as before. Shards write raw output per id as they go, write their findings file even when partial, and end with a COVERAGE line. The collator lists ids with no raw file per shard and marks the battery `incomplete` (never `pass`) when any exist. The return's `battery` gains `status` and `no_raw`.
- Verifier rubric: (a) only `open` critical/high/medium entries at the sha fail the register criterion; `blocked_tier4`, `needs_gui`, `not_a_defect` and `removed_with_feature` are listed as operator-attended; a `fixed` entry with no certification is `fixed-uncertified` unless the verifier's own probe reproduces it. (b) A sample entry is refuted only when its own repro reproduces its defect at the sha. A nearby different defect is an adjacent finding with its own severity. Docs are refuted only on a factual mismatch with the code. Each refutation records the command, the checkout sha and the output. (c) Every FAIL/DEFERRED gate item names its cause: product defect, harness/environment, or operator-attended.
- `skip_gui: true`: the sheet lists every `needs_gui` id (from the register at the sha) as operator-attended, reason "computer-use grant does not cover the built app".

The stage-c batch script also takes `adj_note` and `planner_note` (default `''`). A non-empty note is appended to the adjudicator or planner prompt as a final `LEAD NOTE FOR THIS BATCH: <text>` paragraph. An empty note appends nothing, so resumed prompts stay byte-identical.

## Evidence (all under `docs/redesign/verification/r15/rc1/round-<N>/`)

| File | Proves |
| ---- | ------ |
| `PREFLIGHT.md` | The candidate built clean. Shows the stack and environment state and the register counts at gate start. |
| `GATE8.md`, `gate8.json`, `gate8/*` | Zero order, broker, kill-switch or audit-order routes, tools or MCP names. Every grep hit is explained. The tracked portfolio round-trips, and an agent write is gated. |
| `REGRESSION.md`, `logs/ci-local.log`, `logs/smoke.log` | `pnpm ci-local` is green from a clean sidecar build at the sha, with per-stage counts. The built binaries boot. |
| `SCENARIOS.md`, `scenarios/<scenario>-<local\|hosted>-t<n>.jsonl` | Read-back-before-claim, skepticism and self-consistency, ≥4 scenarios each. The local lane (llama3.1:8b) is single-trial; the hosted lane (OpenRouter free, else OpenAI gpt-4o-mini via vy.py, $0.90 lane stop) runs graded triples scored pass^3. No hosted key is the named failure `scenarios-lane`. Model weakness is kept separate from product defects. |
| `OWNER_DRIVE.md`, `drives/<group>.md`, `r15/surface/<group>/rc1/round-<N>/` | Every census-driven control is re-driven, with census→rc1 deltas. Each scored row has its own raw file `<nn>-<slug>.txt\|json\|jsonl`; a group dir with no raw file is the named failure `drive-raw-missing` (OWNER_DRIVE.md `## Drive raw output`). |
| `BATTERY.md`, `battery/INDEX.json`, `battery/set-<i>.md`, `battery/raw/set-<i>/<id>.txt` | Every certified entry's original repro still holds against the fresh build. There is one file per writer set (i = its index in INDEX.json), written by its batch's shard, plus the raw repro output per entry. `battery/MISSING_RAW.json` and BATTERY.md `## Missing ids by shard` are always written; any id without raw output is the named failure `battery-raw-missing`. |
| `DATAPACK.md`, `battery/collected/` | The 24 names are re-collected, without overwriting the census baseline. The fields fixes touched are re-diffed, and no census match has regressed. |
| `FINDINGS.json` / `.md` | Every finding from every lane, with its kind and severity. |
| `fix-r<N>/PLAN.md`, `INTEGRATION.md`, `RECHECK.md`, `ci-local.log`, `smoke.log` | Shows how each regression was fixed and certified again, or why it was not. |
| `gui/presence.log`, `GUI_ROUND.md`, `docs/screenshots/vr15-rc1/round-<N>/` | The raw presence readings from the gate and before each batch, a verdict per needs_gui entry (or the deferral reason: presence, grant, or `skip_gui`), and populated dark-theme proof shots. |
| `verifier/shard-*.md`, `VERDICT.md`, `docs/redesign/verification/R15_GATE_RC1.md` (fixed path) | The adversarial sample, the evidence behind each gate line, and the sheet: PASS/FAIL/DEFERRED per item, blockers, remaining needs_gui ids, and the sha to tag. |

## After the workflow (the lead)

1. Read `R15_GATE_RC1.md`. A FAIL means a fix batch, then the gate runs again. Tag nothing.
2. If fixes landed, audit `origin/worktree-agent-rc1-round-<N>-<sha7>-fix-int` and fast-forward 004 to the verified head (the sheet's sha). If 004 has moved past the candidate, the tagged tree must be the verified sha or the gate runs again.
3. Tag `r15-rc1` at that sha and push the tag. The script never tags, merges to main, pushes main, opens a PR or force-pushes.
4. Update the register: the GUI round's certified ids go from `needs_gui` to `fixed`. Deferred ids stay `needs_gui` and are recorded with the idle rule.
5. Hygiene: prune dead worktree registrations, the `rc1-*` scratch worktrees, and local branches fully merged into 004. Never main, 004, the remote default, registered branches or this run's branches. Nothing on the remote.

## Assumptions

- The script is authored for the harness's 6-agent cap (enforced by the harness since round 3). The `~2,500`-char prompt limit is read as applying to each role text; COMMON and the facts block (about 2.4k each) are prepended on top. The final verifier is longer.
- Owner-drive groups are the 8 from `PROMPT_surface_s2.md`. New critical/high/medium defects found at the gate go through the fix loop. Lows go to rc2 and are logged.
- The run's computer-use grant was recorded for `com.vysted.desk`, but `src-tauri/tauri.conf.json` says `com.vysted.terminal`. The GUI agent checks `list_granted_applications` before building. If the built app is not granted, it defers with that reason and never requests access while the operator is away.
- The screenshot folder follows `docs/screenshots/v<tag>/` literally: `vr15-rc1/`.
