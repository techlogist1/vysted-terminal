# R15 LAUNCH — run state

## HEADER (rewritten at every checkpoint)

- Brief: `docs/redesign/verification/R15_BRIEF.md` (verbatim; re-read at every stage boundary + after every compaction)
- Register: `docs/redesign/verification/vysted-r15-register.json` (+ `vysted-r15-register.md` view) — NOT YET CREATED
- Report: `docs/redesign/verification/R15_RUN_REPORT.md` — NOT YET CREATED
- Log: `docs/redesign/verification/R15_RUN_LOG.md` — NOT YET CREATED
- Evidence root: `docs/redesign/verification/r15/<surface>/`
- Current stage: **Stage 0 — Ground truth** (scouts in flight) + **Stage 1 census sweeps 3+4 (Intent, World) in flight** — they depend on no Stage 0 output
- Pacing mode: **SPRINT** (until 15:30 IST Sat 19 Sep 2026 — weekly allowance use-it-or-lose-it; run as wide as work splits; Opus 5 workhorse, Fable only where judgement decides). 5-hour session wall resets 07:40 IST then every 5h (12:40, 17:40, 22:40 …).
- Lead model: Fable 5.1 (claude-fable-5-1)
- Gates that hold: none yet. Fallback release line: `r13-bedrock` @ 6a40f83.
- Newest tag: `r13-bedrock`
- Next action: collect Stage 0 workflow `wf_6871fdb3-621` results (files under `r15/stage0/`); merge `worktree-agent-pushguard` + `worktree-agent-rig` (local branches, NOT pushed), install hooks, FIRST PUSH; read `r15/stage0/ci-local-baseline.log` for `EXIT=`; then launch Stage 1 census waves.

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
- origin = git@github.com:techlogist1/vysted-terminal.git. Workflows: build.yml, lint.yml, test.yml — all `on: push: branches:[main]` + `pull_request`. (Public/private: TO VERIFY via gh.)
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
