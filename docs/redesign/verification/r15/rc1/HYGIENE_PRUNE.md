# R15 rc1 Hygiene Prune Inventory

Read-only inventory for the lead's hygiene pass right after the r15-rc1 tag is cut.
Nothing in this document deletes, prunes, or checks anything out — every line below is
sourced from a git command run against `/Users/lokavyasingh/Documents/dev/vysted-terminal`
on branch `004-r4-experience-rebuild`.

Snapshot captured `07:11 IST` (worktree tips) / `07:13 IST` (branch and tag listings),
2026-09-26. **Caveat:** several burst agents were committing to their own worktree
branches and to `004-r4-experience-rebuild` concurrently while this snapshot was taken
(observed HEAD moving from `a61f9896` → `acd43e6f` → `4ac94b8c` across ~10 minutes, and at
least one lows-CN worktree tearing itself down mid-inventory). Treat exact SHAs for the
`lows-*` and `batch-*` in-flight branches as indicative of the moment captured, not frozen
fact — re-run the cited commands before acting on them.

No `r15-*` tag exists yet (`git tag -l 'r15-*'` returned nothing) — this document is
prepared in advance of the rc1 tag, not after it.

---

## 1. Registered worktrees

Source: `git worktree list --porcelain`, cross-checked with `git merge-base --is-ancestor
<tip> 004-r4-experience-rebuild`, `/bin/ls -la <path>`, and `git log -1 --format='%cd
%s' --date=short <tip>`.

| Path | Branch | Tip | Contained in 004? | Path exists? | Last commit | Recommendation |
|---|---|---|---|---|---|---|
| `/Users/lokavyasingh/Documents/dev/vysted-terminal` | `004-r4-experience-rebuild` | `acd43e6f`→`4ac94b8c` (moving) | yes (is 004) | yes | 2026-09-26 | **keep** — main worktree |
| `…/scratchpad/lows-cn/r15-agent-077` | `worktree-agent-lows-CN-r15-agent-077-4c6dfe8` | `80f8d7a2` | no | yes | 2026-09-26 | **keep: in use** (lows-CN burst agent) |
| `…/scratchpad/lows-cn/r15-code-agent-031` | `worktree-agent-lows-CN-r15-code-agent-031-4c6dfe8` | `695e934a` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-cn/r15-code-data-019` | `worktree-agent-lows-CN-r15-code-data-019-4c6dfe8` | `31aa053b` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-cn/r15-code-frontend-027` | `worktree-agent-lows-CN-r15-code-frontend-027-4c6dfe8` | `cba8df9f` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-cn/r15-code-research-005` | `worktree-agent-lows-CN-r15-code-research-005-4c6dfe8` | `113ab130` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-cn/r15-data-102` | `worktree-agent-lows-CN-r15-data-102-4c6dfe8` | `09d8da83` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-cn/r15-lifecycle-035` | `worktree-agent-lows-CN-r15-lifecycle-035-4c6dfe8` | `954ffa89` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-deferred-A` | `worktree-agent-lows-DEF-A-4c6dfe8` | `8113ddc1` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-deferred-B` | `worktree-agent-lows-DEF-B-4c6dfe8` | `c67d09dc` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-lead036` | `worktree-agent-lows-LEAD-036-4c6dfe8` | `8315c857` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-new-lows` | `worktree-agent-lows-NEW-drafted-4c6dfe8` | `abcee383` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-preint/P1` | `worktree-agent-lows-P1-int-4c6dfe8` | `a642caac` | no | yes | 2026-09-26 | **keep: in use** (P1 pre-integration candidate) |
| `…/scratchpad/lows-preint/P2` | `worktree-agent-lows-P2-int-4c6dfe8` | `d7d0d325` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/lows-preint/P3` | `worktree-agent-lows-P3-int-4c6dfe8` | `aa1690ee` | no | yes | 2026-09-26 | **keep: in use** |
| `…/scratchpad/rc1-cand` | *(detached)* | `4c6dfe8c` | **yes** | yes | 2026-09-26 | **keep-until-<rc1 tag cut>** — this is the candidate commit several `-4c6dfe8`-suffixed branches above are staged against; once `r15-rc1` is tagged at (or past) this commit, this checkout is redundant |
| `…/scratchpad/version-0.9.0` | `worktree-agent-r15-version-0.9.0` | `c1e9164c` | no | yes | 2026-09-26 | **keep-until-<version branch merges after rc1 tag>** (known case) |
| `/Users/lokavyasingh/Documents/dev/vysted-terminal/.claude/worktrees/agent-a47228f53658c48ac` | `worktree-agent-palette` | `a2b3a21c` | no (local ref) | yes | 2026-06-05 | **operator-decides** — see finding below |

A transient `…/scratchpad/lows-cn/mergesim-027` worktree (detached, tip `780a62ed`,
directory already absent) existed at the start of this inventory and was gone by the end
— its owning burst agent tore it down itself. `git worktree prune --dry-run --verbose`
returned no output at snapshot time, i.e. **no stale worktree administrative entries need
pruning right now**; re-check with the same command before the hygiene pass in case
another burst agent's worktree dies mid-flight without self-cleaning.

### Palette worktree finding (pre-R15, `.claude/worktrees/agent-a47228f53658c48ac`)

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
  `src/store/command-palette.ts`) against 004's current tree: all seven paths already
  exist in 004 (`git cat-file -e 004-r4-experience-rebuild:<path>` succeeds for all), and
  004's versions have diverged substantially further (291/287-line diffs on
  `CommandPalette.tsx`/`command-palette.ts` alone). `cmdk` is already a 004 dependency
  (`package.json` → `"cmdk": "1.1.1"`).
- **Nothing in this worktree is absent from 004.** It is a superseded, stale snapshot of
  work whose full branch history already landed. Lead decides whether to keep it around
  for archaeology or reclaim the directory; recommendation is prune-eligible but not
  forced here.

---

## 2. Local branches

Source: `git for-each-ref refs/heads --format='%(refname:short) %(objectname:short)
%(committerdate:short)'` (359 refs), `git branch --merged 004-r4-experience-rebuild`
(306 refs, including `004-r4-experience-rebuild` itself), set-differenced with `comm`
against the full local list, and origin-counterpart membership checked against `git
branch -r`.

359 local branches split as follows (counts sum to 359):

| Group | Count | Merged into 004 | Has origin counterpart | Recommendation |
|---|---|---|---|---|
| `004-r4-experience-rebuild` | 1 | n/a (current) | yes | keep — current branch |
| `main` | 1 | yes | yes | **keep** — default branch, never touch |
| Milestone/spec branches: `001-agent-native-redesign`, `002-jarvis-intelligence`, `003-vysted-rebuild`, `phase-9.5-p1-fixes`, `phase-9.5-p2-ux`, `phase-9.5-p3-visual`, `phase-10-bugfix`, `phase-10-copilot`, `phase-10-customizability`, `phase-10-design`, `phase-10-integrations` | 11 | yes, all 11 | yes, all 11 | **operator-decides** — historical phase milestones, not burst-agent scratch; out of this doc's prune remit |
| `worktree-agent-batch-*` (int + writers) | 104 | 100 yes / 4 no | yes, all 104 | 100 merged = **prune candidate** (see §3 for exact origin deletes); 4 unmerged (`batch-22-W2`, `batch-22-int`, `batch-23-W1`, `batch-23-int`) = **keep**, still in flight |
| `worktree-agent-rc1-4097dac-fix-*` (round-1 + round-2 fix branches) | 8 | yes, all 8 | yes, all 8 | **prune candidate** — rc1 fix rounds, commits fully in 004 |
| `worktree-agent-lows-*` (CN/DEF/LEAD/NEW/P1-P3 writers + Pn-int) | 41 | no, all 41 | yes, all 41 | **keep**, pending integration merge |
| `worktree-agent-r15-version-0.9.0` | 1 | no | yes | **keep-until-<version branch merges after rc1 tag>** (known case) |
| `worktree-agent-<17-hex-char hash>` (old local Agent-tool leftovers, e.g. `worktree-agent-a0f66b3235af400e6`) | 17 | yes, all 17 | no, none | **prune candidate** — dead local-only scratch, no remote push to worry about |
| `worktree-wf_*` (Workflow-tool leftovers) | 133 | 132 yes / 1 no | matches merge status | 132 merged = **prune candidate**; 1 unmerged (`worktree-wf_3d774b10-8d4-10`, tip `68875b60`) = **operator-decides** — see finding below |
| Misc named `worktree-agent-*` (pre-R15: `bhav`, `design`, `fe`, `fixa`, `fixb`, `fixc`, `growth`, `hardening`, `identity`, `jarvis`, `lastfix`, `narrative`, `notes`, `palette`, `panel`, `pushguard`, `r7-*`(via origin only — none checked out locally except through the palette-style pattern), `r8-composer/proportion/research/seams/settings`, `r10-errors/fedata/frontend/resolve/runtime/screener`, `research`, `res`, `retrieval`, `rig`, `screener-perf`, `searxfloor`, `sem`, `smokefix`, `spine`, `trading-docs/frontend/int/sidecar`, `wireup`, `witness`) | 42 | 36 yes / 6 no | yes, all 42 | 36 merged = **operator-decides** (pre-R15 named branches, outside this sweep's scope); 6 unmerged (`design`, `notes`, `palette`†, `r10-errors`, `research`, `screener-perf`) = **operator-decides** — old, apparently abandoned June/July work |

† `palette`'s **local** ref is unmerged (stale, see §1), but its **origin** ref is merged —
listed as unmerged here strictly per the local-branch check `git branch --merged
004-r4-experience-rebuild`.

### `worktree-wf_3d774b10-8d4-10` finding

The one unmerged `worktree-wf_*` branch is a duplicate of dead work: its tip `68875b60`
(`fix(r10-errors): address all adversarial review findings — reblocker + 5 majors`,
2026-06-12) is the **exact same commit** as the unmerged `worktree-agent-r10-errors`
branch above. Both are stale R10-era branches that never merged; recommend the operator
review once, not twice — deleting one does not lose anything the other doesn't already
hold.

Full 53-line "not merged" branch list (source of the counts above) is reproducible via:

```
comm -23 \
  <(git for-each-ref refs/heads --format='%(refname:short)' | sort) \
  <(git branch --merged 004-r4-experience-rebuild --format='%(refname:short)' | sort)
```

---

## 3. Remote agent branches (`origin/worktree-agent-*`)

Source: `git branch -r` (229 remote refs total, 223 under `origin/worktree-agent-*`),
merge status sampled per-branch via `git merge-base --is-ancestor origin/<branch>
004-r4-experience-rebuild`.

| Family | Count | Merged into 004 | Recommendation |
|---|---|---|---|
| `batch-N` int + writer branches (`batch-2` … `batch-24`) | 104 | 100 merged / 4 unmerged | Merged 100 → **delete on origin after the tag** (commands below). Unmerged 4 (`batch-22-W2`, `batch-22-int`, `batch-23-W1`, `batch-23-int`) → **keep**, integration still open |
| `lows-P1/P2/P3` writers (`-W1` … `-W9` per partition) | 27 | 0 merged | **keep until their `Pn-int` integration merges** |
| `lows-Pn-int` candidates (`lows-P1-int-4c6dfe8`, `lows-P2-int-4c6dfe8`, `lows-P3-int-4c6dfe8`) | 3 | 0 merged | **keep until integration merges** |
| `lows-CN` / `lows-DEF` / `lows-LEAD` / `lows-NEW` (`lows-CN-r15-agent-077`, `-code-agent-031`, `-code-data-019`, `-code-frontend-027`, `-code-research-005`, `-data-102`, `-lifecycle-035`, `lows-DEF-A`, `lows-DEF-B`, `lows-LEAD-036`, `lows-NEW-drafted`, all `-4c6dfe8`) | 11 | 0 merged | **keep**, active burst work |
| `r15-version-0.9.0` | 1 | 0 merged | **keep-until-<version branch merges after rc1 tag>** |
| `rc1-4097dac-fix-*` round-1 (`-r1-W1`…`-r1-W4`) + round-2 (`-r2-W1`…`-r2-W3`) + `-fix-int` | 8 | 8 merged | **delete on origin after the tag** (commands below) |
| Others: pre-R15 named branches not matching the above (`r7-*`, `r8-*`, `r9-*`, `r10-*`, `bhav`, `brief`, `chat-experience`, `composer`, `consistency`, `data-panels`, `design`, `design-doc`, `fe`, `fixa/b/c`, `formula`, `growth`, `hardening`, `identity`, `jarvis`, `lastfix`, `layout`, `narrative`, `notes`, `overview-narrative`, `palette`, `panel`, `pins`, `pushguard`, `res`, `research`, `retrieval`, `rig`, `screener-backoff`, `screener-perf`, `screener-perf-v2`, `searxfloor`, `sem`, `smokefix`, `space-memory`, `spine`, `surfaces`, `trading-*`, `wireup`, `witness`, plus 2 old hash-named: `a882d06f8e7c3ff56`, `a9d8467a798247f72`) | 69 | 62 merged / 7 unmerged | **operator-decides** — outside this sweep's explicit criteria (not batch/rc1-round); merged 62 are prune-eligible if the operator wants a broader clean, unmerged 7 (`design`, `formula`, `notes`, `r10-errors`, `research`, `screener-perf`, `screener-perf-v2`) look like abandoned June/July work |

Footnote: `origin/phase-1a-foundation` also exists and is unmerged, but it is not a
`worktree-agent-*` branch, so it's outside this section's remit — flagged here only so the
operator knows it's there (**operator-decides**).

### Exact deletion commands (lead runs these, not this clerk)

The 100 merged `batch-*` branches and the 8 merged `rc1-4097dac-fix-*` branches — every
line below was generated from `git merge-base --is-ancestor origin/<branch>
004-r4-experience-rebuild` returning true for that exact branch at snapshot time:

```
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
git push origin --delete worktree-agent-batch-24-W1
git push origin --delete worktree-agent-batch-24-int
git push origin --delete worktree-agent-batch-3-agent-frontend-gate
git push origin --delete worktree-agent-batch-3-agent-runtime
git push origin --delete worktree-agent-batch-3-india-data-witnesses
git push origin --delete worktree-agent-batch-3-int
git push origin --delete worktree-agent-batch-3-llm-adapters-and-errors
git push origin --delete worktree-agent-batch-3-research-depth
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
git push origin --delete worktree-agent-rc1-4097dac-fix-int
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W1-research-coverage
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W2-agent-model-boundary
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W3-fundamentals-derived
git push origin --delete worktree-agent-rc1-4097dac-fix-r1-W4-portfolio-and-docs
git push origin --delete worktree-agent-rc1-4097dac-fix-r2-W1-statements-currency
git push origin --delete worktree-agent-rc1-4097dac-fix-r2-W2-leaked-call-tail
git push origin --delete worktree-agent-rc1-4097dac-fix-r2-W3-overlay-cache
```

`batch-22-W2`, `batch-22-int`, `batch-23-W1`, `batch-23-int` are deliberately **absent**
from the block above — they are still unmerged at snapshot time.

---

## 4. Stale local refs and leftovers

- **`git stash list`**: empty. Nothing to review.
- **Untracked directories from finished runs** (`git status --short | grep '^??'`
  filtered to the example the lead flagged):
  - `docs/redesign/verification/r15/stage-c/lows/P1/writers/`
  - `docs/redesign/verification/r15/stage-c/lows/P2/writers/`
  - `docs/redesign/verification/r15/stage-c/lows/P3/writers/`

  `git ls-files` on all three returns nothing — confirmed untracked, on no commit
  anywhere. Contents (`/bin/ls -la`) are raw per-writer `Wn.jsonl` dumps (P1: W2–W9 minus
  W8, 7 files; P2: W2–W9, 7 files; P3: W2–W8 minus W4, 6 files), last modified 2026-09-25
  19:04–19:33. Checking whether this content exists elsewhere: `git ls-tree -r
  worktree-agent-lows-P1-int-4c6dfe8 -- docs/redesign/verification/r15/stage-c/lows/`
  shows the **aggregated** form is tracked (`P1/WRITERS.json`, `P2/WRITERS.json`,
  `P3/WRITERS.json`, `PARTITION.json`, `PARTITION.md`), and 004 itself already carries
  `lows/P1/PREINT.json`, `PREINT.md`, `PREINT_REVIEW.md`, `NEW_LOWS_DRAFT.{json,md}`. The
  raw per-writer JSONL files are local-only scratch whose rolled-up output already landed
  — safe to clear once the lead confirms nothing further reads the raw files directly.
- Everything else under `git status --short`'s `??` output (the large volume of
  `docs/redesign/verification/r15/rc1/battery/raw/set-*/…` files) is **live, in-progress
  battery output**, not a finished-run leftover — out of scope for this inventory per the
  lead's own framing (only the stage-c writers example was asked for).
- Large ignored build artefacts: explicitly out of scope per the task brief, not audited
  here.

---

## 5. Never touch (restated)

This clerk touched none of the following, and this inventory recommends the lead not
touch them in the hygiene pass either:

- The other Tauri+Python product's containers/listeners.
- The operator's app data / OS keychain entries.
- Anything outside this repository and the session scratchpad.
- Git history (no rebase, no filter, no amend of existing commits).
- Any `v*` tag. `git tag -l 'v*'`: `v0.1.0`, `v0.2.0`, `v0.2.1`, `v0.3.0`, `v0.4.0`,
  `v0.5.0`, `v0.6.0`, `v0.6.1`, `v0.6.5`, `v0.7.0`, `v0.8.0` — 11 tags, all pre-R15
  milestone releases, none touched.
- `r15-*` tags: `git tag -l 'r15-*'` returns **none** — the rc1 tag this hygiene pass is
  named after does not exist yet as of this snapshot.

---

## Section summary (counts)

| Section | Item count |
|---|---|
| Registered worktrees | 18 (1 main + 15 in-use burst/pre-integration + 1 rc1-candidate detached + 1 pre-R15 palette) |
| Local branches | 359 total / 306 merged into 004 / 53 unmerged |
| Remote `worktree-agent-*` branches | 223 total / 170 merged / 53 unmerged (batch 100+4, lows 41, version 1, rc1-round 8, others 62+7) |
| Exact origin delete commands provided | 108 (100 batch + 8 rc1-round) |
| Stashes | 0 |
| Untracked finished-run leftovers flagged | 3 directories (stage-c lows P1/P2/P3 writers) |
| `v*` tags | 11 |
| `r15-*` tags | 0 |
