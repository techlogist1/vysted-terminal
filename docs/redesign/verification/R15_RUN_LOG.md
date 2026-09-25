<!-- backfilled 24 Sep 2026 from journals + run-state; numbers traceable per row -->

# R15 LAUNCH — run log (telemetry)

56 workflow runs tabulated (26 as of the first backfill below, plus 30 more from this backfill:
28 completed/killed runs since the batch-10 row plus the 2 still in flight at write time). The
first 26: the 23 under this session's
`…/3e7ae14d-d48a-4882-8a75-f7608754c23f/subagents/workflows/` (23-Sep/24-Sep) plus 3 from the
prior session's `…/5df12ac0-.../subagents/workflows/` (19 Sep) whose run ids appear in the loop
log. Duration = journal file birth-time → last-write mtime (`stat -f %SB/%Sm`), cross-checked
against every run-state duration that states one — all matched to the stated minute (batch 6's
712.8 min file-derived duration matches the stated "11.9 h" exactly). Agent/model counts = one
`{"type":"result"}` line per completed agent in that run's `journal.jsonl`; model strings are
bucketed fable/opus/sonnet/other. Tokens are **not** a journal field (no journal in this run
carries a token count) — every token figure below is copied from the matching
`vysted-r15-run-state.md` loop-log line and cited as such; where no loop-log line states tokens
for a run, it is marked not recorded.

From this backfill on (rows added below the batch-10 row), tokens, agent counts, model mix and
duration come from each run's own `…/workflows/wf_<id>.json` file (`totalTokens`,
`workflowProgress`'s per-agent `model`/`tokens`/`durationMs`/`state`, `startTime`/`durationMs`),
cross-checked against that run's `journal.jsonl` and against the matching
`vysted-r15-run-state.md` IN-FLIGHT LEDGER line where one exists.

## Waves

| Run id | Stage / batch | Purpose | Launched (IST) | Duration | Agents (landed) | Model mix | Tokens | Outcome | Source |
|---|---|---|---|---|---|---|---|---|---|
| wf_6871fdb3-621 | Stage 0 | truth scouts (env/drift/keys/law/surface/subsystem/battery) + pushguard + rig | 19 Sep 06:20 | 2h08m | 8/11 | sonnet 4, opus 3, haiku 1 | not recorded | 8/11 landed pre-wall; pushguard + rig salvaged later | journal(5df12ac0) + run-state L1,L4 |
| wf_734dffa1-5d4 | Stage 1 | intent-extract (blueprint/pdd-readme/spec/deferred) + world research/compare pipeline | 19 Sep 06:23 | 2h41m | 7 | sonnet 4, opus 3 | not recorded | partial landing pre-wall; remainder relaunched session 2 | journal(5df12ac0) + run-state L2,L6 |
| wf_4073e516-82c | Stage 1 | battery curator + 24 outside-truth packs | 19 Sep 06:27 | 3h30m | 2 (curator only) | opus 2 | not recorded | heavy retry/fail churn on individual packs; most relaunched later | journal(5df12ac0) + run-state L3,L6 |
| wf_aa843beb-8ad | Stage A | worktree/registration salvage scout (RECONCILE_MANIFEST) | 23 Sep 03:50 | 7.8min | 1 | opus 1 | not recorded | facts folded into header | journal + run-state L9/L10 |
| wf_351041f4-938 | Stage A | license writer+reviewer, iso-stack rebuild + Ollama local-lane proof | 23 Sep 04:01 | 17.8min | 3 | sonnet 1, opus 1, ollama 1 | not recorded | license commit 0c63d465; iso stack up on :52152-54 | journal + run-state L10/L11 |
| wf_e5b785bd-002 | Stage A | num_ctx fix writer+verifier, refute-planner | 23 Sep 04:22 | 34.6min | 3 | sonnet 2, opus 1 | not recorded | num_ctx fix d328089; Gate 1 holds | journal + run-state L12, commit 38ded25b |
| wf_338a3672-c14 | Stage B (refute-W1) | 6 subsystem refuters | 23 Sep 04:58 | 7.8min | 6 | opus 6 | 797k | 89 findings: 0 refuted, 38 admitted, 48 corrected, 3 removed_with_feature | journal + run-state L12/L13 |
| wf_f9150967-7cf | Stage B (refute-chain W2-W6) | 29 subsystem/intent refuters | 23 Sep 05:07 | 21min | 29 | opus 29 | 3.37M | 404 verdicts: 183 admitted, 201 corrected, 13 refuted, 7 removed | journal + run-state L14 |
| wf_6a0f9c02-a2e | Stage B items 1-3 | code S2A/S2B critique+refute, data 24/24 packs+diffs | 23 Sep 05:30 | 1h38m | 75 | sonnet 31, opus 44 | 11.56M | closed, 0 failures; commit f763a44b | journal + run-state L15 |
| wf_e5222ca0-412 | Stage B items 4-6 | surface/lifecycle/intent/world/ideation waves | 23 Sep 07:11 | 5h14m | 77/78 | sonnet 20, opus 54, other 3 | not recorded | closed; commit 44497c4c; L6 soak mis-flagged as a stall | journal + run-state L16 |
| wf_94189615-7df | Gate 2 (1st) | l6-finisher, completeness-checker, 13 cluster merges, register build, verify | 23 Sep 12:39 | 50min | 21 | sonnet 4, opus 17 | 3.14M | BLOCKED — intent-census gap missed (counted stale ledgers) | journal + run-state L17, commit 38919fd1 |
| wf_a8d56de8-9b4 | Gate 2 (intent re-close) | 12-chunk extract/verify/refute + delta merges + register rebuild | 23 Sep 13:30 | 46.7min | 35 | sonnet 15, opus 20 | not recorded | BLOCKED (narrower) — spec-135 ledger only 16/45 rows | journal + run-state L18, commit 56b77917 |
| wf_079d13fa-9ac | Gate 2 (final close) | row-count loop, spec-135 completion, delta-2 merges, rebuild, re-verify | 23 Sep 14:19 | 43.1min | 10 | sonnet 6, opus 4 | not recorded | **GATE 2 HOLDS** | journal + run-state L19, commit 99e2ae38 |
| wf_9f29ee60-ba0 | Stage C batch 1 (trading removal) | plan, sidecar/frontend/docs writers, integrate, review, verify | 23 Sep 15:05 | 84.3min | 7 | opus 6, sonnet 1 | 1.74M | merged `a122dbf6`; Gate 8 rewritten-proof pass (0 broker/order/kill/audit hits) | journal + run-state L20 |
| wf_17fd6179-d65 | Stage C batch template | first batch-2 adjudicate launch | 23 Sep 16:32 | instantaneous | 0 (1 started) | — | n/a | aborted; superseded immediately by wf_48478ec5-daf | journal |
| wf_48478ec5-daf | Stage C batch 2 | adjudicate, plan, 5 writers, integrate, review, verify | 23 Sep 16:34 | 132.5min | 10 | sonnet 2, opus 8 | 3.2M | merged `806a90ca`; 37/40 certified, 3 not certified | journal + run-state L22 |
| wf_aaf73f27-1c5 | Stage C batch 3 | same shape | 23 Sep 18:49 | 136.8min | 10 | sonnet 1, opus 9 | 2.9M | merged `c81d879b`; 38/40 certified, 2 not certified | journal + run-state L23 |
| wf_f37de2ba-9d1 | Stage C batch 4 | same shape | 23 Sep 21:08 | 172min | 10 | sonnet 2, opus 8 | 2.6M | merged `dcbe7bae`; 45/52 certified, 2 needs_gui, 3 not certified | journal + run-state L24 |
| wf_17b6cbe4-389 | Stage C batch 5 | same shape (+ an off-journal Opus regression fixer, 14min, no run id) | 24 Sep 00:02 | 165.1min | 10 | sonnet 1, opus 9 | 2.5M | merged `1574ed8e`; 48/58 certified, 2 needs_gui; LEAD-010 regression fixed post-hoc `7ae5117` | journal + run-state L25 |
| wf_94ccf2b8-e97 | Stage C batch 6 — **FAILED** | writers, integrate, verify | 24 Sep 03:04 | 712.8min (11.9h) | 4 (of ~10 phases) | sonnet 1, opus 3 | 6.4M | harness-stall watchdog killed writers/integrator/verifier repeatedly; 21/22 delivered entries recovered by hand, merged `5e147317` | journal + run-state L26 |
| wf_5c799024-a29 | Stage C batch 7 | same shape | 24 Sep 15:36 | 136.6min | 10 | sonnet 1, opus 9 | 3.4M | merged `e81c9e7c`; 50/55 certified, 1 needs_gui, 4 not certified | journal + run-state L27 |
| wf_b829ac35-3a5 | Stage C batch 8 | same shape | 24 Sep 17:54 | 131.4min | 10 | sonnet 1, opus 9 | 3.1M | merged `68bb7aa4`; 39/47 certified, 1 needs_gui, 7 not certified | journal + run-state L28 |
| wf_36d043fa-61f | Stage C batch 9 | same shape | 24 Sep 20:09 | 154.7min | 10 | sonnet 4, opus 6 | 1.8M | merged `6b702305`; 29/45 certified, 2 needs_gui, 14 not certified | journal + run-state L29 |
| wf_c6207d00-908 | Lows pre-triage | 14-shard critique + critic + collate | 24 Sep 22:10 | 23min | 17 | sonnet 2, fable 14, opus 1 | 2.2M | 199/205 still reproduce, 5 already-fixed, collated `84418994` | journal + run-state ledger line 23 |
| wf_31f149cf-57d | Stage D docs wave | facts, 5 drafts + Fable critics, secrets/licence scans | 24 Sep 22:48 | 29.3min | 20 | sonnet 14, fable 5, other 1 | 2.8M | 5 drafts revised, committed `5f1ddaae`; drafts not promoted | journal + run-state ledger line 25 |
| wf_54334d97-0e6 | Stage C batch 10 | adjudicate, plan, 8 writers, integrate, review, verify | 24 Sep 22:47 | ~2h56m wall over 3 dispatches (stopped 00:25 for routing change 4, resumed 00:30, re-dispatched 01:23 after 2 Fable verify weekly-limit rejections; final dispatch alone 18.7min/239k tokens) | 13 in final dispatch (adjudicate, plan, W1-W8, integrate, review, verify) + 2 earlier Fable verify attempts failed (weekly limit) | opus 5, sonnet 5 (dispatch 1) → all-Fable resume/re-dispatch | not recorded overall (final dispatch's verify agent alone: 239k) | MERGED `f407107f` on origin/004 (79 commits over 6b91b8fa); 50 certified, UI-084 needs_gui, AGENT-083 concur_not_defect, 4 not certified with fresh cases | run file + run-state ledger line 30 |
| wf_96670fc2-911 | Stage C batch 11 — aborted first launch | `r15-stage-c-batch` dispatched with `tag:'batch-11'`, aborted | 25 Sep 01:44 | 2.0min (killed: `Error: Workflow aborted`) | 1 (fable, in progress when killed) | fable 1 | not recorded (absent) | Aborted before any agent landed; batch-11 relaunched cleanly 4 min later as `wf_a5e688ba-d35` — **not in the ledger by this id** (the ledger's "first resume... stopped within a minute" text at line 30 describes a different, unlogged batch-10 event; this run file's own `args` show `tag:'batch-11'`, not batch-10) | run file only |
| wf_a5e688ba-d35 | Stage C batch 11 | adjudicate, plan, 6 writers, integrate, review, verify | 25 Sep 01:48 | 186.6min | 13 | opus 10, sonnet 3 | 2.39M | merged `4097dac4` on origin/004; 18 certified, LEAD-028 + RELEASE-007 not certified (no regression), UI-047/UI-059/DATA-080 concurred out of scope | run file + run-state ledger line 34 |
| wf_be24fed9-05a | lows-waves harness check | `lows-waves.js` `{mode:'partition', dry_run:true, max_writers:16}` dry run | 25 Sep 03:57 | ~0min (10ms) | 0 (0 spawned) | — | 0 | Returned in 10ms; `would_spawn` = lows-adjudicate sonnet/high + lows-partition opus/high; also this window the batch-11 integrator appended 32 W3 agent-eval ollama $0 spend rows (177→209 lines) | run file + run-state ledger line 31 |
| wf_3e90ff66-7ea | scope-change-2 groundwork — authoring | groundwork script write (one Opus agent) | 25 Sep 04:43 | 7.2min | 1 | opus 1 | 155,788 | Committed `b3f7f284` on origin/004: the groundwork tooling script + its runbook doc, node --check ok, stubbed dry runs clean, banned-phrase check 0 hits | run file, matched by duration/tokens to run-state ledger line 32 (id not printed there) |
| wf_8607274d-b0e | scope-change-2 groundwork — PREP harness check | groundwork script `{mode:'prep', dry_run:true, sha:'b3f7f284', max_shard:80}` dry run | 25 Sep 04:51 | ~0min (14ms) | 0 (0 spawned) | — | 0 | Dry run only: 0 agents spawned, `would_spawn` lists ~14 fixed prep roles (verify/scout/baseline/options/mine/label shards) — **not in the ledger** | run file only |
| wf_18bf38f4-b9d | scope-change-2 groundwork — PREP | verify, baseline, options, mine, label (26 agents) | 25 Sep 04:52 | 14.3min | 26 | opus 16, sonnet 10 | 2.48M | Package verified Apache-2.0 (the candidate inference package's 0.2.0 build flagged as an unattested third-party port); 366 candidates → 339 agreed; committed `b667140c`/`69853b14`/`2d2fb032` on origin/004 | run file + run-state ledger line 33 |
| wf_fbc3642c-442 | Lows partition | register adjudication of batch-11 + partition build | 25 Sep 04:57 | 36.2min | 2 | opus 1, sonnet 1 | 310,246 | Register adjudication `5a0e97b0` (18→fixed); `PARTITION.json`/`.md` `9ec6bd17` — 207 open lows placed, 191 in 27 writer sets, ownership audit 0 errors over 393 files | run file + run-state ledger line 41 |
| wf_7c4b2e60-141 | rc1 GATE ROUND 1 | full gate: register, ci-local, smoke, data packs, scenarios, drives, battery, adversarial sample | 25 Sep 04:57 | 295.6min | 43 | opus 17, sonnet 26 | 6.38M | **FAIL, no tag.** Committed `b2cfbb68` + fix rounds `57897778`; PASS Gate 8/ci-local/smoke/data packs; FAIL register (5 open c/h/m), scenarios, drives, battery, adversarial sample (14/14 certified entries refuted) | run file + run-state ledger line 36 |
| wf_90712d2d-cab | rc1 REFUTATION AUDIT | 5-agent audit of the 14 adversarially-refuted entries | 25 Sep 09:58 | 14.3min | 5 | opus 4, sonnet 1 | 688,305 | Evidence `4f2aba93` on origin/004: regression_confirmed 1 (DATA-059), partial 12, adjacent 1 (AGENT-003); 13 reopened, gate verifier got nothing wrong | run file + run-state ledger line 37 |
| wf_4e25ca95-a6f | rc1 SCRIPT TUNING | one Opus agent patches `rc1-gate.js` | 25 Sep 09:59 | 4.5min | 1 | opus 1 | 128,318 | `91dac548` on origin/004: `drive_limit`/`batt_limit` args, LOCAL-MODEL LOCK cause, coverage-first battery sharding, skip_gui list | run file, matched by duration/tokens to run-state ledger line 38 (id not printed there) |
| wf_272a4f49-e8a | rc1 GATE RUBRIC RESTORE | one Sonnet/high agent patches `rc1-gate.js` | 25 Sep 10:08 | 3.4min | 1 | sonnet 1 | 122,811 | `3c51ac3c` on origin/004 (+3/-3): register criterion RUBRIC (a) restored — requires a fresh concurrence for not_a_defect/out_of_scope/removed_with_feature in the four named areas | run file + run-state ledger line 39 |
| wf_7e4c4a3f-085 | batch-12 rc1 FIX BATCH | 8 writers / 22 entries | 25 Sep 10:14 | 69.1min | 13 | opus 6, sonnet 7 | 2.35M | Merged `ef33c7f6`; register adjudication `bc3e64fe` (10 new lows, 3 → blocked_tier4); 19 certified, 3 not certified (RESEARCH-007, DOCS-017, AGENT-090) | run file + run-state ledger line 40 |
| wf_ac5e3ff2-49d | scope-change-2 measure | zero-shot measure vs the $0 heuristics + critic re-run | 25 Sep 11:27 | 13.2min | 4 | opus 1, sonnet 3 | 428,248 | `52d6957e` on origin/004: not worth fine-tuning this release (loses or no-signal on 2/3 tasks; entity_match the only signal); backlog entry inserted | run file + run-state ledger line 42 |
| wf_1e4295f3-748 | batch-13 rc1 FIX BATCH | 8 agents | 25 Sep 11:41 | 53.8min | 8 | opus 5, sonnet 3 | 1.28M | Merged `a217a529`; RESEARCH-007 + DOCS-017 certified; AGENT-090 + CODE-AGENT-033 not certified. Open c/h/m after merge: AGENT-090 (high), CODE-AGENT-033 (medium) | run file + run-state ledger line 43 |
| wf_7c5e7b20-e4f | VERIFIER RUBRIC TUNING | one Sonnet/high agent, three prompt files only | 25 Sep 11:42 | 2.5min | 1 | sonnet 1 | 144,380 | `f1a2682d` on origin/004: "CERTIFY THE CLAIM, NOT ONLY THE REPRO" clause added to 4 verifier prompt sites; labels/models/effort/schemas untouched | run file + run-state ledger line 50 |
| wf_b7cf82ec-5ec | batch-14 rc1 FIX BATCH | 6 agents | 25 Sep 12:37 | 50.5min | 6 | opus 5, sonnet 1 | 774,658 | Merged `17301f54`; CODE-AGENT-033 certified; AGENT-090 NOT certified a second time (wording-recognition errs both ways); merged anyway | run file + run-state ledger line 44 |
| wf_45b81e1e-57a | batch-15 STEP 1: AGENT-090 root cause | one Fable/high agent, strongest-tier root cause after 2 failed Opus attempts | 25 Sep 13:32 | 40.7min | 1 | fable 1 | 123,479 | `origin/worktree-agent-batch-15-W1@aaf32a7e`: clause-level attribution redesign in `_guard_tool_citations`; 12 tests added; live bar 0/8 untraced | run file + run-state ledger line 45 |
| wf_b1ca86d0-402 | batch-15 STEP 2 | 6 agents, W1 salvage + integrate | 25 Sep 14:13 | 39.0min | 6 | opus 5, sonnet 1 | 719,905 | Merged `74ee3468`; AGENT-090 NOT certified on one residual (class-qualifier nouns); grounding SIFY/IBN/HDB/INFY holds with 20-F provenance | run file + run-state ledger line 46 |
| wf_3e8b0f3e-a84 | batch-16 rc1 FIX BATCH | 6 agents | 25 Sep 14:55 | 55.2min | 6 | opus 5, sonnet 1 | 775,918 | Merged `d64640d2`; AGENT-090 CERTIFIED, LEAD-032 CERTIFIED, LEAD-030 NOT certified (3 new escapes); LEAD-031 not attempted | run file + run-state ledger line 47 |
| wf_232102df-2f0 | batch-17 rc1 RESIDUAL BATCH | 6 agents | 25 Sep 15:57 | 52.2min | 6 | opus 5, sonnet 1 | 807,671 | Merged `292ba53a`; LEAD-031 CERTIFIED; LEAD-030 NOT certified a second time (true-citation-beside-errored-tool case); 2 new lows surfaced | run file + run-state ledger line 48 |
| wf_037d692d-bcd | LOWS PARTITION PATCH | one Sonnet/high agent | 25 Sep 15:58 | 3.9min | 1 | sonnet 1 | 161,522 | `dd7b98e9` on origin/004: 3 newly-filed lows added to the partition (AGENT-091, CODE-PLATFORM-077, LEAD-029); 0 file overlaps | run file + run-state ledger line 51 |
| wf_116e8cdf-429 | batch-18 STEP 1: LEAD-030 strongest-tier root cause | one Fable/high agent, 203 tool uses | 25 Sep 16:53 | 47.7min | 1 | fable 1 | 112,090 | `origin/worktree-agent-batch-18-W1@ecdd223e`: clause-level attribution in `_guard_tool_citations`; 3 new tests; focused 211 passed; live bar 8 runs, 0 fabricated / 0 true replaced | run file + run-state ledger line 49 |
| wf_9fadb146-f9b | LEAD_FOUND FILING | one Sonnet/high agent | 25 Sep 16:54 | 4.5min | 1 | sonnet 1 | 114,529 | `701751b9` on origin/004: filed R15-LEAD-033 (chat trailer echo) + R15-LEAD-034 (NSE Emerge -SM symbol mismatch) as new mediums | run file + run-state ledger line 52 |
| wf_d855d73b-b6b | Stage E JUDGE PANEL — **DEGRADED** | 4 Opus case-builders → Fable judge A → Fable judge B → Fable synthesis | 25 Sep 17:25 | 22.7min | 7 (2 landed: judge A + synthesis) | fable 3, opus 4 | 527,049 | `afbc3314` on origin/004: 5 of 7 agents died on API safeguard errors (all 4 case-builders + judge B); judge A + synthesis only — 48 survivors, top BL-03; completion re-run separately | run file + run-state ledger line 53 |
| wf_50973ceb-819 | HANDOVER PRE-REFRESH | one Opus agent | 25 Sep 17:27 | 12.2min | 1 | opus 1 | 250,888 | `ac227f43` on origin/004: `R15_RUN_REPORT.md` + `OPERATOR_BRIEFING.draft.md` refreshed; surfaced CHANGELOG gap (batches 12–17) and a CLAUDE.md keychain doc mismatch | run file + run-state ledger line 54 |
| wf_cd489d8e-cf7 | LOWS BUCKET ADJUDICATION | one Sonnet/high agent | 25 Sep 17:28 | 2.9min | 1 | sonnet 1 | 98,766 | `3483b699` on origin/004: 4 lows → blocked_tier4, 2 → needs_gui; register now fixed 388 / open 206 / needs_gui 11 / blocked_tier4 22 | run file + run-state ledger line 55 |
| wf_dc281379-fb7 | CHANGELOG BACKFILL | one Sonnet/high agent | 25 Sep 17:41 | 6.9min | 1 | sonnet 1 | 189,033 | `b1ee6aa5` on origin/004: added CHANGELOG sections for batches 12–17 + rc1 round 1; 56 cited shas resolve; zero banned-phrase hits | run file + run-state ledger line 56 |
| wf_ea0144f4-04a | Stage C batch-18 STEP 2 — **IN FLIGHT** | adjudicate, plan, W1 (opus) + W2 (sonnet) writers | 25 Sep 17:43 | in flight (~26min elapsed at write, 18:09 IST) | 4 (adjudicate + plan + W2 done, W1 opus still running) | sonnet 2, opus 2 (W1 in progress) | not recorded (in flight) | Adjudicate applied batch-17 verdicts + filed LEAD-033/034; plan split W1 (LEAD-030 validate + LEAD-033) / W2 (LEAD-034); W2 done — LEAD-034 fixed `d74a4a4d`, 112 tests passed | run file + run-state ledger line 57 |
| wf_407df695-831 | Stage E PANEL COMPLETION — **IN FLIGHT** | Fable judge B (independent) → Fable synthesis | 25 Sep 17:59 | in flight (~10min elapsed at write, 18:09 IST) | 1 (judge B running) | fable 1 (in progress) | not recorded (in flight) | Independent judge B re-run to complete the 2-judge panel (judge A's raw verdicts from `scratchpad/panel/judge-A.json`); synthesis not yet dispatched | run file + run-state ledger line 58 |

## Strategy changes

- **03:46 IST 23 Sep — SCOPE CHANGE.** Trading removed from the product permanently (operator
  Tier-4 sign-off in-message). Removal became the first Stage C batch; Gate 8 rewritten to prove
  no order/broker/simulated-account path exists anywhere and the tracked portfolio is intact; the
  OpenAI-direct spend cap raised from the session-1 $2.00 hard stop to $8.00 (`vy.py` refuses at
  $7.50). Source: run-state header SCOPE CHANGE bullet, D81 in `DECISIONS.md`.
- **03:52 IST 23 Sep — ROUTING CHANGE 1.** Zero Fable agents for the rest of the run, including
  the judge panel; Sonnet 5 (effort medium) became the default for bounded/mechanical work; Opus
  5.5 (effort high/xhigh) reserved for judgement work — refutation, root-causing, risk-adjacent
  implementation, integration, certification.
- **19:33 IST 24 Sep — ROUTING CHANGE 2** (ack mid batch-8 Verify phase, left to finish on the old
  script). Sonnet became the default for any task with a clear spec and a checkable output,
  including most fixes; Opus narrowed to refutation/root-causing/risk-adjacent
  implementation/integration/fresh-context certification at its default effort; one verification
  per merged batch (writers never re-verify, reviewers never re-run what the integrator ran).
- **20:05 IST 24 Sep — ROUTING CHANGE 3** (ack mid batch-9 run). Fable agents returned for
  judgement-only roles (refutation, root-causing, fresh-context certification, risk-adjacent
  review, the judge panel), model set explicitly per site; never for fan-out labour, packs, diffs,
  docs or mechanical fixes; one automatic fallback to Opus if a Fable verifier returns nothing.
- **21:45 IST 24 Sep — PACING CHANGE** (ack mid batch-9 Write phase, left alone). Concurrent-agent
  ceiling raised 8 → 16; two workflows in flight became the norm on disjoint lanes/tiers (never
  two both needing the live app/GUI/local model/heavy-job lane); waves sized to about half a
  window; a wave starving with no wall reported drops back to 8.
- **19:50 IST 24 Sep — PROCESS NOTE (IN-FLIGHT LEDGER)**, adopted at the batch-8 merge. Every
  workflow or own-hands step is written into the run-state header as IN-FLIGHT before it starts,
  with a stated DONE definition and evidence path, and flipped to DONE only once that evidence
  exists on disk or in git.
- **~15:00 IST 24 Sep — HARNESS STALL RULE**, added after the batch-6 failure (see below). Every
  worker prompt (`COMMON.md`) now forbids running a long command (`ci-local`, full pytest, sidecar
  boots, `sleep`-loops) inside a single tool call — detach and poll instead. Saved to project
  memory as `harness-stall-watchdog.md`.

## Limit walls and failures

- **19 Sep ~15:05 IST — 5-hour session wall.** ~95 of ~100 agents died at once (each burned its 3
  retries instantly). Resumed 15:08 in low-priority mode. (L6)
- **19 Sep 15:08-15:45 IST — low-priority mode starved Opus.** Measured 10 min in: Opus 0
  progressing / 105 starved; Fable 35 progressing / 2 starved. All-Opus workflows were stopped and
  reissued on Fable. (L7)
- **19 Sep, sometime between 10:06 and 14:41 IST — MacBook lost power.** Exact loss time is not
  recorded in `vysted-r15-run-state.md` (only the 14:41 resume is stated); HEAD/hooks/iso-stack/
  caffeinate were confirmed intact on resume; the running code-census workflow had stopped with
  3/31 critiques landed. (L4-L5)
- **19 Sep 15:45-16:10 IST — operator-requested graceful pause.** All 15 workflows + the monitor
  stopped; 21 own sidecars stopped by verified PID; caffeinate released. Not a wall. (L8)
- **24 Sep, Stage C batch 6 harness-stall failure.** `wf_94ccf2b8-e97` (launched 03:16) FAILED at
  14:56: "agent stalled on all 6 attempts (no progress for 180000ms each)" — a 3-minute
  no-progress watchdog repeatedly killed writers, the integrator and the verifier (42 transcripts
  for 10 agents, 6.4M tokens, 11.9h) because they ran long commands inside single tool calls. 22 of
  60 planned entries were delivered before the workflow died; recovered by hand (see next). (L26)
- **24 Sep ~15:00 IST — the Mac slept.** The iso stack, the operator's own dev sidecar (:52052) and
  the run's `caffeinate` all died together with the stall. Lead recovery: killed 2 orphan pool
  workers (PPID 1, 11h old), patched `COMMON.md` with the stall rule, re-armed caffeinate,
  restarted the iso stack, reconstructed `batch-6/VERDICTS.md` from the verifier transcript, and
  dispatched an Opus fixer for the leaking quant-pool workers (`831d52b`); merged as `5e147317`. (L26)
- **24 Sep, batch-8 window — SSH flakes.** SSH to GitHub flaked twice with "Permission denied
  (publickey)" between otherwise-working calls; pushes switched to
  `GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519 -o IdentitiesOnly=yes'`. (L28)
- **GitHub returning HTTP 500 on an infra call: not recorded.** Searched
  `vysted-r15-run-state.md`, `CHANGELOG.md`, `DECISIONS.md`/`DECISIONS_FOR_OPERATOR.md` and every
  Stage C `VERDICTS.md` — no GitHub-infrastructure-500 event is documented in any of them. The
  only HTTP 500s on record are product-level data-vendor errors (e.g. a screener headline fetch in
  `r15/stage-c/batch-6/VERDICTS.md:379`), which are register findings about the app, not run-infra
  failures, and are out of scope here.
- **24 Sep, lows pre-triage workflow-return under-count (`wf_c6207d00-908`).** The script's
  `RETURN counts` field omitted `still_reproduces` (reported 1 instead of 199); the underlying
  files (`LOWS_TRIAGE.json`/`.md`) are correct — fix `lows-triage.js` only if it is ever rerun.
  (run-state ledger line 23)
- **25 Sep 01:22-01:23, batch-10 verify weekly-limit rejections (`wf_54334d97-0e6`).** Two Fable
  verify attempts (`batch-10-verify-fable` then `batch-10-verify-fable-retry`) both failed with
  "You've hit your weekly limit · resets Sep 26 at 3:30pm (Asia/Calcutta)"; a trivial probe agent
  returned ok, so the rejection was momentary — re-dispatched with only the verifier live, which
  then passed. (journal `wf_54334d97-0e6`; run-state ledger line 30)
- **25 Sep 01:44, killed batch-11 first launch attempt (`wf_96670fc2-911`).** Aborted
  (`Error: Workflow aborted`) 2.0min after launch with 1 Fable agent still in progress, 0 agents
  landed; batch-11 relaunched cleanly 4 minutes later as `wf_a5e688ba-d35`. Not named by id in the
  run-state ledger. (run file `wf_96670fc2-911.json`)
- **25 Sep 17:25, Stage E judge panel DEGRADED (`wf_d855d73b-b6b`).** Five of seven agents died on
  API safeguard errors: all 4 Opus case-builders (`cases-q1..q4`) and Fable `judge-B`; only judge A
  and synthesis landed, so `PANEL.md`/`PANEL.json` carry one judge's scores for the whole backlog.
  Completion re-run separately as `wf_407df695-831` to add the missing judge B. (journal
  `wf_d855d73b-b6b`; run-state ledger line 53)

## API spend

Caps: session 1 (D8, 19 Sep) set a $2.00 OpenAI-direct hard stop + the OpenRouter `:free` lane
(1000 req/day, $0), enforced by `scripts/r15/vy.py` refusing at 700 free calls/day or $1.80 paid.
Superseded by the SCOPE CHANGE (03:46 IST 23 Sep): OpenAI-direct hard stop raised to **$8.00**
(`vy.py` refuses at $7.50).

**Refreshed** for this backfill: read at 18:07 IST 25 Sep from
`docs/redesign/verification/r15/spend-ledger.jsonl` (374 lines, 19 Sep 14:58 → 25 Sep 16:48 IST;
this file is dirty on purpose and stays uncommitted — read only, never git-added). By provider:

| Provider | Calls | Paid (est_usd) |
|---|---|---|
| `openai` | 30 | $0.201076 |
| `ollama` | 237 | $0.00 |
| `openrouter` | 104 | $0.00 |
| `deepseek` | 2 | $0.00 |
| `none` (bookkeeping note row, not an API call) | 1 | $0.00 |
| **Total** | **374** | **$0.201076** |

30 rows are paid (all via `openai`); 343 are free (237 `ollama`, 104 `openrouter` free-tier, 2
`deepseek`); 1 is a non-call bookkeeping note (the `budget-change` cap-raise entry). Total spend
$0.20 is well under both the original $2.00 cap and the raised $8.00 cap.

<details>
<summary>Prior snapshot (23:31 IST 24 Sep, 173 rows, by lane)</summary>

| Lane | Calls | Paid (est_usd) |
|---|---|---|
| Stage A / census probes (`s2a-*`) | 25 | $0.159517 |
| Batch verifier probes (`b2v..b9v-*`, `b7/b8-verifier-*`) | 64 | $0.014512 |
| Surface probes (`surf-*`) | 26 | $0.003777 |
| Session bookkeeping / misc (`lead-smoke`, `inducer`, `L2-rot`, `budget-change`, `patch-proof`, `untagged`) | 13 | $0.001547 |
| Local-lane Ollama proof (`local-lane-*`) | 15 | $0.00 |
| Lifecycle probes (`life-*`) | 19 | $0.00 |
| World/harness probes (`wld-*`) | 4 | $0.00 |
| Stage B/C data probes (`s2b/s2c-*`) | 3 | $0.00 |
| Onboarding probes (`onb-*`) | 4 | $0.00 |
| **Total** | **173** | **$0.179353** |

24 rows were paid (all via `openai`); 149 were free (96 `ollama`, 52 `openrouter` free-tier, 1
`deepseek`).

</details>
