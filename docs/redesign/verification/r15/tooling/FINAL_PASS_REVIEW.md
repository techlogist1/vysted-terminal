# R15 final pass: fresh review of final-pass.js

Reviewed at 07:14 IST. The author commit is `66ce4231`. Targets were checked at the authoring head
`6bc6d378cbbf9cfbefd8d155e027c2dc80214331`, which is an ancestor of the author commit. Scope: `final-pass.js`, `FINAL_PASS_PLAN.md`,
`launch-args/final-pass.json`.

**Verdict: launch_ready after the patches below.** No blocking item is left.

## Checks

| Check | Result | How |
| --- | --- | --- |
| Parses | pass | The meta block was stripped and the body wrapped in `new Function('args','agent','parallel','pipeline','phase','log','budget','workflow','return (async()=>{'+body+'})()')` under node 24. A `dry_run` with sha `abcdef1` returns 33 scenario ids and 20 spawn rows. |
| Scenario targets exist at 6bc6d378 | pass | Every file path the catalogue, the surface list and the adversary read-list name was checked with `git cat-file -e`. The only paths missing at the authoring head are `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py` and `src-tauri/src/kill_switch.rs`, and the script already says those were removed under D81. Every route named exists in `sidecar/routers/*.py`. So does every symbol named, checked by `git grep`: the region and origin middlewares, `ALLOWED_ORIGINS`, `_auto_publish_event`, `normalize_depth`, the gate functions, `classify_intent`, `_NO_TOOL_CUE`, `_judge_clause`, the proposed-change kinds, `enqueue`/`accept`/`reject`, `parseHostAction`/`describeIntent`/`applyIntent` with the `unknown` case, `FORBIDDEN_TOOL_SUBSTRINGS`, `KNOWN_TOOL_IDS`, `BudgetGuard`, `deserializeWorkspace`, `downloadCsv`, `fitLayoutTemplate`, `resetToDefaultLayout`, `setDefaultProviderId`, `deriveMetrics` and `BriefBody`. `AUTO_APPLIED_KINDS` is `panel, chart, watchlist`. `sidecar/agents/` holds 13 agent JSONs. The `vy.py` flags `--provider {openrouter,openai,deepseek,ollama}`, `--autonomy`, `--options`, `--no-key`, `--bad-key` and `--out` exist. `r13-bedrock` resolves to `6a40f835`, and `docs/SAFETY_ARCHITECTURE.md` exists at that tag. DECISIONS sections 2.1, 2.2, 3.1-3.5, 4.1, 4.9-4.12, 5.1-5.3, 5.6 and 5.9-5.10 exist. `GET /system/deepresearch/probe` is not routed, as the plan says. `docs/SAFETY_ARCHITECTURE.md` lines 42-44 say every kind auto-applies under AUTO, which matches docs item (h). |
| Register facts | pass after patch 1 | At 6bc6d378 there are 652 entries, with 11 `needs_gui` ids that match `NEEDS_GUI_AT_AUTHORING` exactly. R15-LEAD-030/035/037/038 are `blocked_tier4`. There are 0 open c/h/m entries and 205 open lows. The statuses in use are the six the script lists. |
| Rubric | pass | R4 (signed-off class), R5 (needs_gui, with the 11 named), R6 (gate 3), R7 (three failures) and R9 (run-ending) are all present. `RUN_ENDING_RULE` is quoted byte-identically in the plan, checked by `md.includes('> '+rule+'\n')`. |
| Routing | pass | `call()` refuses any model other than opus/sonnet/fable and any effort other than `high`, and allows fable only in the Sweep phase. `FABLE = limiter(2)` covers retries too. `MECH = limiter(4)` means the sweep peaks at 6. No call uses a fast tier or an effort above high. |
| Forbidden reads | pass | `R15_BRIEF` and `r15/local/` appear only in COMMON's FORBIDDEN READS line, and every prompt carries COMMON. |
| Gate 8 re-proof vs rc1 GATE8.md | pass | G8-1 is GATE8 (a)-(d): routes, tools, the one pytest file, and the classified grep. The portfolio round trip in re-proof step 3 is GATE8 (e): the jsdom harness with only `downloadCsv` replaced and P&L recomputed from raw `/quotes`. G8-3 relies on `accept` returning `"failed"` and re-pending with a `detail` (`src/store/proposed-changes.ts:133-171`). G8-4 relies on `audit_orders` being a banned token in `test_no_trading_surface.py:135`. |
| Args contract | pass | `KNOWN` holds the 12 keys and unknown keys throw. `launch-args/final-pass.json` still has the `RC3_SHA` placeholder, which fails the sha regex until the lead fills it in, as FINAL_PASS_PLAN.md says. |
| Banned word and phrase | pass | Built in the shell and grepped with `-i`: 0 hits in all three files and in this review. |

The author left one point unverified: whether the jsdom harness sends an Origin header. It is now
resolved. `_OriginGuardMiddleware` (`sidecar/app.py`, below `ALLOWED_ORIGINS` at :292) refuses only
a request that carries an Origin not on the list, and lets through a request with no Origin. The
jsdom url `http://localhost:5173` is on the list, so the harness passes either way.

## Patches applied (commit by path)

1. **Wrong register fact.** COMMON told every role "there is no 'source'", and plan R8 said the same.
   At 6bc6d378, 26 entries carry `source` and 14 `removed_with_feature` entries carry
   `closure_reason`. The text now names both as optional older fields that new entries do not carry.
   Before the patch, a triage or re-proof agent reading the register would have hit a contradiction
   with its prompt.
2. **NAMED_LISTS.md was unreachable for the adversaries.** RS-1 and RS-3 point the adversary at
   "NAMED_LISTS.md" for their register entries. The file actually lives at
   `docs/redesign/verification/r15/NAMED_LISTS.md`, and the adversary read-list said "Nothing else
   there". The path is now qualified, and the file is added to the adversary's may-read list.
3. **Triage was skipped when a lane died.** Triage was skipped whenever the lanes returned no
   findings and the register had no open c/h/m. A lane that returned null but left a partial
   `findings/*.json` (which the triage prompt says to include) was therefore never triaged. The
   skip now also requires `missing` to be empty.
4. **R7 miscount.** Every id in a writer set went to the verifier, including `could_not` items and
   the items of a dead writer. Their inevitable `not_certified` then added to the R7 failure count
   without any fix having been tried, so an entry could stop early. Now only ids a writer reports
   `fixed` go to the verifier, and `not_certified` rows for ids the verifier was not given are
   dropped before counting.

Patches 3 and 4 were checked with a no-spawn stub run. A dead drive lane with no findings still
reaches triage. An entry with 2 prior failures and a `fixed` outcome stops at 3. A `could_not`
entry with 2 prior failures stays at 2 and stays open. After the patches the syntax check still
passes, `dry_run` still returns 33 scenarios, and prettier `--check` is clean on the plan and the
json.

## Non-blocking notes

- A round whose writers all return `could_not` still spawns a verifier, with an empty list. This is
  harmless.
- The resume cache keys on prompt bytes. These patches change prompts, but nothing has run yet.
- No `r15-rc*` tag exists in this checkout yet, so preflight step (1) blocks until the lead tags
  rc3. That is intended.
