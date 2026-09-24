<!-- backfilled 24 Sep 2026 from journals + run-state; numbers traceable per row -->

# R15 LAUNCH — run log (telemetry)

26 workflow runs tabulated: the 23 under this session's
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
| wf_54334d97-0e6 | Stage C batch 10 — **IN FLIGHT** | adjudicate, plan, 8 writers dispatched | 24 Sep 22:47 | in flight (30.2min elapsed at last write) | 2 landed + 8 writers running | sonnet 1, opus 1 (+8 writers in progress) | not recorded (in flight) | adjudicate applied batch-9 verdicts; plan took 56/88 open (0/2 highs, 56/86 mediums); no VERDICTS yet | journal + run-state ledger line 28 |

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

## API spend

Caps: session 1 (D8, 19 Sep) set a $2.00 OpenAI-direct hard stop + the OpenRouter `:free` lane
(1000 req/day, $0), enforced by `scripts/r15/vy.py` refusing at 700 free calls/day or $1.80 paid.
Superseded by the SCOPE CHANGE (03:46 IST 23 Sep): OpenAI-direct hard stop raised to **$8.00**
(`vy.py` refuses at $7.50).

By lane, from `docs/redesign/verification/r15/spend-ledger.jsonl` (173 rows, 19 Sep 14:58 → 24 Sep
22:31 IST; tag grouped by prefix):

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

24 rows are paid (all via the `openai` provider); 149 are free (96 `ollama`, 52 `openrouter`
free-tier, 1 `deepseek`). Total spend $0.18 is well under both the original $2.00 cap and the
raised $8.00 cap.
