# R15 lows pre-triage: workflow plan

Script: `docs/redesign/verification/r15/tooling/lows-triage.js`. This is a read-only "refute / re-check" wave over every **open low** entry in `docs/redesign/verification/vysted-r15-register.json` (205 at batch-9 planning). It runs before the low fix batches. Stage C batches 2-9 (`git log a122dbf6..<sha>`) root-cause-fixed many lows as side effects, and some are not defects at today's HEAD. The wave sorts them out so the low batches plan against the real backlog. It fixes nothing and flips no register status.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/lows-triage.js", args: {sha: "<004 commit>", shard_size: 12, cap: 8, exclude_ids: [], only_ids: null, dry_run: false}})
```

## Args

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `sha` | required | The 004 commit to check against (7-40 hex). The script throws without it. The indexer resolves it and refuses (`status: 'blocked'`) if it is not 004 or an ancestor. |
| `shard_size` | 12 | Target entries per Refute shard (hard ceiling `shard_size + 4`, logged). |
| `cap` | 8 | Concurrent agents for this wave: one limiter around every `agent()` call, clamped to 16 (the pacing ceiling). |
| `exclude_ids` | `[]` | Ids to leave out, e.g. lows a running batch owns. |
| `only_ids` | `null` | Restrict the wave to these ids (absent, non-open or non-low ids are listed in `skipped`). |
| `dry_run` | `false` | Index only: writes `INDEX.json` / `INDEX.md` (uncommitted), creates no checkout, refutes and commits nothing. Use it to preview the sharding. |
| `scratch` | this session's scratchpad | Optional, as in rc1-gate: the scratch root if the scratchpad is gone. |

Return: `{status: 'done' | 'partial' | 'dry_run' | 'blocked', sha, counts: {already_fixed, still_reproduces, not_a_defect_proposed, duplicate_of, blocked, missing}, files, missing, commit}`. `partial` means the collator died: counts come from the agents' returns, and nothing is committed.

## Phases

| # | Phase | Agents (model, effort) | What it does |
| - | ----- | ---------------------- | ------------ |
| 1 | Index | 1 Sonnet medium | Resolves the sha. Records the shared stack (pid, cwd, start time, the source head it runs, health). Selects `status == 'open' && severity == 'low'` from the register **at the sha** (`git show <sha>:…`), then applies `only_ids` and `exclude_ids`. Creates `git worktree add --detach <scratch>/lows-triage-<sha7> <sha>` and symlinks the main worktree's `sidecar/.venv` and `node_modules` into it, read-only (`ln -s`; never installs, never writes into either). Boots the wave's **own main sidecar at the sha** on `127.0.0.1:52350` from the checkout. It uses the ISO_STACK.md source-run recipe, the main sidecar only, with the MCP port env vars unset so the openbb-mcp and sec-edgar-mcp routes degrade. The data dir is an empty keyless `<checkout>/.lows-triage-data`, seeded with `dev-keystore.json` `{"secrets": {}, "migrated": true}`. The indexer polls `/health` in separate short calls and writes `stack.json`. Groups entries into shards by subsystem, then shared files, then area. Writes `INDEX.json` / `INDEX.md`. On a restart at the same sha it reuses the shards verbatim. If the dir holds a triage at a different sha, it clears the dir first. The script then re-applies the filters, allows each id in only one shard, and logs anything it drops. |
| 2 | Refute | 1 Fable high per shard, through `run()`. A shard that dies or starves on Fable gets one Opus fallback, never a third try. | Handles each entry in order. It reads the entry (with its verifier note), `git log a122dbf6..<sha> -- <files>`, `--grep=<id>` and the stage-c batch dirs, then opens the code at the sha. It then re-runs the original repro by the cheapest allowed lane. Right after each entry it appends one JSON line to `shard-<k>.jsonl`, so a killed agent's work survives. A restarted agent continues from the first id not yet in the file. At the end it writes `shard-<k>.md`. The shards run as a `pipeline`: each one's tally is logged when it lands, and none waits on another. |
| 3 | Critic | 1 Opus high (a barrier, after every shard) | Re-runs a deterministic sample: 10% of `already_fixed` (at least 8, spread evenly over the sorted ids), every `not_a_defect_proposed` at confidence ≤3, and, for a shard that returned nothing, the same rule over its partial jsonl. It re-runs the probe plus one fresh variant and reads the fix commit's diff. Any verdict that does not hold is flipped. It writes `CRITIC.json` / `CRITIC.md`, including the modalities the wave did not use. It is skipped when there is nothing to sample. |
| 4 | Collate | 1 Sonnet medium | Merges `shard-*.jsonl` (the last line wins for a repeated id) with the critic's flips into `LOWS_TRIAGE.json` / `.md` and lists `missing` ids. Then it stops the own sidecar, killing only the pid in `stack.json`. It first checks that the pid's command line contains the checkout path, and says so if the pid is already gone. It never uses `-9` or a blanket kill. It then kills the recorded `sleep 86400` stdin holder. It unlinks the two dependency symlinks and removes the scratch checkout (that path only, never `prune`). Commits only the evidence dir on 004: `git add -A -- <EV> && git -c core.hooksPath=/dev/null commit --only -F <msg> -- <EV>` in one call, so nothing another agent staged is swept in. The subject is `docs(r15): lows pre-triage at <sha7> - <counts>`. Never pushes. Refuses to commit if the main worktree's HEAD is not on 004. |

## Verdicts (one jsonl line per entry)

`{id, verdict, fix_commit, duplicate_of, blocked_kind, fix_shape, reason, evidence_paths, confidence 1-5, note, model}`

- **`already_fixed`**: names the fixing commit (git log/blame on the cited lines). It needs a **fresh** probe or focused test at the sha showing the original repro no longer reproduces.
- **`still_reproduces`**: the default when uncertain (the cheap error). Carries `fix_shape {files, acceptance_test, effort S/M/L, collides: none | trading_removal | redesign}`. A partial fix lands here, with the residual named.
- **`not_a_defect_proposed`**: the reason is grounded in code at the sha or in the spec (`file:line`).
- **`duplicate_of`**: the surviving id and its status at the sha.
- **`blocked`**: `needs_gui` / `operator` / `tier4`, with the reason. Used only when no allowed lane can decide.

## Lanes

**Used:**

- The read-only scratch checkout at the sha. No builds, installs or edits. Its `sidecar/.venv` and `node_modules` are read-only symlinks to the main worktree's.
- `git show` / `log` / `blame`.
- **The wave's own main sidecar on `:52350`** (GET only), booted from the checkout at the sha. The wave owns this port, and nothing else in the run uses it. The indexer starts it and the collator stops it. It is the probe target for at-sha evidence. It has an empty keyless profile and no MCP sidecars, so MCP-backed routes degrade there by design, and that is not a finding.
- **Fallback only:** the shared stack on `:52152` (GET only; MCP on `:52153` / `:52154`), which runs an older tree. Refuters use it only when `stack.json` says the own sidecar is not up. A verdict that leaned on it says so in its note, and its confidence is capped at 3.
- The outside world via curl.
- Focused tests of 120 s or less, run in the checkout: `PYTHONDONTWRITEBYTECODE=1 ./.venv/bin/python -m pytest file::test -q -p no:cacheprovider` and `pnpm exec vitest run --no-cache <file>`. If a symlink target is missing, the test is skipped with a note, and the script logs the skip.

**Never used** (another workflow owns them):

- The operator's live app, `:5173`, or any GUI.
- Ollama or any local model.
- The heavy-job lane: `pnpm install`, `ci-local`, full pytest/vitest, cargo, PyInstaller, sidecar builds, `tauri build`.
- Any agent run (`/agents/*/invoke`, `/runs`, `vy.py`).
- Any non-GET request.
- Starting or stopping any process.
- Any write to the register or to a tracked file outside the evidence dir.
- Secrets are never printed.

## Evidence (all under `docs/redesign/verification/r15/stage-c/lows-triage/`)

| File | Holds |
| ---- | ----- |
| `INDEX.json`, `INDEX.md` | sha, shards `{k, ids, hint}`, total, skipped (with reasons), the `:52152` stack record, checkout record |
| `stack.json` | the own sidecar: `{up, pid, stdin_pid, wrapper_pid, port: 52350, sha, started_at, health_excerpt, log, reason}` |
| `shard-<k>.jsonl`, `shard-<k>.md` | one verdict line per entry, written as the agent goes; the readable table |
| `evidence/<id>/…` | raw probe / grep / test excerpts per entry (≤100 KB each, no secrets) |
| `evidence/critic/<id>.txt`, `CRITIC.json`, `CRITIC.md` | the critic's re-runs, checked ids, flips `{id, from, to, reason}`, unused modalities |
| `LOWS_TRIAGE.json` | `{sha, by_verdict: {verdict: [ids]}, entries: {id: {verdict, fix_commit?, duplicate_of?, blocked_kind?, fix_shape?, evidence_paths, confidence, note}}, missing}`, the file the next batch reads |
| `LOWS_TRIAGE.md` | counts table, per-verdict lists, critic flips, missing and skipped ids |

## How the next low batch consumes it (downstream; not implemented here)

1. **Adjudicator.** Appends the triage note to each register entry: `Lows pre-triage @ <sha7>: <verdict> (<fix_commit or duplicate or kind>), <evidence path>`. It changes no status on the triage's word.
2. **Planner.** Treats the verdicts this way:
   - **`already_fixed`**: verify-only entries. They take no writer slot, and the batch's fresh verifier still re-runs the original repro and certifies each one before it flips to `fixed`.
   - **`not_a_defect_proposed`**: proposals for the verifier's concur list. `concur_not_defect` / `refused_not_defect` stay the verifier's call. The four operator areas still need that recorded fresh concurrence.
   - **`still_reproduces`**: the fix queue. The planner starts from the sharpened `fix_shape`: files for disjoint writer sets, `acceptance_test` for the brief, and effort for sizing. Entries marked `collides` are routed or deferred explicitly.
   - **`duplicate_of`**: folded into the surviving entry's set.
   - **`blocked`**: `needs_gui` goes to the rc gate's GUI round; `operator` and `tier4` go to `DECISIONS_FOR_OPERATOR.md`.
   - **`missing` / `skipped`**: planned as if untriaged.
3. **Staleness.** The triage is valid at its sha. An entry whose files changed after that sha (`git diff --stat <triage sha> <batch base> -- <files>`) is re-checked by the planner, not trusted.

## Sizing and pacing

205 lows at 12 per shard is about 17-18 shards. At cap 8 that is 3 rounds of Fable at high effort, with a budget of about 2-3 minutes per entry (roughly 25-35 min per shard). The target is about half a window: **60-90 min**.

Agents: 1 indexer + N shards + 1 critic + 1 collator, so about 20 for the full backlog. The worst case is 37, if every Fable shard falls back to Opus. Peak concurrency is `cap` (8).

Everything bounded is logged: script-dropped or duplicated ids, skipped ids, oversize shards, the unsampled `already_fixed` count, high-confidence not-a-defect entries the critic did not re-check, dead shards, the focused-test skip, and any drift between the agents' returns and the collated files.

Routing change 5 (25 Sep 2026): Sonnet at effort medium is the default for the mechanical, checkable-output roles (indexer, collator); Opus at effort high judges refutation and fresh-context certification (the shard refuters, the critic). Fable is not used anywhere in this workflow. The `run()` retry stays a single same-tier retry (label suffix `-retry`, never a third try), now retrying on whichever model the call used rather than hardcoded to Fable.

## Resume

Same script and args with `resumeFromRunId` replays finished agents from the cache. A shard agent that restarts continues from its own jsonl, and the indexer reuses `INDEX.json` at the same sha. If the collator died, cleanup is manual:

1. Kill the own sidecar (the pid in `stack.json`, after checking its command line), then its `sleep` stdin holder.
2. Remove the two symlinks (plain `rm`, no `-r`).
3. Run `git worktree remove --force <scratch>/lows-triage-<sha7>`.

If the indexer restarts, it reuses a running own sidecar whose pid in `stack.json` still matches the checkout path.

## Known limits

- The own sidecar has an empty profile and no MCP sidecars. At the sha, behaviour that depends on user data or MCP is judged from code and focused tests. The older `:52152` stack is used only as the fallback, with confidence capped at 3.
- The symlinked `node_modules` and `.venv` match the main worktree's lockfiles. A sha whose lockfiles differ from the main worktree's could make a focused test fail for dependency reasons. Refuters must name such a failure as a dependency problem, not use it as a verdict.
