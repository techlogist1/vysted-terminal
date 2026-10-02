# R15 rc1 tag-window handover (lead to lead)

This is the **lead-to-lead** handover for the rc1 tag window — not the operator
handover (`r15/stage-d/OPERATOR_HANDOVER.draft.md` is untouched by this
branch). Companion file: `HEADER_DRAFT_rc1.md` (the four run-state header
lines a fresh lead splices in at the tag).

## (a) Where the run stands

Five full pre-tag gate rounds ran (round 1 folded into round 2's resume,
rounds 2-4 each FAILED and re-ran, round 5 FAILED under the old
all-or-nothing rubric but PASSES the fixed bar the operator wrote in
mid-round as gate rule change 1). Round 5's one bounded fix round certified
R15-LEAD-059 (a cross-company disclosure-feed leak) but its own fresh
verifier found one more high, R15-LEAD-116, on a narrower slice of the same
bug class — the one bounded fix round the gate rule allows is already spent,
so the tag waited on the operator's answer to DECISIONS §4.22. The operator took
option (d): `r15-rc1` is tagged (annotated tag object `0e0852e9` on commit
`949c3c9f`, pushed 03:13:57 IST Sat 3 Oct 2026) with R15-LEAD-116 an open high
at 0.9.0-rc1. Its bounded fix runs first inside the lows integration (in
flight), certified by that candidate's fresh verifier; rc2 requires open
critical and high = 0 including it, and if the fix fails certification once it
is filed for 0.9.1 with its fail-safe described. The recheck on `949c3c9f` read
clean on chain and Gate 8. 004 carries 0.9.0 (`06879089`) and the 0.9.1 backlog
draft (`6f165d86`); DECISIONS §5.1-5.10 took their recommended options as
operator-default at 03:22 IST Sat 3 Oct (standing rule). Register at `949c3c9f`: **738 entries** — **fixed 395**, **open
277** (1 high + 28 medium + 248 low), **blocked_tier4 35**, **needs_gui 11**,
removed_with_feature 14, not_a_defect 6.

## (b) Measured wall-clocks

Every `measured` figure recorded in the run-state's IN-FLIGHT LEDGER, in
order. Model tier is given where the ledger states one; "mixed" means the
step ran a mix of Sonnet/Opus roles per the standing routing rule and no
single tier is stated for the whole step. IST throughout, 26-27 Sep 2026.

| Date | Time (done) | Task | Model/tier | Measured | Estimate | Outcome |
|---|---|---|---|---|---|---|
| 26 Sep | 14:50 | rc1 gate round 2 (initial) | mixed | wall-clock span 06:05→14:50 (301 min active + wall pause) | ~5 h | FAIL, no tag |
| 26 Sep | 18:02 | rc1 gate round 2 resume | mixed | 192 min | 60-90 min | FAIL again, no tag |
| 26 Sep | 18:32 | rc1 refutation audit, round 2 | 4 Opus + 1 Sonnet (5 agents) | 16 min | 15-40 min | 11 `partial`, 2 new highs confirmed |
| 26 Sep | 18:43 | rc1 gate-script fix-up for round 3 | 1 Opus | 26 min (agent + merge) | — | re-key root cause fixed |
| 26 Sep | 18:43 | run log backfill #6 part 2 | 1 Sonnet/high | 7 min | — | spend reconciled |
| 26 Sep | 19:52 | Stage C batch 25 | Opus-led (12 agents) | 77 min | 60-120 min | 10 certified, 4 not certified |
| 26 Sep | 20:13 | CHANGELOG backfill #2 | 1 Sonnet/high | 9 min | 15-25 min | — |
| 26 Sep | 21:03 | Stage C batch 26 | Opus-led (7 agents) | 60 min | 45-75 min | AGENT-010 + LEAD-039 certified |
| 26 Sep | 21:09 | CHANGELOG batch-26 section | 1 Sonnet/high | 4 min | 5-10 min | — |
| 26 Sep | 23:35 | rc1 gate round 3 | mixed (22 agents) | 152 min | 3-5 h | FAIL, no tag (harness: battery collapsed to 1 shard) |
| 26 Sep | 23:55 | gate-script fix-up for round 4 (battery-plan root cause) | 1 Opus/high | 15 min | 25-40 min | 25-shard plan validated |
| 27 Sep | 01:09 | Stage C batch 27 | Opus-led (6 agents) | 82 min | 45-60 min | DATA-117 fixed, LEAD-040 fixed |
| 27 Sep | 01:21 | CHANGELOG sections: batch-27 + gate round 3 | 1 Sonnet | 8 min | 15 min | — |
| 27 Sep | 01:29 | hygiene-prune inventory refresh | 1 Sonnet | 17 min | 20 min | read-only, no deletions |
| 27 Sep | 06:27 | rc1 gate round 4 (attempt 2; attempt 1 blocked at 6 min, harness cause) | mixed (58 agents) | 304 min | 150-200 min | FAIL, no tag (7 standing refutations) |
| 27 Sep | 06:56 | CHANGELOG section: gate round 4 | 1 agent | 7.4 min | 10 min | — |
| 27 Sep | 07:14 | rc1 refutation audit round 4, follow-up group `datapack` | 1 Opus | 14.5 min | 15-20 min | DATA-008 regression_confirmed |
| 27 Sep | 07:54 | rc1 refutation audit round 4 | 8 Opus + 1 Sonnet (9 agents) | 70 min | 35-50 min | 3 regression_confirmed, 4 new_defect_confirmed |
| 27 Sep | 10:13 | Stage C batch 28 | Opus-led (11 agents) | 131 min | 120-180 min | 25 certified, 5 not certified |
| 27 Sep | 10:28 | CHANGELOG section: round-4 audit + batch 28 | 1 Sonnet 5/medium | 10.5 min | 12-20 min | — |
| 27 Sep | 11:30 | Stage C batch 29 | Opus-led (9 agents) | 70 min | 90-120 min | NOT MERGED — verifier BLOCK on 1 commit |
| 27 Sep | 11:53 | batch-29 integration rework | 1 Opus 5.5/high | 17 min | 35-50 min | DATA-030 hunks reverted, guard test added |
| 27 Sep | 12:52 | Stage C batch 30 | Opus-led (7 agents) | 56 min | 70-110 min | LEAD-050/051 certified, DATA-030 3rd failure |
| 27 Sep | 13:05 | batch-30 adjudication + DECISIONS 4.21 | 1 Sonnet 5/high | 10 min | 15-25 min | DATA-030 → blocked_tier4 |
| 27 Sep | 13:11 | batch-30 integration rework | 1 Opus 5.5/high | 16 min | 20-35 min | DATA-030 news hunks reverted |
| 27 Sep | 13:25 | CHANGELOG section: batch-29 + batch-30 | 1 Sonnet 5/high | 11 min | — | — |
| 27 Sep | 17:52 | RC1 gate round 5 — gate rule change 1 | mixed (56 agents) | 279 min (4.65 h) | 120-180 min | sheet FAIL (old rubric) / PASSES fixed bar |
| 27 Sep | 17:56 | round-5 adjudication prep (a): vshard triage extraction | Sonnet/medium | 4.3 min | 5-10 min | — |
| 27 Sep | 18:18 | round-5 adjudication under gate rule change 1 | Sonnet/high | 22.5 min | 15-25 min | 4 reopened, 57 filed, open c/h = 1 |
| 27 Sep | 18:19 | round-5 adjudication prep (b): rc1-gate.js lane selection | Sonnet/high | 19 min | 20-40 min | partial re-run capability added |
| 27 Sep | 18:31 | RC1 round-5 bounded fix round (LEAD-059) | Opus/high writer + Sonnet/medium integrator + Opus/high verifier (3 agents) | 31 min | 45-70 min | CERTIFIED; LEAD-116 + LEAD-117 filed by the same verifier |
| 27 Sep | 18:42 | CHANGELOG section: gate round 5 | Sonnet/medium | 6.7 min | 10-15 min | — |
| 27 Sep | 18:42 | version 0.9.0 rebase prep | Sonnet/high | 7.4 min | 10-20 min | branch ready, NOT merged |
| 27 Sep | 18:42 | BL-03 leaves the release line | Sonnet | 2.6 min | 10-15 min | branch pushed, NOT merged |
| 27 Sep | 18:52 | 0.9.1 backlog draft | Sonnet/medium | 7.1 min | 10-15 min | branch pushed, HELD unmerged |
| 27 Sep | 18:58 | hygiene prune plan, dry run | Sonnet/medium | 13.8 min | 10-15 min | merged `2ad36910`, nothing deleted |

**In flight, no completed figure yet:** the RC1 round-5 recheck (launched
18:33 IST, `wf_da354223-f11`) — round-5's own component breakdown put
preflight ~9 min, heavy ~35 min, battery (25 shards, `batt_limit:4`) ~90 min,
total estimate 120-150 min; the recheck's _own_ evidence files, read directly
off disk, show it running faster than that decomposition: preflight build
EXIT=0 in ~7 min (18:32→18:39, warm caches from the same-day round-5 build),
gate8 lane ~18-23 min (18:39/44→19:02 by file mtime), heavy lane (ci-local +
smoke) ~8-10 min (19:02→19:12 by file mtime) — well under the round-5
component estimates. The battery lane started ~19:05 and was still running
multiple shards at the time this handover was written (mtimes into 19:4x).

### Derived remainder for the post-tag steps

Using ONLY measured durations of like steps, per the naming the operator's
brief gave: **a chain run ≈ the recheck's own heavy lane** (~8-10 min,
measured above from file mtimes — this _is_ on disk, not an estimate); **a
battery ≈ the round-5 battery** (~90 min, the one figure on record labelled
"round-5 measured" for the battery component); **a fix round ≈ the round-5
bounded fix round** (31 min, measured directly above); **an integration ≈ a
batch integration**, using the two directly-labelled "integration rework"
runs as the closest precedent (16-17 min each, ~16.5 min average — these are
narrower reworks than a full writer+integrator+reviewer+verifier batch, so
treat this as a floor, not a ceiling, for a larger merge).

| Post-tag step | Analogue used | Derived duration | Has a measured analogue? |
|---|---|---|---|
| Push, version-branch merge, tag | mechanical git ops | ~instant | n/a (no analogue needed) |
| Hygiene prune, live run | the dry run itself (13.8 min) — same classification pass, plus the actual delete/push commands | ~15-20 min (rough; the dry run never executes the deletes) | **partial** — only the dry-run half is measured |
| Lows integration: rebase 3 partitions to 1 candidate | "an integration" (~16.5 min) | ~16.5 min **floor** (spans far more files/branches — 41 lows-writer branches across 3 partitions — than either rework precedent) | partial, floor only |
| Lows integration: one chain run | "a chain run" (~8-10 min) | ~8-10 min | **yes** |
| Lows integration: one fresh verifier | — | — | **NO — no isolated verifier-alone duration exists anywhere in the ledger; every verifier step is bundled into a batch/round total** |
| GUI round on the rig | — | — | **NO — the GUI round has never run this entire release (deferred operator_attended every round, 11 needs_gui ids untouched)** |
| Docs promotion (per doc) | docs/CHANGELOG single-agent tasks, general range | ~7-11 min per doc | partial — no doc-promotion-specific run on record; Stage D's own refresh (`7c685b9f`) has no measured figure captured |
| Clean-profile production bundle | — | — | **NO — the one rehearsal (`c584f545`/`64e9470e`) has no measured figure on record** |
| r15-rc2 tag | mechanical | ~instant | n/a |
| Final adversarial pass | "a chain run" (~8-10 min) + "a battery" (~90 min) + possibly "a fix round" (31 min) if it finds a new c/h | ~100 min clean, ~131 min if one fix round is needed | **NO direct analogue for the adversarial-sample generation/run itself** — this composes the chain+battery infrastructure the pass rides on, not the pass's own authored-scenario timing |
| r15-launch tag | mechanical | ~instant | n/a |

**Rough total, excluding the two fully-unmeasured steps (GUI round, bundle
rehearsal):** hygiene live-run (~0.3 h) + lows rebase+chain (~0.4 h, verifier
duration still unknown) + docs promotion for an estimated 3-5 docs (~0.5-1 h)
+ final adversarial pass (~1.7-2.2 h) ≈ **roughly 3-4 hours of measured-
analogue-backed work**, on top of two steps (GUI round, clean-profile bundle)
that have never been timed this release and one sub-step (the lows fresh
verifier) with no standalone timing anywhere in the ledger.

## (c) What is held, and where

| Branch | Sha | What it is | May / may not, before the tag |
|---|---|---|---|
| `worktree-agent-r15-version-0.9.0-r2` | `6c7c5bbf` | 0.9.0 version bump: 5 version sources + `Cargo.lock` + README + marketplace test; also carries the pre-authorised DOCS-026 CLAUDE.md capture-path fold-in (`/tmp/rigcap.py` pointer) for the post-tag rebase | May sit untouched, be read. **May not merge before the tag** — merges strictly AFTER it |
| `worktree-agent-backlog-0.9.1` | `a3c7a384` | 0.9.1 backlog draft (235 lines): 28 open mediums w/4 regressions flagged, 35 tier-4 rows w/DECISIONS pointers, 11 needs_gui, BL-03/BL-18, a lows-section placeholder | May sit untouched, be read/cited. **May not merge before the tag** — merges AT the tag |
| `feature/bl-03-reasons-about-you` | `4ea397d1` | BL-03 docs only (4 files/598 lines under `docs/redesign/features/bl-03/`), nothing else in the diff | May sit untouched. **May never merge into 004 this release** — first 0.9.1 feature; only its sha is recorded into the backlog at the tag |
| `worktree-agent-hygiene-plan-rc1` | `91f9a30c` (merged `2ad36910`) | Hygiene prune plan, DRY RUN ONLY: `r15/hygiene/PRUNE_PLAN_rc1.{md,json}` — 59 worktrees MERGED/20 KEEP/1 UNPUSHED-LIVE, 390 local branches MERGED/57 KEEP/5 SUPERSEDED, 227 origin branches MERGED/57 KEEP/7 SUPERSEDED | Already merged (docs-only, nothing deleted). The prune itself (the actual deletes) **may not run before the tag, and never while a gate/recheck is running** — the lead's own hands, post-tag only |
| `worktree-agent-lows-P1-int-4c6dfe8` / `-P2-int-4c6dfe8` / `-P3-int-4c6dfe8` | `dbe5fe4f` / `78220d0c` / `f9da207a` | The three lows pre-integration candidates, each rebased onto `4c6dfe8c` with an Opus diff review + conflict/risk map + claimed-tests list | May sit untouched, be read for their conflict/risk maps. **May not merge individually or onto `4c6dfe8c`** — DECISIONS §6.2 requires all three rebased onto the rc1 TAG (not `4c6dfe8c`) as ONE combined candidate, with one chain run and one fresh verifier, only after the tag lands |

## (d) Operator-pending items

**DECISIONS §4.22 — R15-LEAD-116 (high) — RESOLVED, option (d).** The operator's answer is above in (a); the options below are kept as history.

**Original framing:** An explicit `.BO` pin on a
same-ticker, different-company name (FOCUS.BO = Focus Business Solution,
BSE 543312) still serves the NSE company's rows in all five disclosure
lanes, even after the LEAD-059 fix anchored the unpinned case on the
resolved company. Six of 2,657 shared NSE/BSE tickers collide this way
(FOCUS, KALYANI, RAJPUTANA, MAL, SEL, ZEAL). Found by the LEAD-059 fix
round's own fresh verifier, so it has had no fix round of its own — the
lead reads "exactly one bounded fix round" (§6.1) as a ceiling for the gate,
not a per-entry allowance, and did not reopen it unilaterally.

- **(a)** authorise one more bounded writer pass on this single entry before
  the tag (estimated one writer + one integrator + one fresh verifier, about
  an hour) — **recommended**.
- **(b)** tag `r15-rc1` with LEAD-116 open, named in the release notes and
  `CURRENT_STATE.md` as a known open high at 0.9.0, first 0.9.1 item.
- **(c)** re-rate it medium (the response is labelled, no wrong-entity row
  is presented as the BSE company's) — **not recommended**; the register
  rates wrong-entity data high everywhere else (LEAD-044, LEAD-059 itself).

**The four reopened medium regressions** (own stated repro failed again at
round 5, filed as new entries per gate rule change 1, never reopening the
original): R15-CODE-PLATFORM-072 (the data-source catalog in `marketplace.ts`
is hand-maintained and has drifted from `provider_registry`), R15-LIFECYCLE-024
(no schema-version marker or pre-upgrade backup on any of the 8 SQLite
stores), R15-RESEARCH-022 (a keyless search engine's CAPTCHA/block page
reads as a healthy empty result and resets its own circuit breaker),
R15-AGENT-027 (`humanize()` has no 400/413 branch, so context-overflow and
bad-key errors get the wrong next-step text). All four are open at 0.9.0 and
go into the first 0.9.1 batch.

**The rest of the first 0.9.1 batch:** 28 open mediums + 248 open lows
(`docs/redesign/BACKLOG_0.9.1.md` §2/§3, register sha `dfdb882b`). 215+ of
the 248 lows already have fixes pushed on the 41 lows-writer branches
awaiting the post-tag combined-candidate integration described in (c) above.

## (e) Resume prompt (paste verbatim)

```
Resume the VYSTED TERMINAL R15 rc1 tag window in ~/Documents/dev/vysted-terminal,
branch 004-r4-experience-rebuild. The operator may be away; bypass-permissions on;
never end on a question you can answer from disk.

Read first, in order:
1. docs/redesign/verification/vysted-r15-run-state.md — HEADER block (lines 1-25)
   + the newest entries in the IN-FLIGHT LEDGER.
2. docs/redesign/DECISIONS_FOR_OPERATOR.md sections 6.1, 6.2, 4.22.
3. docs/redesign/verification/r15/handover/HANDOVER_rc1.md (this file) and
   HEADER_DRAFT_rc1.md.
4. docs/redesign/verification/vysted-r15-register.json / .md (the register).

Standing rules to re-read BY NAME before acting on them (never assume their
content from memory or from this prompt): R15_BRIEF.md, the gate-rule-change
and operator-decisions brief addenda named in the run-state header,
R15_BRIEF_PROCESS_NOTE_1.md (the in-flight ledger convention),
R15_BRIEF_PROCESS_NOTE_2.md (the post-compaction re-read rule).

Next concrete step: the 4.22 outcome is option (d), already applied (rc1 tagged at
949c3c9f); run the lows integration with the LEAD-116 fix first. The (a)/(b)/(c)
list below is the pre-answer history.

Next concrete step, by the DECISIONS 4.22 outcome (history):
- (a) one more bounded writer pass: launch a single writer -> integrator ->
  fresh-verifier chain on R15-LEAD-116 (the FOCUS.BO explicit-pin case) from
  794bc68f, same shape as the round-5 fix round (r15/tooling/rc1-r5-fix.js is
  the precedent script); then re-run rc1-gate.js's heavy + battery repro-check
  lanes (lane selection at 2d43d5c2) on that merge; tag r15-rc1 once clean.
- (b) tag with it open: confirm open critical/high is 0 apart from LEAD-116,
  tag r15-rc1 at 949c3c9f (or the recheck's candidate sha once its battery
  lane returns clean), list LEAD-116 in the release notes and CURRENT_STATE
  as a known open high, file it as the first line of the 0.9.1 backlog.
- (c) re-rate medium: not recommended by the prior lead; if chosen anyway,
  re-rate LEAD-116 in the register with a rationale note, recompute open
  critical/high (should reach 0), then tag as in (b).

Whichever outcome: once tagged, follow the post-tag order in DECISIONS §6.2
(mirrored in HEADER_DRAFT_rc1.md's Next-action block) verbatim and in
sequence — do not reorder it, and do not merge any held branch out of turn.
```

## (f) `<<recheck-pending>>` markers to fill when the recheck returns

Exactly these figures, nowhere else, once the round-5-recheck's battery lane
and collate step finish (they were still running when this handover was
written):

- **Battery result** — holds / ci_pinned / regressed counts across all 25
  shards (`FILLED 27 Sep 21:3x IST: 316 holds / 79 ci_pinned / 0 regressed over 395 fixed ids in 90 sets, 25 shards`; chain and Gate 8
  are already green on disk and do not need refilling).
- **`MISSING_RAW.json` count** — should be 0 per the hardened round-4/5
  script; fill the actual number (`FILLED: 0 actually missing — the collator listed 11 as `no_file`, all 11 have suffixed raw files under their set directory (see `r15/rc1/round-5-recheck/RECHECK_READING.md`)`).
- **The recheck's own total measured wall-clock** — launch 18:33 IST through
  the collate step's finish (`FILLED: 167 min, 18:33 to about 21:20 IST, 30 agents, 5.35M tokens`); this also
  becomes the new, more accurate "a chain run" / "a battery" analogue for
  section (b) above once it lands, superseding the round-5 decomposition
  figures used there.
- **Hosted spend for the recheck** — OpenAI-direct + OpenRouter ledger rows
  tagged to this run (`FILLED: USD 0.00 hosted (six free local-model rows)`).
- **The tag sha itself** — `949c3c9f` (annotated tag object `0e0852e9`), filled in
  `HEADER_DRAFT_rc1.md`'s `Newest tag:` block.
