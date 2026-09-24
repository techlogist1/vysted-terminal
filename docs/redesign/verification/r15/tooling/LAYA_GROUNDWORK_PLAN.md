# R15 Laya groundwork: workflow plan

Script: `docs/redesign/verification/r15/tooling/laya-groundwork.js`. This is scope change 2. Laya (Convai Innovations, github.com/NandhaKishorM/laya) is a 421M ModernBERT encoder that answers typed questions over a short passage in one forward pass: `choice` over a fixed option set, `score` on an ordered rubric, and `noul` as a yes/no probability. It generates nothing. The terminal makes hundreds of small typed text decisions per session, and today each one costs either a paid model round-trip or a keyless heuristic. Four examples: whether a retrieved passage is about the entity the user asked for (the KSE-class collision), which surface a composer message belongs to, whether a news item concerns a holding, and whether a filing sentence contradicts the written thesis. The groundwork measures whether a fine-tuned Laya could take those decisions locally. The eventual target is a post-0.9.0 filing watcher.

**Operator decision:** nothing here enters the release. No Laya code is added, and no release document mentions Laya (README, CHANGELOG, runbooks, briefings, `docs/*.md`, DECISIONS). All output is verification evidence under `docs/redesign/verification/r15/laya/`, plus one candidate entry in `r15/invent/BACKLOG.md` for the Stage E judge panel. The panel ranks that entry and does not build it.

## Launches

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/laya-groundwork.js", args: {mode: "prep", sha: "<current 004 head>"}})
Workflow({scriptPath: "…/laya-groundwork.js", args: {mode: "prep", dry_run: true}})
Workflow({scriptPath: "…/laya-groundwork.js", args: {mode: "measure", sha: "<current 004 head>"}})
```

Add `dry_run: true` to any of these to check a launch without spending anything. The script logs every agent it would spawn (label, model, effort), returns `{mode, dry_run: true, would_spawn, writes}`, and **spawns no agent**. The number of labelling shards is known only after mining, so a prep dry run lists the labeller pair as one line per family.

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `mode` | required | `prep` or `measure`. The script throws on anything else. |
| `sha` | required for prep unless `dry_run` | The 004 head, recorded as the base in every candidate's provenance and in `DATASET.md`. It must be 7 to 40 hex characters. |
| `max_shard` | 40 | The number of items per labelling shard, an integer from 1 to 200. |
| `min_items` | 1000 | The clean-item target after disagreement drops. It is informational only: the script logs whether it was met. |
| `venv` | `<scratch>/laya-venv` | The scratch venv. The script throws if it points inside the repo, so `sidecar/.venv` can never be used. |
| `scratch` | this session's scratchpad | The scratch root. Weights are cached in `<scratch>/laya-hf` (`HF_HOME`). |

## Lane rules

- **PREP** runs alongside other work that only calls the API. Its heaviest local step is the install smoke: at most 20 items, lasting seconds, in a subprocess that exits so the model is unloaded. It never boots a sidecar or builds anything, and it never touches `sidecar/.venv` or `node_modules`.
- **MEASURE** runs only when both the local-model lane and the heavy-job lane are idle. That is expected in the lows-write window after `r15-rc1`. Its first agent checks the lanes: no ci-local, cargo, pnpm/tauri build, pyinstaller, vitest or pytest running; no ollama generation in progress; 1-minute load below 0.75 × ncpu; at least 3 GB of free plus inactive memory. If any check fails, the run returns `{aborted: 'lane_busy', state}` and spawns nothing else. Relaunch it later.
- Agents write only under `r15/laya/` (measure mode may also write `r15/invent/BACKLOG.md`) and in the scratch dir. They never read `R15_BRIEF*.md` or `r15/local/`. They never touch `src/`, `sidecar/`, `types/`, `CLAUDE.md`, the spend ledger or any release document.
- **Git:** only the assembler, installer and backlog agents commit, and only on 004 in the main worktree. Each one checks the branch first, then runs `git add` followed by `commit --only` on explicit paths, never `-A`. If a push is rejected because origin moved, it is reported as `pushed: false` and never rebased or forced. The backlog drafter runs last so that its commit cannot race the other two.

## Agents

Every call names its model and effort. The `run()` wrapper throws unless the model is `opus` or `sonnet` and the effort is set. A limiter caps the run at 6 agents at once, in first-in, first-out order. An agent that dies gets **one same-tier retry** (`<label>-retry`), never a third try. A disagreement between labellers is never retried.

| Mode | Phase | Label | Model / effort | Job |
| ---- | ----- | ----- | -------------- | --- |
| prep | Verify | `laya-verify` | Opus / high | Checks the repo, the LICENSE file, the release date, the model card, and the PyPI `laya` / `laya-mlx` JSON (authors, versions, `python_requires`, dependencies, backlinks to the repo). It downloads wheels only and inspects them for install-time and import-time hooks. It never installs anything. |
| prep | Baseline | `laya-scout-code` | Sonnet / medium | Lists every small typed text decision in `sidecar/` and `src/` with its file:line, the path it takes today (paid, local, heuristic or none), whether it works keyless, and any cost hints. |
| prep | Baseline | `laya-scout-evidence` | Sonnet / medium | Gathers per-session counts, latencies and costs from the r15 evidence and the spend ledger, with the path to each source. |
| prep | Baseline | `laya-baseline` | Opus / high | Spot-checks the two scouts' results, then writes `BASELINE.md` and `.json` and the business case. |
| prep | Options | `laya-options` | Sonnet / medium | Finds the fixed composer surface set (at most 8 options) in the real routing code. |
| prep | Mine | `laya-mine-{research,collision,composer,news}` | Sonnet / high | One agent per source family. Each copies real passages from the evidence into `candidates/<family>.jsonl` with ids `<family>-1..n`, aiming for about 600 items per family, and says when the evidence runs out. |
| prep | Label | `laya-label-<family>-<k>-{A,B}` | Opus / high | Two labellers per shard of `max_shard` ids. Their prompts are identical apart from the role name, and neither sees the other's labels. |
| prep | Assemble | `laya-assemble` | Sonnet / medium | Runs only if the package is verified. Writes the dataset files and `DATASET.md`, then commits `r15/laya/`. |
| prep | Install | `laya-install` | Sonnet / high | Runs only if the package is verified and the dataset was assembled. Creates the venv with `uv venv --python 3.12` (3.13 as the fallback), installs `laya-mlx` pinned to the verified version, and runs a smoke of at most 20 items under `/usr/bin/time -l`. Writes `INSTALL.md` and commits it. |
| prep | Backlog draft | `laya-backlog-draft` | Sonnet / high | Writes `BACKLOG_ENTRY.md` ending "Verdict: pending MEASURE" and commits `r15/laya/`, which picks up any evidence the assembler did not commit. |
| measure | Lane check | `laya-lane-check` | Sonnet / medium | Checks that both lanes are idle, as described in Lane rules. |
| measure | Measure | `laya-measure` | Sonnet / high | Runs the zero-shot measurement described below, writes `measurements/*.json` and `VERDICT.md`, and exits so the model is unloaded. |
| measure | Critic | `laya-verdict-critic` | Opus / high | Re-runs the commands on a subset of at least 50 items per task and checks the arithmetic (ECE, the gate, the split, the majority baselines), the honesty of the comparison and the sources. Fixes `VERDICT.md` in place. |
| measure | Backlog | `laya-backlog` | Sonnet / high | Finalizes the entry with the verdict numbers, inserts it into `r15/invent/BACKLOG.md` as an unranked candidate, then commits and pushes. |

Agent counts: prep spawns 12 fixed agents plus 2 per labelling shard. About 2,400 candidates at 40 per shard gives 60 shards, which is 120 labellers. Measure spawns 4. Retries can at most double either count.

The measurer runs every dataset item through `noul` for `entity_match` and `holding_relevance`, and through `choice` for `composer_intent`. It splits each task into halves A and B with `Random(918)` over the sorted ids. For each yes/no task it reports a precision/recall sweep and a gate: the lowest threshold that reaches precision ≥ 0.90 on B, or else the max-F1 point. For `composer_intent` it reports accuracy and the confusion matrix against the majority rate. It fits one temperature on A and reports ECE (10 bins) and the reliability table on B, before and after the fit. It also reports p50/p99 latency for single and batched calls, throughput, and peak and steady RSS with the recorded sidecars up. Finally, it compares against the current path: the keyless heuristics are imported read-only from the sidecar source, and the paid paths are marked "not run (needs a key)".

## Labelling protocol

1. The script builds shards from each extractor's `count`: consecutive runs of `max_shard` ids, `<family>-1` onward. It never reads the file, so ids must be contiguous. An extractor whose `ids_first`/`ids_last` do not match is logged, and any id missing from the file is labelled `skip`.
2. For each shard, LABELLER A and LABELLER B run in parallel. They receive the same id list, the same task rule and the same composer option set. Each writes `labels/<family>-<k>-<A|B>.json` as it goes. A yes/no task is answered `yes` or `no`, a `composer_intent` item gets one of the fixed options, and an unusable item gets `skip`.
3. **The script computes agreement in JS.** Answers are normalised: yes/no answers are lowercased, and option answers are matched case-insensitively to the fixed set. An item counts as agreed when both answers are the same and neither is `skip` or invalid. Every other item is dropped with both answers kept (`[n, a, b]`). There is no third labeller and no retry on disagreement. Each shard's agreement rate and the running totals are logged.
4. The assembler joins the agreed ids back to their candidate lines. It uses the fine-tune format the package documents, or `{task, passage, question, options, answer, provenance}` when none is documented, and keeps the id and provenance on every row. When the same task, passage and question appear under two families, the first id is kept and the duplicate is listed in `DATASET.md`.

## Outputs (under `docs/redesign/verification/r15/laya/`)

| File | Written by | Holds |
| ---- | ---------- | ----- |
| `PACKAGE_VERIFICATION.md` | verifier | Each claim marked confirmed, refuted or unverifiable, with its source; the artefact inspection; the licence notice text; the API; the fine-tune format; the risks |
| `baseline/code-sites.json`, `baseline/evidence.json` | scouts | The raw sites and observations |
| `BASELINE.md` / `.json` | analyst | Each decision type with its sites, per-session count, latency, cost and keyless status; the totals; the business case |
| `OPTIONS.json` | options scout | The fixed composer surface set and the code it came from |
| `candidates/<family>.jsonl` | extractors | `{id, task, passage, question, options, context, provenance {file, locator, sha}}` |
| `labels/<family>-<k>-<A\|B>.json` | labellers | `{shard, labels [{id, answer, confidence, note}]}` |
| `dataset/{entity_match,composer_intent,holding_relevance}.jsonl`, `dataset/DROPPED.jsonl` | assembler | The agreed items, plus the dropped items with both answers |
| `DATASET.md` | assembler | Counts, class balance, majority rate per task, provenance by family, the protocol, the base sha |
| `INSTALL.md` | installer | Versions, weights, wall time, peak RSS, per-item latency and p50, exact commands. On failure: NOT FEASIBLE and the error |
| `BACKLOG_ENTRY.md` | drafter, then finalizer | Filing watcher: System 1 triage in front of the BYOK model. Covers the design, whether ingestion exists today, the fine-tune plan, the Apache-2.0 notice, the Windows route (PyTorch or ONNX) and the baseline |
| `measurements/*.json`, `VERDICT.md` | measurer, critic | Every number with its source and command, and the critic's corrections |

Returns: prep gives `{mode, sha, verified, baseline, options, candidates, per_family, agreed, dropped, dataset, feasible, commits}`, plus `status`, `reasons` and `labels` when blocked. Measure gives `{mode, numbers, critic, inserted, commits}`, or `{aborted, state}`.

## Failure modes

- **Verification fails** (`verified !== true`): the run logs `BLOCKED_BY_VERIFICATION` with the reasons, and assembly and install are skipped. Mining and labelling still run. The agreed and dropped lists are returned in the run's `labels` and remain in `labels/*.json`, and the backlog drafter commits `r15/laya/` as evidence. Once the cause is resolved, relaunch prep with `resumeFromRunId`. The labellers replay from the cache.
- **Install fails:** `INSTALL.md` records NOT FEASIBLE with the exact error and `feasible: false`. Do not launch measure until a fixed install records a feasible run.
- **Lane busy:** measure returns `aborted: 'lane_busy'` with the lane state. Relaunch it when both lanes are idle.
- **A dead agent** gets one same-tier retry. A labeller that dies twice drops its whole shard as disagreements, and this is logged. An extractor that dies twice leaves its family empty, also logged. A dead run is relaunched with the same script and args plus `resumeFromRunId`.
- **Push rejected:** the commit stays local and `pushed: false` is logged. The lead pushes.
