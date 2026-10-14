# rc1 gate, round 4: script changes

Script `rc1-gate.js` (442 lines; the line numbers below are the new file unless marked "r3"), dry run `rc1-gate.dryrun.mjs`, plan `RC1_GATE_PLAN.md`. Round 3 was run `wf_3bab62fa-c4d` at candidate `01d6920a`, and it failed on three harness gaps (R15_GATE_RC1.md, Blockers 2-4). This round repairs them. `launch-args/rc1-gate-r3.json` is untouched.

## 1. Battery: only 1 of 25 shards ran

**Root cause.** The shard plan was built from the indexer's structured return, and nothing checked that return until after every lane had finished.

- The journal (row 12) shows the indexer returned `sets` as one placeholder: `{batch: "see INDEX.json", set: "75 sets total (...)", entries: ["full per-set id lists are in INDEX.json/INDEX.md, too large to inline here"]}` with `fixed_total: 392`. It wrote the real 75-set/392-id plan only to `INDEX.json`.
- r3 L196 `const planP = indexP.then(planShards)` planned from that return unchecked. The r3 INDEX schema (L70) accepts any strings.
- `planShards` (r3 L166-177) packed the single "set" into shard 0.
- r3 L201 `([sh]) => (sh[k].sets.length ? shardLane(sh[k], k) : null)` then issued nothing for shards 1-24, with no log line.
- NB was correct: `ceil(392/16) = 25`, from preflight's `status_counts.fixed = 392`. `liveShards` counted non-empty shards, so it read 1.
- The only coverage check (r3 L213) was a log after the barrier.
- Shard 0's prompt (transcript `agent-a19ed89f5da472cd7`) carried the placeholder. That agent read INDEX.json itself and took the first contiguous sets, 27 ids.

**Fix, and the extra safeguards.**

- **Validate the return.**
  - L177: the indexer is told its return IS the shard plan. It must inline every set with its full id list in INDEX.json order, never a placeholder or a pointer.
  - L180-190 `indexProblem`: a valid return has non-empty entries that are all register ids (`RID`, L147), no duplicates, and an id count equal to both `fixed_total` and preflight's fixed count.
- **One redo.** L238-241: after the first drive wave and before shard 0, a static step checks the index.
  - A valid index issues nothing.
  - A rejected one issues one redo, `rc1-battery-index-redo`, which is told why and continues from its INDEX.json. It goes through `once()`, so there is never a third try.
  - The step sits at a fixed position, and whether the redo is issued depends only on the result, never on timing. Cache keys stay chained on a static sequence.
- **Hard assertions.**
  - L193-212 `planShards` throws `BATTERY PLAN INVALID (harness): <why>` in three cases: an invalid index, a plan where some id is not in exactly one shard (placed count, distinct count, and every indexed id present), or any shard above `BATT_MAX = 24` ids. The error names the shards and says "raise args.batt_shards".
  - L245 `await planP`: the throw surfaces as soon as the index settles, before any shard runs. It never waits for the barrier or continues silently.
- **`args.batt_shards`.** L38 (1..64, checked before preflight) overrides NB at L146. The lead passes ⌈fixed/16⌉ from the register at the candidate.
- **Named harness failure for missing raw output.**
  - L273: the collator gets the script's plan inline (shard → set raw dir → ids). It ALWAYS writes `battery/MISSING_RAW.json` (`{"harness_failure": "battery-raw-missing", count, missing[{id, shard, set, reason}]}`, count 0 when none) and the BATTERY.md section `## Missing ids by shard` (reading `none` when nothing is missing).
  - L277-278: the script adds `HARNESS battery-raw-missing: <n> of <total> ...: <ids>` to the blockers. A dead collator is `HARNESS collator-died`.
  - L417: the verifier checks on disk itself. Any fixed id without raw output makes the battery item FAIL with cause harness_environment, listed in the sheet's Blockers under that name.
  - L433: the return carries `harness: {battery_raw_missing, drive_raw_missing, scenarios}`.

## 2. Scenarios: one model, one trial, hosted lane skipped `no_key`

**Root cause.** The agent looked in the isolated seed profile's `dev-keystore.json`, which is keyless by design, and ran its only OpenRouter probe with `--no-key`. The adapter then 400'd ("Missing credentials"), and the agent recorded every hosted cell as skipped (transcript `agent-a13208897e4f00497`).

**Key source.** `scripts/r15/vy.py` reads the provider key in-process from the operator's dev keystore, the file named by vy.py's `KEYSTORE` constant (`_key()`, entries `llm-provider:openai` and `llm-provider:openrouter`). It sends the key per request as `api_key`, so the scratch sidecar stays keyless.

- Round 3's paid OpenAI rows were `rc1-r3-drive-research-briefs` on its own keyless `:52321`: three gpt-4o-mini calls, about $0.011.
- The `rc1-fix-r1-recheck` (:52336) and verifier (:52312) OpenAI rows show `in: 0, out: 0`. Those were the no-key and bad-key humanize probes, not paid calls.
- Both keystore entries resolve (checked as booleans only; no value was printed). The OpenRouter key was not absent in round 3.
- Ledger total `est_usd` is $0.2591 of the $8 stop, and vy.py refuses at $7.50.

**Change** (the scenario role, L160-164, with the `SCEN` schema at L75-76):

- **Two graded lanes.**
  - Local: llama3.1:8b runs each scenario once under the lock, reported as single-trial and never as pass^3.
  - Hosted: each scenario runs as a triple of fresh trials. For self-consistency, the triple is the two fresh asks plus the in-thread ask. Each trial is graded against a pass rule written down before the run, and a scenario passes only at pass^3.
  - There are ≥4 scenarios per property.
- **Hosted provider choice.**
  - Key availability is resolved through vy.py itself, printing booleans only. vy.py's in-process read is the one sanctioned access to the protected app-support dir, and the role forbids `--no-key` and `--bad-key`.
  - The lane uses OpenRouter's default `:free` slug when that key resolves and a probe returns tokens. Otherwise it uses `openai --model gpt-4o-mini`.
  - If neither key resolves, the provider is `none`, lane status is `fail`, and the reason is named. It is never a skip.
  - If OpenRouter leaves more than 2 trials failed on 429/5xx, the remaining triples switch to OpenAI.
- **Spend.** Every hosted call is tagged `--tag rc1-round-4-scenarios`, and the lane's own OpenAI spend stops at $0.90. 36 trials of gpt-4o-mini at about 25k tokens in comes to roughly $0.20-0.30. There is no deep or ultra depth, and a trial not run for budget is `budget_stop`.
- **Files and return.** Each trial writes `${EV}/scenarios/<scenario>-<local|hosted>-t<n>.jsonl`. The return adds `hosted {provider, model, reason}` and `properties[{property, hosted_triples, hosted_complete, hosted_pass3, local_ran, local_pass}]`.
- **Script check** (L257-258): a missing lane, provider `none`, or any property with fewer than 4 complete hosted triples adds `HARNESS scenarios-lane: ...` to the blockers. The verifier (L417) grades at least one hosted triple per property itself.

## 3. Owner drives: onboarding-stranger saved a narrative only

**Root cause.** The r3 drive role (L158) said "Evidence under `${SURF}/${g}/rc1/${RN}/`" but never required raw files. The onboarding-stranger drive returned four `.md` paths and nothing else. The other seven groups returned 3-16 raw `.json`/`.jsonl`/`.txt` files each (checked from the journal returns).

**Change.**

- **Drive role** (L170): RAW OUTPUT IS MANDATORY.
  - Every scored row gets `<nn>-<slug>.txt|json|jsonl` in the group's round dir: the command or request, its exit or HTTP status, and the untrimmed key-scrubbed output. The file is written before the row is scored.
  - A row that could not run still gets a file whose first line is `NOT RUN: <reason>`.
  - A `.md` is never raw output. Each table row cites its raw file, and every raw file goes in `evidence_files`.
- **Script** (L255): any group whose return lists no non-`.md` file under `surface/<g>/rc1/round-<N>/` is flagged.
- **Collator** (L273): lists each group's dir on disk and writes the mandatory OWNER_DRIVE.md section `## Drive raw output`. Each failing group gets a `FAIL drive-raw-missing: <group>` line, and rows citing a missing raw file are listed. It returns `drive_no_raw`.
- **Union and verifier.** L279 merges both lists into `HARNESS drive-raw-missing: <groups>`. The verifier fails the owner-drives item with cause harness_environment by that name.

## Dry run

Command: `node rc1-gate.dryrun.mjs rc1-gate.js --control <round-3 script>`. Exit 0, 32 PASS, 0 FAIL.

The battery checks run against round 3's real `INDEX.json` (392 ids, 75 sets). Excerpt:

```
PASS refuses to run with round=… (6) and batt_shards=0 | 65 | "abc" | 2.5 (4)
PASS labels, prompts and keys byte-identical across 3 completion sequences (55 calls each)
PASS resume (asc|desc|mix-timed original) replays 55/55 calls (3); max_fix_rounds 2 -> 3 replays 55/55
PASS every prompt is scoped to r15/rc1/round-4 …
PASS batt_shards 25: 25 shards cover all 392 fixed ids of the 75-set round-3 index exactly once (sizes 15-16, cap 24)
PASS no batt_shards (NB = ceil(preflight fixed 392 / 16)): 25 shards … exactly once (sizes 15-16)
PASS batt_shards 30 overrides the preflight-derived 25: 30 shards … exactly once (sizes 13-14)
PASS batt_shards 10 throws the named cap error: BATTERY PLAN INVALID (harness): shard 0 carries 40 ids, …
PASS round 3's placeholder index return gets ONE redo, issued at call 10 (rc1-drive-screener > rc1-battery-index-redo > rc1-battery-0) under all 3 completion sequences, keys identical
PASS after the redo: 25 shards cover all 392 … exactly once; resume of the redo path replays 56/56
PASS index placeholder-both / short on the ask and the redo: the gate throws by name and issues no shard
PASS collator gets the full shard plan (392 ids) and must always write MISSING_RAW.json, "## Missing ids by shard" and "## Drive raw output"
PASS baseline: no HARNESS blocker
PASS a narrative-only drive dir is flagged by name: HARNESS drive-raw-missing: onboarding-stranger …
PASS a hosted lane with no key is a named lane failure: HARNESS scenarios-lane: no hosted key: …
PASS scenario role …; drive role makes per-row raw files mandatory
CONTROL <round-3 script> fed round 3's placeholder index return: issued 1 battery shard(s) carrying 0 of 392 fixed ids, and did not stop
```

The control reproduces round 3. Its one shard got the placeholder and zero ids; the real agent then improvised 27.

Syntax: the workflow body (meta stripped) compiles under `new Function(...)` in the dry run's loader, and the `meta` literal evaluates on its own. Plain `node --check rc1-gate.js` rejects the script's top-level `return` by design, because a Workflow script is a function body. The dry run itself passes `node --check`.

Longest prompts at 392 ids: collator 20.1k characters (the inline plan), verifier 24.9k, scenarios 12.3k, battery shard 10.6k.

## Round-4 launch object

```
{sha: '<candidate = HEAD of origin/004 at launch>', round: 4, max_fix_rounds: 2, skip_gui: true, drive_limit: 3, batt_limit: 4, batt_shards: 25, note: '<round-3 note re-stamped GATE ROUND 4>'}
```

- **`batt_shards`.** 25 holds at 392 fixed. Recompute ⌈fixed/16⌉ from `vysted-r15-register.json` at the candidate: 393-400 is still 25, and 401 or more is 26.
- **Count check.** The index must equal preflight's fixed count exactly, or the gate throws.
- **`note`.** Copy the note from `launch-args/rc1-gate-r3.json` and make three edits:
  - "GATE ROUND 3 (…round 2 ended FAIL…)" becomes "GATE ROUND 4 (…round 3 ended FAIL at candidate 01d6920a…)".
  - Item (7) gets what changed since round 3 (batch-27 and this repair).
  - Item (10) reads "round 4 … r15/rc1/round-4/ … the battery covers all fixed ids in args.batt_shards shards".

## Not changed, and why

- The rest of the harness is unchanged: the rubric, Gate 8, the fix loop, the models and efforts, the LOCAL-MODEL LOCK, COMMON and facts, the `run()` single same-tier retry, and the verifier sampling.
- **The throw is deliberate.** An unplannable battery throws instead of degrading, because a gate without its battery cannot pass. Lanes already issued at that point are the harness's to stop.
- **No JSON-schema `pattern`/`minItems` on INDEX entries.** Whether the harness supports those keywords is unverified. The script-side check does the same job with a named error.
