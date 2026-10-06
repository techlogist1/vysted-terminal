# Critic — OPERATOR_HANDOVER.draft.md

Reviewer: Opus, once, 07:00 IST Sat 26 Sep. Draft reviewed: `05f7e178` (writer: Sonnet). Task
head `6bc6d378`. The repo moved to `76842bd8` during review because of other agents' commits.
None of those commits changes a cited source line: the `6bc6d378..HEAD` diff touches only
run-state in-flight lines, specs, lows PREINT files and new Stage D gap drafts. Every source was
opened and checked. The eight sections are kept, and the draft was corrected in place.

## Verdict

**ready_to_promote**, with conditions. After the corrections below, every stated fact traces to a
file opened at this head. The remaining gaps are marked `unverified:` in the text. Before
promotion the lead must still:

- fill round 2's verdict and sha;
- pick a promotion target, because `STAGE_D_INDEX.md` lists none for this file.

## Corrections made (28)

**§1**
1. The "everything else open is a low or a `blocked_tier4`" claim was wrong. It left out 11
   `needs_gui` entries, 4 of them high. The status split was rewritten from the register JSON:
   391 fixed / 205 open / 26 blocked_tier4 / 11 needs_gui / 14 removed / 5 not_a_defect.
2. The paraphrase of the known-limitation class was replaced with the verbatim `FACTS.md` class
   sentence. The 26 Sep 04:15 IST sign-off is now attributed to `OPERATOR_BRIEFING.draft.md` §3,
   and LEAD-035 is kept distinct from the signed-off class.
3. Added the tag and gate state, with sources: no `r15-*` tag, round 1 FAIL, round 2 unverified.

**§2**
4. Item 6 named `llama3.1:8b` as "the keyless default local model". `README.draft.md` BYOK names
   `qwen2.5:7b` as the default. `llama3.1:8b` is what the run's live bars used, per briefing §5.
5. Items 6, 7 and 8 now use the verbatim `FACTS.md` wording for LEAD-030, LEAD-035 and LEAD-038.
   LEAD-030 keeps FACTS's own note on the struck clause.
6. Item 1 described a "panel no longer exists" action but cited `R15-CODE-FRONTEND-001`, whose
   defect is a named-workspace load rolling back later edits. The action now matches the register
   entry.
7. Item 12 cited `sidecar/services/yfinance_provider.py`. The register lists
   `sidecar/services/resolver.py`.
8. Item 13 called the FAST fundamentals drop "a named, accepted rc1 budget trade-off".
   `DECISIONS_FOR_OPERATOR.md` §4.1 says the lead recommends it and it is yours to decide.
9. Item 15 had unsourced example tickers (DHANBANK, JONJUA). They were cut.
10. Item 17 claimed a "thinly-traded scrip 52-week range" fix under `R15-DATA-035/036`. Those
    entries are BSE-bhavcopy defects (a poisoned trading day, and a per-day re-parse). The item
    was rewritten to match the register.
11. Item 19 cited "Gate 8 boundary re-proved at every rc" and "`OPERATOR_BRIEFING` §7's fail-safe
    framing". Neither is in the source. The item now cites briefing §2 (0 order routes, 22 former
    routes 404). The chat reply's wording is marked unverified.
12. Item 9: the interpretive line about the "removed order-attempt halt" was cut. The citation
    was tightened to `types/proposed-change.ts:38-42` plus DECISIONS §3.5.
13. Item 3: the "trendline … not duplicated or bled" detail was trimmed to what RELEASE_NOTES
    states.

**§3**
14. **Order fix.** The rc gate round-2 PASS item sat after step 1. The runbook checklist puts it
    before step 1, and it now does.
15. Step 1 used an invented two-line command block. The runbook has no command block for §1, so
    it now quotes the run-state MERGE PLAN note as the runbook does, including "(… 
    `scratchpad/claude-md-local.diff` keeps a copy)". Added a warning that `git restore CLAUDE.md`
    discards uncommitted `CLAUDE.md` edits.
16. The section was titled "operator-only" but presented lead steps (§0–§7) as the operator's.
    Each step now carries the runbook's "Who". Only §8, the licence contact and §9 are marked
    operator. Nothing says the run did or may do an operator-only action.
17. "Releases are tagged directly off `004-r4-experience-rebuild`" was unsourced. The runbook
    tags `<gated-sha>` and merges "into the release-candidate branch". The text was replaced.
18. The §9 DECISIONS quote was labelled verbatim but altered "this also unblocks 2.10" to
    "(§2.10)". The original text was restored. Both quotes now say the "Why Tier-4" paragraph is
    omitted.
19. `gh release create` used `<promoted-RELEASE_NOTES-path>`. It is now byte-identical to runbook
    §1b: `<promoted-path>`.
20. Added runbook checklist item 11 (rollback), which the draft had dropped, so the order is
    complete. Added the runbook's pre-tag CI-signal note.

**§4**
21. §4.1 was missing from the priority list. It is added as item 17.
22. §2.6 was filed as "closed". DECISIONS lists it under "Yours to decide" as a measured fact. It
    moved to the open list.
23. §3.3 was filed as "closed". DECISIONS §3 says §3.x are "yours to review or act on". It moved
    to the open list.
24. §2.11's commit count said "655+". §2.11 says 654 (655+ is §2.17's figure). Fixed.
25. §3.4 now includes its `CLAUDE.md` and `COMMERCIAL_LICENSE.md` bullets. §5.5 now includes
    option (b). §5.8 now separates the 41-file folder from the two tooling files.
26. §4.9, §4.11 and §4.12 are now grouped as signed off 26 Sep 04:15 IST, per briefing §3. The
    list covers every `###` section of DECISIONS_FOR_OPERATOR.md: 1.1–1.4, 2.1–2.21, 3.1–3.6,
    4.1–4.12 and 5.1–5.10, all checked against the heading index.

**§5–§8**
27. §5 claimed "Settings is the only UI surface that touches it". README says the frontend's
    keychain wrapper `src/lib/keychain.ts` is the only credentials path, and the text now says
    so. The line "deep research degrades to the keyless-fallback tier without it" conflated
    OpenRouter with the SearXNG tier and was cut. A wrong cross-reference ("§2.2 below") was
    fixed. The "run-state header line 4" citation was unsourced and was dropped.
28. Several fixes in §6, §7 and §8:
    - **§6:** "guided setup in Settings" was changed to the docstring's "guided 'Unlimited
      Research' flow". DOCKER_STATE is dated 23 Sep, and the current state is marked unverified.
    - **§7:** the draft attributed "(~11 h left)" to PID 22698. Run-state line 33 attaches it
      to 34805. The dead PID 47158 is now named. The "not executed" claim about `final-pass.js`
      now rests on its post-rc3 placement plus the empty `r15-*` tag list.
    - **§8:** "promoted at the rc1 tag, per this run's task brief" had no file source. The
      header line and the table now say that STAGE_D_INDEX lists no target. The full paths of
      the batch-23 and batch-24 extra files were added.

## Checks that passed as written

- Every public-button command matches the runbook byte for byte: §0 exports, `pnpm install
  --frozen-lockfile`, `pnpm ci-local`, `VYSTED_SKIP_DEV_SIGN=1 pnpm sidecars:build`,
  `node scripts/smoke-test-sidecars.mjs`, `VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build`, the tag and
  push block, and the `HOME=` launch line.
- The §2.8 blocked and smallest-unblock quote matches `DECISIONS_FOR_OPERATOR.md:135-144` exactly.
- Register statuses and severities are correct for FRONTEND-001, UI-009, UI-022, LEAD-022/030/
  035/038, DATA-007/035/036, LIFECYCLE-001/008 and AGENT-017/049, checked in the JSON.
- The version branch is unmerged at head: `git merge-base --is-ancestor 517da226 HEAD` fails.
- The SearXNG state machine, container name, loopback binding and daemon-down detail string match
  `searxng_manager.py`.
- No secret appears in the draft. The banned words are absent: a case-insensitive grep returns 0.

## Stays unverified (and what would verify it)

- The rc1 gate round-2 verdict and gated sha. Verified by: the round-2 `VERDICT.md` or
  `R15_GATE_RC1.md` once committed. The committed sheet still reads round 1 FAIL.
- Whether you land this branch on `main`, before or after tagging. Verified by: your decision;
  the runbook has no such step.
- The dmg name and signing state at the real candidate sha. Verified by: runbook §6 and §7 run at
  that sha. Only the `64e9470e` rehearsal exists.
- Which caffeinate process is alive now. Verified by: `pgrep -fl caffeinate`.
- The live Docker/OrbStack state. Verified by: `orb status`. The recorded state dates from 23 Sep.
- OpenRouter and DeepSeek balances. They live in the git-ignored `r15/local/BUDGET.md`, which is
  outside this lane by rule.
- Whether the UI surfaces the Docker-down state. This is an open census item in DECISIONS §2.2.
- The exact chat reply to a trade request (item 19). Verified by: a live agent run, which is
  off-lane.
- Whether LEAD-035's wording is final. Verified by: your choice of (a) or (b) under §4.10.

## Promotion readiness

The draft is ready once the lead has:

1. filled round 2's result and sha into §1 and §3;
2. chosen a promotion target and, if needed, added it to `STAGE_D_INDEX.md`;
3. stripped line 1 and everything from `<!-- critic-footer -->` down, per the index convention.

No structural rewrite is needed.
