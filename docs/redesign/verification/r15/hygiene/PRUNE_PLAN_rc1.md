# Worktree & Branch Prune Plan — R15 rc1 Tag Window

Dry run. Read-only audit, nothing removed. Produced against branch `004-r4-experience-rebuild` (tip `dfdb882b`) for the lead to execute **after** the r15-rc1 tag lands. Every classification below is generated from `git merge-base --is-ancestor` against `origin/004-r4-experience-rebuild`, cross-referenced against `origin/*` and, where the tip is not an ancestor, against commit-subject matches in the 004 log — never from branch names alone.

**Categories:** `MERGED` (tip is an ancestor of 004 — safe to delete locally and on origin) · `SUPERSEDED` (not an ancestor, but proven landed under a different sha — cited below) · `UNPUSHED-LIVE` (local-only or ahead-of-origin, unmerged — judgment call, listed for awareness, no blind command) · `KEEP` (explicitly protected, or unmerged with no supersession evidence) · `SELF` (this audit's own branch/worktree).

## Repo hygiene stats

- `docs/redesign/verification/r15/local/` exists: **yes** (directory only checked, contents never opened, per hard rule).
- `.git` size: **293M**
- `git count-objects -vH`: `count: 239`, `size: 4.16 MiB`, `in-pack: 32659`, `packs: 3`, `size-pack: 198.97 MiB`, `prune-packable: 0`, `garbage: 0`, `size-garbage: 0 bytes`
- Tags matching `r13-*`/`r15-*`: only `r13-bedrock` exists (`6a40f835`); no branch/worktree tip currently matches it, so nothing extra to protect on that account. No `r15-*` tag exists yet (expected — this plan prepares for it).

## Worktree list before/after this audit

The only difference between `hygiene-before.txt` and `hygiene-after.txt` is the one worktree this audit created: `worktree-agent-hygiene-plan-rc1` at the scratchpad `hygiene-plan` path. See the final message for the literal `diff` output.

## 1. Worktrees (`git worktree list --porcelain`, 82 total incl. main)

### Primary worktree (never a prune target) (1)

| Path | Branch | HEAD | Dirty | Reason |
|---|---|---|---|---|
| `/Users/lokavyasingh/Documents/dev/vysted-terminal` | `004-r4-experience-rebuild` | `dfdb882b` | 2 | the main worktree (004-r4-experience-rebuild) — never a prune target |

### This audit's own artifact (remove after merge, not now) (1)

| Path | Branch | HEAD | Dirty | Reason |
|---|---|---|---|---|
| `hygiene-plan` | `worktree-agent-hygiene-plan-rc1` | `dfdb882b` | 0 | this audit's own branch/worktree — remove AFTER this prune plan is merged into 004, not now |

### MERGED — tip is an ancestor of 004 (59)

| Path | Branch | HEAD | Dirty | Reason |
|---|---|---|---|---|
| `batch-25-int` | `worktree-agent-batch-25-int` | `2e988c0d` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-26-int` | `worktree-agent-batch-26-int` | `2e1950fe` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-27-int` | `worktree-agent-batch-27-int` | `9bb60037` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-28-int` | `worktree-agent-batch-28-int` | `c780c516` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-29-int` | `worktree-agent-batch-29-int` | `cee5dc19` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-29-rework` | `worktree-agent-batch-29-rework` | `a1d39053` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-30-adjudicate` | `worktree-agent-batch-30-adjudicate` | `02de39d1` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-30-int` | `worktree-agent-batch-30-int` | `67c56430` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `batch-30-rework` | `worktree-agent-batch-30-rework` | `8d77a6cd` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `changelog-2` | `worktree-agent-changelog-2` | `fecdde48` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `changelog-3` | `worktree-agent-changelog-3` | `3f580b14` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `changelog-4` | `worktree-agent-changelog-4` | `1a9257c7` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `changelog-b29-b30` | `worktree-agent-changelog-b29-b30` | `2cf43e93` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `changelog-r4` | `worktree-agent-changelog-r4` | `d76a61be` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `changelog-r4audit` | `worktree-agent-changelog-r4audit` | `44414841` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `gate-r3` | `worktree-agent-rc1-gate-r3` | `6553c92d` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `gate-r4` | `worktree-agent-rc1-gate-r4` | `f906f219` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `hygiene-2` | `worktree-agent-hygiene-2` | `a0dccda3` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-cand` | `DETACHED` | `4c6dfe8c` | 1 | detached HEAD; commit is an ancestor of origin/004-r4-experience-rebuild — no branch to delete, worktree only |
| `rc1-gate-lanes` | `worktree-agent-rc1-gate-lanes` | `2dc599f3` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-gate-r5` | `worktree-agent-rc1-gate-r5` | `8704a491` | 12 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-r5-adjudicate` | `worktree-agent-rc1-r5-adjudicate` | `510e936d` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-r5-fix-focus` | `worktree-agent-rc1-r5-fix-focus` | `52fd29e9` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-r5-fix-int` | `worktree-agent-rc1-r5-fix-int` | `769b1f31` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-r5-fix-verify` | `verify-rc1-r5-fix` | `897eb38a` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-round-3-01d6920-fix-int` | `worktree-agent-rc1-round-3-01d6920-fix-int` | `5ff9be04` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-round-3-cand` | `DETACHED` | `01d6920a` | 1 | detached HEAD; commit is an ancestor of origin/004-r4-experience-rebuild — no branch to delete, worktree only |
| `rc1-round-4-1006c6d-fix-int` | `worktree-agent-rc1-round-4-1006c6d-fix-int` | `68d5573a` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-round-4-cand` | `DETACHED` | `1006c6da` | 5150 | detached HEAD at 1006c6da, an ancestor of 004 — but the worktree has an EXTREME dirty state: 5148 deletions + 1 modified + 1 untracked (looks like most of docs/ and more got deleted in the working tree without being committed). Since the checked-out commit is fully merged, nothing is lost by removing this worktree UNLESS that deletion was itself unreviewed intended work — flagged for the lead to eyeball before running `git worktree remove --force` (required: status is dirty). |
| `rc1-round-5-9bc600e-fix-int` | `worktree-agent-rc1-round-5-9bc600e-fix-int` | `633f8440` | 1 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `rc1-round-5-cand` | `DETACHED` | `9bc600ec` | 1 | detached HEAD; commit is an ancestor of origin/004-r4-experience-rebuild — no branch to delete, worktree only |
| `rc1-round-5-recheck-cand` | `DETACHED` | `949c3c9f` | 0 | detached HEAD; commit is an ancestor of origin/004-r4-experience-rebuild — no branch to delete, worktree only |
| `.claude/worktrees/wf_046c15b6-ff0-3` | `worktree-agent-batch-28-W1` | `efd87e05` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_046c15b6-ff0-4` | `worktree-agent-batch-28-W2` | `4800f18d` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_046c15b6-ff0-5` | `worktree-agent-batch-28-W3` | `cd1c0f0c` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_046c15b6-ff0-6` | `worktree-agent-batch-28-W4` | `ab53f543` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_046c15b6-ff0-7` | `worktree-agent-batch-28-W5` | `fb5fe5a6` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_046c15b6-ff0-8` | `worktree-agent-batch-28-W6` | `fcecdf18` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_0b0dfe4e-282-3` | `worktree-agent-batch-30-A` | `c3309201` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_0b0dfe4e-282-4` | `worktree-agent-batch-30-B` | `a1b87702` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_3bab62fa-c4d-18` | `worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize` | `ac0d8617` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_7ded8293-3fe-42` | `worktree-agent-rc1-round-5-9bc600e-fix-r1-insider-table` | `38a64fda` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_80230d64-134-3` | `worktree-agent-batch-27-W1` | `b80f082b` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_942ece8f-ad9-3` | `worktree-agent-batch-26-W1` | `4d7bc887` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_942ece8f-ad9-4` | `worktree-agent-batch-26-W2` | `a5a72488` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_a404279c-3f4-42` | `worktree-agent-rc1-round-4-1006c6d-fix-r1-W1-autobrief-staged` | `fae05766` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_a404279c-3f4-43` | `worktree-agent-rc1-round-4-1006c6d-fix-r1-W2-yf-not-found` | `fbc5b87e` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_a404279c-3f4-44` | `worktree-agent-rc1-round-4-1006c6d-fix-r1-W3-resolver-current-name` | `ea2ebd50` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_d476870a-216-3` | `worktree-agent-batch-29-W1` | `79d63896` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_d476870a-216-4` | `worktree-agent-batch-29-W2` | `2812d214` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_d476870a-216-5` | `worktree-agent-batch-29-W3` | `163d74c6` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_d476870a-216-6` | `worktree-agent-batch-29-W4` | `5ad6ab9d` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-3` | `worktree-agent-batch-25-W1` | `ef102fa5` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-4` | `worktree-agent-batch-25-W2` | `ab826232` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-5` | `worktree-agent-batch-25-W3` | `ce63da47` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-6` | `worktree-agent-batch-25-W4` | `aecc9dab` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-7` | `worktree-agent-batch-25-W5` | `1288ec19` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-8` | `worktree-agent-batch-25-W6` | `816f7cac` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `.claude/worktrees/wf_fbb7a07b-9f8-9` | `worktree-agent-batch-25-W7` | `8f0962bb` | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |

### UNPUSHED-LIVE — judgment call, no blind command (1)

| Path | Branch | HEAD | Dirty | Reason |
|---|---|---|---|---|
| `.claude/worktrees/agent-a47228f53658c48ac` | `worktree-agent-palette` | `a2b3a21c` | 0 | 1 commit ahead of origin/worktree-agent-palette AND unmerged into 004: a2b3a21c 'feat(palette): rebuild CommandPalette with cmdk (FR-120/SC-031)'. 004 already ships its own cmdk palette rebuild (bbb15ec0 'cmdk Raycast-grade grouped/scoped palette + AI-ask routing', 694caf1b 'wire AI-ask consume hook into ChatSidebar + cmdk test infra'). Pre-R15, unpushed. RECOMMEND: DEAD — superseded in spirit by the mainline's own cmdk rebuild; keep only if this commit's diff has content the mainline lacks (not verified in this audit). Worktree .claude/worktrees/agent-a47228f53658c48ac is clean (0 dirty). |

### KEEP — protected, or unmerged with no supersession evidence (20)

| Path | Branch | HEAD | Dirty | Reason |
|---|---|---|---|---|
| `lows-cn/r15-agent-077` | `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` | `80f8d7a2` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-cn/r15-code-agent-031` | `worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` | `695e934a` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-cn/r15-code-data-019` | `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` | `31aa053b` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-cn/r15-code-frontend-027` | `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` | `cba8df9f` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-cn/r15-code-research-005` | `worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` | `113ab130` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-cn/r15-data-102` | `worktree-agent-lows-CN-r15-data-102-4c6dfe8` | `09d8da83` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-cn/r15-lifecycle-035` | `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` | `954ffa89` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-deferred-A` | `worktree-agent-lows-DEF-A-4c6dfe8` | `8113ddc1` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-deferred-B` | `worktree-agent-lows-DEF-B-4c6dfe8` | `af933bcc` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-lead036` | `worktree-agent-lows-LEAD-036-4c6dfe8` | `8315c857` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-new-lows` | `worktree-agent-lows-NEW-drafted-4c6dfe8` | `abcee383` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-preint/P1` | `worktree-agent-lows-P1-int-4c6dfe8` | `dbe5fe4f` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-preint/P2` | `worktree-agent-lows-P2-int-4c6dfe8` | `78220d0c` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `lows-preint/P3` | `worktree-agent-lows-P3-int-4c6dfe8` | `f9da207a` | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `rc1-4c6dfe8-fix-int` | `worktree-agent-rc1-4c6dfe8-fix-int` | `81fbfe91` | 0 | known-FAILED fix attempt: register entry 62c11c8e 'citation-marker grammar filed as R15-RESEARCH-043 (medium, research-search, two failed fix rounds on record)' — this branch IS those two failed rounds (r1 + r2 merged together), never landed on 004, open defect on file. Not superseded. |
| `version-0.9.0` | `worktree-agent-r15-version-0.9.0` | `c1e9164c` | 0 | named KEEP by the operator brief (version prep branch) |
| `version-0.9.0-rc1` | `worktree-agent-r15-version-0.9.0-rc1` | `1dfda1f3` | 0 | unmerged, real commits, no supersession evidence found — cannot prove superseded |
| `.claude/worktrees/wf_4ed38558-4d0-25` | `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar` | `a30f693c` | 1 | round-1 half of the failed R15-RESEARCH-043 attempt (see fix-int) — open defect, not superseded. |
| `.claude/worktrees/wf_4ed38558-4d0-26` | `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class` | `39585dc3` | 8 | branch worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class is SUPERSEDED at the branch level (duplicate pointer, content preserved on origin under the sibling name) — but THIS WORKTREE carries 8 dirty files of real uncommitted work (citecheck.py, deep.py, iter.py, test_research_citecheck.py, test_research_iter.py, brief-ingest.ts, brief-ingest.test.ts + untracked node_modules): a possible third, never-committed continuation of the R15-RESEARCH-043 citation-grammar fix. DO NOT remove until the lead reviews/commits or explicitly discards this diff — `git worktree remove` would silently lose it. |
| `.claude/worktrees/wf_4ed38558-4d0-29` | `worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2` | `39585dc3` | 0 | round-2 half of the failed R15-RESEARCH-043 attempt (see fix-int) — open defect, not superseded. |

## 2. Local branches (`git branch`, 454 total, excludes `004-r4-experience-rebuild`/`main` shown separately)

### This audit's own artifact (remove after merge, not now) (1)

| Branch | Tip | On origin | Ahead of origin | Reason |
|---|---|---|---|---|
| `worktree-agent-hygiene-plan-rc1` | `dfdb882b` | no | n/a | this audit's own branch/worktree — remove AFTER this prune plan is merged into 004, not now |

### MERGED — tip is an ancestor of 004 (390)

<details><summary>390 branches — tip is an ancestor of 004; expand for the full list</summary>

| Branch | Tip | On origin | Ahead of origin | Reason |
|---|---|---|---|---|
| `001-agent-native-redesign` | `fcd6fcff` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `002-jarvis-intelligence` | `4143296c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `003-vysted-rebuild` | `20fe0044` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-10-bugfix` | `0521f8a4` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-10-copilot` | `0aee7d14` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-10-customizability` | `0255ca50` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-10-design` | `511a3140` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-10-integrations` | `4b3eefa5` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-9.5-p1-fixes` | `ac000417` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-9.5-p2-ux` | `40746bd2` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `phase-9.5-p3-visual` | `4932fabe` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `verify-rc1-r5-fix` | `897eb38a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a0f66b3235af400e6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a3b89d4c77edd3d2e` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a4050617afe66bc3d` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a4ad1b49cee7ce8f5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a5ae5375cc836dbf9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a9141cf82965b0f93` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a9213be4d0e8eacb7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a9dffdd47629cfa40` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-aa9cf4277720b8972` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-aad46a7311f3a2d1d` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-abde4703b4971c624` | `32b7a5d8` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-aca67059c0f509aec` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-ad884fe79fe84332f` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-ad9616945f3d5052b` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-ae06c3598f33ae85a` | `16094749` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-ae2d27cf756bf0462` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-ae4a8098f17ac2413` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-backlog-0.9.1` | `dfdb882b` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W1-runtime-backtest` | `2ef48a4b` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W2-catalog-hostactions` | `cf95fb48` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W3-fundamentals-bse-cache` | `a9109f8c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W4-screener-routes-statedocs` | `f10fb8ce` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W5-chat-search-workflow` | `149015ba` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W6-chart-notes-blueprint` | `bb788b10` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W7-panels-marketplace` | `2eec39a9` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W8-plugins-dock` | `2666cf22` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-int` | `f4ef5673` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W1-scripts-build` | `f2aca2e0` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W2-runtime-schema` | `6737c16f` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W3-agent-eval` | `2156719f` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W4-registry-loop` | `20d500d5` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W5-data-reference` | `f51ab96c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W6-options-chain` | `5f7be1e2` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W7-preferences` | `51233975` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W8-frontend-visual` | `cd4d1787` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-int` | `9985b00e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W1` | `8adfba10` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W2` | `190b380e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W3` | `b4585d7a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W4` | `bcfd696a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W5` | `88bbdaaf` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W6` | `79485bb2` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W7` | `f053f472` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W8` | `a9a91430` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-int` | `3d588a29` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-W1` | `b24a0860` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-W2` | `5e5e742e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-W3` | `3cb5bc29` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-int` | `e02073bd` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-14-W1` | `71da3b9a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-14-int` | `11e23ace` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-15-W1` | `aaf32a7e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-15-int` | `4daf6507` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-16-W1` | `50399b67` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-16-int` | `7b65b217` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-17-W1` | `ede02247` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-17-int` | `a340ad7b` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-18-W1` | `016c0f22` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-18-W2` | `d74a4a4d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-18-int` | `be0cd066` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-19-W1` | `95e7942e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-19-int` | `705c3626` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W1-fundamentals-seam` | `0e154ab5` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W2-instrument-identity` | `8f8f5f34` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W3-research-integrity` | `96598262` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W4-workspace-persistence` | `7b59a256` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W5-surfaces-and-math` | `652dc715` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-int` | `16f2a5eb` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-20-W1` | `05a98380` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-20-int` | `3595bcd6` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-21-W1` | `ed9cbe0a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-21-W2` | `2e8593eb` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-21-int` | `7d74e44e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-22-W1` | `946a8661` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-24-W1` | `227c1e25` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-24-int` | `d1290f66` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W1` | `ef102fa5` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W2` | `ab826232` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W3` | `ce63da47` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W4` | `aecc9dab` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W5` | `1288ec19` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W6` | `816f7cac` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W7` | `8f0962bb` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-int` | `2e988c0d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-26-W1` | `4d7bc887` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-26-W2` | `a5a72488` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-26-int` | `2e1950fe` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-27-W1` | `b80f082b` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-27-int` | `9bb60037` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W1` | `efd87e05` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W2` | `4800f18d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W3` | `cd1c0f0c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W4` | `ab53f543` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W5` | `fb5fe5a6` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W6` | `fcecdf18` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-int` | `c780c516` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W1` | `79d63896` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W2` | `2812d214` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W3` | `163d74c6` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W4` | `5ad6ab9d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-int` | `cee5dc19` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-rework` | `a1d39053` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-agent-frontend-gate` | `f95ff079` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-agent-runtime` | `cf186ad5` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-india-data-witnesses` | `fd75b199` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-int` | `b572152a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-llm-adapters-and-errors` | `42087077` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-research-depth` | `1d424050` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-A` | `c3309201` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-B` | `a1b87702` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-adjudicate` | `02de39d1` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-int` | `67c56430` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-rework` | `8d77a6cd` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W1-agent-runtime` | `8833512e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W2-workflow-backtest-feeds` | `ab844996` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W3-chat-runs-mcp` | `cb00f035` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W4-market-data-gate` | `bf48003a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W5-panels-screener` | `78223e35` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-int` | `0d16e8fd` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W1-india-disclosures-agent-surface` | `e7128795` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W2-resolver-market-data` | `1df9cb0e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W3-agent-runtime-chat` | `5e03442e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W4-platform-workflow-boundary` | `4136ad1f` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W5-screener-earnings-sec` | `896a5b72` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-int` | `a4c5039a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W1-india-exchange-data` | `bc03be5b` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W2-delegate-runs-runtime` | `26ea55c3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W3-unattended-platform-chart` | `bc03be5b` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W4-research-funnel` | `ffbd8f62` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W5-host-actions-portfolio` | `e6ea8bb3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-int` | `831d52b5` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W1-india-exchange-data` | `c07f121e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W2-delegate-runs-runtime` | `a1bdd9fd` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W3-unattended-chart-workspace` | `1835630c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W4-research-funnel` | `e6f281b3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W5-agent-writes-portfolio` | `734d8ccc` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-int` | `b7f7023f` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W1-sidecar-lifecycle-transport` | `26694809` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W2-provider-readiness-host-actions` | `c3bba8ad` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W3-data-error-honesty` | `2a025a84` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W4-resolver-exchange-lanes` | `7a83c3ad` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W5-agent-runtime-research` | `9703eee7` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-int` | `04eb5e16` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W1-agent-runtime` | `8609ad11` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W2-research-search-news` | `91f75e77` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W3-fundamentals-identity-earnings` | `84f18c5f` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W4-market-lanes-errors-quant` | `9277035e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W5-frontend-shell` | `8b9a67b3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-int` | `a3b82180` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-bhav` | `1bbdaf75` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-2` | `fecdde48` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-3` | `3f580b14` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-4` | `1a9257c7` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-b29-b30` | `2cf43e93` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-r4` | `d76a61be` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-r4audit` | `44414841` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-r5` | `796a7118` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fe` | `73192e4c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fixa` | `77e78343` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fixb` | `f9a1eecd` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fixc` | `34d88c73` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-growth` | `a6c67708` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-hardening` | `088fe322` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-hygiene-2` | `a0dccda3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-identity` | `85b049a9` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-jarvis` | `ad8ca238` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-lastfix` | `66f0cbc3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-narrative` | `f5332a11` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-panel` | `ac694ea1` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-pushguard` | `13ce4c97` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-fedata` | `ed64c9d8` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-frontend` | `4d783ba1` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-resolve` | `59bcf4f4` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-runtime` | `80d9cf2d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-screener` | `6a3a8e83` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-composer` | `bd949a75` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-proportion` | `72425f93` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-research` | `cefb31be` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-seams` | `b19b92a0` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-settings` | `897d7ca9` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-int` | `1d6511c8` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage` | `0f1a4a71` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary` | `1379f26a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived` | `7e1f3627` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs` | `ed1ed202` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency` | `d4741bc6` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail` | `54f28231` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache` | `d004d6fd` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-lanes` | `2dc599f3` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-r3` | `6553c92d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-r4` | `f906f219` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-r5` | `8704a491` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-r5-adjudicate` | `510e936d` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-r5-fix-focus` | `52fd29e9` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-r5-fix-int` | `769b1f31` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-3-01d6920-fix-int` | `5ff9be04` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize` | `ac0d8617` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-int` | `68d5573a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-r1-W1-autobrief-staged` | `fae05766` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-r1-W2-yf-not-found` | `fbc5b87e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-r1-W3-resolver-current-name` | `ea2ebd50` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-5-9bc600e-fix-int` | `633f8440` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-5-9bc600e-fix-r1-insider-table` | `38a64fda` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-res` | `e9041f2f` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-retrieval` | `9aeea79a` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rig` | `c5f4bafa` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-searxfloor` | `efba663c` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-sem` | `3a123d9e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-smokefix` | `2e0e0c61` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-spine` | `cf83b5e0` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-docs` | `c5802535` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-frontend` | `7167dbc7` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-int` | `69165638` | yes | 1 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-sidecar` | `a9f3c68e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-wireup` | `7ec8618e` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-witness` | `43a45549` | yes | 0 | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_046c15b6-ff0-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_046c15b6-ff0-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_046c15b6-ff0-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_046c15b6-ff0-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_046c15b6-ff0-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_046c15b6-ff0-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_0b0dfe4e-282-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_0b0dfe4e-282-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_116e8cdf-429-1` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_152b123d-228-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_17b6cbe4-389-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_17b6cbe4-389-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_17b6cbe4-389-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_17b6cbe4-389-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_17b6cbe4-389-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_1e4295f3-748-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_1e4295f3-748-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_1e4295f3-748-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_232102df-2f0-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_36d043fa-61f-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_36d043fa-61f-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_36d043fa-61f-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_36d043fa-61f-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_36d043fa-61f-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3bab62fa-c4d-18` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-1` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-13` | `8c328fb5` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-14` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-15` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-17` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-2` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3d774b10-8d4-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3e8a9abe-7f7-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3e8a9abe-7f7-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_3e8b0f3e-a84-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_45b81e1e-57a-1` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_48478ec5-daf-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_48478ec5-daf-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_48478ec5-daf-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_48478ec5-daf-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_48478ec5-daf-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_4ed38558-4d0-25` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_4ed38558-4d0-26` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_4ed38558-4d0-29` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_54334d97-0e6-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_5c799024-a29-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_5c799024-a29-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_5c799024-a29-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_5c799024-a29-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_5c799024-a29-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_6871fdb3-621-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_6871fdb3-621-11` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_727db864-af6-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-25` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-26` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-27` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-28` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-32` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-33` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7c4b2e60-141-34` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7ded8293-3fe-42` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_7e4c4a3f-085-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_80230d64-134-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_942ece8f-ad9-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_942ece8f-ad9-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_94ccf2b8-e97-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_94ccf2b8-e97-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_94ccf2b8-e97-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_94ccf2b8-e97-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_94ccf2b8-e97-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_9f29ee60-ba0-2` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_9f29ee60-ba0-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_9f29ee60-ba0-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-2` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a342e2a8-74a-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a404279c-3f4-42` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a404279c-3f4-43` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a404279c-3f4-44` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_a5e688ba-d35-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_aaf73f27-1c5-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_aaf73f27-1c5-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_aaf73f27-1c5-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_aaf73f27-1c5-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_aaf73f27-1c5-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b1ca86d0-402-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b7cf82ec-5ec-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b829ac35-3a5-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b829ac35-3a5-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b829ac35-3a5-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b829ac35-3a5-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_b829ac35-3a5-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_c1b4581a-8d6-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_c1b4581a-8d6-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_d476870a-216-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_d476870a-216-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_d476870a-216-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_d476870a-216-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_dab096e5-3ae-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e17e21c5-cb8-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-2` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_e64eeddf-e23-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_ea0144f4-04a-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_ea0144f4-04a-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f37de2ba-9d1-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f37de2ba-9d1-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f37de2ba-9d1-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f37de2ba-9d1-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f37de2ba-9d1-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-10` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-2` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_f724edac-bff-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-3` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-4` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-5` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-6` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-7` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-8` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-wf_fbb7a07b-9f8-9` | `cfcf5bef` | no | n/a | tip is an ancestor of origin/004-r4-experience-rebuild |

</details>

### SUPERSEDED — proven landed under a different sha (5)

| Branch | Tip | On origin | Ahead of origin | Reason |
|---|---|---|---|---|
| `worktree-agent-batch-25-W1-data002-wip` | `b91ddef3` | yes | 0 | R15-DATA-002 WIP draft; ticket landed via 4d7bc887 'fix(watchlist): carry the picked listing's region through watchlist, palette and agent add (R15-DATA-002)' (already-merged worktree-agent-batch-26-W1 lineage) — same ticket, extended scope, not an exact subject match (ticket-ID-matched). |
| `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class` | `39585dc3` | no | n/a | same tip (39585dc3) as worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2, which IS on origin — round-2 half of the failed R15-RESEARCH-043 attempt. This LOCAL branch name has no origin counterpart of its own, but the commit is preserved on origin under the sibling name — safe LOCAL-ONLY delete, no data loss. (Underlying content itself remains an open defect, not merged.) |
| `worktree-agent-research` | `a1e06a73` | yes | 0 | single commit, EXACT subject match already on 004: f97a3fec 'refactor(research): collapse to ONE research model with in-place "go deeper" (FR-115/SC-028)'. |
| `worktree-agent-screener-perf` | `1afd04dc` | yes | 0 | near-exact subject match ('...Yahoo v7 batch fast path + itemized skip ledger' + extra '+ warm precompute'). Sibling origin-only branch worktree-agent-screener-perf-v2 has the EXACT-match subject already landed on 004 as 72117f7d — corroborating evidence this lineage landed. VERIFY the 'warm precompute' delta isn't lost before deleting. |
| `worktree-wf_3d774b10-8d4-10` | `68875b60` | no | n/a | leftover harness-init branch pointer, same tip (68875b60) as worktree-agent-r10-errors, which already preserves this content on origin under its real name. No unique content — safe LOCAL-ONLY delete (duplicate pointer, not itself on origin). |

### UNPUSHED-LIVE — judgment call, no blind command (1)

| Branch | Tip | On origin | Ahead of origin | Reason |
|---|---|---|---|---|
| `worktree-agent-palette` | `a2b3a21c` | yes | 1 | 1 commit ahead of origin/worktree-agent-palette AND unmerged into 004: a2b3a21c 'feat(palette): rebuild CommandPalette with cmdk (FR-120/SC-031)'. 004 already ships its own cmdk palette rebuild (bbb15ec0 'cmdk Raycast-grade grouped/scoped palette + AI-ask routing', 694caf1b 'wire AI-ask consume hook into ChatSidebar + cmdk test infra'). Pre-R15, unpushed. RECOMMEND: DEAD — superseded in spirit by the mainline's own cmdk rebuild; keep only if this commit's diff has content the mainline lacks (not verified in this audit). Worktree .claude/worktrees/agent-a47228f53658c48ac is clean (0 dirty). |

### KEEP — protected, or unmerged with no supersession evidence (55)

| Branch | Tip | On origin | Ahead of origin | Reason |
|---|---|---|---|---|
| `feature/bl-03-reasons-about-you` | `4ea397d1` | yes | 0 | named KEEP by the operator brief (0.9.1 feature branch, held off-lane) |
| `worktree-agent-batch-22-W2` | `ca609488` | yes | 0 | LEAD-035 no-tool-cue-matcher attempt, round 1 — register: batch-22 'closed W1-only' (LEAD-035 explicitly excluded; 'batch-23 = LEAD-035 final round'). That final round ALSO failed (see batch-23-int) — LEAD-035 has no certified landing. Blocked/abandoned, not provably superseded; flag for a future cleanup pass. |
| `worktree-agent-batch-22-int` | `e4d72417` | yes | 0 | same LEAD-035 lineage as batch-22-W2 — blocked, not merged. |
| `worktree-agent-batch-23-W1` | `5a0f1ffe` | yes | 0 | LEAD-035 'final round' per the register: 'batch-23 closed (int unmerged: LEAD-035 stop rule fired...)' — this final attempt ALSO failed. LEAD-035 remains uncertified, blocked/abandoned, not provably superseded; flag for a future cleanup pass. |
| `worktree-agent-batch-23-int` | `9aa9fb6c` | yes | 0 | same LEAD-035 final-round lineage as batch-23-W1 — blocked, not merged. |
| `worktree-agent-design` | `876fde35` | yes | 0 | unmerged, real commit (feat(design): apply R4 Cold Instrument design language via token re-value). The only name-similar citation in 004 — merge(004): integrate worktree-agent-design-doc (0ab48d56) — merges a DIFFERENT branch (worktree-agent-design-doc, tip bff9301a is its 2nd parent, confirmed by `git show --no-patch --format=%H %P 0ab48d56`), not this one. Cannot prove superseded. |
| `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` | `80f8d7a2` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` | `695e934a` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` | `31aa053b` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` | `cba8df9f` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` | `113ab130` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-data-102-4c6dfe8` | `09d8da83` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` | `954ffa89` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-DEF-A-4c6dfe8` | `8113ddc1` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-DEF-B-4c6dfe8` | `af933bcc` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-LEAD-036-4c6dfe8` | `8315c857` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-NEW-drafted-4c6dfe8` | `abcee383` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W1-backtest` | `6cb980bf` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W2-runtime-catalog` | `31e61ce5` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W3-actions-research` | `dd1ceed2` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W4-chat-composer` | `57d0e546` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W5-portfolio` | `95a94e16` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W6-runs-stores` | `104d96a5` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W7-rust-core` | `8d07e2f6` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W8-tokens-market` | `2a2f0564` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W9-docs-truth` | `dd10d2e0` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-int-4c6dfe8` | `dbe5fe4f` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W1-research-semantics` | `feba1762` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W2-scripts-gates` | `d9228cc3` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W3-tools-envelope` | `2505d47b` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W4-warm-screener` | `1cc7ff1f` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W5-data-resilience` | `eaaef44a` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W6-llm-router-mcp` | `d80e01a1` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W7-mcp-client` | `e581a3be` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W8-shell-page` | `26c0cb03` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W9-workspace-persist` | `a7408560` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-int-4c6dfe8` | `78220d0c` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W1-client-plugins` | `9d0a9129` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W2-llm-chat` | `69ce5999` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W3-provenance-data` | `d7059b24` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W4-quant-macro` | `c60f921f` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W5-workflow-backend` | `d9c8da22` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W6-data-hygiene` | `9eaab2ac` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W7-notes-datatable` | `f714efe5` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W8-panels-polish` | `e4a77aca` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W9-search-backends` | `95b60cc1` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-int-4c6dfe8` | `f9da207a` | yes | 0 | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-notes` | `0a078ceb` | yes | 0 | unmerged; 004 already ships a differently-scoped Tiptap notes feature (e7981829 'Tiptap markdown editor + atomic Rust persistence + md/PNG/PDF export') — same subsystem, different scope (this branch: slash/wikilink menus + sharing, FR-121/SC-032) — not an exact subject match, cannot prove superseded. |
| `worktree-agent-r10-errors` | `68875b60` | yes | 0 | unmerged, 3 commits (R10-era 'errors humanizer' work: feat(errors) add humanizer + extend LLMErrorEvent). No match anywhere in the 004 log for 'humanizer'. Cannot prove superseded — likely stale/abandoned; flag for a future cleanup pass, not this window. |
| `worktree-agent-r15-version-0.9.0` | `c1e9164c` | yes | 0 | named KEEP by the operator brief (version prep branch) |
| `worktree-agent-r15-version-0.9.0-r2` | `6c7c5bbf` | yes | 0 | named KEEP by the operator brief (version prep branch, r2) |
| `worktree-agent-r15-version-0.9.0-rc1` | `1dfda1f3` | yes | 0 | unmerged, real commits, no supersession evidence found — cannot prove superseded |
| `worktree-agent-rc1-4c6dfe8-fix-int` | `81fbfe91` | yes | 0 | known-FAILED fix attempt: register entry 62c11c8e 'citation-marker grammar filed as R15-RESEARCH-043 (medium, research-search, two failed fix rounds on record)' — this branch IS those two failed rounds (r1 + r2 merged together), never landed on 004, open defect on file. Not superseded. |
| `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar` | `a30f693c` | yes | 0 | round-1 half of the failed R15-RESEARCH-043 attempt (see fix-int) — open defect, not superseded. |
| `worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2` | `39585dc3` | yes | 0 | round-2 half of the failed R15-RESEARCH-043 attempt (see fix-int) — open defect, not superseded. |

## 3. `origin/*` branches (`git branch -r`, 292 total)

### MERGED — tip is an ancestor of 004 (227)

<details><summary>227 branches — tip is an ancestor of 004; expand for the full list</summary>

| Branch | Tip | Unmerged commits | First commit subject | Reason |
|---|---|---|---|---|
| `001-agent-native-redesign` | `fcd6fcff` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `002-jarvis-intelligence` | `4143296c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `003-vysted-rebuild` | `20fe0044` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `origin` | `cfcf5bef` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `verify-rc1-r5-fix` | `897eb38a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a882d06f8e7c3ff56` | `df91e7a8` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-a9d8467a798247f72` | `4227af58` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W1-runtime-backtest` | `2ef48a4b` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W2-catalog-hostactions` | `cf95fb48` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W3-fundamentals-bse-cache` | `a9109f8c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W4-screener-routes-statedocs` | `f10fb8ce` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W5-chat-search-workflow` | `149015ba` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W6-chart-notes-blueprint` | `bb788b10` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W7-panels-marketplace` | `2eec39a9` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-W8-plugins-dock` | `2666cf22` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-10-int` | `f4ef5673` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W1-scripts-build` | `f2aca2e0` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W2-runtime-schema` | `6737c16f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W3-agent-eval` | `2156719f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W4-registry-loop` | `20d500d5` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W5-data-reference` | `f51ab96c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W6-options-chain` | `5f7be1e2` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W7-preferences` | `51233975` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-W8-frontend-visual` | `cd4d1787` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-11-int` | `9985b00e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W1` | `8adfba10` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W2` | `190b380e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W3` | `b4585d7a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W4` | `bcfd696a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W5` | `88bbdaaf` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W6` | `79485bb2` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W7` | `f053f472` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-W8` | `a9a91430` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-12-int` | `3d588a29` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-W1` | `b24a0860` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-W2` | `5e5e742e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-W3` | `3cb5bc29` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-13-int` | `e02073bd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-14-W1` | `71da3b9a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-14-int` | `11e23ace` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-15-W1` | `596ae9e9` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-15-int` | `4daf6507` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-16-W1` | `50399b67` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-16-int` | `7b65b217` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-17-W1` | `ede02247` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-17-int` | `a340ad7b` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-18-W1` | `016c0f22` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-18-W2` | `d74a4a4d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-18-int` | `72dc8f68` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-19-W1` | `95e7942e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-19-int` | `705c3626` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W1-fundamentals-seam` | `0e154ab5` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W2-instrument-identity` | `8f8f5f34` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W3-research-integrity` | `96598262` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W4-workspace-persistence` | `7b59a256` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-W5-surfaces-and-math` | `652dc715` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-2-int` | `16f2a5eb` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-20-W1` | `05a98380` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-20-int` | `3595bcd6` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-21-W1` | `ed9cbe0a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-21-W2` | `2e8593eb` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-21-int` | `7d74e44e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-22-W1` | `946a8661` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-24-W1` | `227c1e25` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-24-int` | `d1290f66` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W1` | `ef102fa5` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W2` | `ab826232` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W3` | `ce63da47` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W4` | `aecc9dab` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W5` | `1288ec19` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W6` | `816f7cac` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-W7` | `8f0962bb` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-25-int` | `2e988c0d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-26-W1` | `4d7bc887` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-26-W2` | `a5a72488` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-26-int` | `2e1950fe` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-27-W1` | `b80f082b` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-27-int` | `0338a7bf` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W1` | `efd87e05` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W2` | `4800f18d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W3` | `cd1c0f0c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W4` | `ab53f543` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W5` | `fb5fe5a6` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-W6` | `fcecdf18` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-28-int` | `c780c516` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W1` | `79d63896` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W2` | `2812d214` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W3` | `163d74c6` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-W4` | `5ad6ab9d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-int` | `cee5dc19` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-29-rework` | `a1d39053` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-agent-frontend-gate` | `f95ff079` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-agent-runtime` | `cf186ad5` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-india-data-witnesses` | `fd75b199` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-int` | `1b5a5e5e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-llm-adapters-and-errors` | `42087077` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-3-research-depth` | `1d424050` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-A` | `c3309201` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-B` | `a1b87702` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-adjudicate` | `02de39d1` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-int` | `67c56430` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-30-rework` | `8d77a6cd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W1-agent-runtime` | `8833512e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W2-workflow-backtest-feeds` | `ab844996` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W3-chat-runs-mcp` | `cb00f035` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W4-market-data-gate` | `bf48003a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-W5-panels-screener` | `78223e35` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-4-int` | `0d16e8fd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W1-india-disclosures-agent-surface` | `e7128795` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W2-resolver-market-data` | `1df9cb0e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W3-agent-runtime-chat` | `5e03442e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W4-platform-workflow-boundary` | `4136ad1f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-W5-screener-earnings-sec` | `896a5b72` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-5-int` | `7ae5117b` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W1-india-exchange-data` | `42a449c6` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W2-delegate-runs-runtime` | `26ea55c3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W3-unattended-platform-chart` | `d2e0e78a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W4-research-funnel` | `ffbd8f62` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-W5-host-actions-portfolio` | `e6ea8bb3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-6-int` | `831d52b5` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W1-india-exchange-data` | `c07f121e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W2-delegate-runs-runtime` | `a1bdd9fd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W3-unattended-chart-workspace` | `1835630c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W4-research-funnel` | `e6f281b3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-W5-agent-writes-portfolio` | `734d8ccc` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-7-int` | `b7f7023f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W1-sidecar-lifecycle-transport` | `26694809` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W2-provider-readiness-host-actions` | `c3bba8ad` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W3-data-error-honesty` | `2a025a84` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W4-resolver-exchange-lanes` | `7a83c3ad` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-W5-agent-runtime-research` | `9703eee7` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-8-int` | `04eb5e16` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W1-agent-runtime` | `8609ad11` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W2-research-search-news` | `91f75e77` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W3-fundamentals-identity-earnings` | `84f18c5f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W4-market-lanes-errors-quant` | `9277035e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-W5-frontend-shell` | `8b9a67b3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-batch-9-int` | `a3b82180` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-bhav` | `1bbdaf75` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-brief` | `c8bb2c27` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-2` | `fecdde48` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-3` | `3f580b14` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-4` | `1a9257c7` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-b29-b30` | `2cf43e93` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-r4` | `d76a61be` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-r4audit` | `44414841` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-changelog-r5` | `796a7118` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-chat-experience` | `8a796cbd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-composer` | `2e8757cf` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-consistency` | `d0f31892` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-data-panels` | `8b14f1a7` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fe` | `73192e4c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fixa` | `77e78343` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fixb` | `f9a1eecd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-fixc` | `34d88c73` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-growth` | `a6c67708` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-hardening` | `088fe322` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-hygiene-2` | `a0dccda3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-identity` | `85b049a9` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-jarvis` | `ad8ca238` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-lastfix` | `66f0cbc3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-layout` | `4057e1aa` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-narrative` | `f5332a11` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-overview-narrative` | `e62c32bd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-panel` | `ac694ea1` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-pins` | `78a5ad71` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-fedata` | `8c328fb5` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-frontend` | `4d783ba1` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-resolve` | `d5acca93` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-runtime` | `80d9cf2d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r10-screener` | `a5e368ee` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-chart` | `db722ff7` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-chat` | `f0aa705c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-data` | `a56068da` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-hack` | `7ec73846` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-panels` | `ec1101c7` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-research` | `bd9f4fe0` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r7-tiers` | `76d0aba6` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-composer` | `bd949a75` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-proportion` | `72425f93` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-research` | `cefb31be` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-seams` | `b19b92a0` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r8-settings` | `897d7ca9` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r9-composer` | `76a14545` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r9-loop` | `e71cd3e2` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r9-proportion` | `78e4e001` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r9-settings` | `f3951c9f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-r9-tiers` | `7b6a5a22` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-int` | `1d6511c8` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage` | `0f1a4a71` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary` | `1379f26a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived` | `7e1f3627` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs` | `ed1ed202` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency` | `d4741bc6` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail` | `54f28231` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache` | `d004d6fd` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-lanes` | `2dc599f3` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-r3` | `6553c92d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-r4` | `f906f219` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-gate-r5` | `8704a491` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-r5-adjudicate` | `510e936d` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-r5-fix-focus` | `52fd29e9` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-r5-fix-int` | `769b1f31` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-3-01d6920-fix-int` | `5ff9be04` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize` | `ac0d8617` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-int` | `68d5573a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-r1-W1-autobrief-staged` | `fae05766` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-r1-W2-yf-not-found` | `fbc5b87e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-4-1006c6d-fix-r1-W3-resolver-current-name` | `ea2ebd50` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-5-9bc600e-fix-int` | `633f8440` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rc1-round-5-9bc600e-fix-r1-insider-table` | `38a64fda` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-res` | `e9041f2f` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-retrieval` | `9aeea79a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-rig` | `c5f4bafa` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-screener-backoff` | `4079c418` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-searxfloor` | `efba663c` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-sem` | `3a123d9e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-smokefix` | `2e0e0c61` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-space-memory` | `ac07209a` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-spine` | `cf83b5e0` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-surfaces` | `d3cd6152` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-docs` | `c5802535` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-frontend` | `7167dbc7` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-int` | `252a7e51` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-trading-sidecar` | `a9f3c68e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-wireup` | `7ec8618e` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |
| `worktree-agent-witness` | `43a45549` | 0 |  | tip is an ancestor of origin/004-r4-experience-rebuild |

</details>

### SUPERSEDED — proven landed under a different sha (7)

| Branch | Tip | Unmerged commits | First commit subject | Reason |
|---|---|---|---|---|
| `phase-1a-foundation` | `0bab5c72` | 4 | docs(blueprint): sync stack details with Phase 0 shipped reality | origin-only, ALL 4 commit subjects exact-match commits already on 004 (early foundational work, pre-numbered-batch era): 4691d576, b7572b15, 3f7324ae, e53ee885. |
| `worktree-agent-batch-25-W1-data002-wip` | `b91ddef3` | 1 | wip(watchlist): carry the picked listing's region through the watchlist (R15-DATA-002) | R15-DATA-002 WIP draft; ticket landed via 4d7bc887 'fix(watchlist): carry the picked listing's region through watchlist, palette and agent add (R15-DATA-002)' (already-merged worktree-agent-batch-26-W1 lineage) — same ticket, extended scope, not an exact subject match (ticket-ID-matched). |
| `worktree-agent-design-doc` | `bff9301a` | 0 |  | origin-only; tip bff9301a is the confirmed 2nd parent of 004 merge commit 0ab48d56 'merge(004): integrate worktree-agent-design-doc'. |
| `worktree-agent-formula` | `87a5cec7` | 1 | feat(screener): nested AND/OR editor + mathjs formula leaf + write_screener_filters host action | origin-only, EXACT subject match already on 004: ba2d0eb5 'feat(screener): nested AND/OR editor + mathjs formula leaf + write_screener_filters host action'. |
| `worktree-agent-research` | `a1e06a73` | 1 | refactor(research): collapse to ONE research model with in-place "go deeper" (FR-115/SC-028) | single commit, EXACT subject match already on 004: f97a3fec 'refactor(research): collapse to ONE research model with in-place "go deeper" (FR-115/SC-028)'. |
| `worktree-agent-screener-perf` | `1afd04dc` | 1 | perf(screener): Yahoo v7 batch fast path + itemized skip ledger + warm precompute | near-exact subject match ('...Yahoo v7 batch fast path + itemized skip ledger' + extra '+ warm precompute'). Sibling origin-only branch worktree-agent-screener-perf-v2 has the EXACT-match subject already landed on 004 as 72117f7d — corroborating evidence this lineage landed. VERIFY the 'warm precompute' delta isn't lost before deleting. |
| `worktree-agent-screener-perf-v2` | `cb9d2821` | 1 | perf(screener): Yahoo v7 batch fast path + itemized skip ledger (FR-126 / SC-034) | origin-only, EXACT subject match already on 004: 72117f7d 'perf(screener): Yahoo v7 batch fast path + itemized skip ledger (FR-126 / SC-034)'. |

### UNPUSHED-LIVE — judgment call, no blind command (1)

| Branch | Tip | Unmerged commits | First commit subject | Reason |
|---|---|---|---|---|
| `worktree-agent-palette` | `71bf9b40` | 0 |  | 1 commit ahead of origin/worktree-agent-palette AND unmerged into 004: a2b3a21c 'feat(palette): rebuild CommandPalette with cmdk (FR-120/SC-031)'. 004 already ships its own cmdk palette rebuild (bbb15ec0 'cmdk Raycast-grade grouped/scoped palette + AI-ask routing', 694caf1b 'wire AI-ask consume hook into ChatSidebar + cmdk test infra'). Pre-R15, unpushed. RECOMMEND: DEAD — superseded in spirit by the mainline's own cmdk rebuild; keep only if this commit's diff has content the mainline lacks (not verified in this audit). Worktree .claude/worktrees/agent-a47228f53658c48ac is clean (0 dirty). |

### KEEP — protected, or unmerged with no supersession evidence (55)

| Branch | Tip | Unmerged commits | First commit subject | Reason |
|---|---|---|---|---|
| `feature/bl-03-reasons-about-you` | `4ea397d1` | 1 | docs(bl-03): BL-03 leaves the release line — spec, critic and panel verdict attached (first 0.9.1 feature, scope change 3) | named KEEP by the operator brief (0.9.1 feature branch, held off-lane) |
| `worktree-agent-batch-22-W2` | `ca609488` | 1 | fix(agent): normalised no-tool cue matcher replaces closed phrase list (R15-LEAD-035) | LEAD-035 no-tool-cue-matcher attempt, round 1 — register: batch-22 'closed W1-only' (LEAD-035 explicitly excluded; 'batch-23 = LEAD-035 final round'). That final round ALSO failed (see batch-23-int) — LEAD-035 has no certified landing. Blocked/abandoned, not provably superseded; flag for a future cleanup pass. |
| `worktree-agent-batch-22-int` | `e4d72417` | 2 | fix(agent): normalised no-tool cue matcher replaces closed phrase list (R15-LEAD-035) | same LEAD-035 lineage as batch-22-W2 — blocked, not merged. |
| `worktree-agent-batch-23-W1` | `5a0f1ffe` | 1 | fix(agent): per-clause no-tool cue matcher replaces the closed phrase list (R15-LEAD-035) | LEAD-035 'final round' per the register: 'batch-23 closed (int unmerged: LEAD-035 stop rule fired...)' — this final attempt ALSO failed. LEAD-035 remains uncertified, blocked/abandoned, not provably superseded; flag for a future cleanup pass. |
| `worktree-agent-batch-23-int` | `9aa9fb6c` | 3 | fix(agent): per-clause no-tool cue matcher replaces the closed phrase list (R15-LEAD-035) | same LEAD-035 final-round lineage as batch-23-W1 — blocked, not merged. |
| `worktree-agent-design` | `876fde35` | 1 | feat(design): apply R4 Cold Instrument design language via token re-value | unmerged, real commit (feat(design): apply R4 Cold Instrument design language via token re-value). The only name-similar citation in 004 — merge(004): integrate worktree-agent-design-doc (0ab48d56) — merges a DIFFERENT branch (worktree-agent-design-doc, tip bff9301a is its 2nd parent, confirmed by `git show --no-patch --format=%H %P 0ab48d56`), not this one. Cannot prove superseded. |
| `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` | `80f8d7a2` | 3 | fix(llm): thread the adapter base_url into the repair and native-search oneshots (R15-AGENT-077) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` | `695e934a` | 2 | fix(runs): one snake_case wire for the runs routes, drop _dual_case (R15-CODE-AGENT-031) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` | `31aa053b` | 2 | fix(screener): delete the dead matched_criteria row field on both sides of the wire (R15-CODE-DATA-019) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` | `cba8df9f` | 3 | fix(agents): a failed custom-agents load is an error, not an empty list (R15-CODE-FRONTEND-027) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` | `113ab130` | 3 | refactor(research): make deep's shared round helpers public exports (R15-CODE-RESEARCH-005) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-data-102-4c6dfe8` | `09d8da83` | 4 | fix(fundamentals): store rows state their growth basis and per-field provenance (R15-DATA-102, partial) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` | `954ffa89` | 2 | fix(research): a serving SearXNG container supersedes a sticky setup error (R15-LIFECYCLE-035) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-DEF-A-4c6dfe8` | `8113ddc1` | 2 | test(host-actions): pin arrange_layout focus alias resolution (R15-CODE-FRONTEND-033) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-DEF-B-4c6dfe8` | `af933bcc` | 7 | fix(R15-CROSS-PLATFORM-012): split regenerable caches into a --cache-dir | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-LEAD-036-4c6dfe8` | `8315c857` | 2 | fix(agent): carry an open code fence across releases so a replaced note never renders inside it (R15-LEAD-036) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-NEW-drafted-4c6dfe8` | `abcee383` | 6 | docs(r15): R15-DOCS-025 fix stale AUTO-autonomy exemption in SAFETY_ARCHITECTURE.md | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W1-backtest` | `6cb980bf` | 6 | fix(backtest): fold keyword case in DSL AND/OR/NOT parsing (R15-AGENT-079) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W2-runtime-catalog` | `31e61ce5` | 9 | fix(agent): select research's args-derived timeout by a catalog flag, not its name (R15-AGENT-070) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W3-actions-research` | `dd1ceed2` | 6 | fix(host-actions): carry the apply ack status on ApplyResult instead of matching the 'Kept' label (R15-CODE-FRONTEND-034) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W4-chat-composer` | `57d0e546` | 2 | fix(chat-composer): show pre-dispatch Tier B research cost estimate (R15-RESEARCH-040) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W5-portfolio` | `95a94e16` | 6 | fix(portfolio): reword updateHolding doc comment to state replace semantics (R15-CODE-PLATFORM-052) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W6-runs-stores` | `104d96a5` | 3 | fix(agents): skip and log an unparseable custom-agent row in list_agents (R15-CODE-AGENT-017) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W7-rust-core` | `8d07e2f6` | 12 | fix(rust-core): one write_atomic helper behind the text and bytes commands (R15-CODE-PLATFORM-055) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W8-tokens-market` | `2a2f0564` | 5 | fix(design-tokens): enable slashed-zero font feature to match tokens.css claim (R15-UI-075) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-W9-docs-truth` | `dd10d2e0` | 11 | docs(blueprint): back-port dark-only zinc palette + MCP degrade caveat (R15-DOCS-007) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P1-int-4c6dfe8` | `dbe5fe4f` | 83 | fix(agents): skip and log an unparseable custom-agent row in list_agents (R15-CODE-AGENT-017) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W1-research-semantics` | `feba1762` | 4 | fix(research): declare all emitted derived-metric fields on BriefDerivedMetrics (R15-CODE-RESEARCH-007) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W2-scripts-gates` | `d9228cc3` | 7 | fix(build): guard sidecar-staleness statSync against TOCTOU deletion (R15-CODE-PLATFORM-061) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W3-tools-envelope` | `2505d47b` | 8 | refactor(agent-tools): inline registry_v0_6_0 pass-through (R15-CODE-AGENT-028) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W4-warm-screener` | `1cc7ff1f` | 8 | fix(fundamentals-warm): run the India boot seed once, from start_warm_fundamentals only (R15-LIFECYCLE-030) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W5-data-resilience` | `eaaef44a` | 9 | fix(disclosures): widen lane-loop catches to Exception (R15-CODE-DATA-007) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W6-llm-router-mcp` | `d80e01a1` | 4 | fix(llm): humanize the key-validate transport-failure detail (R15-CODE-AGENT-019) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W7-mcp-client` | `e581a3be` | 3 | fix(mcp-servers): pass MCP structuredContent through (R15-CODE-AGENT-025) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W8-shell-page` | `26c0cb03` | 13 | fix(workflow): take notifications atomically before send (R15-CODE-FRONTEND-026) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-W9-workspace-persist` | `a7408560` | 5 | fix(settings): apply the default persona only from the launch restore, drop the first-setAll latch (R15-CODE-FRONTEND-030) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P2-int-4c6dfe8` | `78220d0c` | 105 | fix(build): guard sidecar-staleness statSync against TOCTOU deletion (R15-CODE-PLATFORM-061) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W1-client-plugins` | `9d0a9129` | 6 | fix(search): omit tier_b BYOK key on the default sidecar REST path (R15-CODE-PLATFORM-039) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W2-llm-chat` | `69ce5999` | 10 | fix(llm): declare LLMProvider.stream_chat as an async-iterator def, not a coroutine (R15-CODE-PLATFORM-044) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W3-provenance-data` | `d7059b24` | 14 | fix(resolver): garbled bundled master degrades to empty, not a /resolve 500 (R15-LIFECYCLE-036) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W4-quant-macro` | `c60f921f` | 7 | fix(quant): delete dead monte_carlo.py (R15-CODE-PLATFORM-040) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W5-workflow-backend` | `d9c8da22` | 6 | fix(workflow): end every /workflow/run stream on a run-error frame carrying the engine's reason (R15-CODE-PLATFORM-065) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W6-data-hygiene` | `9eaab2ac` | 4 | fix(sidecar): one shared cached-fetch helper for fundamentals + earnings routers (R15-CODE-DATA-011, R15-CODE-DATA-012) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W7-notes-datatable` | `f714efe5` | 3 | fix(frontend): delete dead fuzzy.ts and unused exportNoteMd (R15-CODE-FRONTEND-024) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W8-panels-polish` | `e4a77aca` | 8 | fix(sec): reactive per-key selectors, no getState() in render path (R15-CODE-DATA-014) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-W9-search-backends` | `95b60cc1` | 4 | fix(search): remove duplicate ddg pacing + surface 403-then-429 as rate-limited (R15-CODE-RESEARCH-009, R15-RESEARCH-039) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-lows-P3-int-4c6dfe8` | `f9da207a` | 97 | fix(llm): declare LLMProvider.stream_chat as an async-iterator def, not a coroutine (R15-CODE-PLATFORM-044) | named KEEP by the operator brief (lows P1/P2/P3 family, 4c6dfe8 lineage) |
| `worktree-agent-notes` | `0a078ceb` | 1 | feat(notes): Tiptap editor with slash/wikilink menus, atomic persistence, and sharing (FR-121/SC-032) | unmerged; 004 already ships a differently-scoped Tiptap notes feature (e7981829 'Tiptap markdown editor + atomic Rust persistence + md/PNG/PDF export') — same subsystem, different scope (this branch: slash/wikilink menus + sharing, FR-121/SC-032) — not an exact subject match, cannot prove superseded. |
| `worktree-agent-r10-errors` | `68875b60` | 3 | feat(errors): add humanizer + extend LLMErrorEvent with action/detail/code | unmerged, 3 commits (R10-era 'errors humanizer' work: feat(errors) add humanizer + extend LLMErrorEvent). No match anywhere in the 004 log for 'humanizer'. Cannot prove superseded — likely stale/abandoned; flag for a future cleanup pass, not this window. |
| `worktree-agent-r15-version-0.9.0` | `c1e9164c` | 2 | chore(release): bump version to 0.9.0 | named KEEP by the operator brief (version prep branch) |
| `worktree-agent-r15-version-0.9.0-r2` | `6c7c5bbf` | 1 | chore(release): bump version to 0.9.0 in all five sources + Cargo.lock; stale 0.8.0 references updated | named KEEP by the operator brief (version prep branch, r2) |
| `worktree-agent-r15-version-0.9.0-rc1` | `1dfda1f3` | 2 | chore(release): bump version to 0.9.0 | unmerged, real commits, no supersession evidence found — cannot prove superseded |
| `worktree-agent-rc1-4c6dfe8-fix-int` | `81fbfe91` | 5 | fix(rc1): expand citation marker groups and strip pseudo-citations (rc1-drive-research-briefs:2) | known-FAILED fix attempt: register entry 62c11c8e 'citation-marker grammar filed as R15-RESEARCH-043 (medium, research-search, two failed fix rounds on record)' — this branch IS those two failed rounds (r1 + r2 merged together), never landed on 004, open defect on file. Not superseded. |
| `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar` | `a30f693c` | 1 | fix(rc1): expand citation marker groups and strip pseudo-citations (rc1-drive-research-briefs:2) | round-1 half of the failed R15-RESEARCH-043 attempt (see fix-int) — open defect, not superseded. |
| `worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2` | `39585dc3` | 4 | fix(rc1): expand citation marker groups and strip pseudo-citations (rc1-drive-research-briefs:2) | round-2 half of the failed R15-RESEARCH-043 attempt (see fix-int) — open defect, not superseded. |

## 4. Special cases called out explicitly

**`.claude/worktrees/wf_046c15b6-ff0-*`** — the batch-28 W1..W6 worker worktrees (`worktree-agent-batch-28-W1` … `-W6`). All 6 are **MERGED** (ancestors of 004), clean (0 dirty). Safe worktree-remove + branch -D + origin delete.

**`.claude/worktrees/wf_d476870a-216-*`** — the batch-29 W1..W4 worker worktrees (`worktree-agent-batch-29-W1` … `-W4`). All 4 are **MERGED**, clean. Safe.

**`.claude/worktrees/agent-a47228f53658c48ac` on `worktree-agent-palette@a2b3a21c`** — **UNPUSHED-LIVE**. Pre-R15, genuinely unpushed: local is 1 commit ahead of `origin/worktree-agent-palette` (`71bf9b40`), and that commit is not an ancestor of 004. The single commit: `a2b3a21c feat(palette): rebuild CommandPalette with cmdk (FR-120/SC-031)`. Worktree is clean (0 dirty). 004 already ships its own cmdk palette rebuild (`bbb15ec0`, `694caf1b`) — **recommend DEAD** (superseded in spirit, not exact-match certified) unless the lead confirms this diff has unique content. Not included in the blind command list below — the lead's call.

**batch-28/29/30 and rc1-round-5 scratch worktrees under the scratchpad** — `batch-28-int`, `batch-29-int`, `batch-29-rework`, `batch-30-adjudicate`, `batch-30-int`, `batch-30-rework` are all **MERGED**, clean. The three `rc1-round-5-9bc600e-*` worktrees: see next entry.

**The three `rc1-round-5-9bc600e-*` worktrees** — `rc1-round-5-9bc600e-fix-int` (branch, MERGED, **dirty=1**), `rc1-round-5-cand` (detached @ `9bc600ec`, MERGED, **dirty=1**) and `rc1-round-5-recheck-cand` (detached @ `949c3c9f`, MERGED, clean). **Confirmed: two of the three still carry the uncommitted spend-ledger diff** (`git status --short` in both shows ` M docs/redesign/verification/r15/spend-ledger.jsonl`) — exactly the diff the lead said was already folded elsewhere. Since the diff is un-committed in both worktrees and the file itself is off-limits to this audit (hard rule: never touch the spend-ledger), the lead should verify the fold landed before running `git worktree remove` on either — a plain `remove` will refuse on a dirty tree; `--force` would silently discard the diff. `rc1-round-5-recheck-cand` is clean and safe as-is.

**`rc1-round-4-cand`** (not explicitly named in the brief, flagged because of what the audit found) — detached @ `1006c6da`, MERGED, but the worktree has an **extreme dirty state**: 5148 deletions + 1 modified + 1 untracked, effectively the whole `docs/` tree (and more) deleted in the working copy without being committed. The checked-out commit itself is fully merged into 004, so nothing tracked is lost by removing the worktree — but the lead should eyeball it first in case the deletion was itself unreviewed intended work. Needs `--force`.

**`.git` size / object count** — see Repo hygiene stats above; no `prune-packable` or `garbage` objects, so a `git gc` is not urgent on that account.

## 5. Commands for the lead (run after the r15-rc1 tag; MERGED first; KEEP is never a command)

Dirty worktrees need `--force` (noted inline) — that discards the uncommitted diff, so read the note next to it first. Every `git push origin --delete` needs `GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20"` in front of it (omitted below for brevity — prefix every push/delete line with it).

### MERGED

```bash
# --- worktree removes (59) ---
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-25-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-26-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-27-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-28-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-29-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-29-rework
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-30-adjudicate
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-30-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-30-rework
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-2
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-3
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-4
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-b29-b30
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-r4
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-r4audit
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/gate-r3
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/gate-r4
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/hygiene-2
git worktree remove --force /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-cand  # dirty=1, discards uncommitted diff
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-gate-lanes
git worktree remove --force /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-gate-r5  # dirty=12, discards uncommitted diff
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-r5-adjudicate
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-r5-fix-focus
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-r5-fix-int
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-r5-fix-verify
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-3-01d6920-fix-int
git worktree remove --force /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-3-cand  # dirty=1, discards uncommitted diff
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-1006c6d-fix-int
git worktree remove --force /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand  # dirty=5150, discards uncommitted diff
git worktree remove --force /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-9bc600e-fix-int  # dirty=1, discards uncommitted diff
git worktree remove --force /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-cand  # dirty=1, discards uncommitted diff
git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-5-recheck-cand
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_046c15b6-ff0-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_046c15b6-ff0-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_046c15b6-ff0-5
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_046c15b6-ff0-6
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_046c15b6-ff0-7
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_046c15b6-ff0-8
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_0b0dfe4e-282-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_0b0dfe4e-282-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_3bab62fa-c4d-18
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_7ded8293-3fe-42
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_80230d64-134-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_942ece8f-ad9-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_942ece8f-ad9-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_a404279c-3f4-42
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_a404279c-3f4-43
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_a404279c-3f4-44
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_d476870a-216-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_d476870a-216-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_d476870a-216-5
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_d476870a-216-6
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-5
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-6
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-7
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-8
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-9

# --- local branch deletes (390) ---
git branch -D 001-agent-native-redesign
git branch -D 002-jarvis-intelligence
git branch -D 003-vysted-rebuild
git branch -D phase-10-bugfix
git branch -D phase-10-copilot
git branch -D phase-10-customizability
git branch -D phase-10-design
git branch -D phase-10-integrations
git branch -D phase-9.5-p1-fixes
git branch -D phase-9.5-p2-ux
git branch -D phase-9.5-p3-visual
git branch -D verify-rc1-r5-fix
git branch -D worktree-agent-a0f66b3235af400e6
git branch -D worktree-agent-a3b89d4c77edd3d2e
git branch -D worktree-agent-a4050617afe66bc3d
git branch -D worktree-agent-a4ad1b49cee7ce8f5
git branch -D worktree-agent-a5ae5375cc836dbf9
git branch -D worktree-agent-a9141cf82965b0f93
git branch -D worktree-agent-a9213be4d0e8eacb7
git branch -D worktree-agent-a9dffdd47629cfa40
git branch -D worktree-agent-aa9cf4277720b8972
git branch -D worktree-agent-aad46a7311f3a2d1d
git branch -D worktree-agent-abde4703b4971c624
git branch -D worktree-agent-aca67059c0f509aec
git branch -D worktree-agent-ad884fe79fe84332f
git branch -D worktree-agent-ad9616945f3d5052b
git branch -D worktree-agent-ae06c3598f33ae85a
git branch -D worktree-agent-ae2d27cf756bf0462
git branch -D worktree-agent-ae4a8098f17ac2413
git branch -D worktree-agent-backlog-0.9.1
git branch -D worktree-agent-batch-10-W1-runtime-backtest
git branch -D worktree-agent-batch-10-W2-catalog-hostactions
git branch -D worktree-agent-batch-10-W3-fundamentals-bse-cache
git branch -D worktree-agent-batch-10-W4-screener-routes-statedocs
git branch -D worktree-agent-batch-10-W5-chat-search-workflow
git branch -D worktree-agent-batch-10-W6-chart-notes-blueprint
git branch -D worktree-agent-batch-10-W7-panels-marketplace
git branch -D worktree-agent-batch-10-W8-plugins-dock
git branch -D worktree-agent-batch-10-int
git branch -D worktree-agent-batch-11-W1-scripts-build
git branch -D worktree-agent-batch-11-W2-runtime-schema
git branch -D worktree-agent-batch-11-W3-agent-eval
git branch -D worktree-agent-batch-11-W4-registry-loop
git branch -D worktree-agent-batch-11-W5-data-reference
git branch -D worktree-agent-batch-11-W6-options-chain
git branch -D worktree-agent-batch-11-W7-preferences
git branch -D worktree-agent-batch-11-W8-frontend-visual
git branch -D worktree-agent-batch-11-int
git branch -D worktree-agent-batch-12-W1
git branch -D worktree-agent-batch-12-W2
git branch -D worktree-agent-batch-12-W3
git branch -D worktree-agent-batch-12-W4
git branch -D worktree-agent-batch-12-W5
git branch -D worktree-agent-batch-12-W6
git branch -D worktree-agent-batch-12-W7
git branch -D worktree-agent-batch-12-W8
git branch -D worktree-agent-batch-12-int
git branch -D worktree-agent-batch-13-W1
git branch -D worktree-agent-batch-13-W2
git branch -D worktree-agent-batch-13-W3
git branch -D worktree-agent-batch-13-int
git branch -D worktree-agent-batch-14-W1
git branch -D worktree-agent-batch-14-int
git branch -D worktree-agent-batch-15-W1
git branch -D worktree-agent-batch-15-int
git branch -D worktree-agent-batch-16-W1
git branch -D worktree-agent-batch-16-int
git branch -D worktree-agent-batch-17-W1
git branch -D worktree-agent-batch-17-int
git branch -D worktree-agent-batch-18-W1
git branch -D worktree-agent-batch-18-W2
git branch -D worktree-agent-batch-18-int
git branch -D worktree-agent-batch-19-W1
git branch -D worktree-agent-batch-19-int
git branch -D worktree-agent-batch-2-W1-fundamentals-seam
git branch -D worktree-agent-batch-2-W2-instrument-identity
git branch -D worktree-agent-batch-2-W3-research-integrity
git branch -D worktree-agent-batch-2-W4-workspace-persistence
git branch -D worktree-agent-batch-2-W5-surfaces-and-math
git branch -D worktree-agent-batch-2-int
git branch -D worktree-agent-batch-20-W1
git branch -D worktree-agent-batch-20-int
git branch -D worktree-agent-batch-21-W1
git branch -D worktree-agent-batch-21-W2
git branch -D worktree-agent-batch-21-int
git branch -D worktree-agent-batch-22-W1
git branch -D worktree-agent-batch-24-W1
git branch -D worktree-agent-batch-24-int
git branch -D worktree-agent-batch-25-W1
git branch -D worktree-agent-batch-25-W2
git branch -D worktree-agent-batch-25-W3
git branch -D worktree-agent-batch-25-W4
git branch -D worktree-agent-batch-25-W5
git branch -D worktree-agent-batch-25-W6
git branch -D worktree-agent-batch-25-W7
git branch -D worktree-agent-batch-25-int
git branch -D worktree-agent-batch-26-W1
git branch -D worktree-agent-batch-26-W2
git branch -D worktree-agent-batch-26-int
git branch -D worktree-agent-batch-27-W1
git branch -D worktree-agent-batch-27-int
git branch -D worktree-agent-batch-28-W1
git branch -D worktree-agent-batch-28-W2
git branch -D worktree-agent-batch-28-W3
git branch -D worktree-agent-batch-28-W4
git branch -D worktree-agent-batch-28-W5
git branch -D worktree-agent-batch-28-W6
git branch -D worktree-agent-batch-28-int
git branch -D worktree-agent-batch-29-W1
git branch -D worktree-agent-batch-29-W2
git branch -D worktree-agent-batch-29-W3
git branch -D worktree-agent-batch-29-W4
git branch -D worktree-agent-batch-29-int
git branch -D worktree-agent-batch-29-rework
git branch -D worktree-agent-batch-3-agent-frontend-gate
git branch -D worktree-agent-batch-3-agent-runtime
git branch -D worktree-agent-batch-3-india-data-witnesses
git branch -D worktree-agent-batch-3-int
git branch -D worktree-agent-batch-3-llm-adapters-and-errors
git branch -D worktree-agent-batch-3-research-depth
git branch -D worktree-agent-batch-30-A
git branch -D worktree-agent-batch-30-B
git branch -D worktree-agent-batch-30-adjudicate
git branch -D worktree-agent-batch-30-int
git branch -D worktree-agent-batch-30-rework
git branch -D worktree-agent-batch-4-W1-agent-runtime
git branch -D worktree-agent-batch-4-W2-workflow-backtest-feeds
git branch -D worktree-agent-batch-4-W3-chat-runs-mcp
git branch -D worktree-agent-batch-4-W4-market-data-gate
git branch -D worktree-agent-batch-4-W5-panels-screener
git branch -D worktree-agent-batch-4-int
git branch -D worktree-agent-batch-5-W1-india-disclosures-agent-surface
git branch -D worktree-agent-batch-5-W2-resolver-market-data
git branch -D worktree-agent-batch-5-W3-agent-runtime-chat
git branch -D worktree-agent-batch-5-W4-platform-workflow-boundary
git branch -D worktree-agent-batch-5-W5-screener-earnings-sec
git branch -D worktree-agent-batch-5-int
git branch -D worktree-agent-batch-6-W1-india-exchange-data
git branch -D worktree-agent-batch-6-W2-delegate-runs-runtime
git branch -D worktree-agent-batch-6-W3-unattended-platform-chart
git branch -D worktree-agent-batch-6-W4-research-funnel
git branch -D worktree-agent-batch-6-W5-host-actions-portfolio
git branch -D worktree-agent-batch-6-int
git branch -D worktree-agent-batch-7-W1-india-exchange-data
git branch -D worktree-agent-batch-7-W2-delegate-runs-runtime
git branch -D worktree-agent-batch-7-W3-unattended-chart-workspace
git branch -D worktree-agent-batch-7-W4-research-funnel
git branch -D worktree-agent-batch-7-W5-agent-writes-portfolio
git branch -D worktree-agent-batch-7-int
git branch -D worktree-agent-batch-8-W1-sidecar-lifecycle-transport
git branch -D worktree-agent-batch-8-W2-provider-readiness-host-actions
git branch -D worktree-agent-batch-8-W3-data-error-honesty
git branch -D worktree-agent-batch-8-W4-resolver-exchange-lanes
git branch -D worktree-agent-batch-8-W5-agent-runtime-research
git branch -D worktree-agent-batch-8-int
git branch -D worktree-agent-batch-9-W1-agent-runtime
git branch -D worktree-agent-batch-9-W2-research-search-news
git branch -D worktree-agent-batch-9-W3-fundamentals-identity-earnings
git branch -D worktree-agent-batch-9-W4-market-lanes-errors-quant
git branch -D worktree-agent-batch-9-W5-frontend-shell
git branch -D worktree-agent-batch-9-int
git branch -D worktree-agent-bhav
git branch -D worktree-agent-changelog-2
git branch -D worktree-agent-changelog-3
git branch -D worktree-agent-changelog-4
git branch -D worktree-agent-changelog-b29-b30
git branch -D worktree-agent-changelog-r4
git branch -D worktree-agent-changelog-r4audit
git branch -D worktree-agent-changelog-r5
git branch -D worktree-agent-fe
git branch -D worktree-agent-fixa
git branch -D worktree-agent-fixb
git branch -D worktree-agent-fixc
git branch -D worktree-agent-growth
git branch -D worktree-agent-hardening
git branch -D worktree-agent-hygiene-2
git branch -D worktree-agent-identity
git branch -D worktree-agent-jarvis
git branch -D worktree-agent-lastfix
git branch -D worktree-agent-narrative
git branch -D worktree-agent-panel
git branch -D worktree-agent-pushguard
git branch -D worktree-agent-r10-fedata
git branch -D worktree-agent-r10-frontend
git branch -D worktree-agent-r10-resolve
git branch -D worktree-agent-r10-runtime
git branch -D worktree-agent-r10-screener
git branch -D worktree-agent-r8-composer
git branch -D worktree-agent-r8-proportion
git branch -D worktree-agent-r8-research
git branch -D worktree-agent-r8-seams
git branch -D worktree-agent-r8-settings
git branch -D worktree-agent-rc1-4097dac-fix-int
git branch -D worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage
git branch -D worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary
git branch -D worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived
git branch -D worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs
git branch -D worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency
git branch -D worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail
git branch -D worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache
git branch -D worktree-agent-rc1-gate-lanes
git branch -D worktree-agent-rc1-gate-r3
git branch -D worktree-agent-rc1-gate-r4
git branch -D worktree-agent-rc1-gate-r5
git branch -D worktree-agent-rc1-r5-adjudicate
git branch -D worktree-agent-rc1-r5-fix-focus
git branch -D worktree-agent-rc1-r5-fix-int
git branch -D worktree-agent-rc1-round-3-01d6920-fix-int
git branch -D worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize
git branch -D worktree-agent-rc1-round-4-1006c6d-fix-int
git branch -D worktree-agent-rc1-round-4-1006c6d-fix-r1-W1-autobrief-staged
git branch -D worktree-agent-rc1-round-4-1006c6d-fix-r1-W2-yf-not-found
git branch -D worktree-agent-rc1-round-4-1006c6d-fix-r1-W3-resolver-current-name
git branch -D worktree-agent-rc1-round-5-9bc600e-fix-int
git branch -D worktree-agent-rc1-round-5-9bc600e-fix-r1-insider-table
git branch -D worktree-agent-res
git branch -D worktree-agent-retrieval
git branch -D worktree-agent-rig
git branch -D worktree-agent-searxfloor
git branch -D worktree-agent-sem
git branch -D worktree-agent-smokefix
git branch -D worktree-agent-spine
git branch -D worktree-agent-trading-docs
git branch -D worktree-agent-trading-frontend
git branch -D worktree-agent-trading-int
git branch -D worktree-agent-trading-sidecar
git branch -D worktree-agent-wireup
git branch -D worktree-agent-witness
git branch -D worktree-wf_046c15b6-ff0-3
git branch -D worktree-wf_046c15b6-ff0-4
git branch -D worktree-wf_046c15b6-ff0-5
git branch -D worktree-wf_046c15b6-ff0-6
git branch -D worktree-wf_046c15b6-ff0-7
git branch -D worktree-wf_046c15b6-ff0-8
git branch -D worktree-wf_0b0dfe4e-282-3
git branch -D worktree-wf_0b0dfe4e-282-4
git branch -D worktree-wf_116e8cdf-429-1
git branch -D worktree-wf_152b123d-228-3
git branch -D worktree-wf_17b6cbe4-389-3
git branch -D worktree-wf_17b6cbe4-389-4
git branch -D worktree-wf_17b6cbe4-389-5
git branch -D worktree-wf_17b6cbe4-389-6
git branch -D worktree-wf_17b6cbe4-389-7
git branch -D worktree-wf_1e4295f3-748-3
git branch -D worktree-wf_1e4295f3-748-4
git branch -D worktree-wf_1e4295f3-748-5
git branch -D worktree-wf_232102df-2f0-3
git branch -D worktree-wf_36d043fa-61f-3
git branch -D worktree-wf_36d043fa-61f-4
git branch -D worktree-wf_36d043fa-61f-5
git branch -D worktree-wf_36d043fa-61f-6
git branch -D worktree-wf_36d043fa-61f-7
git branch -D worktree-wf_3bab62fa-c4d-18
git branch -D worktree-wf_3d774b10-8d4-1
git branch -D worktree-wf_3d774b10-8d4-13
git branch -D worktree-wf_3d774b10-8d4-14
git branch -D worktree-wf_3d774b10-8d4-15
git branch -D worktree-wf_3d774b10-8d4-17
git branch -D worktree-wf_3d774b10-8d4-2
git branch -D worktree-wf_3d774b10-8d4-3
git branch -D worktree-wf_3d774b10-8d4-4
git branch -D worktree-wf_3d774b10-8d4-5
git branch -D worktree-wf_3d774b10-8d4-6
git branch -D worktree-wf_3e8a9abe-7f7-3
git branch -D worktree-wf_3e8a9abe-7f7-4
git branch -D worktree-wf_3e8b0f3e-a84-3
git branch -D worktree-wf_45b81e1e-57a-1
git branch -D worktree-wf_48478ec5-daf-3
git branch -D worktree-wf_48478ec5-daf-4
git branch -D worktree-wf_48478ec5-daf-5
git branch -D worktree-wf_48478ec5-daf-6
git branch -D worktree-wf_48478ec5-daf-7
git branch -D worktree-wf_4ed38558-4d0-25
git branch -D worktree-wf_4ed38558-4d0-26
git branch -D worktree-wf_4ed38558-4d0-29
git branch -D worktree-wf_54334d97-0e6-10
git branch -D worktree-wf_54334d97-0e6-3
git branch -D worktree-wf_54334d97-0e6-4
git branch -D worktree-wf_54334d97-0e6-5
git branch -D worktree-wf_54334d97-0e6-6
git branch -D worktree-wf_54334d97-0e6-7
git branch -D worktree-wf_54334d97-0e6-8
git branch -D worktree-wf_54334d97-0e6-9
git branch -D worktree-wf_5c799024-a29-3
git branch -D worktree-wf_5c799024-a29-4
git branch -D worktree-wf_5c799024-a29-5
git branch -D worktree-wf_5c799024-a29-6
git branch -D worktree-wf_5c799024-a29-7
git branch -D worktree-wf_6871fdb3-621-10
git branch -D worktree-wf_6871fdb3-621-11
git branch -D worktree-wf_727db864-af6-3
git branch -D worktree-wf_7c4b2e60-141-25
git branch -D worktree-wf_7c4b2e60-141-26
git branch -D worktree-wf_7c4b2e60-141-27
git branch -D worktree-wf_7c4b2e60-141-28
git branch -D worktree-wf_7c4b2e60-141-32
git branch -D worktree-wf_7c4b2e60-141-33
git branch -D worktree-wf_7c4b2e60-141-34
git branch -D worktree-wf_7ded8293-3fe-42
git branch -D worktree-wf_7e4c4a3f-085-10
git branch -D worktree-wf_7e4c4a3f-085-3
git branch -D worktree-wf_7e4c4a3f-085-4
git branch -D worktree-wf_7e4c4a3f-085-5
git branch -D worktree-wf_7e4c4a3f-085-6
git branch -D worktree-wf_7e4c4a3f-085-7
git branch -D worktree-wf_7e4c4a3f-085-8
git branch -D worktree-wf_7e4c4a3f-085-9
git branch -D worktree-wf_80230d64-134-3
git branch -D worktree-wf_942ece8f-ad9-3
git branch -D worktree-wf_942ece8f-ad9-4
git branch -D worktree-wf_94ccf2b8-e97-3
git branch -D worktree-wf_94ccf2b8-e97-4
git branch -D worktree-wf_94ccf2b8-e97-5
git branch -D worktree-wf_94ccf2b8-e97-6
git branch -D worktree-wf_94ccf2b8-e97-7
git branch -D worktree-wf_9f29ee60-ba0-2
git branch -D worktree-wf_9f29ee60-ba0-3
git branch -D worktree-wf_9f29ee60-ba0-4
git branch -D worktree-wf_a342e2a8-74a-10
git branch -D worktree-wf_a342e2a8-74a-2
git branch -D worktree-wf_a342e2a8-74a-3
git branch -D worktree-wf_a342e2a8-74a-4
git branch -D worktree-wf_a342e2a8-74a-5
git branch -D worktree-wf_a342e2a8-74a-6
git branch -D worktree-wf_a342e2a8-74a-7
git branch -D worktree-wf_a342e2a8-74a-8
git branch -D worktree-wf_a342e2a8-74a-9
git branch -D worktree-wf_a404279c-3f4-42
git branch -D worktree-wf_a404279c-3f4-43
git branch -D worktree-wf_a404279c-3f4-44
git branch -D worktree-wf_a5e688ba-d35-10
git branch -D worktree-wf_a5e688ba-d35-3
git branch -D worktree-wf_a5e688ba-d35-4
git branch -D worktree-wf_a5e688ba-d35-5
git branch -D worktree-wf_a5e688ba-d35-6
git branch -D worktree-wf_a5e688ba-d35-7
git branch -D worktree-wf_a5e688ba-d35-8
git branch -D worktree-wf_a5e688ba-d35-9
git branch -D worktree-wf_aaf73f27-1c5-3
git branch -D worktree-wf_aaf73f27-1c5-4
git branch -D worktree-wf_aaf73f27-1c5-5
git branch -D worktree-wf_aaf73f27-1c5-6
git branch -D worktree-wf_aaf73f27-1c5-7
git branch -D worktree-wf_b1ca86d0-402-3
git branch -D worktree-wf_b7cf82ec-5ec-3
git branch -D worktree-wf_b829ac35-3a5-3
git branch -D worktree-wf_b829ac35-3a5-4
git branch -D worktree-wf_b829ac35-3a5-5
git branch -D worktree-wf_b829ac35-3a5-6
git branch -D worktree-wf_b829ac35-3a5-7
git branch -D worktree-wf_c1b4581a-8d6-3
git branch -D worktree-wf_c1b4581a-8d6-4
git branch -D worktree-wf_d476870a-216-3
git branch -D worktree-wf_d476870a-216-4
git branch -D worktree-wf_d476870a-216-5
git branch -D worktree-wf_d476870a-216-6
git branch -D worktree-wf_dab096e5-3ae-3
git branch -D worktree-wf_e17e21c5-cb8-3
git branch -D worktree-wf_e64eeddf-e23-10
git branch -D worktree-wf_e64eeddf-e23-2
git branch -D worktree-wf_e64eeddf-e23-3
git branch -D worktree-wf_e64eeddf-e23-4
git branch -D worktree-wf_e64eeddf-e23-5
git branch -D worktree-wf_e64eeddf-e23-6
git branch -D worktree-wf_e64eeddf-e23-7
git branch -D worktree-wf_e64eeddf-e23-8
git branch -D worktree-wf_e64eeddf-e23-9
git branch -D worktree-wf_ea0144f4-04a-3
git branch -D worktree-wf_ea0144f4-04a-4
git branch -D worktree-wf_f37de2ba-9d1-3
git branch -D worktree-wf_f37de2ba-9d1-4
git branch -D worktree-wf_f37de2ba-9d1-5
git branch -D worktree-wf_f37de2ba-9d1-6
git branch -D worktree-wf_f37de2ba-9d1-7
git branch -D worktree-wf_f724edac-bff-10
git branch -D worktree-wf_f724edac-bff-2
git branch -D worktree-wf_f724edac-bff-3
git branch -D worktree-wf_f724edac-bff-4
git branch -D worktree-wf_f724edac-bff-5
git branch -D worktree-wf_f724edac-bff-6
git branch -D worktree-wf_f724edac-bff-7
git branch -D worktree-wf_f724edac-bff-8
git branch -D worktree-wf_f724edac-bff-9
git branch -D worktree-wf_fbb7a07b-9f8-3
git branch -D worktree-wf_fbb7a07b-9f8-4
git branch -D worktree-wf_fbb7a07b-9f8-5
git branch -D worktree-wf_fbb7a07b-9f8-6
git branch -D worktree-wf_fbb7a07b-9f8-7
git branch -D worktree-wf_fbb7a07b-9f8-8
git branch -D worktree-wf_fbb7a07b-9f8-9

# --- origin deletes (227) — prefix each with the GIT_SSH_COMMAND above ---
git push origin --delete 001-agent-native-redesign
git push origin --delete 002-jarvis-intelligence
git push origin --delete 003-vysted-rebuild
git push origin --delete origin  # branch literally named 'origin' — unusual, double-check before running
git push origin --delete verify-rc1-r5-fix
git push origin --delete worktree-agent-a882d06f8e7c3ff56
git push origin --delete worktree-agent-a9d8467a798247f72
git push origin --delete worktree-agent-batch-10-W1-runtime-backtest
git push origin --delete worktree-agent-batch-10-W2-catalog-hostactions
git push origin --delete worktree-agent-batch-10-W3-fundamentals-bse-cache
git push origin --delete worktree-agent-batch-10-W4-screener-routes-statedocs
git push origin --delete worktree-agent-batch-10-W5-chat-search-workflow
git push origin --delete worktree-agent-batch-10-W6-chart-notes-blueprint
git push origin --delete worktree-agent-batch-10-W7-panels-marketplace
git push origin --delete worktree-agent-batch-10-W8-plugins-dock
git push origin --delete worktree-agent-batch-10-int
git push origin --delete worktree-agent-batch-11-W1-scripts-build
git push origin --delete worktree-agent-batch-11-W2-runtime-schema
git push origin --delete worktree-agent-batch-11-W3-agent-eval
git push origin --delete worktree-agent-batch-11-W4-registry-loop
git push origin --delete worktree-agent-batch-11-W5-data-reference
git push origin --delete worktree-agent-batch-11-W6-options-chain
git push origin --delete worktree-agent-batch-11-W7-preferences
git push origin --delete worktree-agent-batch-11-W8-frontend-visual
git push origin --delete worktree-agent-batch-11-int
git push origin --delete worktree-agent-batch-12-W1
git push origin --delete worktree-agent-batch-12-W2
git push origin --delete worktree-agent-batch-12-W3
git push origin --delete worktree-agent-batch-12-W4
git push origin --delete worktree-agent-batch-12-W5
git push origin --delete worktree-agent-batch-12-W6
git push origin --delete worktree-agent-batch-12-W7
git push origin --delete worktree-agent-batch-12-W8
git push origin --delete worktree-agent-batch-12-int
git push origin --delete worktree-agent-batch-13-W1
git push origin --delete worktree-agent-batch-13-W2
git push origin --delete worktree-agent-batch-13-W3
git push origin --delete worktree-agent-batch-13-int
git push origin --delete worktree-agent-batch-14-W1
git push origin --delete worktree-agent-batch-14-int
git push origin --delete worktree-agent-batch-15-W1
git push origin --delete worktree-agent-batch-15-int
git push origin --delete worktree-agent-batch-16-W1
git push origin --delete worktree-agent-batch-16-int
git push origin --delete worktree-agent-batch-17-W1
git push origin --delete worktree-agent-batch-17-int
git push origin --delete worktree-agent-batch-18-W1
git push origin --delete worktree-agent-batch-18-W2
git push origin --delete worktree-agent-batch-18-int
git push origin --delete worktree-agent-batch-19-W1
git push origin --delete worktree-agent-batch-19-int
git push origin --delete worktree-agent-batch-2-W1-fundamentals-seam
git push origin --delete worktree-agent-batch-2-W2-instrument-identity
git push origin --delete worktree-agent-batch-2-W3-research-integrity
git push origin --delete worktree-agent-batch-2-W4-workspace-persistence
git push origin --delete worktree-agent-batch-2-W5-surfaces-and-math
git push origin --delete worktree-agent-batch-2-int
git push origin --delete worktree-agent-batch-20-W1
git push origin --delete worktree-agent-batch-20-int
git push origin --delete worktree-agent-batch-21-W1
git push origin --delete worktree-agent-batch-21-W2
git push origin --delete worktree-agent-batch-21-int
git push origin --delete worktree-agent-batch-22-W1
git push origin --delete worktree-agent-batch-24-W1
git push origin --delete worktree-agent-batch-24-int
git push origin --delete worktree-agent-batch-25-W1
git push origin --delete worktree-agent-batch-25-W2
git push origin --delete worktree-agent-batch-25-W3
git push origin --delete worktree-agent-batch-25-W4
git push origin --delete worktree-agent-batch-25-W5
git push origin --delete worktree-agent-batch-25-W6
git push origin --delete worktree-agent-batch-25-W7
git push origin --delete worktree-agent-batch-25-int
git push origin --delete worktree-agent-batch-26-W1
git push origin --delete worktree-agent-batch-26-W2
git push origin --delete worktree-agent-batch-26-int
git push origin --delete worktree-agent-batch-27-W1
git push origin --delete worktree-agent-batch-27-int
git push origin --delete worktree-agent-batch-28-W1
git push origin --delete worktree-agent-batch-28-W2
git push origin --delete worktree-agent-batch-28-W3
git push origin --delete worktree-agent-batch-28-W4
git push origin --delete worktree-agent-batch-28-W5
git push origin --delete worktree-agent-batch-28-W6
git push origin --delete worktree-agent-batch-28-int
git push origin --delete worktree-agent-batch-29-W1
git push origin --delete worktree-agent-batch-29-W2
git push origin --delete worktree-agent-batch-29-W3
git push origin --delete worktree-agent-batch-29-W4
git push origin --delete worktree-agent-batch-29-int
git push origin --delete worktree-agent-batch-29-rework
git push origin --delete worktree-agent-batch-3-agent-frontend-gate
git push origin --delete worktree-agent-batch-3-agent-runtime
git push origin --delete worktree-agent-batch-3-india-data-witnesses
git push origin --delete worktree-agent-batch-3-int
git push origin --delete worktree-agent-batch-3-llm-adapters-and-errors
git push origin --delete worktree-agent-batch-3-research-depth
git push origin --delete worktree-agent-batch-30-A
git push origin --delete worktree-agent-batch-30-B
git push origin --delete worktree-agent-batch-30-adjudicate
git push origin --delete worktree-agent-batch-30-int
git push origin --delete worktree-agent-batch-30-rework
git push origin --delete worktree-agent-batch-4-W1-agent-runtime
git push origin --delete worktree-agent-batch-4-W2-workflow-backtest-feeds
git push origin --delete worktree-agent-batch-4-W3-chat-runs-mcp
git push origin --delete worktree-agent-batch-4-W4-market-data-gate
git push origin --delete worktree-agent-batch-4-W5-panels-screener
git push origin --delete worktree-agent-batch-4-int
git push origin --delete worktree-agent-batch-5-W1-india-disclosures-agent-surface
git push origin --delete worktree-agent-batch-5-W2-resolver-market-data
git push origin --delete worktree-agent-batch-5-W3-agent-runtime-chat
git push origin --delete worktree-agent-batch-5-W4-platform-workflow-boundary
git push origin --delete worktree-agent-batch-5-W5-screener-earnings-sec
git push origin --delete worktree-agent-batch-5-int
git push origin --delete worktree-agent-batch-6-W1-india-exchange-data
git push origin --delete worktree-agent-batch-6-W2-delegate-runs-runtime
git push origin --delete worktree-agent-batch-6-W3-unattended-platform-chart
git push origin --delete worktree-agent-batch-6-W4-research-funnel
git push origin --delete worktree-agent-batch-6-W5-host-actions-portfolio
git push origin --delete worktree-agent-batch-6-int
git push origin --delete worktree-agent-batch-7-W1-india-exchange-data
git push origin --delete worktree-agent-batch-7-W2-delegate-runs-runtime
git push origin --delete worktree-agent-batch-7-W3-unattended-chart-workspace
git push origin --delete worktree-agent-batch-7-W4-research-funnel
git push origin --delete worktree-agent-batch-7-W5-agent-writes-portfolio
git push origin --delete worktree-agent-batch-7-int
git push origin --delete worktree-agent-batch-8-W1-sidecar-lifecycle-transport
git push origin --delete worktree-agent-batch-8-W2-provider-readiness-host-actions
git push origin --delete worktree-agent-batch-8-W3-data-error-honesty
git push origin --delete worktree-agent-batch-8-W4-resolver-exchange-lanes
git push origin --delete worktree-agent-batch-8-W5-agent-runtime-research
git push origin --delete worktree-agent-batch-8-int
git push origin --delete worktree-agent-batch-9-W1-agent-runtime
git push origin --delete worktree-agent-batch-9-W2-research-search-news
git push origin --delete worktree-agent-batch-9-W3-fundamentals-identity-earnings
git push origin --delete worktree-agent-batch-9-W4-market-lanes-errors-quant
git push origin --delete worktree-agent-batch-9-W5-frontend-shell
git push origin --delete worktree-agent-batch-9-int
git push origin --delete worktree-agent-bhav
git push origin --delete worktree-agent-brief
git push origin --delete worktree-agent-changelog-2
git push origin --delete worktree-agent-changelog-3
git push origin --delete worktree-agent-changelog-4
git push origin --delete worktree-agent-changelog-b29-b30
git push origin --delete worktree-agent-changelog-r4
git push origin --delete worktree-agent-changelog-r4audit
git push origin --delete worktree-agent-changelog-r5
git push origin --delete worktree-agent-chat-experience
git push origin --delete worktree-agent-composer
git push origin --delete worktree-agent-consistency
git push origin --delete worktree-agent-data-panels
git push origin --delete worktree-agent-fe
git push origin --delete worktree-agent-fixa
git push origin --delete worktree-agent-fixb
git push origin --delete worktree-agent-fixc
git push origin --delete worktree-agent-growth
git push origin --delete worktree-agent-hardening
git push origin --delete worktree-agent-hygiene-2
git push origin --delete worktree-agent-identity
git push origin --delete worktree-agent-jarvis
git push origin --delete worktree-agent-lastfix
git push origin --delete worktree-agent-layout
git push origin --delete worktree-agent-narrative
git push origin --delete worktree-agent-overview-narrative
git push origin --delete worktree-agent-panel
git push origin --delete worktree-agent-pins
git push origin --delete worktree-agent-r10-fedata
git push origin --delete worktree-agent-r10-frontend
git push origin --delete worktree-agent-r10-resolve
git push origin --delete worktree-agent-r10-runtime
git push origin --delete worktree-agent-r10-screener
git push origin --delete worktree-agent-r7-chart
git push origin --delete worktree-agent-r7-chat
git push origin --delete worktree-agent-r7-data
git push origin --delete worktree-agent-r7-hack
git push origin --delete worktree-agent-r7-panels
git push origin --delete worktree-agent-r7-research
git push origin --delete worktree-agent-r7-tiers
git push origin --delete worktree-agent-r8-composer
git push origin --delete worktree-agent-r8-proportion
git push origin --delete worktree-agent-r8-research
git push origin --delete worktree-agent-r8-seams
git push origin --delete worktree-agent-r8-settings
git push origin --delete worktree-agent-r9-composer
git push origin --delete worktree-agent-r9-loop
git push origin --delete worktree-agent-r9-proportion
git push origin --delete worktree-agent-r9-settings
git push origin --delete worktree-agent-r9-tiers
git push origin --delete worktree-agent-rc1-4097dac-fix-int
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs
git push origin --delete worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency
git push origin --delete worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail
git push origin --delete worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache
git push origin --delete worktree-agent-rc1-gate-lanes
git push origin --delete worktree-agent-rc1-gate-r3
git push origin --delete worktree-agent-rc1-gate-r4
git push origin --delete worktree-agent-rc1-gate-r5
git push origin --delete worktree-agent-rc1-r5-adjudicate
git push origin --delete worktree-agent-rc1-r5-fix-focus
git push origin --delete worktree-agent-rc1-r5-fix-int
git push origin --delete worktree-agent-rc1-round-3-01d6920-fix-int
git push origin --delete worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize
git push origin --delete worktree-agent-rc1-round-4-1006c6d-fix-int
git push origin --delete worktree-agent-rc1-round-4-1006c6d-fix-r1-W1-autobrief-staged
git push origin --delete worktree-agent-rc1-round-4-1006c6d-fix-r1-W2-yf-not-found
git push origin --delete worktree-agent-rc1-round-4-1006c6d-fix-r1-W3-resolver-current-name
git push origin --delete worktree-agent-rc1-round-5-9bc600e-fix-int
git push origin --delete worktree-agent-rc1-round-5-9bc600e-fix-r1-insider-table
git push origin --delete worktree-agent-res
git push origin --delete worktree-agent-retrieval
git push origin --delete worktree-agent-rig
git push origin --delete worktree-agent-screener-backoff
git push origin --delete worktree-agent-searxfloor
git push origin --delete worktree-agent-sem
git push origin --delete worktree-agent-smokefix
git push origin --delete worktree-agent-space-memory
git push origin --delete worktree-agent-spine
git push origin --delete worktree-agent-surfaces
git push origin --delete worktree-agent-trading-docs
git push origin --delete worktree-agent-trading-frontend
git push origin --delete worktree-agent-trading-int
git push origin --delete worktree-agent-trading-sidecar
git push origin --delete worktree-agent-wireup
git push origin --delete worktree-agent-witness

```

### SUPERSEDED

```bash
# --- local branch deletes (5) ---
git branch -D worktree-agent-batch-25-W1-data002-wip
git branch -D worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class
git branch -D worktree-agent-research
git branch -D worktree-agent-screener-perf
git branch -D worktree-wf_3d774b10-8d4-10

# --- origin deletes (7) — prefix each with the GIT_SSH_COMMAND above ---
git push origin --delete phase-1a-foundation
git push origin --delete worktree-agent-batch-25-W1-data002-wip
git push origin --delete worktree-agent-design-doc
git push origin --delete worktree-agent-formula
git push origin --delete worktree-agent-research
git push origin --delete worktree-agent-screener-perf
git push origin --delete worktree-agent-screener-perf-v2

```

### UNPUSHED-LIVE (judgment call — NOT auto-run; lead decides after reading the diff)

```bash
# worktree-agent-palette — 1 unpushed, unmerged commit; recommend DEAD (see §4) but do not run blind:
# git log -p a2b3a21c -1   # review the diff first
# git worktree remove .claude/worktrees/agent-a47228f53658c48ac
# git branch -D worktree-agent-palette
# GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20" git push origin --delete worktree-agent-palette
```

### SELF (this audit's own branch/worktree — remove after this plan is merged, not now)

```bash
# after worktree-agent-hygiene-plan-rc1 is merged into 004:
# git worktree remove /private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/hygiene-plan
# git branch -D worktree-agent-hygiene-plan-rc1
# GIT_SSH_COMMAND="ssh -i $HOME/.ssh/id_ed25519 -o IdentitiesOnly=yes -o ConnectTimeout=20" git push origin --delete worktree-agent-hygiene-plan-rc1
```

### KEEP branches flagged for a FUTURE cleanup pass (not this window — listed for visibility only, no commands)

- `worktree-agent-batch-22-W2`, `worktree-agent-batch-22-int`, `worktree-agent-batch-23-W1`, `worktree-agent-batch-23-int` — the two LEAD-035 no-tool-cue-matcher rounds, both blocked, never certified (register: `ab2c29de`, `0c18af28`).
- `worktree-agent-rc1-4c6dfe8-fix-int`, `-fix-r1-W1-citation-marker-grammar`, `-fix-r2-W1-citation-grammar-r2` — the two failed R15-RESEARCH-043 citation-grammar rounds (register: `62c11c8e`), open defect, never landed.
- `worktree-agent-r10-errors` (+ its duplicate local pointer `worktree-wf_3d774b10-8d4-10`, already handled as SUPERSEDED above) — old R10-era work, no trace in the 004 log.
- `worktree-agent-design`, `worktree-agent-notes` — unmerged drafts in subsystems (design tokens, notes editor) that 004 later reimplemented differently; not exact-subject-matched so left KEEP rather than guessed superseded.

