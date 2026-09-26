# R15 final pass: workflow plan

Script: `docs/redesign/verification/r15/tooling/final-pass.js`. It is the one final adversarial pass allowed after `r15-rc3`: one workflow, its findings closed under gate 3 inside that workflow, and no second pass. It ends with the run-ending steps, which run only when `run_ending` is true.

The scenarios and the verifier rubric were re-authored against head `6bc6d378cbbf9cfbefd8d155e027c2dc80214331` (26 Sep 2026). Every scenario names the file or route it targets at that head; preflight records whether that head is an ancestor of the sha under test, and an adversary that finds a target moved says where it went.

## Launch

The file `launch-args/final-pass.json` holds the first launch's args. Before launching, replace `RC3_SHA` with `git rev-parse r15-rc3^{commit}`.

```
Workflow({scriptPath: "/Users/lokavyasingh/Documents/dev/vysted-terminal/docs/redesign/verification/r15/tooling/final-pass.js", args: {sha: "<r15-rc3 sha>", max_fix_rounds: 2, adversaries: 2, run_ending: false, slice: ["data-smallcaps", "research-search", "agent-chat", "ui-panels", "lifecycle-safety"]}})
```

To check that the harness loads the script without spawning anything, add `dry_run: true`. That call validates the args, logs every agent it would spawn (label, model, effort, port, and each adversary's scenario ids) and returns `{dry_run: true, sha, max_fix_rounds, adversaries, run_ending, slice, scenarios, would_spawn}`.

The run-ending steps run on the **same** workflow, resumed. After reading the sheet (see the lead's steps below), relaunch with `resumeFromRunId: "<the first run's id>"`, the same args and `run_ending: true`, plus `caffeinate_pids: [...]` if you want to name the pids yourself. No prompt in stages 1-5 reads `run_ending` or `caffeinate_pids` (the run-ending rule the rubric quotes is a constant), so every earlier agent replays from the cache and only stage 6 runs live.

| Arg | Default | Meaning |
| --- | ------- | ------- |
| `sha` | required | The `r15-rc3` commit, 7-40 lowercase hex. Preflight blocks if the `r15-rc3` tag points elsewhere. |
| `max_fix_rounds` | 2 | Gate-3 fix rounds, 0..3. With 0, admitted entries go to the re-proof unfixed. |
| `adversaries` | 2 | Strongest-tier adversaries, 1..2. With 2, `investor` and `maintainer` split the catalogue by lens; with 1, `solo` runs the whole selected catalogue under both lenses. 3 or more is refused. |
| `run_ending` | false | Stage 6. It must be the boolean `true` (or `"true"`), and stage 6 still runs only after a PASS. |
| `drive_groups` | the 8 census groups | The owner-drive groups from `PROMPT_surface_s2.md`: 1..8 names. |
| `batt_shards` | 4 | Battery shards, 1..8. Ids are dealt by sorted position mod N. |
| `max_writers` | 4 | Writer sets per round, 1..6. Sets beyond the cap are logged and stay open. |
| `bundle_path` | none | An absolute path to a production bundle already built at the sha. Preflight accepts it only if the evidence behind it names the sha. |
| `caffeinate_pids` | none | Stage 6 only. Without it, the agent reads the armed pids from the run-state header. |
| `scratch` | this session's scratchpad | The scratch root. |
| `dry_run` | false | Spawn nothing (see above). |
| `slice` | all five | A non-empty list of distinct scenario slices: `data-smallcaps`, `research-search`, `agent-chat`, `ui-panels`, `lifecycle-safety`. It selects which scenarios the adversaries run; every other lane runs regardless. A sliced launch cannot pass: the sheet's "sweep complete" item is FAIL by definition. This arg was added by the re-authoring; the 25 Sep script had no `slice`. |

Unknown keys are refused, so a typo like `slise` throws instead of being ignored.

## Stages and agents

`call()` enforces routing change 5 in code: every call names its model and sets `effort: 'high'` explicitly (a call without it throws), the strongest tier may run only in the Sweep phase, and a limiter holds it to two agents at once, retries included. A call that dies gets one same-tier retry (label `-retry`), never a third try.

| # | Phase | Agents (model, effort) | What it does |
| - | ----- | ---------------------- | ------------ |
| 1 | Preflight | `final-preflight`: Opus, high | Resolves the sha, checks the `r15-rc3` tag, records whether the authoring head is an ancestor and what `r13-bedrock` resolves to. Creates `final-cand`, installs clean, accepts or builds the production bundle there (`VYSTED_SKIP_DEV_SIGN=1 pnpm tauri build`), seeds the keyless data dir, boots the shared stack :52800-52802 from the built binaries, records Ollama and disk, snapshots the register. Blocked or dead: the script returns `blocked` and spawns nothing else. |
| 2 | Sweep | `final-adv-investor` + `final-adv-maintainer` (or `final-adv-solo`): strongest tier, high. Beside them, Opus/high: `final-chain`, `final-docs`, 8 × `final-drive-<group>`, 4 × `final-battery-<k>`, at most 4 at once | The adversaries run the scenario catalogue below from a stranger's clean profile on their own stack (investor :52810-52812 and :52815 for writes; maintainer :52820-52822 and :52825), then free attacks. Chain: `pnpm ci-local` and the smoke test in `final-cand`. Drives: the rc1 owner-drive method, writes to :52840+i. Battery: every `fixed` id at the sha, raw output per id, on :52860+k. Docs: the grep set (a)-(i). A barrier: triage dedupes across all lanes. |
| 3 | Triage | `final-triage`: Opus, high | Applies the rubric in the order R4, R5, R3, then R1 and R2, re-running repros on :52880. Admitted items become `R15-FINAL-NNN` entries with the register's own fields; each carries `prior_failures` for R7. |
| 4 | Close (≤ `max_fix_rounds`) | Per round: `final-fix-r<N>-plan` (Opus/high), up to 4 writers (Sonnet/high by default, Opus/high for root-cause or risk-adjacent sets, worktree isolation), `final-fix-r<N>-int` (Opus/high), `final-fix-r<N>-verify` (Opus/high, fresh) | Gate 3 by R6. Tier-1 fixes are deferred with a DECISIONS draft. Each `not_certified` adds one to the entry's count; at the third the entry stops (R7) and leaves the rounds. The loop also stops early if the planner, every writer, the integration or the verifier dies. |
| 5 | Re-proof | `final-reproof`: Opus, high, fresh | At the final head on :52895: the regression suite, the Gate 8 re-proof (G8-1 to G8-5 run again, independently), the tracked-portfolio round trip, the sidecar-level first run, the scenario catalogue's verdicts, gate 3 and R7, R4 and R5, the four areas; writes `R15_FINAL_PASS.md` and stops the shared stack. |
| 6 | Run-ending | `final-run-ending`: Opus, high | R9, below. |

Peak concurrency is 6: 2 adversaries plus 4 Opus lanes in the Sweep. The total is 17 (preflight + 16 in the Sweep) + 1 triage + 7 per round + 1 re-proof (+1 run-ending), plus retries.

## The scenario catalogue (33 scenarios, five slices)

Each adversary writes `final-pass/scenarios/<id>.md` as it goes, ending with one line `VERDICT <id>: pass | finding <keys> | needs_gui | known_limitation <keys> | blocked_env <probe> | lock_timeout`. The re-proof fails the catalogue item for any id without a verdict line. Lens I = investor, M = maintainer.

| Id | Slice | Lens | Targets | Attacks | Register |
| -- | ----- | ---- | ------- | ------- | -------- |
| DS-1 | data-smallcaps | I | `/fundamentals/{s}/income`, `/balance`, `/cashflow`, `/quotes`, `X-Vysted-Region` (`_RegionMiddleware`), `/resolve` | US/India collisions DAL, CHTR, SAFE, CSL, ICON, AMAL, SMR, TTC, bare under both regions and qualified | DATA-001/002/003, CODE-DATA-001 |
| DS-2 | data-smallcaps | I | `/quotes`, `/fundamentals`, `/history`, every `/disclosures/*` route | Three fresh names not in `battery/manifest.json` (an SME/Emerge listing, a thin BSE-only scrip, a 2026 listing), every field against screener.in and BSE | DATA-005/006/013-017/019/021-023/025 |
| DS-3 | data-smallcaps | I | `/fundamentals/SIFY`, `/fundamentals/WIT`, `/earnings/{s}/estimates`, `brief-blocks.tsx` `deriveMetrics` | Currency and unit labels, the SIFY ADR ratio (1 ADS = 6 shares), fraction vs percent, raw-rupee market cap | DATA-008, DATA-113, AGENT-090, AGENT-001 |
| DS-4 | data-smallcaps | I | `/resolve`, `/resolve/autocomplete` | zomato, SEQUENT, a reused BSE ticker | DATA-012, DATA-018 |
| DS-5 | data-smallcaps | I | `POST /screener/run`, `/screener/universe` | Cross-currency ranking, nulls last, header count vs page cap | DATA-043/044/112, UI-006 |
| DS-6 | data-smallcaps | I | `/history`, `/quotes`, `/earnings/{s}/history`, `/news?symbol=`, `/fundamentals/{s}/ratings` | ^NSEI, BHP.AX, 0700.HK, 7203.T, VOD.L, .NS/.BO forms | LEAD-011, LEAD-022, DATA-029/030 |
| DS-7 | data-smallcaps | I | ownership fields, `/disclosures/shareholding`, the brief's ownership label | Vendor estimate shown as the filing; a BSE 403 counts as environment only with its direct probe | DATA-004, RESEARCH-011 |
| RS-1 | research-search | I | catalog `research` (depth normal/quick, deep, heavy/ultra via `research/depth.py`), `options.research_depth`, `_auto_publish_event` | The two-tier path on a DS-2 name, normal then deep, on llama3.1:8b and the OpenAI lane; structured metrics against DS-2 truth | research entries |
| RS-2 | research-search | I | the deep news leg, `BriefBody` | News bleed on a common-word or shared name; ticker chips | RESEARCH-001, DATA-030 |
| RS-3 | research-search | I | `/search/status`, `/search/searxng/status`, `web_search` | Search-tier honesty with SearXNG down; the OpenAI lane's web search does not 400 | search-tier entries |
| RS-4 | research-search | I | fast research on an uncached Indian name | Attached to DECISIONS 4.1 either way | DECISIONS 4.1, AGENT-049 |
| AC-1 | agent-chat | I | `POST /agents/{id}/invoke` via `vy.py` on every configured lane (ollama, an OpenRouter `:free` slug, OpenAI under the guard, DeepSeek once expecting an honest error, `--no-key`, `--bad-key`) | Compare, explain, "should I buy", conflicting data, follow-up | LEAD-030/037 (class), AGENT-017 |
| AC-2 | agent-chat | M | `AUTO_APPLIED_KINDS`, `proposed-changes.ts` enqueue/accept, `POST /agents/actions/ack`, `_grounded_host_action_result` | A data-write stages under ask and auto; a watchlist change applies under auto only | CODE-FRONTEND-013/008 are stated gaps |
| AC-3 | agent-chat | M | `planner.classify_intent`, the read-intent strip, `_NO_TOOL_CUE`, `test_toolbelt_integrity.py` | Pure read, no-tool instruction, no-tool plus a write | LEAD-035/038 (class) |
| AC-4 | agent-chat | M | `POST /agents/{id}/runs`, `/runs/{id}/cancel`, `/resume`, `BudgetGuard` | Tiny ceiling, cancel, resume; halted host actions never enqueue | AGENT-092 |
| AC-5 | agent-chat | M | `/mcp/status`, the `/mcp` mount, `_OriginGuardMiddleware` | Tool count and dict returns; foreign and `null` Origin get 403 | CODE-AGENT-001 (needs_gui half) |
| AC-6 | agent-chat | M | `/custom-agents`, `custom_agent.KNOWN_TOOL_IDS` | Unknown, forbidden (`place_order`) and all-writes grants | `FORBIDDEN_TOOL_SUBSTRINGS` |
| UI-1 | ui-panels | M | `workspace.ts` `deserializeWorkspace`, `/workspace` | Loading a named layout never rolls back state | CODE-FRONTEND-001 |
| UI-2 | ui-panels | M | `src/modules/portfolio`, `csv.ts` `downloadCsv` | Tracked portfolio in two currencies, no-quote holding, P&L recomputed, CSV rows | UI-005, DATA-042; UI-009 is needs_gui |
| UI-3 | ui-panels | M | watchlist, equity overview | Freshness by exchange calendar | UI-090 |
| UI-4 | ui-panels | M | `src/modules/screener` | DS-5 through the panel | UI-006, DATA-112 |
| UI-5 | ui-panels | M | `layout-templates.ts` `fitLayoutTemplate`, `PanelHost.tsx` | 1920×1080, 1280×800, 1024×768; clipping needs the proven browser seam, else needs_gui | UI-084 |
| UI-6 | ui-panels | M | `ProposedChangesReview.tsx`, `describeIntent`, `applyIntent` | Old/new per row, reject, unknown action cannot apply | none |
| UI-7 | ui-panels | M | `onboarding.ts`, `provider-keys.ts`, `llm-providers.ts` | Browser-mode first run on a keyless clean profile | onboarding-stranger |
| LS-1 | lifecycle-safety | M | the bundle's own sidecar binaries on an empty data dir; `/health`, `/agents`, `/mcp/status`, `/system/ollama/status`, `/system/local-model-recommendation`, `/llm/providers` | First run from a clean profile, timed against REHEARSAL.md; the GUI half is needs_gui | UI-044, LIFECYCLE-001 |
| LS-2 | lifecycle-safety | M | stdin-EOF shutdown, the MCP children | Reboot on same data, corrupt copies, orphans, taken port | lifecycle entries |
| LS-3 | lifecycle-safety | M | every write route in `/openapi.json`, `services/llm/` | Closed provider port, garbage upstream, malformed bodies, kill mid-request, kill openbb-mcp mid-research | LIFECYCLE-005 |
| LS-4 | lifecycle-safety | M | `history_secrets_scan.py`, `licence_scan.py`, the tree and bundle binaries | Secrets, licences (DECISIONS 5.1-5.3 are not new), banned word and phrase | DECISIONS 5.x |
| G8-1 | lifecycle-safety | M | `/openapi.json`, catalog, `TOOL_SCHEMAS`, `KNOWN_TOOL_IDS`, the live MCP list, `test_no_trading_surface.py` | rc1 GATE8.md (a)-(d): no trading path | D81 |
| G8-2 | lifecycle-safety | M | `POST /agents/{id}/invoke` under ask and auto; `POST /orders`, `POST /brokers/kite/orders`, `POST /safety/kill-switch` | An order attempt halts for human review; order-shaped paths are 404/405 | D81 |
| G8-3 | lifecycle-safety | M | `proposed-changes.ts` enqueue/accept; `host-actions.ts` `parseHostAction` (unknown branch), `describeIntent`, `applyIntent` (jsdom harness) | `place_order`/`submit_order` enqueued under ask and auto, then a human accept: it fails closed (returns `failed`, re-pends, store, blob and `/portfolio/positions` unchanged, ack `failed`) | none |
| G8-4 | lifecycle-safety | M | `audit_orders` | `git grep` at the sha; `.tables` and row counts over the pass's own data dirs before and after G8-2/G8-3: zero rows; never the operator's leftover db | D81 |
| G8-5 | lifecycle-safety | M | the order-safety surface vs `r13-bedrock` | The safety diff below | D81 |

### Frontend access under the origin guard

`sidecar/app.py` `_OriginGuardMiddleware` answers 403 to any request whose Origin is not `tauri://localhost`, `http(s)://tauri.localhost`, `http://localhost:5173` or `http://127.0.0.1:5173`. A headless page served on :5281/:5282 is therefore refused, and ISOLATION_MAP.md section 1b predates the guard. The repo has no playwright. The panel scenarios run through the scratch jsdom harness of rc1 GATE8.md section (e), with its jsdom url set to `http://localhost:5173` and proven with one GET first. Rendering checks (widths, clipping) need headless Chrome over the DevTools protocol with the Fetch domain rewriting Origin, proven by a 403-then-200 pair; unproven, they are needs_gui.

### First run from a clean profile

The pass proves first run at sidecar level (LS-1 and re-proof step 4): the bundle's own binaries on an empty data dir holding only `{"secrets": {}, "migrated": true}`. The GUI first run is not run: a `HOME=` launch leaks WKWebView files into the real `~/Library` (DECISIONS 5.9) and cannot show the terms dialog (REHEARSAL.md, R15-UI-044). It is a needs_gui item for the operator on a separate macOS user account.

### The safety-surface diff (G8-5, and again in the re-proof)

The surface is `sidecar/models/audit_log.py`, `sidecar/services/kill_switch.py`, `src-tauri/src/kill_switch.rs` (all three absent at the authoring head, removed with trading under D81), `sidecar/services/agent_runtime.py`, `types/proposed-change.ts`, `src/store/proposed-changes.ts`, `src/lib/host-actions.ts`, `src/modules/chat/ProposedChangesReview.tsx`, `src/store/agent-autonomy.ts`, `sidecar/services/action_ledger.py`, `sidecar/services/agent_tools/catalog.py`, `sidecar/tests/test_no_trading_surface.py`, `docs/SAFETY_ARCHITECTURE.md`, `src/modules/safety/`, `src/store/safety.ts`, plus every path that `git show r13-bedrock:docs/SAFETY_ARCHITECTURE.md` names.

1. Against `r13-bedrock`: `git diff --binary r13-bedrock <head> -- <path>` per path. Every non-empty diff is saved in full to `safety-surface.diff`, and every differing path gets a row in `SAFETY_SURFACE.md` (the blobs, lines, commits, and the reason: removed under D81 with the deleting commit, or changed since). The bar: byte-identical, or every differing byte is in the saved diff and every differing path has its row. A difference without a row fails.
2. From the candidate to the head: no hunk may touch the gate semantics (`_build_local_tools`/`_make_host_action`, `_staged_actions_notice`, `_grounded_host_action_result`, `_await_host_action_acks`, the read-intent strip, `PROPOSED_CHANGE_KINDS`, `AUTO_APPLIED_KINDS`, `autoApplies`, `enqueue`/`accept`/`reject`, `parseHostAction`, `describeIntent`, `applyIntent`, `FORBIDDEN_TOOL_SUBSTRINGS`) unless its entry was deferred as Tier-4 first.

## The verifier rubric (in the script as `RUBRIC`, quoted into every adversary, drive, triage, planner, verifier and re-proof prompt)

- **R1 Admission.** A finding is admitted only when it reproduces at the sha under test, either from the running app (own sidecar from that sha, the jsdom harness, `vy.py`) with the command and an output excerpt saved, or from the repo at that sha (path:line quoted). A claim about the world also carries a URL and a quote. It must be a product defect (price drift inside the as-of skew, taste, and weak prose the product does not render as data are not). An outage is kind `environment` only with a direct probe of the upstream. It must survive R3. Its severity comes from R2, not from the finder.
- **R2 Severity.** The COMMON.md rubric verbatim (critical: wrong money-relevant data shown as true, data loss, safety boundary; high: a core flow breaks or silently degrades, or a central promise is missing; medium: a real defect a demanding owner hits in normal use, or that bites the next maintainer; low: polish or edge; no padding). Every gate8 finding is critical.
- **R3 Duplicate check** against the register at the sha, by id and by repro. A reproducing `fixed` entry becomes a new entry noted `regression of <id>`. A match on an open, `blocked_tier4`, `needs_gui`, `removed_with_feature` or `not_a_defect` entry is attached (`ATTACHED.json`), except a `not_a_defect` whose rationale the new evidence contradicts. The same mechanism found twice is one item. DECISIONS items awaiting the operator (3.x, 4.x, 5.1-5.10) are attached, never filed as new.
- **R4 The signed-off class** (operator, 26 Sep 2026): "the local model states a figure for a subject with no ok tool call behind it". Entries R15-LEAD-030, R15-LEAD-035, R15-LEAD-037, R15-LEAD-038; DECISIONS_FOR_OPERATOR.md sections 4.9, 4.10, 4.11, 4.12. A local-lane instance is kind `known_limitation`, filed in `KNOWN_LIMITATION_INSTANCES.json` against the matching entry. It is never admitted, never planned and never put through a fix round, and no writer touches the figure guard, `_judge_clause` or `_NO_TOOL_CUE` on its account. A hosted-lane instance, a fabricated figure rendered as data, or a write that lands without the gate is outside the class.
- **R5 needs_gui.** A check that needs a real window, a native dialog, a separate macOS user or pixel rendering without a proven seam is operator-attended: written to `NEEDS_GUI.md` with manual steps and the expected result, never a fail, a pass or an admitted finding. The 11 entries already `needs_gui` at the authoring head (CODE-AGENT-001, LIFECYCLE-001, LIFECYCLE-008, UI-009, UI-022, UI-025, UI-050, UI-083, UI-084, DOCS-024, LIFECYCLE-040) stay operator-attended. The sheet marks them DEFERRED, which is allowed for needs_gui only.
- **R6 Gate 3 closure.** Every admitted critical/high/medium entry, and every c/h/m entry still `open` at the sha, is either fixed or adjudicated. Fixed means a root-cause fix, pinned by a test that fails without it, integrated with green ci-local and smoke, and certified in a fresh context from the running app: the original repro plus one fresh case of the same class. Adjudicated means a re-runnable rationale: `not_a_defect`, `not_reproducible` (probe saved), `environment` (direct probe saved) or `blocked_tier4` (Tier-1 or a locked decision, with its DECISIONS draft). "Ran out of rounds", "low impact" or "model weakness" alone is never a rationale. New lows are fixed or adjudicated where writers have room, else listed. The pre-existing low backlog is a count, not a gate item.
- **R7 Three-failures stop.** Failures count across the whole R15 run: those the entry's note records plus every `not_certified` in this pass (round verifier or re-proof). At the third, the entry stops. It leaves the rounds, becomes `blocked_tier4` with a DECISIONS item drafted in `DECISIONS_ADDITIONS.md` (what was tried, the three verdicts, what a fix would take), and is listed as stopped. It counts as adjudicated only once that item exists.
- **R8 Register statuses.** Only the register's own values: certified is `fixed` (with `closure_evidence '<sha7> final-pass r<N>'`); not_a_defect, not_reproducible and environment are `not_a_defect` with the reason in `note`; Tier-4 or stopped is `blocked_tier4`; then `needs_gui`, else `open`. The field is `note` (singular). `source` (26 older entries, provenance) and `closure_reason` (the `removed_with_feature` entries) exist but new entries carry neither.
- **R9 Run-ending**, stated once in the script (`RUN_ENDING_RULE`) and here with the same words:

> The run-ending stage runs only when args.run_ending is true AND the re-proof returned VERDICT PASS with a certified sha. Precondition: the main checkout HEAD and origin/004-r4-experience-rebuild both equal the certified sha (the lead fast-forwards 004 first); otherwise nothing changes and the stage returns blocked. Then, in order: (1) refresh the graphify index with graphify update, never --force; (2) relaunch the operator's dev stack detached on freshly built sidecars (node scripts/ensure-all-sidecars.mjs --force, then pnpm tauri:dev), stopping only the pids proven to be his Vysted dev stack; (3) through the dev-tools bridge only, Reset layout to default and make OpenAI the default provider, each read back, else left as a one-click instruction; (4) kill exactly the caffeinate pids the run armed. A FAIL stops the run at the sheet; this workflow never tags, merges, pushes 004 or main, or releases.

### The sheet's gate items (`R15_FINAL_PASS.md`, in this order)

1. Sweep complete: every lane returned or left its files, and all five slices ran.
2. ci-local green at the head.
3. Smoke test green at the head.
4. Owner-drives re-driven.
5. Battery coverage: every fixed entry has a raw probe.
6. Docs vs reality.
7. Banned words 0.
8. Scenario catalogue fully verdicted.
9. G8-1: no trading path.
10. G8-2: an order attempt halts for human review.
11. G8-3: a human accept of an order-shaped change fails closed.
12. G8-4: `audit_orders` has zero rows.
13. G8-5: the safety surface is byte-identical to `r13-bedrock`, or every differing byte is listed.
14. The tracked (paper) portfolio writes round-trip.
15. First run from a clean profile at sidecar level; the GUI half is DEFERRED as needs_gui.
16. Gate 3: every critical/high/medium entry closed (R6).
17. New lows dispositioned.
18. Signed-off class instances filed, none admitted or fixed (R4).
19. Three-failures stops recorded (R7).
20. needs_gui items listed (R5, DEFERRED).
21. The four named areas, before and after.

The verdict is PASS only when no item is FAIL. The script also refuses a PASS whose `gate_items` contain a FAIL.

### The docs-vs-reality grep set (`final-docs`)

- **(a)** One version string everywhere: package.json, Cargo.toml, tauri.conf.json, `FastAPI(version=…)`, `HOST_VERSION`, the top of CHANGELOG, README and `/health`.
- **(b)** Every `pnpm <script>` and `node scripts/…` in README, CURRENT_STATE, the runbook and the release notes exists.
- **(c)** Every repo path those documents and the top CHANGELOG section name exists at the sha.
- **(d)** docs/SIDECAR_API.md matches the live `/openapi.json`, both ways.
- **(e)** docs/MCP_INTEGRATION.md matches the live MCP list, both ways.
- **(f)** No user-facing document or in-app string offers trading (D81). Historical records are classified.
- **(g)** The banned word and phrase, case-insensitive, over the release docs and `src/` user-facing strings. The bar is 0.
- **(h)** docs/SAFETY_ARCHITECTURE.md section 2 says every kind auto-applies under AUTO. At the authoring head, `types/proposed-change.ts` `AUTO_APPLIED_KINDS` (panel, chart, watchlist) and DECISIONS 3.5 keep data-write and settings staged. The lane states which is true at the sha and files the doc if it is wrong.
- **(i)** CLAUDE.md is Tier-1. Its mismatches with the code (for example `GET /system/deepresearch/probe`, which the authoring head does not route) are notes for the operator, never writer work.

## Evidence (under `docs/redesign/verification/r15/final-pass/`, uncommitted until the lead commits it)

| File | Written by | Proves |
| ---- | ---------- | ------ |
| `PREFLIGHT.md`, `pids.json`, `register-at-<sha7>.json` | preflight | The sha, tags, the clean build and bundle, the shared stack, the register snapshot |
| `scenarios/<id>.md`, `scenarios/free-<lens>-<n>.md`, `scenarios/G8-5/`, `findings/<lens>.json` | adversaries | One file and one VERDICT line per scenario |
| `KNOWN_LIMITATION_INSTANCES.json`, `NEEDS_GUI.md`, `ATTACHED.json` | adversaries, drives, triage | R4, R5 and R3 attachments |
| `REGRESSION.md`, `logs/ci-local.log`, `logs/smoke.log`, `findings/chain.json` | chain | ci-local and smoke at the sha |
| `drives/<group>.md`, `../surface/<group>/final/`, `findings/drive-<group>.json` | drives | Re-drives compared with the census |
| `battery/shard-<k>.ids`, `shard-<k>.md`, `raw/<id>.txt`, `findings/battery-<k>.json` | battery | Every fixed entry's original repro at the sha |
| `DOCS_VS_REALITY.md`, `findings/docs.json` | docs | The grep set (a)-(i) |
| `TRIAGE.md`, `TRIAGE.json` (`REGISTER_ADDITIONS.json` if the register had moved) | triage | Admitted, refuted, duplicate, attached, class and needs_gui findings |
| `fix-r<N>/PLAN.md`, `INTEGRATION.md`, `ci-local.log`, `smoke.log`, `VERDICTS.json`, `VERDICTS.md` | round N | How each entry was fixed and certified, or adjudicated |
| `DECISIONS_ADDITIONS.md` | planner, verifier, re-proof | Tier-4 deferrals and R7 stops, for the lead to fold into DECISIONS_FOR_OPERATOR.md |
| `reproof/gate8/`, `reproof/safety-surface.diff`, `reproof/SAFETY_SURFACE.md`, `reproof/ci-local.log`, `smoke.log` | re-proof | The final head's chain and Gate 8 |
| `../../R15_FINAL_PASS.md` | re-proof (+ stage 6) | The gate sheet |
| `run-ending/*.log`, `stack-before.txt`, `stack-after.txt` | stage 6 | The graph refresh, the stack relaunch, the caffeinate release |

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

## What the lead does by hand afterwards

1. Read `docs/redesign/verification/R15_FINAL_PASS.md`. A FAIL ends the run here without a launch tag: no second pass is allowed. Report the FAIL and its reasons to the operator honestly.
2. On a PASS where fixes landed, audit `origin/worktree-agent-final-int` (the review-before-merge rule) and fast-forward 004 to the certified sha. On a PASS with no fixes, the certified sha is the rc3 sha.
3. Fold `final-pass/DECISIONS_ADDITIONS.md` into `DECISIONS_FOR_OPERATOR.md` (no workflow agent edits that file). Commit the evidence and the register edits (`r15/final-pass/**`, `R15_FINAL_PASS.md`, the register `.json` and `.md`, `DECISIONS_FOR_OPERATOR.md`) as one docs commit, with explicit paths. Never commit CLAUDE.md or the spend ledger. Push 004.
4. Resume the workflow with `run_ending: true` (see Launch). Read its lines in the sheet, and do by hand any step it marks not_done, using the commands above.
5. **Tags are only ever made by the lead.** Tag `r15-launch` on the newest rc and push the tag. If the pass landed fixes, the certified sha is newer than `r15-rc3`, and the production bundle the pass inspected is the candidate's; whether it first becomes the next rc is the lead's call. Tag the evidence commit only if `git diff --stat <certified>..<evidence commit>` touches `docs/` alone.
6. Hygiene: prune `final-cand` and `final-int`, and the `worktree-agent-final-*` branches merged into 004 (local only). Rewrite the run-state header and the handover.
7. Operator-attended afterwards: every DEFERRED needs_gui item, including the GUI first run on a separate macOS user account.

## Assumptions and decisions

- **The adversaries see the product through the built artifact.** They run the bundle's own sidecar binaries. The panels are reached through the jsdom harness or a proven browser seam, never by launching the `.app`.
- **Resolving "read-only data" against "clean default workspace".** Stage 6 never writes his workspace blob or settings itself. It backs the blob up read-only to scratch, then uses the app's own "Reset layout to default" and provider controls.
- **The safety-surface bar.** D81 removed most of the R13 safety surface, so a byte-identical surface is not expected. The bar is byte-identical, or every differing byte saved in the full diff with every differing path listed and explained. The table lives in the sheet.
- **Where evidence and register edits live.** Evidence and register edits stay uncommitted in the main checkout. Only writers and the integrator commit, on their own branches. Nothing in the workflow tags, merges to main, pushes 004 or main, signs, notarizes, releases, opens a PR or force-pushes.
- **Ports.** :52800-52802 (shared stack), :52810-52815 and :52820-52825 (adversaries), :52840+i (drives), :52860+k (battery), :52880 (triage), :52881+N (planner), :52886+N (verifier), :52895 (re-proof), web :5281/:5282 (browser seam only).
- **How the script was checked.** The body, with the meta block stripped, was wrapped in `new Function('args','agent','parallel','pipeline','phase','log','budget','workflow', …)` and run under node 24 with stub agents that spawn nothing. The stub checked:
  - `dry_run` with the full catalogue (33 ids) and with one adversary on one slice (`final-adv-solo`);
  - refusals for an empty slice, a duplicate slice, `adversaries: 3` and an unknown key;
  - every call has `effort: 'high'`;
  - peak concurrency of 6, with at most 2 strongest-tier agents;
  - the R7 stop: an entry with one prior failure stops after two failed rounds, and one with three prior failures never enters a round;
  - the stage 1-5 prompts are byte-identical with `run_ending` on, and only stage 6 is added.
- **Unverified.** The adversary scenario paths reflect the authoring head. Whether they still hold at `r15-rc3` needs preflight's ancestry check plus the adversaries' re-location notes. Whether the jsdom harness sends an Origin at all needs its first proof GET.
