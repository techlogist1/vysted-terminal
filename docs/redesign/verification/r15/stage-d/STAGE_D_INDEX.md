<!-- DRAFT at 4d893147def983623de681effd1bfbae2e7441c5 by the Stage D docs wave; refresh before rc2 -->

# Stage D index

- sha: `4d893147def983623de681effd1bfbae2e7441c5`
- mode: refresh
- cap: 6
- generated (UTC): Fri Sep 25 23:23:37 UTC 2026

## Files

| File | Lane | Status | Critic findings | Open questions for the lead |
|---|---|---|---|---|
| `README.draft.md` | draft | REVISED | 7 (wrong 2, missing 4, stale 1, unverifiable 0) — [critic/README.md](critic/README.md) | Release pipeline / code-signing still `blocked_tier4` at this sha (R15-RELEASE-001/002/003/004/012) — download-section fill marker stays open until a signed asset exists at rc2. Version bump to 0.9.0 has not landed at this sha (all 6 version sources still read 0.8.0, unchanged since f4444790) — reprint as 0.9.0 only after the version branch merges post-tag. |
| `RELEASE_RUNBOOK.draft.md` | draft | REVISED | 11 (wrong 5, missing 3, stale 2, unverifiable 1) — [critic/RELEASE_RUNBOOK.md](critic/RELEASE_RUNBOOK.md) | Whether the operator keeps a locally-built prior .dmg/.app for real rollback (§11, VERIFY). Exact dmg filename pattern from tauri build not directly observed this wave (§6, VERIFY). §4/§5 build/smoke `<!-- fill at rc2 -->` markers unchanged — no logged run at this sha exists yet. Post-bump git-grep residual count (93) not confirmed against the actual bump commit. |
| `OPERATOR_BRIEFING.draft.md` | draft | REVISED | 15 (wrong 13, missing 1, stale 1, unverifiable 0) — [critic/OPERATOR_BRIEFING.md](critic/OPERATOR_BRIEFING.md) | Whether R15-LEAD-035's residual gets `blocked_tier4` on batch-24's verifier concurrence — no concurrence file existed at this sha; draft says "confirm at the tag". Exact newest tag / rc1 gate round-2 result — `<!-- fill at rc2 -->` in §1. Remaining run-state step completion — `<!-- fill at rc2 -->` in §5. Whether the filing-watcher groundwork folder moves under git-ignored `r15/local/` per the operator's one-line call (§4). |
| `RELEASE_NOTES.draft.md` | draft | REVISED | 13 (wrong 8, missing 3, stale 2, unverifiable 0) — [critic/RELEASE_NOTES.md](critic/RELEASE_NOTES.md) | Fixed-list completeness: only batches 2-9 plus 3 individually-verified entries (LEAD-031/033/034) are itemized; a full per-batch VERDICTS.md sweep is needed at rc2. CHANGELOG.md has no per-batch section for batches 18-22 at this sha — draft sourced those one-liners from each batch's VERDICTS.md header instead. rc1 gate round 1 FAILED against an earlier candidate sha and has not re-run to a verdict at this sha; round 2 launches once batch-24 merges — confirm final verdict/tag at the tag. R15-LEAD-035 still `open` at this sha (batch-24 in flight, only PLAN.md, no concurrence file) — confirm before promoting Known-limitations wording to rc2. batch-22's overall verdict was `block` with only its W1 lane merged (c155e5ad) — no Fixed-list claims made from it; confirm at rc2 whether any entries were actually certified. Version-bump branch `worktree-agent-r15-version-0.9.0` is prepared but unmerged — confirm it lands right after the r15-rc1 tag, not before. |
| `CURRENT_STATE.draft.md` + `BLOCKERS.draft.md` (+ `.diff` files) | draft | REVISED | 17 (wrong 11, missing 0, stale 6, unverifiable 0) — [critic/STATE.md](critic/STATE.md) | vitest/pytest/cargo-test pass counts not re-run at 4d89314 (VERIFY markers at CURRENT_STATE.draft.md:172, :990) — needs `pnpm ci-local` / `pytest` re-run before rc2. BLOCKERS.draft.md's "Open register entries" section points at the register JSON rather than fully reproducing 205 open-low entries by subsystem — confirm this satisfies the brief's literal ask before rc2 promotion. R15-LEAD-035 wording is still placeholder pending a batch-24 concurrence file that does not yet exist — needs a follow-up refresh once batch-24 lands. |
| `SECRETS_SCAN.md` + `SECRETS_SCAN.json` | scan | DONE | n/a (scan, no critic) | The 7 tree-at-sha "gone" hits vs. the prior f444479 scan (register.json/md, stage-d-docs.js) look like line-number shifts from file growth, not removed content — worth a byte-exact diff confirmation at rc1 tag time. class_breakdown counts come from this role's own path/keyword classifier (same taxonomy as prior scan) — a different classifier could bucket a couple of edge entries differently, though none flipped into real_or_unknown. |
| `DEPS_LICENCES.md` + `DEPS_LICENCES.json` | scan | DONE | n/a (scan, no critic) | None beyond the flagged copyleft/empty-licence rows themselves (see OPEN_QUESTIONS.md — Tier-4 for the operator). |
| `LICENCE_CHECK.md` | scan | DONE | n/a (scan, no critic) | `docs/redesign/AGENT_TOOLUSE_PLAN.md` reads AGPL-3.0 as the live licence throughout (pre-relicense, not swept by D83) and sits under `docs/redesign/` not `docs/archive/` — worth a one-line "superseded" pointer if the lead wants it addressed. The single actionable item (CLAUDE.md:57-58) has been open across two scans at different shas with no interim fix. |

## Output guard

Ran `scripts/r15/history_secrets_scan.py`'s `RULES` regexes over every file under this
directory (`docs/redesign/verification/r15/stage-d`) via `PYTHONDONTWRITEBYTECODE=1
python3` importing `history_secrets_scan`. **0 matches** — no redaction performed, no
files under this directory were modified by the guard.

## How to promote at rc2

1. Run this workflow with mode `refresh` first, at the tag candidate sha.
2. For each `.draft.md`, strip line 1 (the `<!-- DRAFT ... -->` header) and everything
   from the line `<!-- critic-footer -->` down.
3. Copy the stripped body to its target path:
   - `README.draft.md` → `README.md`
   - `RELEASE_RUNBOOK.draft.md` → `docs/RELEASE_RUNBOOK.md`
   - `OPERATOR_BRIEFING.draft.md` → `docs/redesign/OPERATOR_BRIEFING.md`
   - `RELEASE_NOTES.draft.md` → the GitHub release body + the `CHANGELOG.md` `v0.9.0` section
   - `CURRENT_STATE.draft.md` → `docs/CURRENT_STATE.md`
   - `BLOCKERS.draft.md` → `BLOCKERS.md`
4. The `CURRENT_STATE.draft.diff` and `BLOCKERS.draft.diff` state diffs apply with
   `patch -p1` from the repo root as an alternative to a full copy-over.

## LEAD-035 disposition pass (post-`4d893147`, at `4c6dfe8c`)

Batch-24 merged as `6778f892` after this index's capture. Its named narrowing-only fix
holds as a strict subset, but `R15-LEAD-035` failed certification a fourth time; the fresh
verifier REFUSED the `blocked_tier4` concurrence and named a further narrowing-only guard
it would certify (`stage-c/batch-24/LEAD-035-CONCURRENCE.md`). The lead set `R15-LEAD-035`
to `blocked_tier4` at `4c6dfe8c` under the operator's three-failure rule — an escalation,
not an adjudication-away (`DECISIONS_FOR_OPERATOR.md` §4.10, which now carries the
operator's (a)/(b) choice at rc1; lead recommends (b)). Open critical/high/medium is now
**0** (was 1, `R15-LEAD-035`, at this index's own `4d893147` capture).

This pass wrote the disposition into `FACTS.md`, `FACTS.json`, `OPERATOR_BRIEFING.draft.md`,
`RELEASE_NOTES.draft.md`, `CURRENT_STATE.draft.md`, `BLOCKERS.draft.md` and
`OPEN_QUESTIONS.md` (each via an appended refresh trailer or inline `RESOLVED`/`Update as
of 4c6dfe8c` annotation, per this file's own hand-added-block convention — nothing was
deleted). The "Open questions for the lead" cells above that still say "confirm at the
tag" / "batch-24 in flight" / "no concurrence file existed" describe the `4d893147`
capture only; they are superseded by this note and by each file's own trailer, not
rewritten in place (this table's cells are the critic wave's own output, out of this
pass's lane). The `.draft.diff` files were left untouched — regenerating them correctly
requires replicating the promote-time strip (§"How to promote" above) before diffing,
which this pass did not attempt.

<!-- critic-footer -->
