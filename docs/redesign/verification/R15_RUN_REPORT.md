<!-- refreshed 25 Sep 2026 17:35 IST at 82d3d083 by the handover pre-refresh; every line marked "(at the rc1 tag: …)" changes at the tag, so the at-tag refresh is a delta -->

# R15 LAUNCH — run report

## Outcome so far

R15 has not tagged a release candidate yet. The newest tag is still `r13-bedrock` (`6a40f83`),
which remains the fallback release line. (at the rc1 tag: the newest tag becomes `r15-rc1` at the
round-2 sha, and `r13-bedrock` stops being the fallback.)

The census closed on 23 Sep (Gate 2). Stage C has since merged seventeen fix batches into
`004-r4-experience-rebuild`, the last one at `292ba53a` (16:50 IST 25 Sep).

The first rc1 gate round failed at 09:57 IST 25 Sep and no tag was cut. It passed Gate 8 (no
trading path, tracked portfolio intact), ci-local, smoke and the data packs. It failed on open
register entries, agent scenarios, owner-drives, the fixed-name battery and the fix loop, and on
an adversarial sample in which all 14 re-tested certified entries failed. An audit of those 14
upheld every refutation: 13 entries were reopened and one adjacent defect was filed.

Batches 12 to 17 worked through the reopened and residual entries. One critical/high/medium
entry is open in the register now: `R15-LEAD-030` (high, agent-chat). After a tool errors, the
local model can write a made-up "the tool returned …" citation; the guard against it failed
certification in batch 16 and again in batch 17. Batch 18 step 1, a strongest-tier root cause of
LEAD-030, is running now. Two new mediums, `R15-LEAD-033` and `R15-LEAD-034`, were filed from the
batch-17 verifier's observations. They join the rc1 residual when batch 18's adjudicator enters
them in the register.

Gate round 2 runs once batch 18 is merged and adjudicated to zero open critical/high/medium
entries, and once no lows writer is still running tests. (at the rc1 tag: replace this paragraph
with the round-2 verdict, its time and the tag sha.)

## Gate table

| # | Gate | Status | Evidence | Time (IST) |
|---|---|---|---|---|
| 1 | Truth | **HOLDS** | run-state decisions R15-D1..D6 + `r15/stage0/`; commit `38ded25b` | 04:57 23 Sep |
| 2 | Census closed | **HOLDS** (after two BLOCKED passes) | `R15_GATE2.md` (three fresh-context Opus verifiers); commit `99e2ae38` | BLOCKED 13:28 and 14:17, HOLDS 15:00, all 23 Sep |
| 3–7 | not individually named | **not recorded** | The run brief is the only document that names gates 3–7, and this report does not read it. The run-state goes from Gate 2 to Stage C and then to the rc1 gate. | — |
| 8 | Safety (rewritten by the scope change): no order, broker or simulated-account path anywhere; tracked portfolio intact | **PASS in rc1 round 1** | `R15_GATE_RC1.md` items 2–3, `r15/rc1/GATE8.md`: 111 routes, none for orders, brokers, the kill switch or the audit log; 40 MCP tools, none for orders; the portfolio round-trip passed, including an agent write held for review | 09:57 25 Sep (at the rc1 tag: re-proved by round 2) |
| rc1 | Release-candidate gate | **round 1 FAILED 09:57 IST 25 Sep, no tag; round 2 pending on the batch-18 residual** | `R15_GATE_RC1.md` + `r15/rc1/` (commit `b2cfbb68`); the gate's own fix rounds merged as `57897778` | (at the rc1 tag: round-2 verdict, time and tag sha) |

rc1 round 1, item by item (run `wf_7c4b2e60-141`, 43 agents, 296 min; candidate `1d6511c8`):

| Item | Result | Item | Result |
|---|---|---|---|
| 1 Register criterion | FAIL — 5 c/h/m open + LEAD-010 fixed but uncertified | 7 Owner-drives | FAIL — a null market cap ranked first in a market_cap-desc sort |
| 2 Gate 8: no trading path | PASS | 8 Fixed-name battery | FAIL — 160 of 376 fixed ids had no raw output |
| 3 Gate 8: tracked portfolio | PASS | 9 Data packs | PASS — 24/24 complete |
| 4 ci-local | PASS — vitest 1825, cargo 19, pytest 3150 + 1 skipped | 10 Fix loop closed | FAIL — a fabricated SIFY ADR ratio unclosed after two rounds |
| 5 smoke | PASS — 3 sidecars, MCP toolCount 40 | 11 GUI round | DEFERRED — the computer-use grant does not cover the built app |
| 6 Agent scenarios | FAIL — 11/20 OpenRouter runs hit upstream 5xx; local-model runs contended | 12 Adversarial sample | FAIL — 14/14 certified entries refuted when re-run |

## Stages

**A — reconcile and relicense (closed 04:57 IST 23 Sep).** A worktree-salvage scout, the
relicense to PolyForm Strict 1.0.0 plus a commercial licence (`0c63d465`), an isolated stack
rebuilt from source on :52152-54, the Ollama local-lane proof (`r15/stage0/LOCAL_LANE_PROOF.md`)
and the num_ctx fix. Gate 1 holds. Loop log L9–L12.

**B — census (closed 15:00 IST 23 Sep).** Refute waves over every raw finding, Stage B items
1–6, and three Gate 2 attempts. Result: 887 raw findings became 603 register entries plus 76
rejections, all 23 intent chunks and 1,032/1,032 promises were assessed, and the coverage map
covers 101 surfaces in 288 cells. Loop log L12–L19.

**C — fix batches 1–17.** "Certified" means a fresh verifier re-proved the claim on the running
app, not that the writer said so. Tallies are each batch's own `r15/stage-c/batch-N/VERDICTS.json`.
Batch 1 has no VERDICTS file; its evidence is `r15/stage-c/REMOVAL_PLAN.md` and loop log L20.
Ids drop the `R15-` prefix.

| Batch | Scope | Merge | Merged (IST) | Certified | needs_gui | Not certified |
|---|---|---|---|---|---|---|
| 1 | trading removed from the product (D81) | `a122dbf6` | 23 Sep 16:33 | removal proved by the batch verifier (0 broker/order/kill/audit routes; all 22 former routes 404) | 0 | 0 |
| 2 | critical/high data, research, workspace | `806a90ca` | 23 Sep 18:47 | 37 | 0 | 3 (DATA-005, DATA-014, AGENT-001) |
| 3 | agent runtime, AUTO gate, LLM adapters, research depth | `c81d879b` | 23 Sep 21:07 | 38 | 0 | 2 (DATA-020, RESEARCH-005) |
| 4 | context admission, Gemini/xAI lanes, workflows, market-data gate | `dcbe7bae` | 24 Sep 00:01 | 45 | 2 | 3 (DATA-015, DATA-020, DATA-032) |
| 5 | India exchange lanes, resolver, runtime liveness | `1574ed8e` | 24 Sep 03:03 | 48 | 2 | 6 (LEAD-010, DATA-017, CODE-PLATFORM-018, AGENT-051, AGENT-052, CODE-FRONTEND-015) |
| 6 | India Emerge lanes, tool-call identity, research funnel (recovered after a harness stall; 22 delivered) | `5e147317` | 24 Sep 15:34 | 21 | 0 | 3 (CODE-PLATFORM-018, AGENT-046, RESEARCH-024); UI-041 concurred not a defect |
| 7 | India fundamentals, durable Delegate runs, chart integrity | `e81c9e7c` | 24 Sep 17:53 | 50 | 1 | 4 (AGENT-045, LEAD-005, AGENT-046, CODE-PLATFORM-021) |
| 8 | sidecar lifecycle, provider readiness, data-error honesty | `68bb7aa4` | 24 Sep 20:06 | 39 | 1 | 7 |
| 9 | tool-call identity, research brief contract, fundamentals truth | `6b702305` | 24 Sep 22:44 | 29 | 2 | 14 |
| 10 | runtime and backtest integrity, catalog and host actions, plugin lifecycle | `f407107f` | 25 Sep 01:43 | 50 | 1 | 4 (CODE-AGENT-009, UI-091, DATA-071, LEAD-013); AGENT-083 concurred not a defect |
| 11 | build recipe and gates, schema versions, agent eval, option chain | `4097dac4` | 25 Sep 04:55 | 18 | 0 | 2 (LEAD-028, RELEASE-007); UI-047, UI-059, DATA-080 concurred out of scope |
| 12 | rc1 refutation-audit reopenings and gate findings | `ef33c7f6` | 25 Sep 11:25 | 19 | 0 | 3 (RESEARCH-007, DOCS-017, AGENT-090) |
| 13 | source tiers via the Public Suffix List, live universe counts, ADR ratio guard | `a217a529` | 25 Sep 12:36 | 2 (RESEARCH-007, DOCS-017) | 0 | 2 (AGENT-090, CODE-AGENT-033) |
| 14 | tool_result stream event and grader; ADR ratio guard, second pass | `17301f54` | 25 Sep 13:29 | 1 (CODE-AGENT-033) | 0 | 1 (AGENT-090) |
| 15 | ADR ratio grounded from the SEC 20-F cover page (strongest-tier root cause) | `74ee3468` | 25 Sep 14:54 | 0 | 0 | 1 (AGENT-090) |
| 16 | ratio-guard class qualifier, tool-citation guard, bounded ADR lookup | `d64640d2` | 25 Sep 15:55 | 2 (AGENT-090, LEAD-032) | 0 | 1 (LEAD-030); LEAD-031 not attempted |
| 17 | citation guard across turns, partial tool-call marker hold | `292ba53a` | 25 Sep 16:50 | 1 (LEAD-031) | 0 | 1 (LEAD-030) |
| 18 | LEAD-030 root cause (step 1, running), then the batch with LEAD-033/034 (step 2) | in flight | — | — | — | — |

(at the rc1 tag: fill row 18 with its merge sha and tally.)

**rc1 gate, round 1 (failed 09:57 IST 25 Sep).** See the gate table. The gate's two fix rounds
merged as `57897778`. The chain was green at `1d6511c8`, but the verifier failed the candidate on
the items above. The needs_gui set stays operator-attended because the rig's computer-use grant
does not cover the built app.

**Refutation audit (10:12 IST 25 Sep, `4f2aba93`).** Run `wf_90712d2d-cab` re-examined the 14
refuted certifications. It found 1 confirmed regression (DATA-059) and 12 partial fixes, where the
entry's own repro holds but the verifier's adjacent claim reproduces. It also filed 1 adjacent
finding as the new entry AGENT-092 and found 0 verifier errors. 13 entries were reopened, and the
gate verifier had got nothing wrong. Evidence:
`r15/rc1/refutation-audit/REFUTATION_AUDIT.md`. Round-2 preparation followed:
- Gate-script tuning `91dac548`: drive and battery limits, a local-model lock, and a battery
  indexer that covers every fixed id.
- The not-a-defect concurrence rubric restored in `3c51ac3c`.
- A verifier rule, "certify the claim, not only the repro", in `f1a2682d`.

**Filing-watcher model groundwork (measured; verdict: not worth fine-tuning; backlog candidate).**
Off the release line; no code in this release. The prep ran 05:07 IST and the measurement 11:41
IST on 25 Sep, committed as `52d6957e`. The backlog entry sits in `r15/invent/BACKLOG.md` for the
judge panel.

**Lows.**
- Pre-triage (`84418994`): 199 still reproduce, 5 were already fixed, 1 was proposed as not a
  defect and 1 was a duplicate.
- Partition (`9ec6bd17`, patched `dd7b98e9`): 194 entries in 27 writer sets (P1 63, P2 64, P3 67),
  4 verify-only, 1 proposed not-a-defect, 4 blocked on Tier-1 files, and 7 deferred.
- Bucket adjudication (`3483b699`): the 4 blocked lows went to blocked_tier4, with
  `DECISIONS_FOR_OPERATOR.md` rows 4.5–4.8. The 2 GUI-only deferrals went to needs_gui. The 5
  inseparable lows stay open for a serial set after the partitions merge.
- Pacing change 3 moved the write runs up: they launch at the batch-18 merge. Integration comes
  after the tag, one partition at a time.

**D — docs wave drafts.** Run `wf_31f149cf-57d` wrote the drafts at `f4444790`, committed as
`5f1ddaae` (24 Sep 23:17). It produced 5 drafts, each revised after a critic, plus the secrets,
licence and dependency scans. The drafts are not promoted. This pre-refresh updates the briefing
draft, and Stage D reruns in refresh mode before rc2.

**E — judge panel (in flight).** Run `wf_d855d73b-b6b` launched at 17:31 IST 25 Sep. It judges
the 76-entry ranked backlog plus the filing-watcher entry, and it builds nothing. Its output,
`r15/invent/PANEL.md`, is not on disk at this sha.

**Pacing changes (operator).**
1. 21:45 IST 24 Sep: the agent ceiling rose from 8 to 16 and two workflows could run on
   different lanes. Waves were sized at about half a window, single lanes stayed single, and each
   merged batch got one fresh verifier.
2. about 01:45 IST 25 Sep: the ceiling rose to 32, with up to three workflows on different lanes
   and no workflow outliving two walls. `r15-rc1` is to be tagged the moment its gate passes,
   before the lows. A follow-up note at 03:35 split the lows into three concurrent partitioned
   workflows with serial integration.
3. 17:15 IST 25 Sep: the lows write runs launch at the batch-18 merge, not at the tag. Gate round
   2 waits until no writer is running tests. The judge panel starts now, off-machine. Up to four
   workflows can run on different lanes, and the panel and docs lanes do not count. At most 18
   test-running writers run on this Mac. Waves run full-size, and low-priority mode is allowed in
   a wall gap only if the tiers in flight are actually served.

## Register now

The snapshot is `vysted-r15-register.json` as last committed at `3483b699` (the lows bucket
adjudication, 17:31 IST 25 Sep). Before that it was `5d4ca99c`, the batch-17 adjudication that
applied batch 16's verdicts. Its declared counts: **887 raw findings → 646 entries + 76
rejections** (16 critical / 116 high / 288 medium / 226 low). The table below is derived from the
entries.

| Severity | fixed | open | needs_gui | blocked_tier4 | removed_with_feature | not_a_defect | total |
|---|---|---|---|---|---|---|---|
| critical | 16 | 0 | 0 | 0 | 0 | 0 | 16 |
| high | 105 | 1 | 4 | 5 | 1 | 0 | 116 |
| medium | 256 | 0 | 5 | 13 | 9 | 5 | 288 |
| low | 11 | 205 | 2 | 4 | 4 | 0 | 226 |
| **total** | **388** | **206** | **11** | **22** | **14** | **5** | **646** |

- **Open critical/high/medium: 1** — `R15-LEAD-030` (high, agent-tools, agent-chat area).
- **Known but not yet applied** (batch 18's adjudicator applies them): `R15-LEAD-031` (low) was
  certified in batch 17 and flips to fixed. `R15-LEAD-033` and `R15-LEAD-034` (mediums) are filed
  in `r15/stage-c/LEAD_FOUND.json` (`701751b9`) and enter the register as open.
- **needs_gui (11):** CODE-AGENT-001, LIFECYCLE-001, LIFECYCLE-008, UI-009 (high); UI-022,
  UI-025, UI-050, UI-083, UI-084 (medium); DOCS-024, LIFECYCLE-040 (low). Each needs a human
  click-through; `r15/stage-d/OPERATOR_BRIEFING.draft.md` §4 lists the check for each.
- **blocked_tier4 (22):** RELEASE-001..004 and AGENT-017 (high); AGENT-049, AGENT-064,
  CODE-FRONTEND-013, CODE-PLATFORM-010/015/071/073, CROSS-PLATFORM-001, DOCS-002/003/015, UI-044,
  UI-088 (medium); CODE-PLATFORM-063, DOCS-008, DOCS-011, RELEASE-012 (low). The briefing draft
  §3 groups them by the decision each waits on.

(at the rc1 tag: re-derive this section from the register at the tag sha. Expected: 0 open
critical/high/medium, LEAD-031 fixed, and LEAD-033/034 closed or adjudicated.)

## What is still ahead

The order comes from the run-state header's "Next action" line:

1. Batch 18 step 1: a strongest-tier root cause of LEAD-030 (running, run `wf_116e8cdf-429`).
2. Batch 18 step 2: the adjudicator applies batch 17's verdicts and files LEAD-033/034; the
   writers take the step-1 salvage plus LEAD-033 and LEAD-034; then the integrator, the reviewer
   and a fresh verifier run.
3. Lead merge, then adjudication to 0 open critical/high/medium, LEAD-033/034 included. If the
   strongest tier also fails LEAD-030, a fresh verifier adjudicates it with a written rationale,
   and that is recorded in `DECISIONS_FOR_OPERATOR.md`.
4. The three lows write runs (P1, P2, P3) launch at that merge head. Writers stay in their own
   worktrees and run focused tests only.
5. rc1 gate round 2, launched only once no writer is still running tests.
6. Tag `r15-rc1` the moment round 2 passes, then push, prune worktrees and refresh this handover.
7. Lows integrate P1, P2, P3 one at a time, rebased onto the rc1 head, each with a fresh verifier
   and a lead merge. Then a serial set handles the 5 inseparable lows.
8. Stage D: refresh and promote the drafts, write 0.9.0 into every version file, make the single
   CLAUDE.md commit, and build a production bundle from a clean profile.
9. Tag `r15-rc2`.
10. The one small build of the judge panel's top survivor.
11. Tag `r15-rc3`.
12. Exactly one final adversarial pass.
13. Tag `r15-launch`.

The handover is refreshed at every tag.

## Where the evidence lives

- Header, in-flight ledger and loop log: `docs/redesign/verification/vysted-r15-run-state.md`
- Waves table and spend: `docs/redesign/verification/R15_RUN_LOG.md`; paid-call ledger
  `docs/redesign/verification/r15/spend-ledger.jsonl`
- Register: `docs/redesign/verification/vysted-r15-register.json` (+ `.md` view); new leads
  waiting to be filed: `r15/stage-c/LEAD_FOUND.json`
- Gate 2: `docs/redesign/verification/R15_GATE2.md`
- rc1 round 1: `docs/redesign/verification/R15_GATE_RC1.md`, `r15/rc1/` (`VERDICT.md`,
  `FINDINGS.md`, `GATE8.md`, `fix-r1/`, `fix-r2/`, `verifier/`), and the refutation audit
  `r15/rc1/refutation-audit/`
- Stage C: `docs/redesign/verification/r15/stage-c/batch-{2..17}/` (`PLAN.md`, `VERDICTS.json`,
  `VERDICTS.md`; batches 14–17 also `verifier-evidence/`); the trading removal
  `r15/stage-c/REMOVAL_PLAN.md`
- Lows: `r15/stage-c/lows-triage/LOWS_TRIAGE.md`, `r15/stage-c/lows/PARTITION.md`
- Filing-watcher model groundwork: `docs/redesign/verification/r15/laya/` (`VERDICT.md`,
  `measurements/`)
- Ranked backlog and judge panel: `r15/invent/BACKLOG.md`; `r15/invent/PANEL.md` once the panel
  commits
- Stage D drafts and scans: `docs/redesign/verification/r15/stage-d/`
- Workflow scripts and exact relaunch arguments: `docs/redesign/verification/r15/tooling/`
- Decision logs: `docs/redesign/DECISIONS.md`, `docs/redesign/DECISIONS_FOR_OPERATOR.md`
- Batch summaries: `CHANGELOG.md` has sections for the trading removal and batches 2–11.
  Batches 12–17 and the rc1 fix rounds have no CHANGELOG section yet.
- Workflow journals: `…/3e7ae14d-d48a-4882-8a75-f7608754c23f/subagents/workflows/<runId>/journal.jsonl`
  (this session) and `…/5df12ac0-f23e-48c6-b614-80321cbbfb31/subagents/workflows/<runId>/journal.jsonl`
  (the 19 Sep session). Both folders are outside the repo, in the operator's local Claude Code project store.
