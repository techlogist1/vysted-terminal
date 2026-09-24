<!-- CRITIC of OPERATOR_BRIEFING.draft.md at f444479031d7d493b7955b9af041d18e7c7a40cc -->

# Critic — OPERATOR_BRIEFING.draft.md (Fable, cold read)

Verdict: **REVISE**. The register numbers are copied correctly, but the draft misreads
what the register at this sha represents: batch 9 merged (`6b702305`, an ancestor) and its
29 certifications are NOT yet applied — commit `a288397` applied batch 8's verdicts, not
batch 9's. The draft says the opposite, then labels 25 batch-9-certified mediums (and one
high) "not yet attempted / needs you". Two evidence rows are declared "present at this sha"
but are not in any commit. Ten findings: 7 wrong, 2 stale, 1 missing.

## Findings

1. **wrong** — §2, lines 65-68 ("Register adjudication … commit `a288397` folded batches 8
   and 9 into … the register"). Evidence: `git show a288397` body: "Applies batch-8's
   VERDICTS.json (39 -> fixed @ 68bb7aa4, LIFECYCLE-001 -> needs_gui …)"; run-state
   (`docs/redesign/verification/vysted-r15-run-state.md` at the sha) line 26: "Adjudicator
   [batch 10] applies `r15/stage-c/batch-9/VERDICTS.json` (29 fixed @ 6b702305, UI-083/UI-050
   needs_gui, 14 open with reason)"; line 29: "Applied batch-8 `VERDICTS.json`". Register at
   the sha: all 29 ids in batch-9 `VERDICTS.json.certified` still `status: open`. Fix: "commit
   `a288397` (the batch-9 workflow's adjudicator) applied **batch 8's** verdicts and registered
   LEAD-021/022/023; **batch 9's 29 certifications are not in the register at this sha** — the
   batch-10 adjudicator applies them. So every §3 count is one batch behind the code."

2. **wrong** — §3, lines 112-142 ("Not yet attempted (queued for batch 10 or later)") and
   lines 108-110 (UI-053 / UI-015 / RESEARCH-027 as batch-8 residuals). Evidence:
   `docs/redesign/verification/r15/stage-c/batch-9/VERDICTS.json` at the sha, key `certified`
   (29 ids), intersected with the draft's list: AGENT-046, CODE-AGENT-005, CODE-AGENT-008,
   CODE-FRONTEND-016, CROSS-PLATFORM-002, CROSS-PLATFORM-004, DATA-052, DATA-062, DATA-065,
   DATA-066, DATA-069, DATA-073, DATA-092, DATA-094, LEAD-016, LEAD-023, LIFECYCLE-018,
   LIFECYCLE-021, LIFECYCLE-025, UI-016, UI-033, UI-051, UI-052, UI-058, UI-086 (25) are
   certified fixed at merge `6b702305` (ancestor of the sha; `VERDICTS.md:47` "AGENT-046:
   certified", `:50` "CODE-AGENT-008: certified", `:55` "RESEARCH-027: certified"); UI-053,
   UI-015, RESEARCH-027 are certified too (not "batch-8 residuals"); UI-050/UI-083 are
   `needs_gui` in the same file. Fix: split the 114 into (a) 28 mediums certified by batch 9 and
   awaiting the batch-10 adjudication (list them), (b) the 14 batch-9 not-certified residuals
   with reasons (lines 99-107 are right), (c) the ~72 genuinely unattempted, regrouped by
   subsystem after removing (a). Drop UI-053/UI-015/RESEARCH-027 from the residual list.

3. **stale** — §1, line 23 ("a tenth is in flight on the ~114 open mediums"). Evidence:
   run-state line 9: "Mediums ~85 open once the batch-10 adjudicator applies batch-9's 29
   (114 − 29)"; line 26: "planner takes the ~85 remaining mediums". Fix: "a tenth is in
   flight on the ~85 mediums left once batch 9's 29 certifications are applied (the register
   still shows 114)".

4. **wrong** — §3, lines 87-92 ("Open high (3) — none queued for a normal fix batch; each
   needs you" … "see open_questions"). Evidence: batch-9 `VERDICTS.json.certified` contains
   `R15-LEAD-022`; `VERDICTS.md:109` "LEAD-022: certified."; run-state line 9 "LEAD-022 fixed
   in batch 9 pending the batch-10 adjudication". LEAD-022 needs nobody. There is no
   "open_questions" section in the draft. Fix: "Open high (3 in the register, 2 real):
   AGENT-007/017 need you (§2.1); LEAD-022 is certified fixed in batch 9 (`6b702305`) and flips
   at the batch-10 adjudication." Delete the "see open_questions" pointer.

5. **wrong** — §6, line 258 ("All paths verified present at this sha via `git cat-file -e`")
   against rows 262 and 273. Evidence: `git cat-file -e f4444790:docs/redesign/verification/r15/stage-d`
   → missing (untracked; `git status` shows `?? docs/redesign/verification/r15/stage-d/`);
   `.gitignore:65` at the sha: `docs/redesign/verification/R15_BRIEF*.md` — the brief is
   git-ignored and in no commit (`git ls-tree` of `docs/redesign/verification/` lists no
   R15_BRIEF file). Fix: row 262 → "on disk only, git-ignored (`.gitignore:65`), never in a
   commit"; row 273 → "untracked at this sha; the collator commits it"; soften line 258 to
   "except the two rows marked".

6. **wrong** — §5, line 252 (`r15/tooling/rc1-gate.js`). Evidence: `git cat-file -e
   f4444790:r15/tooling/rc1-gate.js` → missing; the file is
   `docs/redesign/verification/r15/tooling/rc1-gate.js` (present). The run-state uses the
   `r15/` shorthand under a declared evidence root; the draft never declares one. Fix: write
   the full path (or declare the shorthand once in §6).

7. **wrong** — §5, lines 252-254 (the rc1 gate workflow "… tags `r15-rc1`, pushes"). Evidence:
   `docs/redesign/verification/r15/tooling/rc1-gate.js` at the sha has no `git tag` / `git
   push` site (grep `tag|push`: only `q.push`, `blockers.push`, and `:11` "Verify … gate
   sheet, tag sha", `:349` "WRITE docs/redesign/verification/R15_GATE_RC1.md", `:352` logs
   `verifier.tag_sha`); run-state line 16 puts "tag `r15-rc1` + push" after the verifier as
   the lead's step; line 28 "DONE looks like: … verdict PASS + tag `r15-rc1` on origin". Fix:
   "… ends in `R15_GATE_RC1.md` naming a tag sha; the lead tags `r15-rc1` and pushes."

8. **wrong** — §4 heading "things only you can do" applied to the six `needs_gui` ids (lines
   209-230), contradicted by §5 line 253 ("drives `needs_gui` items through the GUI rig").
   Evidence: run-state line 16: "GUI round for needs_gui (UI-009, UI-025, UI-022,
   CODE-AGENT-001, LIFECYCLE-008) when HIDIdleTime ≥ 1500 s"; `rc1-gate.js:303` "run pnpm
   tauri build --debug … the packaged tauri:// origin R15-CODE-AGENT-001 needs"; `:347` "GUI
   round, as claimed … deferred …". These are rig-attempted unattended; only what the rig
   cannot do falls to the operator. Fix: retitle the block "needs_gui (6) — the rc1 gate's GUI
   round tries these unattended on a `--debug` package when the Mac is idle ≥ 1500 s; yours
   only if it defers them", and mark the two the rig plausibly cannot do: LIFECYCLE-001
   (packaged cold launch **after a reboot**, register note) and UI-022 (native event
   injection, register note).

9. **stale** — §4 §3.3, lines 204-207 ("no AUTO stop control … (`R15-CODE-FRONTEND-008`)").
   Evidence: register at the sha, `R15-CODE-FRONTEND-008.status == "fixed"`, note: "The
   order-kind predicate … moot … Core finding stays open: AUTO autonomy still auto-applies
   note/portfolio/set_region writes …". The operator following the id finds a closed entry
   whose note says the opposite. (`docs/SAFETY_ARCHITECTURE.md:125` and
   `DECISIONS_FOR_OPERATOR.md:213` still say "tracked as".) Fix: "(`R15-CODE-FRONTEND-008` —
   register status `fixed` for the order predicate; its note says the core gap stays open, so
   the id is not a live tracker)".

10. **missing** — the three `<!-- VERIFY -->` markers (lines 63, 148, 270) ask questions the
    evidence at this sha already answers, and a promoted briefing cannot carry them. Evidence:
    register at the sha: UI-083/UI-050 `open` (batch-9 flip not applied, see 1); run-state line
    26: the Tier-4 reclassification (DOCS-003, AGENT-064, CODE-PLATFORM-015/071/010/073,
    DOCS-015/002, CODE-FRONTEND-013, UI-044, CROSS-PLATFORM-001 → `blocked_tier4`) is batch 10's
    plan, register shows all 11 `open`; `git cat-file -e
    f4444790:docs/redesign/verification/r15/stage-c/batch-10` → missing. Fix: replace each
    marker with the stated fact ("not applied at this sha; lands with batch 10's
    adjudication" / "batch-10 dir absent at this sha") and keep one line in the header
    telling the lead which three facts to re-read at rc2.

## Checked and correct

- Line 1 is exactly `<!-- DRAFT at f444479031d7d493b7955b9af041d18e7c7a40cc by the Stage D docs wave; refresh before rc2 -->`.
- Versions: `package.json:3`, `src-tauri/Cargo.toml:3`, `src-tauri/tauri.conf.json:4`,
  `sidecar/app.py:327`, `src/lib/plugin-bootstrap.ts:37`, `src-tauri/Cargo.lock:5487` all
  `0.8.0` at the sha; 0.9.0 only under `r15/census/` (FACTS §versions).
- Register counts (887 raw / 626 / 76 rejections; 16/112/279/219; the severity × status
  table; status totals 279/322/6/14/4/1; open-high ids; needs_gui 6; blocked_tier4
  RELEASE-001..004) equal the register JSON and FACTS. The 114 open-medium ids in §3 are the
  register's 114 exactly (scripted set-compare: no extras, no omissions) — only their
  "attempted" labelling is wrong (finding 2). The 14 batch-9 not-certified reasons (lines
  99-107) match `VERDICTS.json.not_certified` and the run-state header.
- Batch commits `a122dbf6`, `0c63d465`, `806a90ca`, `c81d879b`, `dcbe7bae`, `1574ed8e`,
  `5e147317`, `e81c9e7c`, `68bb7aa4`, `6b702305`, `a288397`, `043850c`, `7a1cd8f` are all
  ancestors of the sha; per-batch tallies match FACTS §stage-c (batch-6 `VERDICTS.md:64`
  "## Certified (21)"; batch-9 `VERDICTS.md:10` "29 certified, 2 need GUI (UI-083, UI-050),
  14 not certified"). `r13-bedrock` newest r13-/r15- tag; `v0.6.0`..`v0.8.0` exist.
- Lows: `LOWS_TRIAGE.md:7-10` 5 / 199 / 1 / 1, `:243` 206 unique ids; register 205 open + 10
  fixed + 4 removed = 219.
- §4 decisions text matches `DECISIONS_FOR_OPERATOR.md` at the sha: `:121-122` 2507 / 1504 /
  13; `:127-129` 900 s; `:136,142-143` "damaged" + `signingIdentity: "-"`; `:151,158`
  `tauri-action` / `createUpdaterArtifacts` / `TAURI_SIGNING_PRIVATE_KEY` (env-var name only,
  no value anywhere); `:181-184` `audit_log.db` + `broker:<id>:…` key names; `:200-203`
  DisclaimerFlow licence line / no kill-switch line; `:209-213` 10-min TTL; `:217-225`
  plugin.ts + `COMMERCIAL_LICENSE.md:36-48`. Code: `types/plugin.ts:28` `"trading-bot"`;
  `COMMERCIAL_LICENSE.md:36-48` is the broker/trading-loss clause; `sidecar/services/
  action_ledger.py:25` `TTL_SECONDS = 600.0`; `docs/SAFETY_ARCHITECTURE.md:114-125` accepted
  gaps; `src/modules/safety/DisclaimerFlow.tsx:32,35`; `types/proposed-change.ts:35`
  `autoApplies`; `sidecar/services/llm/ollama.py:132` `context_window`; `7a1cd8f` diff reads
  `raw.get("instruments", [])`.
- Six needs_gui descriptions condense the register `note` fields faithfully.
- Keychain paragraph matches `docs/redesign/KEYCHAIN_DEV_SIGNING.md:3-10,25-27` (dev-keystore,
  `0600`, one migration dialog, 2026-06-11). Observation, not a finding: `CLAUDE.md:270` at the
  sha still describes the superseded self-signed-cert flow — a candidate for
  `CLAUDE_MD_PROPOSAL.md`, which the lead may want the briefing to mention.
- Commands: `pnpm tauri:dev` → `pnpm tauri:mcp` → `tauri dev --features dev-tools`
  (`package.json:22-23`); `pnpm ci-local` exists (`:20`); no other command is instructed.
  Workflows `build/lint/test.yml`: `on: push: branches: [main]` + `pull_request`, 3-OS matrix.
- Product facts: trading described only as removed (D81) with leftovers to purge; licence split
  stated correctly; 0.9.0 as target, not written; packaged build deferred to the lead. No key,
  token or keystore content (pattern scan of the draft: none).
- Evidence rows other than 262/273: all 24 paths (`cat-file -e`) present at the sha, batch-2..9
  `PLAN.md` + `VERDICTS.md` included.
