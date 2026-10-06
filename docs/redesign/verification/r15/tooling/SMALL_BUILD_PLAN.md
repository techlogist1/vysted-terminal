# R15 small build: workflow plan

Script: `docs/redesign/verification/r15/tooling/small-build.js`. The brief allows one small build between rc2 and rc3, and no more than one. The Stage E panel chose **BL-03 "Reasons about you", the position half**: `r15/invent/PANEL.md` section 5 and the `top` entry of `PANEL.json`. That sketch is the whole spec. It gives the files and lines (verified at `913235f3`, and unchanged at `e1fd10f1`), the acceptance test, the demo, the merge gates and the explicit out-of-scope list. The script builds the row on its own branches, using the Stage C writer, integrator, reviewer and verifier roles. It adds an owner-drive demo and refreshes the release docs. It returns the int branch head as the **rc3 candidate**. It never merges into 004, never runs the rc3 gate and never tags. The lead does all three by hand.

## Launch

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/small-build.js", args: {"sha": "r15-rc2", "tag": "small-build", "row": "BL-03", "sketch_section": "5"}})
```

The same args are in `launch-args/small-build.json`. Launch once `r15-rc2` is tagged and pushed. Launch only when no other workflow holds the heavy lane (the integrator) or the local model (the verifier). The lows write runs and the rc gate both use those lanes.

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `sha` | required unless `dry_run` | The rc2 head: a hex sha, or the tag name `r15-rc2`. The plan checker resolves it to a 40-hex `base_sha`, and every branch is cut from that. |
| `tag` | `small-build` | Sets the branch names (`worktree-agent-<tag>-W<k>`, `worktree-agent-<tag>-int`), the evidence root `r15/<tag>/`, the scratch int worktree `<scratch>/<tag>-int` and every agent label. |
| `row` | `BL-03` | The backlog row to build. A fallback row must bring its own `tag`, or the script throws. |
| `sketch_section` | `5` | The `PANEL.md` section that holds the sketch. Section 6 holds both fallbacks. |
| `dry_run` | `false` | Logs the six agent roles with their model, effort, branch and ports, returns `{status: 'dry_run', would_spawn}`, and spawns nothing. |
| `salvage` | none | `{"<agent label>": "<note>"}`. On a resume, the note is appended as `RESUME SALVAGE` to that one agent's prompt. The default of no note keeps every prompt byte-identical, so a resume replays from the cache. |
| `scratch` | this session's scratchpad | The scratch root, used if the session's scratchpad is gone. |

Any other key throws, which catches typos such as `sketch`. So do a bad `tag`, `row` or `sketch_section`, a missing or non-sha `sha`, and a `salvage` that is not an object.

**Fallback rows.** When the plan check stops on BL-03, the lead decides whether to fall back. Section 6 names BL-18 first, then BL-11. For BL-18: `{"sha": "r15-rc2", "tag": "small-build-bl18", "row": "BL-18", "sketch_section": "6"}`. For a fallback row, the reviewer, the verifier and the docs agent get prompts driven by the sketch rather than BL-03's written-out checks. The stub harness asserts that no BL-03 detail leaks into them.

## Stages and agents

Routing follows the brief. Sonnet always runs at effort `high`, and Opus runs at its default effort, so its calls pass no effort key. Fable is not used, and neither is Haiku or a fast tier. The `call()` wrapper throws on any other combination. Each agent that dies (returns null or throws) gets **one same-tier retry** with the label `<label>-retry`, and never a third try.

| # | Phase | Label | Model / effort | Why this tier | What it does |
| - | ----- | ----- | -------------- | ------------- | ------------ |
| 1 | Plan check | `<tag>-plan` | Opus / default | Refutation of the sketch plus the boundary judgement | Resolves `base_sha` and re-verifies every path, symbol and line the sketch cites at that sha (the `drift` table). Runs the **boundary check**. Splits the work into at most 3 writer sets that share no file, with tests going to the set that owns the code they pin. Writes `PLAN.md` and `PLAN.json`. It returns **status `stop`**, with a stated reason, if the build would touch the trading surface or write to the portfolio, need a Tier-4 or §6.5 file, change the catalog, TOOL_SCHEMAS, the allow-list, the MCP surface or a roster count, add a dependency, or change a wire contract. |
| 2 | Write | `<tag>-write-W<k>` (≤3, in parallel, `isolation: 'worktree'`) | Opus / default for the set that owns `sidecar/services/agent_runtime.py`; Sonnet / high for the frontend set | The preamble sits in the agent runtime, which is risk-adjacent. The selector, `brief-blocks` and the call sites have a clear spec and a checkable output. | Branch `worktree-agent-<tag>-W<k>`, cut from `base_sha`. On a restart it continues from its own origin branch. **Pinning tests first**: it commits them failing for the right reason, then builds the change. It runs the sketch's gate commands for its files only, lints, and commits and pushes after every deliverable, appending a line to `writers/W<k>.jsonl` each time. It never touches the full chain, a sidecar, the GUI, `:523xx` or `pnpm install`. It symlinks `node_modules` and `.venv` read-only. |
| 3 | Integrate | `<tag>-integrate` | Opus / default | Integration | Works in `<scratch>/<tag>-int` on `worktree-agent-<tag>-int`. Merges the writer branches in the plan's order and runs `pnpm ci-local` detached, which includes ensure-all-sidecars. The main sidecar rebuilds because its source changed. It checks that the sketch's gates are inside those counts, then runs `smoke-test-sidecars.mjs`. A wrong writer commit is reverted, never patched around. It pushes and leaves the worktree in place. |
| 4 | Review | `<tag>-review` | Opus / default | Review | A read-only diff review of `base_sha...origin/<int>` against PLAN.md, the out-of-scope list item by item, and the boundary list. It checks that each writer stayed inside its set's files. For BL-03 it also checks that the position line is exact-symbol and case-insensitive, sits before the deixis sentence, never shows 0 for an unmarked value, and caps the Held list at 12. It checks that `deriveMetrics` with no second argument returns today's output and that the selector reads the active portfolio. It checks for weakened tests, and runs the banned-word grep over the diff. Trivial fixes are pushed to the int branch, and the gates are re-run after a fix. Any boundary hit, or a substantively wrong change, returns **block**. There is **one** integrate→review round. |
| 5 | Demo + verify | `<tag>-verify` | Opus / default | Fresh-context certification | Fast-forwards the int worktree to the reviewed head. It reads neither INTEGRATION.md nor REVIEW.md before forming its own verdict. It boots its own three sidecars on **:52370 / :52371 / :52372** with a copy of the ISO data dir (see Ports). Then it runs five checks, listed below the table. It writes `VERDICT.json` and `VERDICT.md`. **The verdict is final.** |
| 6 | Release docs | `<tag>-docs` | Sonnet / high | Clear spec, checkable output | Runs only on an `approve`. It picks each target at HEAD: the Stage D draft (`r15/stage-d/<NAME>.draft.md`) while it exists, or the promoted file if the draft was promoted. `CHANGELOG.md` at the root is always a target. It describes only the certified behaviour and adds one line to OPERATOR_BRIEFING. It makes **one commit** on the int branch and pushes it. It runs the banned-word grep over the lines it added, which must return 0. Hits that were already there are reported, not edited. It writes `DOCS.md`. |

The verifier's five checks, in order:

1. **Acceptance test.** It runs the sketch's acceptance test and pins itself. Then it tries fresh cases the tests were not written against: a lowercase focused symbol, pnl null, a 13-holding book, and `holdingFor` on a symbol held only in a non-active portfolio (through a temporary test copy, deleted afterwards).
2. **Owner-drive demo.** It is keyless and uses `llama3.1:8b` under the shared local-model lock. It sets up the book TANLA 500 @ 812 and KAYNES 100 @ 4070, but only in its own data copy and only through the app's own routes. It builds the terminal snapshot the Portfolio panel publishes, with marks taken from the sidecar's own quotes (`demo/context-TANLA.json`). It then runs three fresh `vy.py invoke copilot "should I add to TANLA?" --context …` chats and saves them as `demo/chat-<n>.txt`. For each run it records whether the position was quoted before the reasoning, and whether a `get_portfolio` step appeared.
3. **Captures.** A populated TANLA brief showing the 'Your position' card, dark theme, at 1920x1080 and 2560x1440, saved to `docs/screenshots/vr15-rc3/` without overwriting anything. The GUI Quartz path is used only if HIDIdleTime is at least 1500 s, the built app is already granted, and HOME is isolated. Otherwise it captures with headless Chromium through Playwright against vite on :5191 (never the operator's :5173), with the Tauri port invoke stubbed.
4. **Register finding.** WLD-agent-native-ux-1: whether this build closes it.
5. **Out of scope.** The roster count, the MCP tool list and the catalog ids must equal the base. There must be no new portfolio write route.

Verify approves when the acceptance test and the fresh cases hold, at least one demo run quotes the position from the preamble with no `get_portfolio` step, and nothing is out of scope. The demo counts are reported as they fell. A model weakness is recorded as such, and is never counted as a product defect while the preamble line is provably present.

Peak concurrency is 3 (the writers). The total is 7 agents, or at most 13 with retries.

## Script-side guards (no agent needed)

After the plan check, the script itself stops (`stopped_at_plan`) if the checker died twice, returned `stop`, left `base_sha` as something other than 40-hex, returned 0 or more than 3 sets, returned duplicate set names, or put a file in more than one set. It also stops if any set owns a file matching the `FORBIDDEN` pattern: Tier-4 files, the §6.5 safety files, `catalog.py`, `schemas.py`, `custom_agent.py`, `sidecar/agents/`, `sidecar/models/`, `types/data.ts`, or any dependency manifest or lockfile. A set that owns `agent_runtime.py` is always routed to Opus, even when the plan said Sonnet. When every writer dies twice, the run returns `writers_failed`. A single dead set goes to the integrator marked `died_twice`, and the integrator merges only what that set pushed. If the set is incomplete, the chain fails and the run returns `integration_failed`.

## Ports

The verifier owns **:52370** (main sidecar), **:52371** (openbb-mcp) and **:52372** (sec-edgar-mcp). This range is clear of every other R15 lane that can run in the same window:

- the three lows-waves verifiers: :52320, :52330 and :52340, each +2
- the rc1/rc3 gate: :52310-13, :52320-47 and :52600+
- the lows triage: :52350
- the shared ISO stack: :52152-54

A port that is already bound is inspected by its command line. Only a sidecar that an earlier attempt of this same role started from the int worktree is stopped. Anything else goes into `blocking`.

## Evidence (under `docs/redesign/verification/r15/<tag>/`)

| File | Written by | Holds |
| ---- | ---------- | ----- |
| `PLAN.md`, `PLAN.json` | plan checker | base sha, drift table, boundary flags, writer sets (files → change → pinning test → gate), merge order, acceptance test, demo, out-of-scope list |
| `writers/W<k>.jsonl` | each writer | `{what, commit, test}` per pushed deliverable |
| `INTEGRATION.md` | integrator | branches merged, conflicts, chain stages with counts, smoke, reverts |
| `REVIEW.md` | reviewer | hunk review, out-of-scope and boundary hits, fixes, gates after a fix |
| `demo/context-TANLA.json`, `demo/chat-<n>.txt` | verifier | the snapshot the chats ran with, and each full event stream and reply |
| `VERDICT.json`, `VERDICT.md` | verifier | `{row, tag, int_head, acceptance, demo, captures, register_finding, out_of_scope_ok, verdict, blocking}` plus evidence excerpts |
| `DOCS.md` | docs agent | files touched, draft or promoted target per file, grep result |
| `docs/screenshots/vr15-rc3/*` | verifier | the populated brief captures, labelled by lane (quartz or headless) |

The script commits none of the evidence. Agents commit only code, tests and the docs commit, all on their own branches. The lead commits `r15/<tag>/` to 004 together with the merge.

## Returns

`{status, row, tag, sha_arg, base_sha, rc3_candidate: {branch, sha}, plan, writers, integ, review, verify, docs, lead_next}`. The status is one of the following:

| Status | Meaning |
| ------ | ------- |
| `dry_run` | The dry run finished. Nothing was spawned. |
| `stopped_at_plan` | Stopped at the plan check. The return carries the `reason` and a `fallback` pointer. |
| `writers_failed` | Every writer died twice. |
| `integration_failed` | The integrator died, the chain failed, or the int branch was not pushed. |
| `unreviewed` | The reviewer died twice. |
| `review_blocked` | The reviewer blocked the diff. |
| `unverified` | The verifier died twice. |
| `verifier_blocked` | The verifier blocked. |
| `candidate_ready` | Verified, and the release docs are refreshed. |
| `candidate_ready_docs_pending` | Verified, but the docs agent died, did not push, or added a banned-word hit. The candidate is then the verified head without the doc refresh. |

## After the workflow (the lead, by hand)

1. Read `VERDICT.md` and `REVIEW.md`. On a stop or block, choose: fall back to BL-18 (then BL-11) with its own tag, or record that there is no small build this release. There is never a second attempt at the same row inside the run.
2. Audit `origin/worktree-agent-<tag>-int` at `rc3_candidate.sha`. Grep the diff for the boundary files and the banned words. Merge it into 004 by hand, and commit `r15/<tag>/` along with it.
3. Run the existing **`rc1-gate.js` at the merge sha as the rc3 gate**, with the same script and the rc3 sha. It re-runs the regression suite and re-proves Gate 8, as the brief requires. This workflow deliberately does not duplicate that gate.
4. On a PASS sheet only, the lead tags `r15-rc3` at the gated sha with their own hands. No agent ever tags.
5. Register: record what the verifier said about WLD-agent-native-ux-1. At authoring time, that id was a `raw_id` of **R15-AGENT-020** (high, `fixed`, the notes half, fixed by an earlier batch). This build adds the position half. Append a note to the entry, and flip nothing that is not certified.
6. Hygiene: remove `<scratch>/<tag>-int` and `<scratch>/<tag>-verify-data`, and check that :52370-72 are free.

## Verification of this script (authoring, 25 Sep)

- `node --check` on the wrapped body is clean. Like every R15 workflow script, it uses a top-level `return`, which only the harness's async wrapper accepts, so a bare `node --check` rejects it the same way it rejects `lows-waves.js`.
- A stub harness at `<scratch>/tail-authoring/stub-small-build.mjs` imports the body with recording stubs for `agent`, `parallel`, `phase` and `log`. It asserts every call's model and effort rule, and it asserts that every prompt carries the stall rule, the forbidden-reads rule, the git rules and the banned-word grep, with no banned literal in any prompt. It ran 35 scenarios, all passing: 8 bad-arg refusals, a dry run with 0 spawns, every plan-stop branch (died twice, threw twice, `stop`, unresolved sha, file clash, catalog owner, `types/data.ts` owner, 4 sets), the happy path (7 agents), a mislabelled runtime owner rerouted to Opus, writer death (once, then retried; twice for one set; twice for all), integrator death and an unpushed branch, reviewer death and a block, verifier death and a block, docs death and a banned hit, a fallback row, a salvage note, BL-03 prompt content, and fallback prompts free of BL-03 detail.
- There is one raw `agent()` site, inside `call()`, and six `run()` sites. Every one names its model. Sonnet sites pass `effort: 'high'`, and Opus sites pass no effort.
- Not validated: a real run. The boot on :52370, the headless capture path, and the Playwright availability in the int worktree are all untested.
