# R15 final pass: workflow plan

Script: `docs/redesign/verification/r15/tooling/final-pass.js`. It is the one final adversarial pass the brief allows after `r15-rc3`: one workflow, its findings closed under gate 3 inside that workflow, and no second pass. It ends with the run-ending steps, which run only when `run_ending` is true.

## Launch

The file `launch-args/final-pass.json` holds the first launch's args. Before launching, replace `RC3_SHA` with `git rev-parse r15-rc3^{commit}`.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/final-pass.js", args: {sha: "<r15-rc3 sha>", max_fix_rounds: 2, adversaries: 2, run_ending: false}})
```

To check that the harness loads the script without spawning anything, add `dry_run: true`. That call validates the args, logs every agent it would spawn (label, model, effort, port) and returns `{dry_run: true, would_spawn}`.

The run-ending steps run on the **same** workflow, resumed. After reading the sheet (see the lead's steps below), relaunch with `resumeFromRunId: "<the first run's id>"`, the same args and `run_ending: true`, plus `caffeinate_pids: [...]` if you want to name the pids yourself. No prompt in stages 1-5 reads `run_ending` or `caffeinate_pids`, so every earlier agent replays from the cache and only stage 6 runs live. The stub harness proves this by comparing the prompts of both launches.

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `sha` | required | The `r15-rc3` commit, 7-40 lowercase hex. Preflight blocks if the `r15-rc3` tag points elsewhere. |
| `max_fix_rounds` | 2 | Gate-3 fix rounds, 0..3. With 0, admitted entries go to the re-proof unfixed. |
| `adversaries` | 2 | Strongest-tier adversaries, 1..2 (lens 1 investor, lens 2 maintainer). A value of 3 or more is refused. |
| `run_ending` | false | Stage 6. It must be the boolean `true` (or `"true"`), and stage 6 still runs only after a PASS. |
| `drive_groups` | the 8 census groups | The owner-drive groups from `PROMPT_surface_s2.md`: 1..8 names. |
| `batt_shards` | 4 | Battery shards, 1..8. Ids are dealt by sorted position mod N, so no indexer agent is needed. |
| `max_writers` | 4 | Writer sets per round, 1..6. Sets beyond the cap are logged and stay open. |
| `bundle_path` | none | An absolute path to a production bundle already built at the sha. Preflight accepts it only if the evidence behind it names the sha. |
| `caffeinate_pids` | none | Stage 6 only. Without it, the agent reads the armed pids from the run-state header. |
| `scratch` | this session's scratchpad | The scratch root. |
| `dry_run` | false | Spawn nothing (see above). |

Unknown keys are refused, so a typo like `max_fix_round` throws instead of being ignored.

## Stages and agents

`run()` enforces routing change 5 in code. Sonnet and the strongest tier always run at effort `high`. Opus runs at its default effort, with no `effort` key. The strongest tier may run only in the Sweep phase, and a limiter holds it to two agents at once, retries included. A call that dies gets one same-tier retry (label `-retry`), never a third try. There are 13 agent call sites, and every one names its model.

| # | Phase | Agents (model, effort) | Why that tier | What it does |
| - | ----- | ---------------------- | ------------- | ------------ |
| 1 | Preflight | `final-preflight`: Opus, default effort | Risk-adjacent: it builds the artifact and boots the shared stack | Resolves the sha and checks the `r15-rc3` tag. Creates the worktree `final-cand` and installs clean (`ensure-all-sidecars --force`). Accepts a production bundle built at the sha, or builds one there with `pnpm tauri build` in its own node_modules, venvs and target (this also writes `out/`). Seeds the keyless data dir and boots the dedicated stack on :52800 (main), :52801 (openbb-mcp) and :52802 (sec-edgar-mcp) from the built binaries. Records Ollama and disk state and takes the register snapshot at the sha. If preflight is blocked or dies, the script returns `blocked` and spawns nothing else. |
| 2 | Sweep | `final-adv-investor` and `final-adv-maintainer`: strongest tier, high. Beside them, Opus at default effort: `final-chain`, `final-docs`, 8 × `final-drive-<group>` and 4 × `final-battery-<k>`, at most 4 at once | The brief allows the strongest tier for the final adversarial pass, at most two at once and never above high. The mechanical re-runs are Opus, as the tail brief specifies, and 2 + 4 keeps the harness cap of 6 | Each adversary starts from a stranger's clean profile (an empty data dir plus a keyless `migrated: true` keystore), runs its own stack from the built binaries, and drives the static frontend headless. **Investor** (:52810-52812, web :5281): first launch, data trust on a small-cap it picks itself and a trap India name against screener.in, NSE/BSE and EDGAR, the agent's reflexes (no order in any mode), and the UI at 1920×1080, 1280×800 and 1024×768. **Maintainer** (:52820-52822, web :5282): lifecycle, edge failures induced at the app's edge only, docs vs reality, the safety boundary (an order attempt halts, `audit_orders` has zero rows, the safety-surface diff against `r13-bedrock`), and scans for secrets, licences and the banned word and phrase. **Chain**: `pnpm ci-local` and the smoke test in `final-cand`. **Drives**: the rc1 owner-drive method, with writes to :52840+i. **Battery**: every `fixed` id at the sha, raw output per id, on :52860+k. **Docs**: the grep set (a) through (g) below. This is a barrier, because triage dedupes across all lanes. |
| 3 | Triage | `final-triage`: Opus, default effort | Refutation and root-causing | Dedupes the findings and refutes or admits each one against the code and the register at the sha, re-running repros on :52880. Assigns severity by the rubric. Admitted items become `R15-FINAL-NNN` register entries. These are edited in the main checkout's working tree only when that copy equals the sha's; otherwise they go to `REGISTER_ADDITIONS.json`. Nothing is committed. Refuted findings are recorded with rationale. Triage is skipped when there are no findings and no open c/h/m entries. |
| 4 | Close (≤ `max_fix_rounds`) | Per round: `final-fix-r<N>-plan` (Opus), up to 4 writers `final-fix-r<N>-<name>` (Sonnet/high by default, Opus for root-cause or risk-adjacent sets, worktree isolation), `final-fix-r<N>-int` (Opus) and `final-fix-r<N>-verify` (Opus). That is at most 7 agents per round | Sonnet for clear-spec fixes with an acceptance test; Opus for planning, integration and fresh certification | The planner puts c/h/m first and adds lows where a writer has capacity. Tier-1 fixes go to `deferred`, with a DECISIONS_FOR_OPERATOR item. Writers commit and push `worktree-agent-final-r<N>-<name>` after each entry. The integrator merges into `worktree-agent-final-int`, in the scratch `final-int` worktree, and needs ci-local and smoke green. The verifier certifies each claim from the running app on :52886+N, with one fresh case per entry, or adjudicates it (not_a_defect, not_reproducible or environment) with a rationale anyone can re-run. The loop stops early if the planner, every writer, the integration or the verifier dies. A dead verifier leaves its entries marked `uncertified` for the re-proof to certify. |
| 5 | Re-proof | `final-reproof`: Opus, default effort | Fresh-context certification | Works at the final head (the int head if a round integrated green, else the sha), on :52895. Runs the regression suite: ci-local and smoke at the head, or at the sha it cites the chain lane's EXIT=0 logs and re-runs smoke. Re-proves the gate-8 boundary: routes, tools and MCP names, `test_no_trading_surface.py`, agent and direct order attempts halt, zero rows in `audit_orders` (or proven absence), the full safety-surface diff against `r13-bedrock` with a per-file table, a tracked-portfolio round trip and a gated agent write. Checks gate 3: re-runs every certified critical and high entry and up to 3 mediums, and concurs or refuses the four-area adjudications. It adjudicates leftovers only on evidence; "ran out of rounds" is never a rationale. Records before/after evidence per named area. Sets final register statuses in the working tree. Writes `R15_FINAL_PASS.md`, whose last line reads `VERDICT: PASS - certified sha …` or `VERDICT: FAIL - …`. Finally it stops the :52800-52802 stack by its recorded sleep pids. |
| 6 | Run-ending (only when `run_ending` is true and the re-proof passed) | `final-run-ending`: Opus, default effort | Risk-adjacent: it touches the operator's stack | Refuses (`blocked`, changes nothing) unless the main checkout's HEAD and `origin/004` both equal the certified sha. Otherwise it runs the four steps below and writes one evidence line per step into the sheet. |

Peak concurrency is 6: 2 adversaries plus 4 Opus lanes in the Sweep. Every other stage runs one agent at a time, except the writers (at most 4). The total is 17 (preflight + 16 in the Sweep) + 1 triage + 7 per round + 1 re-proof (+1 run-ending), plus retries: 26 agents for one round and 33 for two.

Each prompt starts with COMMON. It carries the rc1 text (the stall rule, the local-model lock, tests-are-state and the forbidden reads) and adds:

- the brief's boundaries: no order in any mode, failures induced only at the app's edge, the operator's data, keystore and installed copy read-only, never a blanket kill, never stopping anything that is not Vysted's, never a secret;
- the git rules: `git -c core.hooksPath=/dev/null commit`, pushes with the id_ed25519 `GIT_SSH_COMMAND`, never `git add -A`, CLAUDE.md and the spend ledger left uncommitted, and the main checkout's HEAD never moved;
- the words rule. The script builds the banned word and phrase from char codes, so none of these files contains them (a case-insensitive grep over the three files finds 0 hits). Agents grep for them through `printf` escapes and report counts and file:line only.

### The docs-vs-reality grep set (`final-docs`)

- **(a)** One version string everywhere: package.json, Cargo.toml, tauri.conf.json, `FastAPI(version=…)`, `HOST_VERSION`, the top of CHANGELOG, README and `/health`.
- **(b)** Every `pnpm <script>` and `node scripts/…` in README, CURRENT_STATE, the runbook and the release notes exists.
- **(c)** Every repo path those documents and the top CHANGELOG section name exists at the sha.
- **(d)** docs/SIDECAR_API.md matches the live `/openapi.json`, both ways.
- **(e)** docs/MCP_INTEGRATION.md matches the live MCP list, both ways.
- **(f)** No user-facing document or in-app string offers trading (D81). Historical records are classified.
- **(g)** The banned word and phrase, case-insensitive, over the release docs and `src/` user-facing strings. The bar is 0.

## Evidence (under `docs/redesign/verification/r15/final-pass/`, uncommitted until the lead commits it)

| File | Written by | Proves |
| ---- | ---------- | ------ |
| `PREFLIGHT.md`, `pids.json`, `register-at-<sha7>.json`, `logs/final-preflight.md` | preflight | The sha, the tag, the clean build and bundle (path, sha256), the shared stack and the register snapshot |
| `adversary/investor/**`, `findings/investor.json` | lens 1 | The first hour, with outside-world comparisons and UI widths |
| `adversary/maintainer/**` (incl. `safety-surface.diff`), `findings/maintainer.json` | lens 2 | Lifecycle, edge failures, docs vs reality, the safety boundary and the scans |
| `REGRESSION.md`, `logs/ci-local.log`, `logs/smoke.log`, `findings/chain.json` | chain | ci-local and smoke at the sha |
| `drives/<group>.md`, `../surface/<group>/final/`, `findings/drive-<group>.json` | drives | Re-drives compared with the census |
| `battery/shard-<k>.ids`, `shard-<k>.md`, `raw/<id>.txt`, `findings/battery-<k>.json` | battery | Every fixed entry's original repro at the sha, with COVERAGE lines |
| `DOCS_VS_REALITY.md`, `findings/docs.json` | docs | The grep set (a)-(g) |
| `TRIAGE.md`, `TRIAGE.json` (`REGISTER_ADDITIONS.json` if the register had moved) | triage | Admitted, refuted and duplicate findings, with rationale |
| `fix-r<N>/PLAN.md`, `INTEGRATION.md`, `ci-local.log`, `smoke.log`, `VERDICTS.json`, `VERDICTS.md` | round N | How each entry was fixed and certified, or adjudicated |
| `reproof/ci-local.log`, `smoke.log`, `safety-surface.diff` (`REGISTER_FINAL_STATUS.json` if needed) | re-proof | The final head's chain and boundary |
| `../../R15_FINAL_PASS.md` | re-proof (+ stage 6) | The gate sheet: PASS/FAIL per item with evidence paths, the certified sha, and the run-ending lines |
| `run-ending/*.log`, `stack-before.txt`, `stack-after.txt` | stage 6 | The graph refresh, the stack stop and relaunch, and the caffeinate release |

## Run-ending steps (stage 6): the exact commands

The run-ending agent runs these commands. The lead can run the same ones by hand if the agent dies.

```bash
REPO=/Users/lokavyasingh/Documents/dev/vysted-terminal
EVR=$REPO/docs/redesign/verification/r15/final-pass/run-ending; mkdir -p $EVR
export PATH=$HOME/.nvm/versions/node/v24.15.0/bin:$HOME/.cargo/bin:$PATH
git -C $REPO rev-parse HEAD origin/004-r4-experience-rebuild     # both must equal the certified sha

# 1. Graph index: graphify-out/ at the repo root (git-ignored; graph.json, GRAPH_REPORT.md, manifest.json),
#    built by the graphify CLI (pipx venv) and refreshed code-only by the post-commit hook. Never --force.
cd $REPO && nohup $HOME/.local/bin/graphify update . > $EVR/graphify-update.log 2>&1 &

# 2. His dev stack: find it by evidence, stop only those pids, relaunch on fresh binaries from the certified sha.
lsof -nP -iTCP:5173 -sTCP:LISTEN                      # vite
ps -axo pid,ppid,command | grep -E 'tauri dev|vysted-terminal|vysted-sidecar|openbb-mcp|sec-edgar-mcp' | grep -v grep
lsof -a -d cwd -p <pid>                                # each candidate's cwd must be $REPO or under it
kill -TERM <app pid>; kill -TERM <tauri dev pid>; kill -TERM <vite pid if still up>   # verified pids only
cd $REPO && nohup node scripts/ensure-all-sidecars.mjs --force > $EVR/ensure.log 2>&1 &
cd $REPO && nohup pnpm tauri:dev > $EVR/tauri-dev.log 2>&1 &

# 3. Clean default workspace + composer on the OpenAI lane, through the app's own controls
cp "$HOME/Library/Application Support/com.vysted.terminal/workspaces/__autosave__.vysted-workspace" <scratch>/final-run-ending/autosave-before.vysted-workspace   # read-only backup, before step 2's stop
#    then, via the dev-tools bridge (.mcp.json 'tauri-mcp': node node_modules/tauri-plugin-mcp/packages/tauri-mcp/dist/index.js):
#    Settings -> "Reset layout to default" (resetToDefaultLayout) and Settings -> make OpenAI the default provider;
#    read back from the status chrome. Otherwise it is one click each for the operator, recorded as not_done.

# 4. Caffeinate: only the pids the run armed.
ps -o pid,ppid,lstart,command -p <pid>                 # must be caffeinate
kill <pid>
```

What I found for the graph index: `graphify-out/` exists at the repo root and is git-ignored (`.gitignore:46`). The CLI is `$HOME/.local/bin/graphify`, a pipx venv whose interpreter is recorded in `graphify-out/.graphify_python`. `.git/hooks/post-commit` rebuilds code-only in the background after each commit (log `~/.cache/graphify-rebuild.log`). `graphify update <path>` re-extracts code without an LLM, and refuses to overwrite a graph with fewer nodes unless `--force`, which the stage never passes.

## What the lead does by hand afterwards

1. Read `docs/redesign/verification/R15_FINAL_PASS.md`. A FAIL ends the run here without a launch tag: the brief allows no second pass. Report the FAIL and its reasons to the operator honestly.
2. On a PASS where fixes landed, audit `origin/worktree-agent-final-int` (the review-before-merge rule) and fast-forward 004 to the certified sha. On a PASS with no fixes, the certified sha is the rc3 sha.
3. Commit the evidence and the register edits (`r15/final-pass/**`, `R15_FINAL_PASS.md`, the register `.json` and `.md`, and `DECISIONS_FOR_OPERATOR.md` if the planner deferred anything) as one docs commit, with explicit paths. Never commit CLAUDE.md or the spend ledger. Push 004.
4. Resume the workflow with `run_ending: true` (see Launch). Read its lines in the sheet, and do by hand any step it marks not_done, using the commands above.
5. **Tags are only ever made by the lead.** Tag `r15-launch` on the newest rc and push the tag. If the pass landed fixes, the certified sha is newer than `r15-rc3`. Whether it first becomes the next rc (for example `r15-rc4`), and whether `r15-launch` goes on it or on the evidence commit above it, is the lead's call. The rule: tag the evidence commit only if `git diff --stat <certified>..<evidence commit>` touches `docs/` alone.
6. Hygiene: prune `final-cand` and `final-int`, and the `worktree-agent-final-*` branches merged into 004 (local only; nothing on the remote). Rewrite the run-state header and the handover.

## Assumptions and decisions

- **The adversaries see the product through the built artifact.** They run the bundle's own sidecar binaries plus the static `out/`, served headless. Launching the `.app` would be a GUI act, and the operator may be present.
- **Resolving "read-only data" against "clean default workspace".** The brief asks for both his read-only data and a relaunch on a clean default workspace. Stage 6 never writes his workspace blob or settings itself. It backs the blob up read-only to scratch, then uses the app's own "Reset layout to default" and provider controls, which is what his own click would do. Where the bridge cannot reach those controls, the step is left to him as one click and recorded as not_done.
- **The safety-surface bar.** D81 removed most of the R13 safety surface, so a byte-identical surface is not expected. The bar the pass applies is "every differing file listed for the operator with the reason". The table lives in the sheet and the full diff in `reproof/safety-surface.diff`.
- **Where evidence and register edits live.** Evidence and register edits stay uncommitted in the main checkout, and only writers and the integrator commit, on their own branches. Nothing in the workflow tags, merges to main, pushes 004 or main, opens a PR or force-pushes.
- **Ports.** :52800-52802 (shared stack), :52810-52822 (adversaries), :52840+i (drives), :52860+k (battery), :52880 (triage), :52882+N (planner), :52886+N (verifier), :52895 (re-proof), and web :5281/:5282. None overlap the rc1 or lows ranges (:52152-54, :52310-52350, :52600+).
- **How the script was checked.** Plain `node --check` rejects every workflow script in this folder because the harness allows a top-level `return`. So the check used the same approach as before: the body wrapped in an async function, passed through `node --check`, plus a stubbed harness run (`scratchpad/tail-authoring/stub-final-pass.mjs`). The stub spawns nothing and covers:
  - 14 bad-arg refusals and `dry_run`;
  - preflight dead or blocked;
  - two-round and three-round bounded loops, and `max_fix_rounds` 0;
  - dead adversary, drive, battery, triage, planner, writers, verifier, re-proof and run-ending agents, and a failed integration;
  - adjudication closing entries, no findings, and one adversary;
  - the resume prefix being byte-identical with `run_ending` on;
  - at most 2 strongest-tier agents and at most 6 agents at once.
