<!-- CRITIC of OPERATOR_BRIEFING.draft.md at 4d893147def983623de681effd1bfbae2e7441c5 -->

# Critic — OPERATOR_BRIEFING.draft.md (Opus, cold read)

**Verdict: REVISE.** 15 findings: 13 wrong, 1 missing, 1 stale, 0 unverifiable. Six of them would mislead the operator or make a step fail: #1, #2, #3, #4, #6 and #7. The worst is #2. The fail-safe paragraph brings back, in other words, the exact claim that the operator's sign-off struck from the LEAD-030 wording.

All reads were made at the sha with `git show 4d893147…:<path>` / `git cat-file -e` / `git grep`. Line numbers are the draft's.

## Findings

1. **wrong** — §6 table line 212 + line 220. The draft says "batch-24 only `PLAN.md` at this sha" and "All paths above were confirmed present at this sha with `git cat-file -e`".
   Evidence: `git cat-file -e 4d893147…:docs/redesign/verification/r15/stage-c/batch-24/PLAN.md` → MISSING, and so is `batch-24/VERDICTS.md`. batch-24 exists only as an untracked working-tree dir. FACTS.md:151 says "no `batch-24` tracked yet at this sha".
   Fix: line 212 → "`r15/stage-c/batch-<2..23>/` (`PLAN.md`, `VERDICTS.md`; batch-23 also `LEAD-030-CONCURRENCE.md`, `DISPOSITION-CONCURRENCE.md`); batch-24 has no tracked dir at this sha". Line 220 → "…except the R15_BRIEF row (deliberately unread) and batch-24 (untracked at this sha)".

2. **wrong** — §3 "Fail-safe (why this ships)" paragraph, lines 113-114. The draft says "ok-subject figures are grounded by `sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause` (rules 1/2a/2b/2c/3…)". That restates the clause the sign-off struck. It also contradicts the LEAD-037 wording six lines above it ("a figure the agent states for a company whose data call succeeded is not checked against that result at all").
   Evidence:
   - `sidecar/services/agent_runtime.py:2378-2383` fires the fail-safe only `if ctx.errored and (attached is None or attached not in ctx.ok_subjects)`. An ungrounded figure attached to an ok subject falls through to `return None` at `:2393`, so it streams.
   - FACTS.md:177: "the guard never checks a figure for a subject whose call succeeded".
   - run-state `vysted-r15-run-state.md:16`: "`_judge_clause` returns None".
   Fix: replace the clause with "figure grounding by provenance (`sidecar/services/figure_grounding.py` + `agent_runtime._judge_clause`, `agent_runtime.py:2321`, rules 1/2a/2b/2c/3) replaces an ungrounded figure tied to an errored or never-called subject with an honest 'returned no data' note. The rule-2c fail-safe (`agent_runtime.py:2378-2383`) fires only in a turn with an errored tool call. A figure for a subject whose call succeeded is not checked (LEAD-037)."

3. **wrong** — §4 "Signing and release", line 165. The draft says "macOS minimum (`signingIdentity: "-"`) is already set".
   Evidence: `git show 4d893147…:src-tauri/tauri.conf.json | grep -i signingIdentity` → 0 hits; the only bundle flag present is `:45 "createUpdaterArtifacts": false`. DECISIONS_FOR_OPERATOR.md §2.8 (the "Smallest unblock" bullet) says that setting it "is still a `tauri.conf.json` edit, so still needs your sign-off even for that minimal step".
   Fix: "the macOS minimum, `bundle.macOS.signingIdentity: "-"` (ad-hoc seal: 'damaged' becomes Open-Anyway), is NOT set. It is a one-line Tier-1 `tauri.conf.json` edit awaiting your sign-off."

4. **wrong** — §2 line 60 (and line 17). The draft says "**Version branch** (`c8d807a6`, workflow `wf_1d24a3f2-c0e`): 0.9.0 everywhere…".
   Evidence: `git log -1 --oneline c8d807a6` → "docs(r15): version branch launched (wf_1d24a3f2-c0e); bundle-rehearsal watcher armed". That is a run-state note on 004, not the bump. The bump lives on branch `worktree-agent-r15-version-0.9.0` (FACTS.md:29; run-state:79 "IN-FLIGHT … VERSION BRANCH … on `worktree-agent-r15-version-0.9.0` from `1db862d0`"). At this sha the branch was launched, not verified ready.
   Fix: "**Version branch** `worktree-agent-r15-version-0.9.0` (launched `c8d807a6`, run `wf_1d24a3f2-c0e`; branch head confirmed at the tag): 0.9.0 in every version source plus the single `CLAUDE.md` commit…". At line 17, "is prepared" → "is prepared on its own branch (head confirmed at the tag)".

5. **wrong** — §2 table, rows 20 and 21, "Not certified" column.
   Evidence: batch-20 `VERDICTS.md` has two "not certified" headings, `## R15-LEAD-030` and `## R15-LEAD-036`. batch-21 `VERDICTS.md:6-7` reads "R15-LEAD-030 is not certified a seventh time, and R15-LEAD-035 and R15-LEAD-036 are not certified" (three entries).
   Fix: row 20 → "2 (LEAD-030, 6th time; LEAD-036)"; row 21 → "3 (LEAD-030, 7th; LEAD-035; LEAD-036)".

6. **wrong** — §7 item 1, lines 227-228. The section is headed "What R15 decided on its own", yet item 1 lists the three-strikes stop rule as R15's own standing policy.
   Evidence: run-state `vysted-r15-run-state.md:13`, inside the operator's "PACING CHANGE 4 + TIER-4 SIGN-OFF (operator, 04:15 IST Sat 26 Sep…)" block: "NEW RULE: any register entry that fails certification THREE times in this run stops and goes to DECISIONS for the operator, whatever its severity". This is the operator's own instruction, and a cold-reading operator would be told he should "revisit" his own rule.
   Fix: take it out of §7, or reword it as "Your three-strikes rule (pacing change 4) was applied to LEAD-030 (eight rounds; the lead's earlier stop rule had already fired) and LEAD-035 (three)…".

7. **wrong** — §5 "The local-model lane", line 194. The draft gives `scripts/r15/vy.py invoke --provider ollama --model llama3.1:8b`, which fails as written.
   Evidence: `scripts/r15/vy.py:276-283`: the `invoke` subparser requires the positionals `agent` and `prompt`, plus `--provider` (required). The `--port` default is 52152 (`:305`).
   Fix: `python3 scripts/r15/vy.py invoke <agent> "<prompt>" --provider ollama --model llama3.1:8b --port <isolated sidecar port>`.

8. **wrong** (low) — §5 line 189-190. The draft says "The three sidecars must exist first: `pnpm sidecars:build` (force-rebuilds all three…)", which implies a required manual pre-step.
   Evidence: `src-tauri/tauri.conf.json:9` is `"beforeDevCommand": "node scripts/ensure-all-sidecars.mjs && pnpm dev"`. `pnpm tauri:dev` therefore builds any missing or stale sidecar itself, and `sidecars:build` = `node scripts/ensure-all-sidecars.mjs --force` (FACTS.md:61) only forces a full rebuild.
   Fix: "`pnpm tauri:dev` builds any missing or stale sidecar itself (its `beforeDevCommand` runs `scripts/ensure-all-sidecars.mjs`, then `pnpm dev`); `pnpm sidecars:build` forces a rebuild of all three."

9. **wrong** (low) — §5 line 191 + §7 item 5, lines 236-237. The draft says the packaged bundle is "a Stage D step, rehearsed on the heavy lane beside batch 24". That reads as concurrent with batch 24 and as the proof itself.
   Evidence: run-state:13 says the rehearsal runs "on the heavy lane whenever batch-24's chain is not using it", and "then the bundle from a clean profile on the integrated head → r15-rc2". run-state:80 says "BUNDLE REHEARSAL, QUEUED". The product rule is that the macOS production build is proven from a clean profile later, by the lead.
   Fix: "A one-off rehearsal is queued for the heavy lane when batch 24 is not using it. The production bundle is proven from a clean profile by the lead on the integrated head, before `r15-rc2`. Not proven at this sha."

10. **wrong** (low) — §5 "Resume the run", lines 198-200. The draft chains "lows integration … → the GUI round … → the production bundle" as a sequence.
    Evidence: run-state:13 says "after the tag, in parallel: lows P1/P2/P3 serially … the GUI round as its own workflow on the rig …, docs promoted as results land; then the bundle from a clean profile on the integrated head → r15-rc2".
    Fix: "→ after the tag, in parallel: lows P1/P2/P3 (serially among themselves, one fresh verifier each, then the 5-item serial set) and the GUI round as its own workflow, docs promoted as results land → the production bundle from a clean profile on the integrated head → `r15-rc2` → …".

11. **wrong** (low) — §3 line 115: "`_NO_TOOL_CUE` list in `sidecar/services/planner.py` (~line 130, batch 21)".
    Evidence: `git show 4d893147…:sidecar/services/planner.py | grep -n _NO_TOOL_CUE` → `136:_NO_TOOL_CUE = re.compile(` and `212:    if _NO_TOOL_CUE.search(lowered):`.
    Fix: "(`planner.py:136`, batch 21)".

12. **stale** (low) — §3 "Lows", line 133: "`LEAD-031` (fixed batch 17) sits in no partition, closed at the next adjudication."
    Evidence: the register JSON at the sha has `R15-LEAD-031` as `('low', 'fixed', 'agent-tools')`. It is already closed and already counted among the 12 fixed lows.
    Fix: "`LEAD-031` (low, certified batch 17) is already `fixed` in the register and sits in no partition."

13. **missing** (low) — §4 "Money and provider lanes", line 147. §2.2 states the problem ("OrbStack not running → SearXNG down…") but not the unblock, and the check requires every operator-attended item to carry one.
    Evidence: DECISIONS_FOR_OPERATOR.md §2.2 (lines 85-89 at the sha): "**Recommendation:** start OrbStack before judging research."
    Fix: append "— start OrbStack before judging research (R15 never starts Docker)."

14. **wrong** (low) — §4 "Signing and release", line 164. The draft says "free SignPath OSS needs an OSI licence without commercial dual-licensing, which the relicense no longer qualifies for". The words "no longer" imply the project used to qualify.
    Evidence: https://signpath.org/terms.html reads "OSS License: The project must use an OSI-approved Open Source license without commercial dual-licensing for all components." The pre-relicense AGPL-3.0 + commercial dual licence (CLAUDE.md:57 at the sha) failed that condition too.
    Fix: "…which neither the old AGPL + commercial dual licence nor PolyForm Strict meets".

15. **wrong** (low) — §3 line 66. The draft says the severity × status table comes "from the register JSON's own `counts` field".
    Evidence: at the sha, `counts` = `{raw 887, entries 652, rejections 76, critical 16, high 116, medium 293, low 227}`, which has no status breakdown. The status columns can only come from `entries[].status`. Recomputed, they match the table cell for cell.
    Fix: "severity totals from the register JSON's `counts` field; the status split from its `entries[].status` (sums equal `counts`; never `register.py status`, which lags)".

## Checked and correct

- **Line 1 header:** the required string, exactly.
- **Banned words:** `grep -ci <banned word>` = 0 and `grep -ci low-latency` = 0. No key, token or keystore content (a secret-shape grep returned nothing). Trading appears only as removed (D81) or as operator leftovers, never as a feature.
- **Versions:** all five cited version lines read 0.8.0 (FACTS Versions table). The draft correctly says 0.9.0 lands with the version-branch merge right after `r15-rc1`, and never claims that `r15-rc1` exists. `git tag --merged 4d893147 --sort=-creatordate` → newest is `r13-bedrock`; `git tag -l 'r15*'` → none.
- **Licence split:** PolyForm Strict 1.0.0 + commercial; `types/plugin.ts` and the example plugin Apache-2.0; `0c63d465` = "chore(license): relicense core to PolyForm Strict 1.0.0".
- **Register table:** every cell equals the recompute from the JSON at the sha (c 16/0/0/0/0/0; h 105/0/4/6/1/0; m 258/1/5/15/9/5; l 12/205/2/4/4/0; total 391/206/11/25/14/5 = 652). The only open critical/high/medium entry is R15-LEAD-035 (medium, agent-tools).
- **blocked_tier4 grouping:** 25 ids, every row mapping matches the DECISIONS_FOR_OPERATOR headings (2.8-2.21, 3.3, 4.2-4.12). The four blocked lows are exactly §4.5-4.8 (CODE-PLATFORM-063, DOCS-008, DOCS-011, RELEASE-012).
- **needs_gui:** all 11 ids equal FACTS.md:127, with a severity split of 4 high, 5 medium and 2 low.
- **Known-limitation block:** LEAD-030 wording is the concurrence sentence (`batch-23/LEAD-030-CONCURRENCE.md:119-124`) with the struck clause removed. LEAD-035/037/038 wording is verbatim from FACTS.md:179-183. LEAD-035 is stated as pending batch-24 concurrence, "confirm at the tag", which is right because no `LEAD-035-CONCURRENCE.md` exists even in the working tree.
- **Fail-safe facts that are correct:** `types/proposed-change.ts:38-46` (`AUTO_APPLIED_KINDS` panel/chart/watchlist, `autoApplies`). `sidecar/tests/test_no_trading_surface.py` exists.
- **Cited commits:** all are ancestors of the sha, with matching subjects: `535307c8`, `4fd3cbfd` (141 live runs, per run-state:16), `1db862d0`, `043850c2` (gpt-5.x reasoning_effort 400), `a122dbf6` ("all 22 former routes 404", per run-state:159).
- **Batch table:** batches 2-19 tallies match each `VERDICTS.md` (batch 7: 1 not certified + 3 undelivered = 4). The first-parent merge shas match FACTS.md:150. Batches 22 and 23 are `block`; batch 22 was merged W1 only.
- **Gate round 1:** "FAIL, no tag" at 09:57 IST 25 Sep (run-state:9, :37). Round-2 parameters `skip_gui`/`max_fix_rounds 2` (run-state:13, :18).
- **Lows figures:** the lows writes (184 fixed / 7 could_not / 3 not_a_defect_proposed, run-state:18, :64) match. LOWS_TRIAGE (199 still reproducing / 5 already fixed / 1 not-a-defect / 1 duplicate) matches. PARTITION (P1 63 / P2 64 / P3 67, plus the inseparable serial set) matches.
- **Filing-watcher and DECISIONS rows:** the filing-watcher 11.3 GiB on a 16 GiB host is confirmed (run-state:43), with the folder name correctly withheld. DECISIONS_FOR_OPERATOR §2.1, §2.6/2.11, §2.9-2.10, §3.1-3.4, §4.1-4.8 are paraphrased accurately.
- **Licence docs:** `COMMERCIAL_LICENSE.md:36-48` carries the broker-relationship clause. `CLAUDE.md:57` still says "AGPL-3.0 + commercial dual license". `CLAUDE_MD_PROPOSAL.md:72-76` queues the fix.
- **Keychain and scans:** the `KEYCHAIN_DEV_SIGNING.md` dev-keystore description (`<app-data-dir>/dev-keystore.json`, 0600, git-ignored, one migration dialog) is accurate. `OPEN_QUESTIONS.md` §2 lists AGPL openbb/sec-edgar-mcp and LGPL frozendict. This refresh's SECRETS_SCAN shows real_or_unknown = 0.
- **Commands:** `pnpm tauri:dev` → `pnpm tauri:mcp` → `tauri dev --features dev-tools`; `pnpm dev` = vite; `pnpm sidecars:build`; `node scripts/smoke-test-sidecars.mjs`; `pnpm ci-local`. All exist at the sha (FACTS scripts block; `git cat-file -e`).
- **Evidence paths:** every other path in §6 exists at the sha (`git cat-file -e`).
