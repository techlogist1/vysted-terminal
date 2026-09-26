# rc1 gate, round 3: script changes

Script `rc1-gate.js` (395 lines, line numbers below are the new file), dry run `rc1-gate.dryrun.mjs`, plan `RC1_GATE_PLAN.md` (args, concurrency, ports, evidence paths). Written 26 Sep 2026, 18:40 IST.

## Why the round-2 resume re-keyed half the run

The harness (Claude Code 2.1.280) caches each `agent()` call under `v2:sha256(prevKey \0 prompt \0 canon(opts))`. Here `prevKey` is the key of the previously invoked call (`""` for the first), and `canon` keeps schema/model/effort/isolation/agentType, sorted. Label and phase are not keyed. On a miss it sets a flag that sends every later call live, and a call that failed originally misses as well. The formula reproduces the journal's keys exactly: preflight `bcb744cb…`, then gate8 `bbde3c20…` chained on it.

The prompts did not differ. The prompts for the re-keyed labels (all five lane-serial drives, battery-0, collate, onboarding-stranger) are byte-identical between the original and the resume. For example, battery-0's prompt hashes to `a9081a03bd41` in both runs, and portfolio-notes's to `6f2f355982f6`. The difference was the chain position:

- **Original:** call 10 was `rc1-battery-0`, invoked after `rc1-drive-screener`, key `0776167b`. `rc1-drive-panels-layouts` was invoked later, after `rc1-battery-3`, key `9bfa87c7`.
- **Resume:** the nine cached calls resolved instantly, so the DRIVE limiter pumped `rc1-drive-panels-layouts` at call 10, after screener, key `7df91f37`. That was a miss, and every call from there ran live. battery-0 re-keyed after settings-plugins, onboarding after battery-4, and collate after a new battery-7.

The only prompt text that ever differed is a downstream effect: the fix-r1 triage's `Findings to close`. The original had `["rc1-scenarios:1","rc1-datapack:1","rc1-datapack:2","rc1-drive-research-briefs:2","set28-research-gap","set67-untraced-ratio-escape"]` (9565 bytes). The resume had `[…,"rc1-drive-research-briefs:2","rc1-drive-onboarding-stranger:1"]` (9548 bytes), because the live re-runs produced different findings.

**Root cause:** the GLOBAL/DRIVE/BATT limiters and the cross-lane awaits invoked `agent()` in completion sequence. The harness keys on invocation sequence, so any change in timing (and a resume's instant cache hits are the biggest one) moved a call's chain position.

## Changes

- **(a) Resume-stable invocation.**
  - L36-48: the limiters are gone, and `step(deps, fn)` issues calls in one static sequence. fn runs only after the previous step's fn ran and its own deps settled.
  - L190-202: the fixed issue sequence is heavy, scenarios, index, data pack, then waves of `drive_limit` drives and `batt_limit` shards. Drive i waits for i−DL, and shard k waits for k−BL.
  - L268, L350: writers and vshards use `Promise.all(map(run))`, so they invoke synchronously in array order.
  - Every prompt is a pure function of `args`, earlier agents' results and static indices. No position comes from a race.
- **(b) No evidence deletion, named reasons.**
  - L52 (COMMON): the restart rule covers only this round's files. NEVER DELETE EVIDENCE forbids rm/mv/truncate/empty of any verification or screenshot file the label did not create this round. A role that cannot run still writes its log and findings naming the reason, returns `blocked`, and touches nothing else.
  - L55 (facts): every role except preflight first checks that the candidate worktree's HEAD equals the sha.
- **(c) `args.round`.**
  - L16-19: a missing round, or one that is not an integer ≥ 1, throws.
  - L26-31: `EV = r15/rc1/round-<N>`, `CAND`/`SEED` become `rc1-round-<N>-*`, drives write to `r15/surface/<group>/rc1/round-<N>/`, and shots go to `docs/screenshots/vr15-rc1/round-<N>/`.
  - L104-108: branches become `worktree-agent-rc1-round-<N>-<sha7>-*`. The GUI home (L328) and the pack copy tree (L188) are per round.
  - Collator (L230) and verifier (L354-375) read only `${EV}` and this round's surface and shot dirs. `R15_GATE_RC1.md` is unchanged at its path.
  - L101 and L382-383: the return carries `round` and `evidence_root`.
- **(d) Battery coverage.**
  - L135-139: NB = ⌈fixed/16⌉ comes from preflight's register count, so it is fixed before any agent returns.
  - L165-177: `planShards` packs whole sets, largest first, into the least-loaded shard. It is a pure function of INDEX.json. The indexer no longer assigns shards (L164, and the INDEX schema drops `shard`/`id_shard`).
  - L182: every fixed id ends with a raw file at the sha, or a `NOT RUN: <named reason>` raw file. There is no copying from other rounds, and restarts skip only this round's complete sets.
  - L230: the collator counts `NOT RUN:` as no raw output, with its reason. L207 and L222: the return's `of` counts non-empty shards.
- **(e) Scenarios.** L152: every transcript is produced by this run at the sha, and no file is reused. Every scenario × model cell records `ran` / `lock_timeout` / `upstream_5xx`, and only `ran` is scored. The LOCAL-MODEL LOCK text is unchanged.
- **(f) Data packs.** L188: all 24 names are re-collected from `${SCRATCH}/rc1-round-<N>-pack` into `${EV}/battery/collected/`. The output is one `<slot>_<SYMBOL>.json` per manifest name from this run, or `.error.txt` with the named reason. Never a census or earlier-round file.

## Dry run (`node rc1-gate.dryrun.mjs rc1-gate.js --control <round-2 script>`, exit 0)

```
PASS refuses to run with round=undefined | 0 | "0" | "abc" | 2.5 | true   (6 lines)
PASS labels, prompts and keys byte-identical across 3 completion sequences (53 calls each): no prompt or position depends on call sequence
PASS resume (asc|desc|mix-timed original, instant cached results) replays 53/53 calls   (3 lines)
PASS resume with max_fix_rounds 2 -> 3 (the round-2 change) replays 53/53
PASS every call names model (opus|sonnet) and effort
PASS every prompt is scoped to r15/rc1/round-3 and no unscoped scratch or screenshot path remains
PASS battery: 25 shards cover all 391 fixed ids exactly once (sizes 15-17)
INFO would spawn 53 agents: preflight 1, gate8 1, heavy 1, scenarios 1, battery-index 1, datapack 1, drives 8, battery shards 25, collate 1, per fix round 4 (triage, 1 stub writer, int, recheck), vshards 8, verifier 1
CONTROL round-2 script (desc-timed original): resume replays 9/36; first miss at call 10 rc1-battery-0 (original call 10 was rc1-drive-panels-layouts)
CONTROL round-2 script (asc/mix-timed original): resume replays 36/36
```

The control reproduces round 2's failure. The same script and args replay or not depending only on timing.

## Round-3 launch object

`{sha: '<candidate sha on 004>', round: 3, max_fix_rounds: 2, skip_gui: true, drive_limit: 3, batt_limit: 4, note: '<the round-2 note re-stamped GATE ROUND 3, items (1)-(6) unchanged>'}`

The three-failure and known-limitation rules live in that `note`, not in the script, so it must be re-passed. `batt_limit: 4` keeps 25 shards to about 7 waves, and the harness cap of 6 is the real pacer.

## Not changed, and why

- The rubric text (3c51ac3c, f1a2682d), the Gate 8 proof steps, the "certify the claim" clause, the register criterion, the LOCAL-MODEL LOCK, every model and effort, the spend guard, and the single same-tier `run()` retry.
- Criterion 2's concurrence path stays the literal `r15/rc1/findings/rc1-verifier.json` (round 2's record). The verifier may read that one file outside `${EV}`, and its own round-3 concurrences go under `${EV}/findings/`. Moving the path would be a rubric edit.
- Round-1/2 files are not moved into `round-<N>/`: the new scheme only reads this round's dir, and moving them would rewrite committed evidence.
- No gap-retry pass for dead shards: 16-id shards plus the same-tier retry bound the loss, and the collator and verifier name every missing id.
