# R15 lows waves: workflow plan

Script: `docs/redesign/verification/r15/tooling/lows-waves.js`. It fixes the open **low** entries of `docs/redesign/verification/vysted-r15-register.json` (207 at batch 11) under the operator's pacing rule. The lows are split once into three partitions, P1, P2 and P3, and no file is owned by more than one of them. The three write runs then go at once, with up to 16 writers each. Integration stays serial on the heavy lane, one partition at a time, and the lead sequences it. The writer, integrator, reviewer and verifier prompts are the Stage C batch script's (`stage-c-batch.js`), with its COMMON text, stall rule and schemas copied verbatim. The `once`/`run` retry helper is rc1-gate's.

## Modes

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/lows-waves.js", args: {mode: "partition", sha: "<004 head incl. the batch-11 merge>", max_writers: 16, exclude_ids: []}})
Workflow({scriptPath: "…/lows-waves.js", args: {mode: "write", partition: "P1", sha: "<004 head at the r15-rc1 tag>", max_writers: 16}})   # and P2, P3 at the same time
Workflow({scriptPath: "…/lows-waves.js", args: {mode: "integrate", partition: "P1", sha: "<current origin/004 head>"}})
```

Add `dry_run: true` to any of these for a check that costs nothing. It logs the agents it would spawn (label, model, effort, branch, ports), returns `{dry_run: true, would_spawn}`, and **spawns no agent**. A workflow script cannot read files, so a dry run can show the per-set detail only when you pass that data in `args.data`: `partitions.P<n>` of `PARTITION.json` for `write`, or `WRITERS.json` for `integrate`. Without it, the dry run logs the fixed skeleton. For example: `python3 -c 'import json;print(json.dumps(json.load(open("docs/redesign/verification/r15/stage-c/lows/PARTITION.json"))["partitions"]["P1"]))'`.

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `mode` | required | `partition`, `write` or `integrate`. The script throws on anything else. |
| `partition` | required for write and integrate | `P1`, `P2` or `P3`. |
| `sha` | required unless `dry_run` | partition: the batch-11 merge on 004, which becomes `base_sha`. write: the commit every writer branch is cut from. integrate: the current `origin/004` head, where the int branch is cut. |
| `max_writers` | 16 | The number of writer sets per partition. It is clamped to 16, and sets beyond it are logged, not spawned. |
| `exclude_ids` | `[]` | partition: lows to leave out, for example ones a running batch owns. |
| `data` | none | write: `partitions.P<n>` of `PARTITION.json`, which skips the loader agent. dry_run: the data described above. |
| `salvage` | none | `{"<agent label>": "<note>"}`. The note is appended as `RESUME SALVAGE` to that one agent's prompt only. |
| `scratch` | this session's scratchpad | The scratch root, as in rc1-gate. |

## Agents per mode

Every call names its model and effort (routing change 5). The `run()` wrapper throws unless the model is `opus` or `sonnet` and the effort is set. There is no third model tier and no fast tier. A call that dies or starves gets **one same-tier retry** (label `<label>-retry`), never a third try.

| Mode | Label | Model / effort | Job |
| ---- | ----- | -------------- | --- |
| partition | `lows-adjudicate` | Sonnet / high | Applies `stage-c/batch-11/VERDICTS.json` to the register `.json` and `.md` the way the batch adjudicator does: certified → `fixed` (closure_evidence `<sha7> <subject>`), needs_gui → `needs_gui` with the GUI check, not_certified and refused → stays open with the reason, concur_not_defect → `not_a_defect`. It is idempotent (`already_applied`). It commits the two paths on 004 with `commit --only` and never pushes. It refuses (`blocked`) if the main worktree is not on 004. If the verdicts file is `missing`, the partition still runs, because batch 11 carried no lows. |
| partition | `lows-partition` | Opus / high | Reads the open lows (minus `exclude_ids`), `lows-triage/LOWS_TRIAGE.json` and `.md`, and the code at `sha`. It writes `lows/PARTITION.json` and `.md`, then audits them with a python check and returns `unassigned` and `overlaps`, both logged. |
| write | `lows-P<n>-load` | Sonnet / medium | Read-only. Returns `partitions.P<n>` verbatim. It is skipped when `args.data` is passed. |
| write | `lows-P<n>-write-W<k>` (≤16) | per set: Sonnet by default, Opus for root-causing or risk-adjacent sets / high, worktree | Uses the batch writer prompt. Branch `worktree-agent-lows-P<n>-W<k>-<slug>`, cut from `sha`. One commit and one push per entry. |
| write | `lows-P<n>-collate` | Sonnet / medium | Serialises the writers' returns into `lows/P<n>/WRITERS.json` and checks each head with `git ls-remote`. A dead writer's outcomes are rebuilt from its jsonl and its origin branch. |
| integrate | `lows-P<n>-integrate` | Opus / high | Uses the batch integrator prompt, working in `<scratch>/lows-P<n>-int` on `worktree-agent-lows-P<n>-int`. |
| integrate | `lows-P<n>-review` | Opus / high | Uses the batch reviewer prompt. It is given the integrator's report and also checks that each writer stayed inside its set's files. |
| integrate | `lows-P<n>-verify` (then `-verify-retry`) | Opus / high | Uses the batch verifier prompt, booted from the int worktree on the partition's own ports. |

Peak agents: partition 2 (4 with retries). Write: 1 + ≤16 + 1 per run, and three runs at once. The harness caps each workflow at min(16, CPUs - 2) concurrent agents. Integrate: 3 (6 with retries).

## Lead sequencing

1. **During the rc1 gate** (lane-free, no build): run `partition` once. Read `PARTITION.md`, and fix any logged `overlaps` or `unassigned` ids before going on. Commit `lows/PARTITION.*` together with the evidence. The adjudicator has already committed the register.
2. **The moment `r15-rc1` is tagged:** launch `write` for P1, P2 and P3 in the same turn, all at the rc1 sha.
3. **When P1's write returns and no other integration is running:** run `integrate` P1 at the current `origin/004` head. Read `VERDICTS.md`, audit `origin/worktree-agent-lows-P1-int`, and merge it into 004. Then flip the register and ledger: certified → `fixed` at the merge sha, needs_gui → `needs_gui`, concur → `not_a_defect`, and not_certified stays open. Remove `<scratch>/lows-P1-int`.
4. Then integrate P2 at the new 004 head, the same way, then P3. Never run two integrations at once.
5. Afterwards, add `blocked_tier4` and `deferred` from `PARTITION.json` to `DECISIONS_FOR_OPERATOR.md` and the run-state, as the operator's decisions require.

## Lane rules

- **Writers:** focused tests only, and never the full chain, `pnpm install`, a sidecar or `tauri` build, the GUI, or a sidecar boot. Writers never touch `:52152-54`, `:52229` or `:523xx`. They symlink the main worktree's `node_modules` and `sidecar/.venv` read-only, as the lows pre-triage did, and stage explicit paths only.
- **Heavy lane:** only the integrator builds or runs `pnpm ci-local` and the smoke test, one partition at a time.
- **Verifier ports:** P1 `:52320`, P2 `:52330`, P3 `:52340`, each with its MCP sidecars on +1 and +2. The rc1 gate used `:52320-52347` for its drives, triage and battery, so integrate only after the gate has finished. The verifier stops its own three sidecars (their sleep pids) before returning.
- **Never-owned files:** `CHANGELOG.md`, `docs/redesign/DECISIONS*.md`, the register, the run-state and every Tier-1 file are never owned by a writer. The integrator writes the CHANGELOG section and the `D-LP<n>-N` DECISIONS rows. A fix that needs a Tier-1 file goes to `blocked_tier4`.
- **Results files:** every worker writes its results to its own file as it goes (see Outputs).
- **Git:** nothing tags, merges to main, pushes main or 004, opens a PR or force-pushes.

## Failure handling

- **A dead run:** relaunch with the same script and args plus `resumeFromRunId`. Finished agents replay from the cache.
- **A dead writer:** it gets one same-tier retry inside the run. On any restart, a writer whose `origin/<branch>` exists fetches it, reads its log and diff against `sha`, and continues after the last pushed commit. It never starts over. A writer that dies twice is logged, and the collator rebuilds its outcomes from the branch and its jsonl.
- **A dead integrator:** it reuses `<scratch>/lows-P<n>-int` and continues from `origin/worktree-agent-lows-P<n>-int`. A dead verifier's retry stops the sidecars its first attempt left on the partition's ports (checked by command line) and continues from `VERDICTS.json`.
- **Salvage notes:** pass `salvage: {"lows-P2-integrate": "…"}` with the resume. The changed prompt runs live, and so does every agent after it in spawn order. Writers after it simply find their branch complete and re-report.
- **Integration not pushed:** review and verify are skipped and logged. Fix the cause, then resume.

## Outputs (under `docs/redesign/verification/r15/stage-c/lows/`; nothing is committed except the register)

| File | Written by | Holds |
| ---- | ---------- | ----- |
| `PARTITION.json` / `.md` | partitioner | `{base_sha, max_writers, exclude_ids, triage_sha, partitions: {P1..P3: {totals, sets: [{name, slug, model, entries, files, brief, merge_order_hint}], verify_only, proposed_not_defect}}, blocked_tier4, deferred}`, plus the readable plan and the mirror notes |
| `P<n>/writers/W<k>.jsonl` | each writer | one line `{id, outcome, commit, test, note}` per entry, appended after its push |
| `P<n>/WRITERS.json` | collator | sets with branch, returned and origin heads, `head_verified`, per-entry outcomes, `dropped_sets` and counts: the integrator's merge list |
| `P<n>/INTEGRATION.md` | integrator | branches merged, conflicts, chain stages with counts, and reverts |
| `P<n>/REVIEW.md` | reviewer | per-entry review notes |
| `P<n>/VERDICTS.json` / `.md` | verifier | `{certified, needs_gui, not_certified[{id, reason}], concur_not_defect, refused_not_defect, merge_target, fixes_applied}` and the evidence per entry |

Returns: partition `{adj, part}`; write `{writers[{name, model, branch, head, pushed, outcomes, summary}], dropped_sets, collate}`; integrate `{integ, review, verify}`.
