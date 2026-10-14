# R15 Stage D docs and scans: workflow plan

Script: `docs/redesign/verification/r15/tooling/stage-d-docs.js`. This is the Stage D "docs and scans" wave of the release run. It drafts the release documents and runs three read-only scans at one 004 sha. It is built to run **beside** the fix batches, so it uses only repo reads (at the sha, via `git show` / `git grep`), git history, the outside world (curl), and cheap local metadata commands. It edits no tracked file outside its own output dir. The lead promotes the drafts at rc2, after a `refresh` run.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/stage-d-docs.js", args: {sha: "<004 commit>", out: "docs/redesign/verification/r15/stage-d", mode: "draft", cap: 6, skip: []}})
```

## Args

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `sha` | required | The 004 commit to draft against (7-40 hex). The script refuses without it. The facts agent refuses (`status: 'blocked'`) if the sha is not 004 or an ancestor. |
| `out` | `docs/redesign/verification/r15/stage-d` | The output dir (EV). It must be `r15/stage-d` or a `stage-d-*` sibling, because the collator runs `git add -A` on the whole dir. |
| `mode` | `draft` | `draft` writes fresh. If the dir holds a run at a different sha, it is cleared first (git keeps the history). `refresh` re-reads the existing drafts and updates them from `git log/diff <header sha>..<sha>`. |
| `cap` | 6 | Concurrent agents: one limiter around every `agent()` call, clamped to 16. |
| `skip` | `[]` | Any of `readme`, `runbook`, `briefing`, `notes`, `state`, `secrets`, `deps`, `licence`. An array, or a comma string. Unknown names are refused. |
| `scratch` | this session's scratchpad | Optional, as in rc1-gate. Scratch files go to `<scratch>/stage-d-<sha7>/` and are never committed. |

Return: `{status: 'done' | 'partial' | 'blocked', sha, mode, rows: [{name, kind, status, files, critic, findings, flagged, open_questions, note}], index, skipped, open_questions, redacted, commit}`. `partial` means the collator died: nothing is committed, and the outputs sit uncommitted in EV.

## Phases

| # | Phase | Agents (model, effort) | What it does |
| - | ----- | ---------------------- | ------------ |
| 1 | Facts | 1 Sonnet medium | Resolves the sha. Writes `FACTS.json` / `FACTS.md`, each fact with its source (path:line at the sha, or the command). Covers: the version strings and every other occurrence of the version, the three sidecars (externalBin, ensure script, venv, spawner), the package.json scripts, the CI triggers, the plugins (bundled/companion, licence), the agent roster count, the panels per module, the register counts by severity x status, the DECISIONS_FOR_OPERATOR items (open/closed, Tier-4, unblock), git since the newest `r13-*`/`r15-*` tag, the licence fields, and which tools are installed. In refresh mode it adds the previous sha and the diff. If this agent is blocked or dies, nothing else runs. |
| 2 | Drafts | 5 Sonnet high | Each drafter reads `FACTS.md` first and writes its file progressively: `README.draft.md`, `RELEASE_RUNBOOK.draft.md`, `OPERATOR_BRIEFING.draft.md`, `RELEASE_NOTES.draft.md` (part A is the release notes, part B the CHANGELOG v0.9.0 section), and `CURRENT_STATE.draft.md` + `BLOCKERS.draft.md` (the full proposed text) with a `.draft.diff` each (`diff -u` against the file at the sha). |
| 3 | Scans | 3 Sonnet high, running alongside Drafts | **Secrets.** Runs `scripts/r15/history_secrets_scan.py` detached (it covers every ref and blob and redacts every value), or gitleaks/trufflehog if installed. Checks the tree at the sha, then history, marking for each hit whether it is reachable from 004 and whether it was pushed. Also lists secret-bearing file names. Output: `SECRETS_SCAN.md/.json`, which hold locations and redacted shapes only (no values, no sha10). **Deps.** Runs `pnpm licenses list` (all and `--prod`), `cargo metadata --locked --offline` (scoped by dep_kinds), and `scripts/r15/licence_scan.py` plus `pip list` per venv (3 venvs). It flags AGPL/GPL/LGPL/SSPL/unknown licences as bundled / build-only / dev-only, with the linkage. Output: `DEPS_LICENCES.md/.json`. **Licence.** Checks every licence statement against PolyForm Strict core + commercial, with Apache-2.0 for the plugin contract and example plugin. Output: `LICENCE_CHECK.md`, listing each mismatch with the exact line and marking Tier-1 files. |
| 4 | Critic | 5 Fable high via `run()` (one Opus fallback each), then 0-5 Sonnet high revisers | Each critic starts as soon as its own draft lands (no barrier). It reads the draft cold as the intended reader, checks every command against package.json/scripts/CI/CLAUDE.md and every claim against `FACTS.md` and the repo at the sha, and writes `critic/<NAME>.md` with numbered findings (wrong / missing / stale / unverifiable) and a PASS/REVISE verdict. On REVISE, one reviser applies the findings in place, then adds a `<!-- critic-footer -->` line and a `## Critic findings applied` section after it. One round only. |
| 5 | Collate | 1 Sonnet medium | Checks that every file exists with the right line-1 header. Runs an **output guard**: the pre-push rule set runs over EV, and any match is redacted in place, never printed. Writes `STAGE_D_INDEX.md` (one row per file: status, critic findings, lead questions, and how to promote) and `OPEN_QUESTIONS.md` (operator-only items: Tier-4, bundled copyleft, Tier-1 licence mismatches, Windows, real or pushed secrets). Then commits **only EV** on 004 with `git add -A -- EV && git -c core.hooksPath=/dev/null commit --only -F msg -- EV` in one call. The subject is `docs(r15): stage-d docs wave at <sha7> - <n> drafts, <m> scans` (`refresh` replaces `wave` in refresh mode). Never pushes. |

Draft status: **PASS** (critic passed), **REVISED** (critic REVISE, reviser applied), **UNREVIEWED** (the critic returned nothing even after the Opus fallback), or **FAILED** (the drafter died, or the reviser died after a REVISE, or the collator's file/header check failed). Scan status is **DONE** or **FAILED**. Lanes skipped by args show as **SKIPPED**.

## Lanes

**Used:**

- `git show / log / grep / ls-tree / blame / diff / cat-file / tag / merge-base / branch --contains` at the sha, read-only.
- `git ls-files --others --exclude-standard` (never `git status`, which can rewrite the index under the other workflows).
- Plain reads of `node_modules` and the three sidecar venvs.
- `pnpm licenses list`, `cargo metadata --offline --locked`, `pip list` and `importlib.metadata`, run detached. If a log shows the cargo or pnpm cache locked for more than 5 minutes, the agent kills only its own process and takes the fallback.
- The two `scripts/r15` probes, run with `PYTHONDONTWRITEBYTECODE=1`.
- curl to the outside world, at most 1 request per 3 s per host.

**Never used:**

- The operator's live app, `:5173`, or any GUI.
- Any sidecar or 127.0.0.1 request.
- Ollama or any local model.
- Agent runs.
- The heavy lane: `pnpm install`, `ci-local`, build, full pytest/vitest, cargo build/test/clippy, PyInstaller, ensure-* scripts, tauri build/dev, and the smoke test.
- Installs.
- Writes outside EV and the scratch dir.

The brief and `r15/local/` are excluded from every grep, and a secrets hit there is reported as path + rule only.

## Outputs (all under EV)

| File | Holds |
| ---- | ----- |
| `FACTS.json`, `FACTS.md` | the facts every agent reads instead of re-deriving |
| `README.draft.md` | stranger-facing README: what it is / is not, macOS install + build from source, BYOK storage, licence split, plugin Apache-2.0 carve-out, support pointers |
| `RELEASE_RUNBOOK.draft.md` | target `docs/RELEASE_RUNBOOK.md`: the ordered steps, each with its command, owner and expected output. Steps: version bump list, `pnpm install --frozen-lockfile`, `pnpm ci-local`, sidecar builds, smoke test, `pnpm tauri build`, clean-profile launch (lead), signing/notarization (NEEDS-OPERATOR, RELEASE-001..004), tag/release (operator-only), Windows (NEEDS-MANUAL-CHECK), rollback |
| `OPERATOR_BRIEFING.draft.md` | target `docs/redesign/OPERATOR_BRIEFING.md`: shipped / open and why / operator-attended / relaunch / evidence map / revertable decisions, with `<!-- fill at rc2: … -->` markers |
| `RELEASE_NOTES.draft.md` | part A: 0.9.0 release notes (changed / removed: trading / licence / fixed (certified only) / known limitations); part B: the CHANGELOG `## v0.9.0` section |
| `CURRENT_STATE.draft.md` + `.draft.diff`, `BLOCKERS.draft.md` + `.draft.diff` | full proposed text and unified diffs against the files at the sha (`patch -p1` from the repo root) |
| `SECRETS_SCAN.md/.json`, `DEPS_LICENCES.md/.json`, `LICENCE_CHECK.md` | the three scans (first line `<!-- SCAN at <sha> … -->`) |
| `critic/<NAME>.md` | numbered findings + verdict per draft (`NAME` = README, RELEASE_RUNBOOK, OPERATOR_BRIEFING, RELEASE_NOTES, STATE) |
| `STAGE_D_INDEX.md`, `OPEN_QUESTIONS.md` | the index for the lead; the operator-only questions |

Line 1 of every draft is `<!-- DRAFT at <sha> by the Stage D docs wave; refresh before rc2 -->`.

## The rc2 refresh (how the lead reuses it)

1. At the rc2 candidate, relaunch with `mode: "refresh"` and the new sha, using the same `out`. Facts regenerates at the new sha and records `previous_sha` and the diff. Each drafter reads its own draft, takes `old_sha` from line 1, and reads `git log` / `git diff --stat <old_sha>..<sha>` plus the diffs of its sources. It then updates only what moved, fills the `fill at rc2` markers the new facts settle, drops the old critic footer, rewrites line 1 and appends a `<!-- refresh a→b: … -->` note. A missing draft is written fresh. The scans re-run in full and add a "Since <previous sha7>" section. The critic runs again, for one round.
2. Promote: strip line 1 and everything from `<!-- critic-footer -->` down, then copy to the targets in `STAGE_D_INDEX.md`. For the state docs, run `patch -p1 < EV/CURRENT_STATE.draft.diff` (and BLOCKERS) from the repo root. Part A of the release notes goes into the GitHub release body, and part B goes into `CHANGELOG.md`.
3. `OPEN_QUESTIONS.md` goes to the operator unchanged.

## Sizing and pacing

- **Agents:** 1 facts + 5 drafts + 3 scans + 5 critics + 0-5 revisers + 1 collator, so 15-20. The worst case is 25, if every Fable critic falls back to Opus.
- **Concurrency:** peak is `cap` (6). The 8 first-wave agents queue behind the limiter, and critics start as their drafts land.
- **Time:** the target is under an hour: facts ~10 min, drafts and scans ~20-25 min, critics and revisers ~15 min, collate ~5 min.
- **Logging:** everything bounded or dropped is logged: skipped lanes, not-scanned ecosystems, the Fable→Opus fallbacks, UNREVIEWED and FAILED rows, files a drafter wrote outside its assignment, rows the collator failed, and output-guard redactions.

Routing change 5 (25 Sep 2026): Sonnet is the default: effort medium for facts and collate, effort high for drafters, scanners and revisers (clear spec, checkable output). Opus at effort high judges the critics (fresh-context review). Fable is not used anywhere in this workflow. The `run()` retry stays a single same-tier retry (label suffix `-retry`, never a third try), now retrying on whichever model the call used rather than hardcoded to Fable.

## Resume

Relaunch with the same script, the same args and `resumeFromRunId`, and finished agents replay from the cache. A restarted agent continues from its own files at the same sha, because every prompt carries the restart rule and each file's line 1 names the sha.

## Known limits

- The deps scan reads the **main worktree's** installed trees (`node_modules`, the venvs, `src-tauri`). When a lockfile at the sha differs from the working tree, every row of that ecosystem says so; the scan never installs to match.
- `history_secrets_scan.py` walks `--all` refs, so its scope is wider than 004. Each hit is classified as reachable from 004 or not, and as pushed or not.
- The drafts quote expected command output from existing evidence only. The lead's clean-profile macOS build fills the remaining `fill at rc2` markers.
