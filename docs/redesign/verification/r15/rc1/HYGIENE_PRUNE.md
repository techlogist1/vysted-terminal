# R15 rc1 Hygiene Prune Inventory

Read-only inventory for the lead's hygiene pass. Nothing in this document deletes,
prunes, or checks anything out — every line below is either sourced directly from a
git command run against `/Users/lokavyasingh/Documents/dev/vysted-terminal` on branch
`004-r4-experience-rebuild`, or is the pasted output of `scripts/r15/hygiene_inventory.py`
(added in this same commit), which re-derives this exact classification straight from
git on demand.

Snapshot captured **01:27 IST, 2026-09-27**. Base: `origin/004-r4-experience-rebuild` @
`045da329895e0a31fae53630ad581429980ced3e`. The prior capture in this document was
**07:11 IST, 2026-09-26** — many commits/runs ago (batch-25 through batch-27, several
changelog and rc1-gate rounds, and rc1 fix rounds 1-3 have all landed since; the base
sha itself moved twice more while this refresh was being written, which is expected
with the gate run live).

**Caveat: two rc1 gate attempts are LIVE right now** — `wf_f8604b35-a49` (round-4,
attempt 1) and `wf_a404279c-3f4` (round-4, attempt 2, launched after attempt 1 blocked
on a sidecar-build wait). Worktrees under `.claude/worktrees/wf_f8604b35-a49-*` and
`.claude/worktrees/wf_a404279c-3f4-*`, and branches `worktree-agent-rc1-round-4-*`, may
appear, move, or disappear while this snapshot is being read — treat any SHA touching
either run as indicative of the moment captured, not frozen fact. The main checkout and
every worktree registered under this session's scratchpad are live burst-agent or gate
infrastructure — see the `LIVE` rows below.

**Re-run the script at prune time; do not act on this snapshot's shas.** For example:

```
python3 scripts/r15/hygiene_inventory.py \
  --live-run wf_f8604b35-a49 \
  --live-run wf_a404279c-3f4 \
  --live-path /path/to/session/scratchpad
```

`--base` overrides the comparison ref, `--tag r15-rc1` (once that tag exists) adds an
ancestor-of-tag cross-check, `--keep <glob>` overrides which branch names are never
proposed for deletion (default: `main`, `master`, `00[0-9]-*` — the milestone branches
land in a `KEEP-MILESTONE` bucket, informational only, never in the exact-commands
section), and `--json` emits the same classification as JSON. The script's
`SAFE-LOCAL-DELETE` / `git worktree remove` / `git branch -d` proposals are otherwise
purely mechanical (merged into base + identical to its origin counterpart, or a
registered worktree whose tip is merged and not live). It never proposes deleting a
remote (`origin/*`) branch, by design — remote deletion stays a manual, deliberate lead
action.

No `r15-*` tag exists yet (`git tag -l 'r15-*'` returns nothing) — this document is
still prepared in advance of the rc1 tag.

---
## 1. Registered worktrees

Source: `git worktree list --porcelain`, base `origin/004-r4-experience-rebuild` @ `045da329895e0a31fae53630ad581429980ced3e`.

| Path | Branch | Tip | Path exists? | Status |
|---|---|---|---|---|
| `/Users/lokavyasingh/Documents/dev/vysted-terminal` | `004-r4-experience-rebuild` | `045da329` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-25-int` | `worktree-agent-batch-25-int` | `2e988c0d` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-26-int` | `worktree-agent-batch-26-int` | `2e1950fe` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/batch-27-int` | `worktree-agent-batch-27-int` | `9bb60037` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-2` | `worktree-agent-changelog-2` | `fecdde48` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-3` | `worktree-agent-changelog-3` | `3f580b14` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/changelog-4` | `worktree-agent-changelog-4` | `1a9257c7` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/gate-r3` | `worktree-agent-rc1-gate-r3` | `6553c92d` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/gate-r4` | `worktree-agent-rc1-gate-r4` | `f906f219` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/hygiene-2` | `worktree-agent-hygiene-2` | `11f6e057` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-agent-077` | `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` | `80f8d7a2` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-code-agent-031` | `worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` | `695e934a` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-code-data-019` | `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` | `31aa053b` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-code-frontend-027` | `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` | `cba8df9f` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-code-research-005` | `worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` | `113ab130` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-data-102` | `worktree-agent-lows-CN-r15-data-102-4c6dfe8` | `09d8da83` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-cn/r15-lifecycle-035` | `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` | `954ffa89` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-deferred-A` | `worktree-agent-lows-DEF-A-4c6dfe8` | `8113ddc1` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-deferred-B` | `worktree-agent-lows-DEF-B-4c6dfe8` | `af933bcc` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-lead036` | `worktree-agent-lows-LEAD-036-4c6dfe8` | `8315c857` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-new-lows` | `worktree-agent-lows-NEW-drafted-4c6dfe8` | `abcee383` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-preint/P1` | `worktree-agent-lows-P1-int-4c6dfe8` | `dbe5fe4f` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-preint/P2` | `worktree-agent-lows-P2-int-4c6dfe8` | `78220d0c` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/lows-preint/P3` | `worktree-agent-lows-P3-int-4c6dfe8` | `f9da207a` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-4c6dfe8-fix-int` | `worktree-agent-rc1-4c6dfe8-fix-int` | `81fbfe91` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-cand` | `*(detached)*` | `4c6dfe8c` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-3-01d6920-fix-int` | `worktree-agent-rc1-round-3-01d6920-fix-int` | `5ff9be04` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-3-cand` | `*(detached)*` | `01d6920a` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/rc1-round-4-cand` | `*(detached)*` | `1006c6da` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/version-0.9.0` | `worktree-agent-r15-version-0.9.0` | `c1e9164c` | yes | **LIVE** |
| `/private/tmp/claude-501/-Users-lokavyasingh-Documents-dev-vysted-terminal/3e7ae14d-d48a-4882-8a75-f7608754c23f/scratchpad/version-0.9.0-rc1` | `worktree-agent-r15-version-0.9.0-rc1` | `1dfda1f3` | yes | **LIVE** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/agent-a47228f53658c48ac` | `worktree-agent-palette` | `a2b3a21c` | yes | **UNMERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_3bab62fa-c4d-18` | `worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize` | `ac0d8617` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_4ed38558-4d0-25` | `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar` | `a30f693c` | yes | **UNMERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_4ed38558-4d0-26` | `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class` | `39585dc3` | yes | **UNMERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_4ed38558-4d0-29` | `worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2` | `39585dc3` | yes | **UNMERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_80230d64-134-3` | `worktree-agent-batch-27-W1` | `b80f082b` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_942ece8f-ad9-3` | `worktree-agent-batch-26-W1` | `4d7bc887` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_942ece8f-ad9-4` | `worktree-agent-batch-26-W2` | `a5a72488` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-3` | `worktree-agent-batch-25-W1` | `ef102fa5` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-4` | `worktree-agent-batch-25-W2` | `ab826232` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-5` | `worktree-agent-batch-25-W3` | `ce63da47` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-6` | `worktree-agent-batch-25-W4` | `aecc9dab` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-7` | `worktree-agent-batch-25-W5` | `1288ec19` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-8` | `worktree-agent-batch-25-W6` | `816f7cac` | yes | **MERGED** |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-9` | `worktree-agent-batch-25-W7` | `8f0962bb` | yes | **MERGED** |

### Palette worktree finding (pre-R15, `.claude/worktrees/agent-a47228f53658c48ac`)

Facts re-verified at this snapshot; unchanged from the prior capture:

- Branch: `worktree-agent-palette`. `git -C <path> log -3`:
  - `a2b3a21c` 2026-06-05 `feat(palette): rebuild CommandPalette with cmdk (FR-120/SC-031)`
  - `cfcf5bef` 2026-05-31 `docs(spec): amend redesign spec — plugin marketplace as the primary extensibility model`
  - `93525654` 2026-05-30 `docs(spec): add redesign constitution v1.0.0 + agent-native spec (clarified)`
- `git -C <path> status --short`: clean, nothing uncommitted in the checkout.
- The **local** branch ref (`a2b3a21c`) is stale: `origin/worktree-agent-palette` has moved
  on to `71bf9b40` (`feat(palette): empty-query state, EmptyState no-results, off-scale
  fixes (R5 §15/§16)`), and `git merge-base --is-ancestor origin/worktree-agent-palette
  004-r4-experience-rebuild` **succeeds** — the branch's real tip is already merged into
  004. Only this specific local worktree checkout never advanced past the branch's first
  commit.
- Diffing the local worktree's touched files (`package.json`, `pnpm-lock.yaml`,
  `src/components/CommandPalette.tsx`, `src/modules/chat/ChatSidebar.tsx`,
  `src/store/chat-pending.ts`, `src/store/command-palette.test.ts`,
  `src/store/command-palette.ts`) against 004's current tree: all seven paths still exist
  in 004 (`git cat-file -e 004-r4-experience-rebuild:<path>` succeeds for all, re-checked
  at this snapshot). `cmdk` is still a 004 dependency (`package.json` →
  `"cmdk": "1.1.1"`).
- **Nothing in this worktree is absent from 004.** It is a superseded, stale snapshot of
  work whose full branch history already landed. Lead decides whether to keep it around
  for archaeology or reclaim the directory; recommendation is prune-eligible but not
  forced here. The script classifies this worktree `UNMERGED` (its local tip, not the
  origin branch's tip, is what's checked) — that is correct and expected given the above,
  not a bug.

## 2. Local branches

Source: `git for-each-ref refs/heads` (400 refs), cross-checked against `origin/<name>`.

### CHECKED-OUT (worktree) — never proposed (44)

- `004-r4-experience-rebuild` `045da329`
- `main` `cfcf5bef`
- `worktree-agent-batch-25-W1` `ef102fa5`
- `worktree-agent-batch-25-W2` `ab826232`
- `worktree-agent-batch-25-W3` `ce63da47`
- `worktree-agent-batch-25-W4` `aecc9dab`
- `worktree-agent-batch-25-W5` `1288ec19`
- `worktree-agent-batch-25-W6` `816f7cac`
- `worktree-agent-batch-25-W7` `8f0962bb`
- `worktree-agent-batch-25-int` `2e988c0d`
- `worktree-agent-batch-26-W1` `4d7bc887`
- `worktree-agent-batch-26-W2` `a5a72488`
- `worktree-agent-batch-26-int` `2e1950fe`
- `worktree-agent-batch-27-W1` `b80f082b`
- `worktree-agent-batch-27-int` `9bb60037`
- `worktree-agent-changelog-2` `fecdde48`
- `worktree-agent-changelog-3` `3f580b14`
- `worktree-agent-changelog-4` `1a9257c7`
- `worktree-agent-hygiene-2` `11f6e057`
- `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` `80f8d7a2`
- `worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` `695e934a`
- `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` `31aa053b`
- `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` `cba8df9f`
- `worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` `113ab130`
- `worktree-agent-lows-CN-r15-data-102-4c6dfe8` `09d8da83`
- `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` `954ffa89`
- `worktree-agent-lows-DEF-A-4c6dfe8` `8113ddc1`
- `worktree-agent-lows-DEF-B-4c6dfe8` `af933bcc`
- `worktree-agent-lows-LEAD-036-4c6dfe8` `8315c857`
- `worktree-agent-lows-NEW-drafted-4c6dfe8` `abcee383`
- `worktree-agent-lows-P1-int-4c6dfe8` `dbe5fe4f`
- `worktree-agent-lows-P2-int-4c6dfe8` `78220d0c`
- `worktree-agent-lows-P3-int-4c6dfe8` `f9da207a`
- `worktree-agent-palette` `a2b3a21c`
- `worktree-agent-r15-version-0.9.0` `c1e9164c`
- `worktree-agent-r15-version-0.9.0-rc1` `1dfda1f3`
- `worktree-agent-rc1-4c6dfe8-fix-int` `81fbfe91`
- `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar` `a30f693c`
- `worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-pseudo-class` `39585dc3`
- `worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2` `39585dc3`
- `worktree-agent-rc1-gate-r3` `6553c92d`
- `worktree-agent-rc1-gate-r4` `f906f219`
- `worktree-agent-rc1-round-3-01d6920-fix-int` `5ff9be04`
- `worktree-agent-rc1-round-3-01d6920-fix-r1-W1-adapter-nokey-humanize` `ac0d8617`

### KEEP-MILESTONE (3)

- `001-agent-native-redesign` `fcd6fcff` (merged: yes; origin: identical) — never proposed, matches a `--keep` glob
- `002-jarvis-intelligence` `4143296c` (merged: yes; origin: identical) — never proposed, matches a `--keep` glob
- `003-vysted-rebuild` `20fe0044` (merged: yes; origin: identical) — never proposed, matches a `--keep` glob

### MERGED (no matching origin ref — not proposed) (182)

- `phase-10-bugfix` `0521f8a4`
- `phase-10-copilot` `0aee7d14`
- `phase-10-customizability` `0255ca50`
- `phase-10-design` `511a3140`
- `phase-10-integrations` `4b3eefa5`
- `phase-9.5-p1-fixes` `ac000417`
- `phase-9.5-p2-ux` `40746bd2`
- `phase-9.5-p3-visual` `4932fabe`
- `worktree-agent-a0f66b3235af400e6` `cfcf5bef`
- `worktree-agent-a3b89d4c77edd3d2e` `cfcf5bef`
- `worktree-agent-a4050617afe66bc3d` `cfcf5bef`
- `worktree-agent-a4ad1b49cee7ce8f5` `cfcf5bef`
- `worktree-agent-a5ae5375cc836dbf9` `cfcf5bef`
- `worktree-agent-a9141cf82965b0f93` `cfcf5bef`
- `worktree-agent-a9213be4d0e8eacb7` `cfcf5bef`
- `worktree-agent-a9dffdd47629cfa40` `cfcf5bef`
- `worktree-agent-aa9cf4277720b8972` `cfcf5bef`
- `worktree-agent-aad46a7311f3a2d1d` `cfcf5bef`
- `worktree-agent-abde4703b4971c624` `32b7a5d8`
- `worktree-agent-aca67059c0f509aec` `cfcf5bef`
- `worktree-agent-ad884fe79fe84332f` `cfcf5bef`
- `worktree-agent-ad9616945f3d5052b` `cfcf5bef`
- `worktree-agent-ae06c3598f33ae85a` `16094749`
- `worktree-agent-ae2d27cf756bf0462` `cfcf5bef`
- `worktree-agent-ae4a8098f17ac2413` `cfcf5bef`
- `worktree-agent-batch-15-W1` `aaf32a7e`
- `worktree-agent-batch-18-int` `be0cd066`
- `worktree-agent-batch-3-int` `b572152a`
- `worktree-agent-batch-5-int` `a4c5039a`
- `worktree-agent-batch-6-W1-india-exchange-data` `bc03be5b`
- `worktree-agent-batch-6-W3-unattended-platform-chart` `bc03be5b`
- `worktree-agent-pushguard` `13ce4c97`
- `worktree-agent-r10-fedata` `ed64c9d8`
- `worktree-agent-r10-resolve` `59bcf4f4`
- `worktree-agent-r10-screener` `6a3a8e83`
- `worktree-agent-trading-int` `69165638`
- `worktree-wf_116e8cdf-429-1` `cfcf5bef`
- `worktree-wf_152b123d-228-3` `cfcf5bef`
- `worktree-wf_17b6cbe4-389-3` `cfcf5bef`
- `worktree-wf_17b6cbe4-389-4` `cfcf5bef`
- `worktree-wf_17b6cbe4-389-5` `cfcf5bef`
- `worktree-wf_17b6cbe4-389-6` `cfcf5bef`
- `worktree-wf_17b6cbe4-389-7` `cfcf5bef`
- `worktree-wf_1e4295f3-748-3` `cfcf5bef`
- `worktree-wf_1e4295f3-748-4` `cfcf5bef`
- `worktree-wf_1e4295f3-748-5` `cfcf5bef`
- `worktree-wf_232102df-2f0-3` `cfcf5bef`
- `worktree-wf_36d043fa-61f-3` `cfcf5bef`
- `worktree-wf_36d043fa-61f-4` `cfcf5bef`
- `worktree-wf_36d043fa-61f-5` `cfcf5bef`
- `worktree-wf_36d043fa-61f-6` `cfcf5bef`
- `worktree-wf_36d043fa-61f-7` `cfcf5bef`
- `worktree-wf_3bab62fa-c4d-18` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-1` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-13` `8c328fb5`
- `worktree-wf_3d774b10-8d4-14` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-15` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-17` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-2` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-3` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-4` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-5` `cfcf5bef`
- `worktree-wf_3d774b10-8d4-6` `cfcf5bef`
- `worktree-wf_3e8a9abe-7f7-3` `cfcf5bef`
- `worktree-wf_3e8a9abe-7f7-4` `cfcf5bef`
- `worktree-wf_3e8b0f3e-a84-3` `cfcf5bef`
- `worktree-wf_45b81e1e-57a-1` `cfcf5bef`
- `worktree-wf_48478ec5-daf-3` `cfcf5bef`
- `worktree-wf_48478ec5-daf-4` `cfcf5bef`
- `worktree-wf_48478ec5-daf-5` `cfcf5bef`
- `worktree-wf_48478ec5-daf-6` `cfcf5bef`
- `worktree-wf_48478ec5-daf-7` `cfcf5bef`
- `worktree-wf_4ed38558-4d0-25` `cfcf5bef`
- `worktree-wf_4ed38558-4d0-26` `cfcf5bef`
- `worktree-wf_4ed38558-4d0-29` `cfcf5bef`
- `worktree-wf_54334d97-0e6-10` `cfcf5bef`
- `worktree-wf_54334d97-0e6-3` `cfcf5bef`
- `worktree-wf_54334d97-0e6-4` `cfcf5bef`
- `worktree-wf_54334d97-0e6-5` `cfcf5bef`
- `worktree-wf_54334d97-0e6-6` `cfcf5bef`
- `worktree-wf_54334d97-0e6-7` `cfcf5bef`
- `worktree-wf_54334d97-0e6-8` `cfcf5bef`
- `worktree-wf_54334d97-0e6-9` `cfcf5bef`
- `worktree-wf_5c799024-a29-3` `cfcf5bef`
- `worktree-wf_5c799024-a29-4` `cfcf5bef`
- `worktree-wf_5c799024-a29-5` `cfcf5bef`
- `worktree-wf_5c799024-a29-6` `cfcf5bef`
- `worktree-wf_5c799024-a29-7` `cfcf5bef`
- `worktree-wf_6871fdb3-621-10` `cfcf5bef`
- `worktree-wf_6871fdb3-621-11` `cfcf5bef`
- `worktree-wf_727db864-af6-3` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-25` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-26` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-27` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-28` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-32` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-33` `cfcf5bef`
- `worktree-wf_7c4b2e60-141-34` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-10` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-3` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-4` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-5` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-6` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-7` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-8` `cfcf5bef`
- `worktree-wf_7e4c4a3f-085-9` `cfcf5bef`
- `worktree-wf_80230d64-134-3` `cfcf5bef`
- `worktree-wf_942ece8f-ad9-3` `cfcf5bef`
- `worktree-wf_942ece8f-ad9-4` `cfcf5bef`
- `worktree-wf_94ccf2b8-e97-3` `cfcf5bef`
- `worktree-wf_94ccf2b8-e97-4` `cfcf5bef`
- `worktree-wf_94ccf2b8-e97-5` `cfcf5bef`
- `worktree-wf_94ccf2b8-e97-6` `cfcf5bef`
- `worktree-wf_94ccf2b8-e97-7` `cfcf5bef`
- `worktree-wf_9f29ee60-ba0-2` `cfcf5bef`
- `worktree-wf_9f29ee60-ba0-3` `cfcf5bef`
- `worktree-wf_9f29ee60-ba0-4` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-10` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-2` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-3` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-4` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-5` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-6` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-7` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-8` `cfcf5bef`
- `worktree-wf_a342e2a8-74a-9` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-10` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-3` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-4` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-5` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-6` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-7` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-8` `cfcf5bef`
- `worktree-wf_a5e688ba-d35-9` `cfcf5bef`
- `worktree-wf_aaf73f27-1c5-3` `cfcf5bef`
- `worktree-wf_aaf73f27-1c5-4` `cfcf5bef`
- `worktree-wf_aaf73f27-1c5-5` `cfcf5bef`
- `worktree-wf_aaf73f27-1c5-6` `cfcf5bef`
- `worktree-wf_aaf73f27-1c5-7` `cfcf5bef`
- `worktree-wf_b1ca86d0-402-3` `cfcf5bef`
- `worktree-wf_b7cf82ec-5ec-3` `cfcf5bef`
- `worktree-wf_b829ac35-3a5-3` `cfcf5bef`
- `worktree-wf_b829ac35-3a5-4` `cfcf5bef`
- `worktree-wf_b829ac35-3a5-5` `cfcf5bef`
- `worktree-wf_b829ac35-3a5-6` `cfcf5bef`
- `worktree-wf_b829ac35-3a5-7` `cfcf5bef`
- `worktree-wf_c1b4581a-8d6-3` `cfcf5bef`
- `worktree-wf_c1b4581a-8d6-4` `cfcf5bef`
- `worktree-wf_dab096e5-3ae-3` `cfcf5bef`
- `worktree-wf_e17e21c5-cb8-3` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-10` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-2` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-3` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-4` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-5` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-6` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-7` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-8` `cfcf5bef`
- `worktree-wf_e64eeddf-e23-9` `cfcf5bef`
- `worktree-wf_ea0144f4-04a-3` `cfcf5bef`
- `worktree-wf_ea0144f4-04a-4` `cfcf5bef`
- `worktree-wf_f37de2ba-9d1-3` `cfcf5bef`
- `worktree-wf_f37de2ba-9d1-4` `cfcf5bef`
- `worktree-wf_f37de2ba-9d1-5` `cfcf5bef`
- `worktree-wf_f37de2ba-9d1-6` `cfcf5bef`
- `worktree-wf_f37de2ba-9d1-7` `cfcf5bef`
- `worktree-wf_f724edac-bff-10` `cfcf5bef`
- `worktree-wf_f724edac-bff-2` `cfcf5bef`
- `worktree-wf_f724edac-bff-3` `cfcf5bef`
- `worktree-wf_f724edac-bff-4` `cfcf5bef`
- `worktree-wf_f724edac-bff-5` `cfcf5bef`
- `worktree-wf_f724edac-bff-6` `cfcf5bef`
- `worktree-wf_f724edac-bff-7` `cfcf5bef`
- `worktree-wf_f724edac-bff-8` `cfcf5bef`
- `worktree-wf_f724edac-bff-9` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-3` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-4` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-5` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-6` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-7` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-8` `cfcf5bef`
- `worktree-wf_fbb7a07b-9f8-9` `cfcf5bef`

### SAFE-LOCAL-DELETE (133)

- `worktree-agent-batch-10-W1-runtime-backtest` `2ef48a4b`
- `worktree-agent-batch-10-W2-catalog-hostactions` `cf95fb48`
- `worktree-agent-batch-10-W3-fundamentals-bse-cache` `a9109f8c`
- `worktree-agent-batch-10-W4-screener-routes-statedocs` `f10fb8ce`
- `worktree-agent-batch-10-W5-chat-search-workflow` `149015ba`
- `worktree-agent-batch-10-W6-chart-notes-blueprint` `bb788b10`
- `worktree-agent-batch-10-W7-panels-marketplace` `2eec39a9`
- `worktree-agent-batch-10-W8-plugins-dock` `2666cf22`
- `worktree-agent-batch-10-int` `f4ef5673`
- `worktree-agent-batch-11-W1-scripts-build` `f2aca2e0`
- `worktree-agent-batch-11-W2-runtime-schema` `6737c16f`
- `worktree-agent-batch-11-W3-agent-eval` `2156719f`
- `worktree-agent-batch-11-W4-registry-loop` `20d500d5`
- `worktree-agent-batch-11-W5-data-reference` `f51ab96c`
- `worktree-agent-batch-11-W6-options-chain` `5f7be1e2`
- `worktree-agent-batch-11-W7-preferences` `51233975`
- `worktree-agent-batch-11-W8-frontend-visual` `cd4d1787`
- `worktree-agent-batch-11-int` `9985b00e`
- `worktree-agent-batch-12-W1` `8adfba10`
- `worktree-agent-batch-12-W2` `190b380e`
- `worktree-agent-batch-12-W3` `b4585d7a`
- `worktree-agent-batch-12-W4` `bcfd696a`
- `worktree-agent-batch-12-W5` `88bbdaaf`
- `worktree-agent-batch-12-W6` `79485bb2`
- `worktree-agent-batch-12-W7` `f053f472`
- `worktree-agent-batch-12-W8` `a9a91430`
- `worktree-agent-batch-12-int` `3d588a29`
- `worktree-agent-batch-13-W1` `b24a0860`
- `worktree-agent-batch-13-W2` `5e5e742e`
- `worktree-agent-batch-13-W3` `3cb5bc29`
- `worktree-agent-batch-13-int` `e02073bd`
- `worktree-agent-batch-14-W1` `71da3b9a`
- `worktree-agent-batch-14-int` `11e23ace`
- `worktree-agent-batch-15-int` `4daf6507`
- `worktree-agent-batch-16-W1` `50399b67`
- `worktree-agent-batch-16-int` `7b65b217`
- `worktree-agent-batch-17-W1` `ede02247`
- `worktree-agent-batch-17-int` `a340ad7b`
- `worktree-agent-batch-18-W1` `016c0f22`
- `worktree-agent-batch-18-W2` `d74a4a4d`
- `worktree-agent-batch-19-W1` `95e7942e`
- `worktree-agent-batch-19-int` `705c3626`
- `worktree-agent-batch-2-W1-fundamentals-seam` `0e154ab5`
- `worktree-agent-batch-2-W2-instrument-identity` `8f8f5f34`
- `worktree-agent-batch-2-W3-research-integrity` `96598262`
- `worktree-agent-batch-2-W4-workspace-persistence` `7b59a256`
- `worktree-agent-batch-2-W5-surfaces-and-math` `652dc715`
- `worktree-agent-batch-2-int` `16f2a5eb`
- `worktree-agent-batch-20-W1` `05a98380`
- `worktree-agent-batch-20-int` `3595bcd6`
- `worktree-agent-batch-21-W1` `ed9cbe0a`
- `worktree-agent-batch-21-W2` `2e8593eb`
- `worktree-agent-batch-21-int` `7d74e44e`
- `worktree-agent-batch-22-W1` `946a8661`
- `worktree-agent-batch-24-W1` `227c1e25`
- `worktree-agent-batch-24-int` `d1290f66`
- `worktree-agent-batch-3-agent-frontend-gate` `f95ff079`
- `worktree-agent-batch-3-agent-runtime` `cf186ad5`
- `worktree-agent-batch-3-india-data-witnesses` `fd75b199`
- `worktree-agent-batch-3-llm-adapters-and-errors` `42087077`
- `worktree-agent-batch-3-research-depth` `1d424050`
- `worktree-agent-batch-4-W1-agent-runtime` `8833512e`
- `worktree-agent-batch-4-W2-workflow-backtest-feeds` `ab844996`
- `worktree-agent-batch-4-W3-chat-runs-mcp` `cb00f035`
- `worktree-agent-batch-4-W4-market-data-gate` `bf48003a`
- `worktree-agent-batch-4-W5-panels-screener` `78223e35`
- `worktree-agent-batch-4-int` `0d16e8fd`
- `worktree-agent-batch-5-W1-india-disclosures-agent-surface` `e7128795`
- `worktree-agent-batch-5-W2-resolver-market-data` `1df9cb0e`
- `worktree-agent-batch-5-W3-agent-runtime-chat` `5e03442e`
- `worktree-agent-batch-5-W4-platform-workflow-boundary` `4136ad1f`
- `worktree-agent-batch-5-W5-screener-earnings-sec` `896a5b72`
- `worktree-agent-batch-6-W2-delegate-runs-runtime` `26ea55c3`
- `worktree-agent-batch-6-W4-research-funnel` `ffbd8f62`
- `worktree-agent-batch-6-W5-host-actions-portfolio` `e6ea8bb3`
- `worktree-agent-batch-6-int` `831d52b5`
- `worktree-agent-batch-7-W1-india-exchange-data` `c07f121e`
- `worktree-agent-batch-7-W2-delegate-runs-runtime` `a1bdd9fd`
- `worktree-agent-batch-7-W3-unattended-chart-workspace` `1835630c`
- `worktree-agent-batch-7-W4-research-funnel` `e6f281b3`
- `worktree-agent-batch-7-W5-agent-writes-portfolio` `734d8ccc`
- `worktree-agent-batch-7-int` `b7f7023f`
- `worktree-agent-batch-8-W1-sidecar-lifecycle-transport` `26694809`
- `worktree-agent-batch-8-W2-provider-readiness-host-actions` `c3bba8ad`
- `worktree-agent-batch-8-W3-data-error-honesty` `2a025a84`
- `worktree-agent-batch-8-W4-resolver-exchange-lanes` `7a83c3ad`
- `worktree-agent-batch-8-W5-agent-runtime-research` `9703eee7`
- `worktree-agent-batch-8-int` `04eb5e16`
- `worktree-agent-batch-9-W1-agent-runtime` `8609ad11`
- `worktree-agent-batch-9-W2-research-search-news` `91f75e77`
- `worktree-agent-batch-9-W3-fundamentals-identity-earnings` `84f18c5f`
- `worktree-agent-batch-9-W4-market-lanes-errors-quant` `9277035e`
- `worktree-agent-batch-9-W5-frontend-shell` `8b9a67b3`
- `worktree-agent-batch-9-int` `a3b82180`
- `worktree-agent-bhav` `1bbdaf75`
- `worktree-agent-fe` `73192e4c`
- `worktree-agent-fixa` `77e78343`
- `worktree-agent-fixb` `f9a1eecd`
- `worktree-agent-fixc` `34d88c73`
- `worktree-agent-growth` `a6c67708`
- `worktree-agent-hardening` `088fe322`
- `worktree-agent-identity` `85b049a9`
- `worktree-agent-jarvis` `ad8ca238`
- `worktree-agent-lastfix` `66f0cbc3`
- `worktree-agent-narrative` `f5332a11`
- `worktree-agent-panel` `ac694ea1`
- `worktree-agent-r10-frontend` `4d783ba1`
- `worktree-agent-r10-runtime` `80d9cf2d`
- `worktree-agent-r8-composer` `bd949a75`
- `worktree-agent-r8-proportion` `72425f93`
- `worktree-agent-r8-research` `cefb31be`
- `worktree-agent-r8-seams` `b19b92a0`
- `worktree-agent-r8-settings` `897d7ca9`
- `worktree-agent-rc1-4097dac-fix-int` `1d6511c8`
- `worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage` `0f1a4a71`
- `worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary` `1379f26a`
- `worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived` `7e1f3627`
- `worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs` `ed1ed202`
- `worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency` `d4741bc6`
- `worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail` `54f28231`
- `worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache` `d004d6fd`
- `worktree-agent-res` `e9041f2f`
- `worktree-agent-retrieval` `9aeea79a`
- `worktree-agent-rig` `c5f4bafa`
- `worktree-agent-searxfloor` `efba663c`
- `worktree-agent-sem` `3a123d9e`
- `worktree-agent-smokefix` `2e0e0c61`
- `worktree-agent-spine` `cf83b5e0`
- `worktree-agent-trading-docs` `c5802535`
- `worktree-agent-trading-frontend` `7167dbc7`
- `worktree-agent-trading-sidecar` `a9f3c68e`
- `worktree-agent-wireup` `7ec8618e`
- `worktree-agent-witness` `43a45549`

### UNMERGED (has origin copy — KEEP) (37)

- `worktree-agent-batch-22-W2` `ca609488`
- `worktree-agent-batch-22-int` `e4d72417`
- `worktree-agent-batch-23-W1` `5a0f1ffe`
- `worktree-agent-batch-23-int` `9aa9fb6c`
- `worktree-agent-batch-25-W1-data002-wip` `b91ddef3`
- `worktree-agent-design` `876fde35`
- `worktree-agent-lows-P1-W1-backtest` `6cb980bf`
- `worktree-agent-lows-P1-W2-runtime-catalog` `31e61ce5`
- `worktree-agent-lows-P1-W3-actions-research` `dd1ceed2`
- `worktree-agent-lows-P1-W4-chat-composer` `57d0e546`
- `worktree-agent-lows-P1-W5-portfolio` `95a94e16`
- `worktree-agent-lows-P1-W6-runs-stores` `104d96a5`
- `worktree-agent-lows-P1-W7-rust-core` `8d07e2f6`
- `worktree-agent-lows-P1-W8-tokens-market` `2a2f0564`
- `worktree-agent-lows-P1-W9-docs-truth` `dd10d2e0`
- `worktree-agent-lows-P2-W1-research-semantics` `feba1762`
- `worktree-agent-lows-P2-W2-scripts-gates` `d9228cc3`
- `worktree-agent-lows-P2-W3-tools-envelope` `2505d47b`
- `worktree-agent-lows-P2-W4-warm-screener` `1cc7ff1f`
- `worktree-agent-lows-P2-W5-data-resilience` `eaaef44a`
- `worktree-agent-lows-P2-W6-llm-router-mcp` `d80e01a1`
- `worktree-agent-lows-P2-W7-mcp-client` `e581a3be`
- `worktree-agent-lows-P2-W8-shell-page` `26c0cb03`
- `worktree-agent-lows-P2-W9-workspace-persist` `a7408560`
- `worktree-agent-lows-P3-W1-client-plugins` `9d0a9129`
- `worktree-agent-lows-P3-W2-llm-chat` `69ce5999`
- `worktree-agent-lows-P3-W3-provenance-data` `d7059b24`
- `worktree-agent-lows-P3-W4-quant-macro` `c60f921f`
- `worktree-agent-lows-P3-W5-workflow-backend` `d9c8da22`
- `worktree-agent-lows-P3-W6-data-hygiene` `9eaab2ac`
- `worktree-agent-lows-P3-W7-notes-datatable` `f714efe5`
- `worktree-agent-lows-P3-W8-panels-polish` `e4a77aca`
- `worktree-agent-lows-P3-W9-search-backends` `95b60cc1`
- `worktree-agent-notes` `0a078ceb`
- `worktree-agent-r10-errors` `68875b60`
- `worktree-agent-research` `a1e06a73`
- `worktree-agent-screener-perf` `1afd04dc`

### UNMERGED-UNPUSHED (only copy — KEEP) (1)

- `worktree-wf_3d774b10-8d4-10` `68875b60`

### `worktree-wf_3d774b10-8d4-10` finding

Facts re-verified at this snapshot; unchanged from the prior capture:

The one unmerged `worktree-wf_*`-named local branch is a duplicate of dead work: its
tip `68875b60` (`fix(r10-errors): address all adversarial review findings — reblocker +
5 majors`, 2026-06-12) is the **exact same commit** as the unmerged
`worktree-agent-r10-errors` branch listed in section 2 above (`git rev-parse
worktree-wf_3d774b10-8d4-10` and `git rev-parse worktree-agent-r10-errors` both resolve
to `68875b607193c367b6ea0ffa7bca0c8ecbc1d8cb`). Both are stale R10-era branches that
never merged; the operator only needs to review the content once, not twice — deleting
either branch does not lose anything the other doesn't already hold. Note this is a
**local branch only** now, not a registered worktree (no `.claude/worktrees/…` or
scratchpad directory backs it) — it shows up under §2 (Local branches), not §1.

## 3. Remote agent branches (`origin/worktree-agent-*`)

Source: `git for-each-ref refs/remotes/origin/worktree-agent-*` (249 refs). Remote deletion is never proposed by this script — local copies only.

- Merged into base: 190
- Unmerged: 59

Unmerged remote agent branches (kept, informational only):

- `origin/worktree-agent-batch-22-W2` `ca609488`
- `origin/worktree-agent-batch-22-int` `e4d72417`
- `origin/worktree-agent-batch-23-W1` `5a0f1ffe`
- `origin/worktree-agent-batch-23-int` `9aa9fb6c`
- `origin/worktree-agent-batch-25-W1-data002-wip` `b91ddef3`
- `origin/worktree-agent-design` `876fde35`
- `origin/worktree-agent-formula` `87a5cec7`
- `origin/worktree-agent-hygiene-2` `11f6e057`
- `origin/worktree-agent-lows-CN-r15-agent-077-4c6dfe8` `80f8d7a2`
- `origin/worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` `695e934a`
- `origin/worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` `31aa053b`
- `origin/worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` `cba8df9f`
- `origin/worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` `113ab130`
- `origin/worktree-agent-lows-CN-r15-data-102-4c6dfe8` `09d8da83`
- `origin/worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` `954ffa89`
- `origin/worktree-agent-lows-DEF-A-4c6dfe8` `8113ddc1`
- `origin/worktree-agent-lows-DEF-B-4c6dfe8` `af933bcc`
- `origin/worktree-agent-lows-LEAD-036-4c6dfe8` `8315c857`
- `origin/worktree-agent-lows-NEW-drafted-4c6dfe8` `abcee383`
- `origin/worktree-agent-lows-P1-W1-backtest` `6cb980bf`
- `origin/worktree-agent-lows-P1-W2-runtime-catalog` `31e61ce5`
- `origin/worktree-agent-lows-P1-W3-actions-research` `dd1ceed2`
- `origin/worktree-agent-lows-P1-W4-chat-composer` `57d0e546`
- `origin/worktree-agent-lows-P1-W5-portfolio` `95a94e16`
- `origin/worktree-agent-lows-P1-W6-runs-stores` `104d96a5`
- `origin/worktree-agent-lows-P1-W7-rust-core` `8d07e2f6`
- `origin/worktree-agent-lows-P1-W8-tokens-market` `2a2f0564`
- `origin/worktree-agent-lows-P1-W9-docs-truth` `dd10d2e0`
- `origin/worktree-agent-lows-P1-int-4c6dfe8` `dbe5fe4f`
- `origin/worktree-agent-lows-P2-W1-research-semantics` `feba1762`
- `origin/worktree-agent-lows-P2-W2-scripts-gates` `d9228cc3`
- `origin/worktree-agent-lows-P2-W3-tools-envelope` `2505d47b`
- `origin/worktree-agent-lows-P2-W4-warm-screener` `1cc7ff1f`
- `origin/worktree-agent-lows-P2-W5-data-resilience` `eaaef44a`
- `origin/worktree-agent-lows-P2-W6-llm-router-mcp` `d80e01a1`
- `origin/worktree-agent-lows-P2-W7-mcp-client` `e581a3be`
- `origin/worktree-agent-lows-P2-W8-shell-page` `26c0cb03`
- `origin/worktree-agent-lows-P2-W9-workspace-persist` `a7408560`
- `origin/worktree-agent-lows-P2-int-4c6dfe8` `78220d0c`
- `origin/worktree-agent-lows-P3-W1-client-plugins` `9d0a9129`
- `origin/worktree-agent-lows-P3-W2-llm-chat` `69ce5999`
- `origin/worktree-agent-lows-P3-W3-provenance-data` `d7059b24`
- `origin/worktree-agent-lows-P3-W4-quant-macro` `c60f921f`
- `origin/worktree-agent-lows-P3-W5-workflow-backend` `d9c8da22`
- `origin/worktree-agent-lows-P3-W6-data-hygiene` `9eaab2ac`
- `origin/worktree-agent-lows-P3-W7-notes-datatable` `f714efe5`
- `origin/worktree-agent-lows-P3-W8-panels-polish` `e4a77aca`
- `origin/worktree-agent-lows-P3-W9-search-backends` `95b60cc1`
- `origin/worktree-agent-lows-P3-int-4c6dfe8` `f9da207a`
- `origin/worktree-agent-notes` `0a078ceb`
- `origin/worktree-agent-r10-errors` `68875b60`
- `origin/worktree-agent-r15-version-0.9.0` `c1e9164c`
- `origin/worktree-agent-r15-version-0.9.0-rc1` `1dfda1f3`
- `origin/worktree-agent-rc1-4c6dfe8-fix-int` `81fbfe91`
- `origin/worktree-agent-rc1-4c6dfe8-fix-r1-W1-citation-marker-grammar` `a30f693c`
- `origin/worktree-agent-rc1-4c6dfe8-fix-r2-W1-citation-grammar-r2` `39585dc3`
- `origin/worktree-agent-research` `a1e06a73`
- `origin/worktree-agent-screener-perf` `1afd04dc`
- `origin/worktree-agent-screener-perf-v2` `cb9d2821`

## 4. Stale tracking refs

Source: `git remote prune origin --dry-run` (read-only; no refs were pruned by this run):

```
(no output — nothing stale)
```

## 5. Never touch (restated)

- The other Tauri+Python product's containers/listeners.
- The operator's app data / OS keychain entries.
- Anything outside this repository and the session scratchpad.
- Git history (no rebase, no filter, no amend of existing commits).
- Any `v*` tag.
- Remote (`origin/*`) branches — remote deletion is never proposed by this script.
- The main checkout, and any worktree or branch this run classified LIVE.

## Summary counts

| Category | Count |
|---|---|
| Worktrees: LIVE | 31 |
| Worktrees: MERGED (prune candidate) | 11 |
| Worktrees: UNMERGED | 4 |
| Worktrees: PRUNABLE-REGISTRATION | 0 |
| Local branches: total | 400 |
| Local branches: SAFE-LOCAL-DELETE | 133 |
| Local branches: UNMERGED-UNPUSHED (keep) | 1 |
| Remote agent branches: total | 249 |
| Remote agent branches: merged | 190 |
| Remote agent branches: unmerged | 59 |

## Exact deletion commands (lead runs these)

```
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_3bab62fa-c4d-18
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_80230d64-134-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_942ece8f-ad9-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_942ece8f-ad9-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-3
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-4
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-5
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-6
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-7
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-8
git worktree remove /Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/wf_fbb7a07b-9f8-9
git worktree prune
git branch -d worktree-agent-batch-10-W1-runtime-backtest
git branch -d worktree-agent-batch-10-W2-catalog-hostactions
git branch -d worktree-agent-batch-10-W3-fundamentals-bse-cache
git branch -d worktree-agent-batch-10-W4-screener-routes-statedocs
git branch -d worktree-agent-batch-10-W5-chat-search-workflow
git branch -d worktree-agent-batch-10-W6-chart-notes-blueprint
git branch -d worktree-agent-batch-10-W7-panels-marketplace
git branch -d worktree-agent-batch-10-W8-plugins-dock
git branch -d worktree-agent-batch-10-int
git branch -d worktree-agent-batch-11-W1-scripts-build
git branch -d worktree-agent-batch-11-W2-runtime-schema
git branch -d worktree-agent-batch-11-W3-agent-eval
git branch -d worktree-agent-batch-11-W4-registry-loop
git branch -d worktree-agent-batch-11-W5-data-reference
git branch -d worktree-agent-batch-11-W6-options-chain
git branch -d worktree-agent-batch-11-W7-preferences
git branch -d worktree-agent-batch-11-W8-frontend-visual
git branch -d worktree-agent-batch-11-int
git branch -d worktree-agent-batch-12-W1
git branch -d worktree-agent-batch-12-W2
git branch -d worktree-agent-batch-12-W3
git branch -d worktree-agent-batch-12-W4
git branch -d worktree-agent-batch-12-W5
git branch -d worktree-agent-batch-12-W6
git branch -d worktree-agent-batch-12-W7
git branch -d worktree-agent-batch-12-W8
git branch -d worktree-agent-batch-12-int
git branch -d worktree-agent-batch-13-W1
git branch -d worktree-agent-batch-13-W2
git branch -d worktree-agent-batch-13-W3
git branch -d worktree-agent-batch-13-int
git branch -d worktree-agent-batch-14-W1
git branch -d worktree-agent-batch-14-int
git branch -d worktree-agent-batch-15-int
git branch -d worktree-agent-batch-16-W1
git branch -d worktree-agent-batch-16-int
git branch -d worktree-agent-batch-17-W1
git branch -d worktree-agent-batch-17-int
git branch -d worktree-agent-batch-18-W1
git branch -d worktree-agent-batch-18-W2
git branch -d worktree-agent-batch-19-W1
git branch -d worktree-agent-batch-19-int
git branch -d worktree-agent-batch-2-W1-fundamentals-seam
git branch -d worktree-agent-batch-2-W2-instrument-identity
git branch -d worktree-agent-batch-2-W3-research-integrity
git branch -d worktree-agent-batch-2-W4-workspace-persistence
git branch -d worktree-agent-batch-2-W5-surfaces-and-math
git branch -d worktree-agent-batch-2-int
git branch -d worktree-agent-batch-20-W1
git branch -d worktree-agent-batch-20-int
git branch -d worktree-agent-batch-21-W1
git branch -d worktree-agent-batch-21-W2
git branch -d worktree-agent-batch-21-int
git branch -d worktree-agent-batch-22-W1
git branch -d worktree-agent-batch-24-W1
git branch -d worktree-agent-batch-24-int
git branch -d worktree-agent-batch-3-agent-frontend-gate
git branch -d worktree-agent-batch-3-agent-runtime
git branch -d worktree-agent-batch-3-india-data-witnesses
git branch -d worktree-agent-batch-3-llm-adapters-and-errors
git branch -d worktree-agent-batch-3-research-depth
git branch -d worktree-agent-batch-4-W1-agent-runtime
git branch -d worktree-agent-batch-4-W2-workflow-backtest-feeds
git branch -d worktree-agent-batch-4-W3-chat-runs-mcp
git branch -d worktree-agent-batch-4-W4-market-data-gate
git branch -d worktree-agent-batch-4-W5-panels-screener
git branch -d worktree-agent-batch-4-int
git branch -d worktree-agent-batch-5-W1-india-disclosures-agent-surface
git branch -d worktree-agent-batch-5-W2-resolver-market-data
git branch -d worktree-agent-batch-5-W3-agent-runtime-chat
git branch -d worktree-agent-batch-5-W4-platform-workflow-boundary
git branch -d worktree-agent-batch-5-W5-screener-earnings-sec
git branch -d worktree-agent-batch-6-W2-delegate-runs-runtime
git branch -d worktree-agent-batch-6-W4-research-funnel
git branch -d worktree-agent-batch-6-W5-host-actions-portfolio
git branch -d worktree-agent-batch-6-int
git branch -d worktree-agent-batch-7-W1-india-exchange-data
git branch -d worktree-agent-batch-7-W2-delegate-runs-runtime
git branch -d worktree-agent-batch-7-W3-unattended-chart-workspace
git branch -d worktree-agent-batch-7-W4-research-funnel
git branch -d worktree-agent-batch-7-W5-agent-writes-portfolio
git branch -d worktree-agent-batch-7-int
git branch -d worktree-agent-batch-8-W1-sidecar-lifecycle-transport
git branch -d worktree-agent-batch-8-W2-provider-readiness-host-actions
git branch -d worktree-agent-batch-8-W3-data-error-honesty
git branch -d worktree-agent-batch-8-W4-resolver-exchange-lanes
git branch -d worktree-agent-batch-8-W5-agent-runtime-research
git branch -d worktree-agent-batch-8-int
git branch -d worktree-agent-batch-9-W1-agent-runtime
git branch -d worktree-agent-batch-9-W2-research-search-news
git branch -d worktree-agent-batch-9-W3-fundamentals-identity-earnings
git branch -d worktree-agent-batch-9-W4-market-lanes-errors-quant
git branch -d worktree-agent-batch-9-W5-frontend-shell
git branch -d worktree-agent-batch-9-int
git branch -d worktree-agent-bhav
git branch -d worktree-agent-fe
git branch -d worktree-agent-fixa
git branch -d worktree-agent-fixb
git branch -d worktree-agent-fixc
git branch -d worktree-agent-growth
git branch -d worktree-agent-hardening
git branch -d worktree-agent-identity
git branch -d worktree-agent-jarvis
git branch -d worktree-agent-lastfix
git branch -d worktree-agent-narrative
git branch -d worktree-agent-panel
git branch -d worktree-agent-r10-frontend
git branch -d worktree-agent-r10-runtime
git branch -d worktree-agent-r8-composer
git branch -d worktree-agent-r8-proportion
git branch -d worktree-agent-r8-research
git branch -d worktree-agent-r8-seams
git branch -d worktree-agent-r8-settings
git branch -d worktree-agent-rc1-4097dac-fix-int
git branch -d worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage
git branch -d worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary
git branch -d worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived
git branch -d worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs
git branch -d worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency
git branch -d worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail
git branch -d worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache
git branch -d worktree-agent-res
git branch -d worktree-agent-retrieval
git branch -d worktree-agent-rig
git branch -d worktree-agent-searxfloor
git branch -d worktree-agent-sem
git branch -d worktree-agent-smokefix
git branch -d worktree-agent-spine
git branch -d worktree-agent-trading-docs
git branch -d worktree-agent-trading-frontend
git branch -d worktree-agent-trading-sidecar
git branch -d worktree-agent-wireup
git branch -d worktree-agent-witness
```

