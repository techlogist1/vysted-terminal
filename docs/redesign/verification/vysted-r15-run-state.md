# R15 LAUNCH — run state

## HEADER (rewritten at every checkpoint)

- Brief: `docs/redesign/verification/R15_BRIEF.md` (verbatim; re-read at every stage boundary + after every compaction)
- Register: `docs/redesign/verification/vysted-r15-register.json` (+ `vysted-r15-register.md` view) — NOT YET CREATED
- Report: `docs/redesign/verification/R15_RUN_REPORT.md` — NOT YET CREATED
- Log: `docs/redesign/verification/R15_RUN_LOG.md` — NOT YET CREATED
- Evidence root: `docs/redesign/verification/r15/<surface>/`
- Current stage: **Stage 1 census — all five sweeps in flight at max width** (18 workflows, ~100 agents, launched 14:50–15:20 after the power-loss resume). Stage 0 is done except the GUI rig proof-of-use (operator present) and the first push.
- Pacing mode: **SPRINT, operator-directed (14:45 IST): max parallelism, Fable 5.1 + Opus mix, slightly Fable-heavy, 'don't waste'.** Weekly allowance boundary 15:30 IST. The machine LOST POWER 10:17→14:36 (hibernate); operator re-logged in 14:41 and is PRESENT (GUI lane OFF).
- Lead model: Fable 5.1 (claude-fable-5-1)
- Gates that hold: none yet. Fallback release line: `r13-bedrock` @ 6a40f83.
- Newest tag: `r13-bedrock`
- Next action: as workflows complete (notifications), (1) re-launch any failed items via `r15/tooling/r15-fanout.js` (same args, `resumeFromRunId`), (2) assemble PROMISE_LEDGER + coverage map, (3) run the ideation judge panel (Fable) over `r15/invent/ideas/*.json`, (4) MERGE all `r15/census/raw/*.json` + `refute/*.json` into `vysted-r15-register.json` (every raw id → entry or one-line rejection), (5) Stage 2 fix waves by file ownership. Merge `worktree-agent-rig` once rig-salvage commits.

### Resume prompt (paste verbatim)

```
Resume VYSTED TERMINAL R15 "LAUNCH" in ~/Documents/dev/vysted-terminal. ultracode. The operator is away, bypass-permissions on; never end on a question.
1. Read docs/redesign/verification/R15_BRIEF.md in full (it is the mandate), then docs/redesign/verification/vysted-r15-run-state.md (header + loop log).
2. Reconcile before new work: git status; git worktree list; git branch (salvage or discard half-finished worktree-agent-* work via origin/<branch>); Vysted processes/ports; newest r15-* tag; regression suite state.
3. Continue from "Next action" in the run-state header. Keep the header current; commit + push at every green checkpoint; stage explicit paths only.
```

## Hard rules in force (compressed from brief — brief wins on conflict)

- Work on `004-r4-experience-rebuild`. No merge to main, no force-push, no history rewrite, no `v*` tag, no GitHub release, no PR (CI triggers on `push: main` + `pull_request` only — verified 06:15; tags `r15-*` and branch pushes trigger nothing).
- Stage explicit paths only until the two sacred files are retired.
- Writers: own isolated worktree, own `worktree-agent-<name>` branch, `git reset --hard <HEAD>` first (memory: agent-worktree-base-hazard), push each deliverable. Audit via `origin/<branch>`.
- Single lanes: heavy local jobs (pytest full, cargo, PyInstaller, prod build) · the GUI · the live app + 3 sidecars (one owner; rebuild before each verification round).
- GUI rig: presence check (HIDIdleTime) immediately before EVERY click/type/capture batch; frontmost-window surprise = hard stop + discard capture.
- §6.5: agent never places/confirms/auto-applies a broker order. Re-prove at every rc. Safety surface baseline = R13's `393e8e5`.
- Tier-4 pre-authorised: version strings (incl. tauri.conf.json) + ONE dedicated CLAUDE.md commit. Everything else Tier-4 → `docs/redesign/DECISIONS_FOR_OPERATOR.md`.
- Never touch the other desktop product on this Mac files or processes. No blanket kill. No Docker-wide prune.
- API budget is a hard stop; cheapest tool-capable model for every driven test; never print a key.
- Tests are state: never delete/skip/weaken to get green.

## Stage 0 facts (as established)

- 06:11 IST run start. HEAD 1d6f1d9 = origin/004. Tree dirty exactly as brief describes (8 files 3-Sep patch incl. CLAUDE.md, + 2 sacred files). 21 worktree registrations, 77 local branches.
- Caffeinate armed: PID 52012 (`caffeinate -dimsu -t 86400`), pidfile in session scratchpad.
- origin = git@github.com:techlogist1/vysted-terminal.git. Workflows: build.yml, lint.yml, test.yml — all `on: push: branches:[main]` + `pull_request`. origin is **PUBLIC** (gh-verified).
- graphify-out/ present (graph.json, GRAPH_REPORT.md) — currency TO VERIFY.
- Skills: aposd-critique, software-design-philosophy, frontend-design (example-skills:), karpathy-guidelines, superpowers:* all PRESENT. context7 docs MCP present. Playwright MCP FAILED to connect this session (CONNECT_TIMEOUT) — headless browser work goes via the repo's own playwright/node or the webapp-testing skill.

## Decisions log (surprising / expensive-to-reverse)

- R15-D1 (06:16): 3 Sep hot patch ADJUDICATED GENUINE — reviewed by lead, touches no §6.5 path, 145 targeted tests green, ruff clean → committed `043850c` (CLAUDE.md hunk held back for the single CLAUDE.md commit). Live proof against an OpenAI-direct key pending keystore scout.
- R15-D2 (06:16): sacred `enrich_nse_sectors.py` diff is EXACTLY the documented `_nse_symbols` fix (sha 5cb28e0d…286abdbe verified) → committed alone `7a1cd8f`; top of DECISIONS_FOR_OPERATOR.md with one-command revert.
- R15-D3 (06:19): `kill-switch-benchmark.json` retired structurally — capture is opt-in via `VYSTED_REFRESH_SAFETY_CAPTURES=1`, else temp dir; no assertion touched; safety test 9/9 → `0112a0c`. Tree now clean except the held CLAUDE.md hunk. Blanket-add rule can relax once CLAUDE.md commit lands.
- R15-D4 (06:14): OPERATOR IS PRESENT (HIDIdleTime <1s, frontmost = Claude) despite the "away" premise → GUI lane OFF; idle monitor armed (bg task, fires at ≥1500s idle). The operator's own dev stack has been running since 13 Sep 20:01 (pids 97534…, sidecar :52052) on STALE pre-patch binaries — it is HIS live session: read-only GETs only until he is away; headless work uses separate instances/ports.
- R15-D5 (06:14): **Docker/OrbStack daemon is NOT running → SearXNG container is down.** Observed before correcting anything: prime boring-cause candidate for "web search bugging out" (silent fall to keyless scraper). Do not start Docker as a fix; first prove what the app does/says in this state (Stage 1 Surface + Research funnel).
- R15-D6 (06:13): origin is PUBLIC. CI = build/lint/test.yml, all `push: [main]` + `pull_request` only → pushes to 004 and `r15-*` tags trigger nothing; never open a PR. No push until the pre-push secrets + stray-capture hook is installed and proven.

## Loop log

- L0 (06:11): fresh start; brief saved verbatim; run-state opened; caffeinate armed.
- L1 (06:20): own-hands Stage 0 done (D1–D6). Background: `pnpm ci-local` baseline detached → `r15/stage0/ci-local-baseline.log` (ends with `EXIT=<code>`); idle monitor armed. Stage 0 workflow `wf_6871fdb3-621` dispatched: 9 read-only scouts (env-verdict, drift-deps, drift-world, keys-budget, law-digest, isolation-map, surface-inventory, subsystem-partition, battery-exclusions) + 2 Opus worktree writers (pushguard, rig). Split rationale: every scout reads a disjoint slice and writes its own file; a single scout would serialize ~9 independent hour-long reads; writers own disjoint files under scripts/.
- L2 (06:23): Stage 1 Intent+World workflow `wf_734dffa1-5d4` dispatched early (no Stage 0 dependency; sprint window). Shape: Intent = 4 source families pipelined extract(Sonnet)→verify-against-code(Opus); World = 6 web-research topics (Opus), the agent-UX + harness-SOTA topics pipelined into a code comparison that emits raw harness-gap findings; then 2 ledger assemblers. Why this split: sources/topics are disjoint so pipeline (no barrier) lets verify start per source; a single reader would serialize ~10 long reads. Outputs: `r15/census/intent/`, `r15/census/world/`, `r15/census/raw/*.json`, `r15/census/PROMISE_LEDGER.md`, `r15/census/OPPORTUNITY_LEDGER.md`. RAW FINDING SHAPE fixed for all sweeps: {raw_id, title, severity, area, subsystem, repro, evidence, notes}. Also `.prettierignore` now covers r13/ + r15/ evidence (`96511d6`).
- L3 (06:30): Data sweep part 1 dispatched — workflow `wf_4073e516-82c` (curator → 24 parallel outside-truth pack builders, Opus; outputs `r15/battery/BATTERY_MANIFEST.md`, `manifest.json`, `packs/<SYM>.json`). Needs no app access, so it runs beside the scouts. Part 2 (in-app collection on an ISOLATED headless sidecar + field diffs → raw DAT findings) waits for `r15/stage0/ISOLATION_MAP.md` + `BUDGET.md`. Code sweep script is pre-written at `<session scratchpad>/r15-census-code.js` (critic→refuter pipeline per subsystem; takes `args.partition` = contents of `r15/stage0/SUBSYSTEM_PARTITION.json`) — if the scratchpad is gone on resume, rebuild it from this description. Live-app read-only probe (`r15/stage0/live-app-readonly-probe.md`): search tier = `t1_keyless` because docker daemon down (sidecar knows and says so at /search/searxng/status — does the UI?); Yahoo breaker since 13 Sep: opens_total 954, throttles_total 28,382 — heavy upstream throttling is a prime suspect for the "data on small stocks feels buggy" experience.
- L4 (09:10–10:06): Stage 0 workflow finished 8/11 (network resets: ECONNRESET / cert errors under a dying battery). Baseline chain GREEN: `pnpm ci-local` EXIT=0 — vitest 1504/135 files, cargo 13, pytest **2507 passed / 1 skipped** (304 s), eslint/prettier/tsc/clippy/ruff clean (`r15/stage0/ci-local-baseline.log`). Pushguard merged (`scripts/git-hooks/pre-push`, 9/9 self-test, installed) — proof `r15/stage0/PUSHGUARD_PROOF.md`. Isolated headless stack booted from source on :52152 (+MCP 52153/52154), data = safe copy in the session scratchpad.
- **R15-D7 (10:00): local UNPUSHED commits were rewritten once** (`git filter-branch` over `0112a0c..HEAD`, 5 commits, never on origin) to remove the verbatim brief from history and scrub a client name: origin is PUBLIC and the brief carries operator-private facts (allowances, machine, other products). The brief now lives on disk only, git-ignored (`docs/redesign/verification/R15_BRIEF.md`; backup in the session scratchpad), as does `r15/local/` (machine process tables, account balances: ENVIRONMENT_VERDICT.md, BUDGET.md). No pushed history was touched; the head-guard hook was moved aside for the rewrite and reinstalled.
- **R15-D8: spend budget** (from `r15/local/BUDGET.md`): OpenRouter paid lane is EXHAUSTED (negative balance) and DeepSeek-direct is at $0 → the app's shipped default lane cannot serve the operator until he tops up (handover item). Run fuel = OpenRouter `:free` tool-capable models (1000 req/day, $0) + OpenAI-direct capped at **$2.00 hard stop** (everything above is the operator's reserve). Enforced structurally by `scripts/r15/vy.py` (key read in-process, never printed; ledger `r15/spend-ledger.jsonl`; refuses at 700 free calls/day or $1.80 paid). `openai/gpt-5.6-luna` verified real at $0.20/$1.20 but unaffordable on the dead OpenRouter lane.
- L5 (14:41 RESUME after power loss): reconciled — HEAD intact, hooks intact, iso stack alive, caffeinate alive, old code-census workflow stopped (3/31 critiques had landed). Per-workflow concurrency is capped at CPUs−2 = 6, so width comes from MANY workflows: one generic templated script `r15/tooling/r15-fanout.js` (pipeline + 3× retry; prompts live in `r15/tooling/COMMON.md`, `PROMPT_code.md`, `PROMPT_census.md`, `PROMPT_wave2.md` so a resume can relaunch any item). Launched: code-A..D (31 subsystems, critique→refute, models crossed Opus↔Fable), packs-A..C (23 names), intent-A..C (23 chunks of 1,032 promises), world-2 (harness SOTA ×2 → compare, agent-UX compare, opportunity ledger), ideate-A/B (8 Fable seats), w2-seats (5 bug-bash seats + failure inducer, own sidecars :52211-16), w2-probes-F (research funnel ×3, screener, resolver, security), w2-mixed-F (agent-behaviour, test-quality, scenario-harness design, L3/L5/L6), w2-opus-A (L1/L2/L4, battery collector+diffs, rig salvage, browser harness), w2-opus-B (route fuzzer, licence audit, history secrets scan, docs truth, 3-Sep patch live proof, deps). Why this shape: every item owns disjoint output files and its own sidecar port; a single wide workflow would have queued behind the 6-slot cap.
