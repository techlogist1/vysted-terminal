# Vysted Terminal

Open-source, AI-native finance desktop terminal — Bloomberg-level coverage with a
plugin architecture, local-first, bring-your-own-keys. Built as a Tauri desktop
app; Tradesa V2 is the first plugin proving the platform.

## Living document

This file is project DNA, not a frozen spec — it is expected to evolve. When you
(a future phase's Claude Code session) learn something the next session would
need, update this file in the same PR that introduced the change:

- A convention emerged or changed → update **Coding standards**.
- A non-obvious trap was diagnosed and solved → append to **Gotchas**.
- The model-assignment rules need adjusting → update **Model assignment**.

Rules: surgical edits only — change the line that is wrong, don't rewrite whole
sections. Keep the file under ~2k tokens and current-state-only. Build-time
decisions, failed approaches, and per-phase outcomes belong in `CHANGELOG.md`,
not here. The operator reviews the diff before it is committed.

## Stack

- **Frontend:** Next.js 16 (App Router, static export) + React 19 + TypeScript,
  Tailwind 4 + shadcn/ui, Zustand, Framer Motion
- **Desktop core:** Tauri 2.x (Rust) — windowing, keychain, auto-updater, sidecar
  lifecycle
- **Sidecar:** Python 3.13 FastAPI service on localhost — data + AI compute; the
  port is assigned by the Tauri core at launch
- **Package manager:** pnpm

## Layout

- `src/` — Next.js frontend
- `src-tauri/` — Rust Tauri core
- `sidecar/` — Python FastAPI sidecar
- `types/` — shared TypeScript types (plugin contract)
- `styles/` — design tokens
- `docs/` — architecture docs

## Coding standards

- TypeScript strict mode; no `any` in shared contracts — use `unknown`.
- Prettier + ESLint (TS), rustfmt + clippy (`-D warnings`), ruff (Python) — all
  enforced in CI.
- Conventional commit messages; one commit per concrete deliverable.
- Builds must stay green on Windows, macOS, and Linux.

## Plugin contract constraints

`types/plugin.ts` defines the `VystedPlugin` interface — the single highest-risk
file in the project. Every plugin and every future phase plugs into it. Six
capabilities: data, panels, commands, agents, nodes, control plane. **Changing
this contract is a breaking change for every downstream plugin.** Never edit it
without weighing the blast radius. Tradesa V2 (Phase 5) must implement all six
capabilities without contract changes. Phase 5 also ships global broker execution
plugins on the same contract — broker execution is v1.0 scope, gated behind the
safety layer in `docs/BLUEPRINT.md` §6.5.

## Model assignment (multi-phase build)

- **Opus** — lead. Owns risk-critical files: the plugin contract, CI workflows,
  Tauri config, licensing, and this file.
- **Sonnet** — mechanical work only (component JSX, design tokens, boilerplate
  docs). The lead reviews every diff before merge.
- **Haiku** — log parsing and high-volume mechanical scanning.

## Decision authority

How a session resolves a choice depends on its blast radius. Four tiers:

1. **Locked** — decisions in `docs/BLUEPRINT.md` §2 "Locked Decisions Summary".
   Never reopen. _E.g._ the stack (Tauri + Next.js + Python sidecar); AGPL-3.0 +
   commercial dual license; global broker execution in v1.0 scope.
2. **Spec-derivable** — the phase brief or blueprint settles it on a careful
   read. Decide and proceed; no asking, no documentation beyond the commit.
   _E.g._ which Pydantic models a phase needs (the brief enumerates them); a
   brief's stated teammate merge order; that the AI chat sidebar is Phase 3.
3. **Spec-ambiguous, derives from DNA** — the spec is silent, but the product
   positioning (finance sandbox, max extensibility, local-first, BYOK,
   research-lab voice) points to an answer. Decide from positioning, record it
   as a one-line append to `CHANGELOG.md` or `docs/BLUEPRINT.md`, continue.
   _E.g._ dockview chosen as layout engine; rationale: max sandboxability per
   product positioning; supports BLUEPRINT §5.2 customization primitives
   natively. _E.g._ sidecar-owned vs Tauri-owned persistence; lexicon vs
   model-based sentiment given the PyInstaller `--onefile` constraint.
4. **High blast radius** — the plugin contract (`types/plugin.ts`), licensing,
   the §6.5 execution safety model, or core architecture (the layer model, the
   sidecar boundary). Block and ask the operator. _E.g._ any `types/plugin.ts`
   change; altering AGPL/commercial terms; weakening a §6.5 safeguard.

Only Tier 4 surfaces to the operator. Tiers 2 and 3 are autonomous — Tier 3 with
a documentation trail. Do not ask permission for spec ambiguities that DNA can
settle; that is what Tier 3 is for. `BLOCKERS.md` (repo root) is for genuine
Tier-4 blocks and hard blockers hit while the operator is unavailable.

## Visual verification protocol

Screenshots used as visual proof MUST capture **populated** panel state, not
empty defaults. Empty-state shots hide bugs that only manifest with real data —
the 00606e7 hot-patch fixed an Equity Overview horizontal overflow that the
v0.2.1 verification screenshots missed because Equity Overview was empty in the
shot.

For any release or hot-patch verification shot:

- **Watchlist** — default symbols loaded, prices ticking.
- **Chart** — SPY with 2–3 indicators active.
- **Equity Overview** — AAPL (or comparable) with all sections populated.
- **News** — 3–5 articles rendered.
- **Portfolio** — ≥1 position.

Capture at **both** 1920×1080 and 2560×1440 via the `chrome-devtools` MCP
`resize_page`. Table widths shift with available space; a panel that looks
fine at one resolution can overflow at the other.

## Screenshot organization

Each release tag and significant patch gets its **own** subfolder under
`docs/screenshots/`. Folder names track release tags exactly (`v0.2.0`,
`v0.2.1`). Inter-tag residual fixes get `<tag>-<descriptor>` (e.g.
`v0.2.1-equity-fit` for commit 00606e7) or the commit short SHA when no
obvious descriptor fits.

**Never overwrite** existing screenshots. The v0.2.1-tag layout-\*.png pair was
silently overwritten by the 00606e7 verification run and is unrecoverable from
the working tree — only the v0.2.1 release commit's blob store still has them.
A per-patch folder costs nothing and preserves the per-release visual record.

## Gotchas

Non-obvious traps and their fixes — append a line or two as they are found, so
the next session does not re-learn them. (Phase 0 build notes live in
`CHANGELOG.md`.)

- **`types/data.ts` mirrors `sidecar/models/` by hand.** The sidecar's Pydantic
  models and their TypeScript counterparts in `types/data.ts` are kept in sync
  manually. Change a Pydantic model → update the matching interface in
  `types/data.ts` in the same commit.
- **Smoke-testing the sidecar binary orphans a worker.** The PyInstaller
  `--onefile` binary re-execs a worker child; `Stop-Process` on the bootloader
  PID leaves the worker alive, holding the binary locked — which breaks the next
  `ensure-sidecar.mjs` copy with `EBUSY`. When running the binary directly, kill
  it by name wildcard (`Get-Process vysted-sidecar*`), not by the spawned PID.
  The stdin-EOF watchdog only covers the Tauri-managed path.
- **dockview is the panel layout engine.** Panels render inside `dockview`
  (`src/components/PanelHost.tsx`); a module registers a `PanelSpec` whose
  `component` id maps to a React component via `VystedModule.panelComponents`.
  dockview's base CSS is imported in `globals.css` before the
  `.dockview-theme-vysted` override so the override wins the cascade. `PanelHost`
  only mounts `DockviewReact` after modules register, which keeps the
  static-export build SSR-safe.
- **chrome-devtools MCP cannot synthesize trusted user events.** Canvas-
  interactive features gated by `isTrusted` (drawing tools, drag-to-pan, any
  lightweight-charts gesture) cannot be visually regression-tested through
  chrome-devtools — its synthesised events are rejected. Phase-3 visual
  verification of canvas-interactive features needs real-event tooling
  (Playwright with native event injection, or equivalent). Phase-2 substitute:
  unit-test the data model + screenshot the toolbar wiring.
- **Spawn subprocess servers via Tauri Rust `Command::new`, not Python
  `subprocess.Popen`.** Verified pattern as of v0.4.0 (`a3b78c5`,
  openbb-mcp-server). A PyInstaller `--onefile` REST/MCP server that
  prewarms cleanly via PowerShell `Start-Process` deadlocks indefinitely
  when launched from `subprocess.Popen` on Windows — anyio + `_MEIPASS`
  - Windows handle-inheritance interact pathologically. v0.3.0's OpenBB
    subprocess hit this; v0.4.0 fixed it by retiring that path and
    spawning `openbb-mcp-server` via `app.shell().sidecar(...)` from
    `src-tauri/src/openbb_mcp.rs`. Use this pattern for any subprocess
    that owns its own port/lifecycle.
- **`keyring` Rust crate v3 has no default features.** The crate compiles
  and the API works without any platform-backend feature, but
  `set_password` silently no-ops on a default-features build. The
  v0.4.0 keychain commands enable the cross-platform set
  `["apple-native", "windows-native", "sync-secret-service",
"crypto-rust"]` explicitly — these are load-bearing, not optional.
- **FastMCP tools must return a dict (or declare an output_schema).**
  Returning a bare list throws `structured_content must be a dict or
  None` at tool-call time. When proxying a REST endpoint that emits a
  bare-list response (e.g. v0.4.0's `GET /agents` returns a `list[
AgentSummary]`), wrap at the MCP-tool boundary as
  `{"agents": [...]}` — don't change the REST contract.
- **Ruff version drift across teammate worktrees.** Phase 3 caught two
  UP041 cases (`asyncio.TimeoutError` → builtin `TimeoutError`) and a
  handful of formatting tweaks that B's worktree ruff didn't flag but
  the lead's did. Run `ruff check sidecar --fix && ruff format sidecar`
  at lead-integration time before tagging; the auto-fixes are safe.
- **Two teammates writing the same file from scratch.** If two
  worktrees both ship a full version of a shared file, the lead
  hand-merges at integration. Don't expect either "bare" version to
  drop in cleanly. Phase-3 plan-side fix: when two teammates need
  the same file, specify which owns it as primary and what the
  secondary adds, OR sequence the secondary's worktree to branch from
  the primary's pushed branch. v0.4.0's `src/store/agents.ts` is the
  precedent.
- **Retirement scope cleanup includes untracked build artefacts.**
  When `git rm` removes a directory like `sidecar/openbb_subprocess/`,
  the untracked `.venv/` left by the old build script stays on disk
  and starts leaking files into Prettier / lint scans. Lead
  integration must `rm -rf` the orphaned directory explicitly. v0.4.0
  hit this with the Phase-2 OpenBB retirement.
- **Sidecar `--onefile` binary footprint targets ≤120 MB main.**
  v0.4.0 distribution: 122 MB total (main sidecar 67 MB + openbb-mcp
  55 MB); main grew +10 MB from 5 AI provider SDKs. v0.5.0 confirmation:
  6 broker SDKs (`dhanhq`, `smartapi-python`, `kiteconnect`, `alpaca-py`,
  `ib_async`, `oandapyV20`) + workflow engine + backtest engine added
  only **+0.4 MB to main** (67.4 MB total). Pure-Python wrappers share
  most upstream deps (httpx, requests, websockets) so the PyInstaller
  graph stays lean. Future phases adding heavy Python deps (Phase 6
  QuantLib) should check projected main-sidecar size against the 120 MB
  threshold and apply the Tauri-Rust-spawn pattern (precedent
  `src-tauri/src/openbb_mcp.rs`) proactively if approaching.
- **Agent-tool `isolation: "worktree"` doesn't fully isolate writes for
  every agent.** v0.5.0 mega-sprint: several teammates (notably K and S)
  wrote tracked files in the lead's main worktree while running,
  bypassing the supposedly-isolated worktree under `.claude/worktrees/`.
  The contamination surfaces at first merge attempt — typically as
  pytest import errors or stale local modifications shown by `git status`.
  **Rule:** the lead audits only via `origin/<branch>`; main-worktree
  contamination is always discarded via
  `git restore --source HEAD -- <file>` + `git clean` of untracked
  contamination, then proper fetch + merge from origin. Documented in
  PHASE_4_HANDOFF.md "Coordination lesson" + PHASE_5_HANDOFF.md.
- **Append-only audit log is enforced at the DB level via SQLite triggers.**
  `sidecar/models/audit_log.py` exports `AUDIT_LOG_DDL` with two
  `RAISE(ABORT, ...)` triggers (BEFORE UPDATE + BEFORE DELETE) on
  `audit_orders`. The trigger raises `sqlite3.IntegrityError` (NOT
  `OperationalError` — the audit-suite tests catch this) with the
  literal message `audit log is append-only: UPDATE not permitted` /
  `... DELETE not permitted`. The reader connection additionally uses
  `PRAGMA query_only=ON` so a misconfigured reader role cannot
  accidentally write either. v0.5.0 BLUEPRINT §6.5 #4 enforcement —
  not convention.
- **`@xyflow/react` is the npm rebrand of `reactflow`** (12.x). Phase 0
  stack docs referred to the old name; v0.5.0 pins `@xyflow/react@12.10.2`
  as the canonical import (`import { ReactFlow } from "@xyflow/react"`).
  Migration paths from `reactflow` are documented at xyflow.com; future
  phases should use the rebranded import.
- **Kite Connect static-IP UX is required for order placement, not
  pre-blocked.** SEBI/NSE retail-algo compliance (in effect 2026-04-01)
  requires a registered static IP for order-placement API calls. Data
  endpoints are unaffected. `services/static_ip_detector.py` performs a
  one-shot HTTPx GET to `api.ipify.org`; the Kite plugin's
  `kite-static-ip-banner.tsx` polls and renders a banner on mismatch.
  Critically, the order placement path does NOT pre-block — a user
  behind VPN/VPS with the registered IP may legitimately succeed. The
  Kite API rejection at order time surfaces a graceful UX dialog
  through the audit-log path.
- **Long-running shells run in background with job-ID tracking.** Heavy
  pytest suites (the §6.5 audit's 25-min kill-switch benchmark, full
  sidecar suites, sidecar `--onefile` builds) auto-background when run
  via the Bash tool; the disciplined pattern is "kick off →
  `Awaiting notification on <jobId>` → resume on completion". Explicit
  contrast with the Phase-2/3 foreground-pipe deadlock (`pnpm dev | head
-20` blocks indefinitely): foreground pipes on long commands hang the
  session. **Rule:** anything > ~30s runtime → background + job-ID;
  never pipe a long-running command through `head`/`tee`/etc. in the
  foreground.
- **Defense-in-depth for safety-critical surfaces — type-level gate +
  DB-enforced invariant + grep-able audit check.** The v0.5.0 §6.5
  9/9-pass precedent: BLUEPRINT §6.5 #4 (append-only audit log) gets a
  private-method type gate (`_place_confirmed` only callable from
  `confirm_and_place`), a DB-level invariant (SQLite triggers
  `RAISE(ABORT)` on UPDATE/DELETE), AND a grep-time check (
  `test_safety_end_to_end.py::test_audit_2` greps the whole sidecar for
  call-sites). Each layer catches a different failure mode; together
  they survive a teammate's mistake at any layer. **Template** for any
  future-phase high-blast-radius surface (Phase 6 QuantLib pricing
  modules, Phase 7 distribution/signing, Phase-5.x Tradesa V2 plugin):
  enforce at the type system where the language allows, at the data
  layer where state lives, and capture a verifiable assertion in the
  dedicated audit suite. Documented in `docs/SAFETY_ARCHITECTURE.md`.
- **Mega-sprint pattern (2 BLUEPRINT phases under one tag) is viable —
  ceiling reference.** v0.5.0 shipped Phase 4 (workflow + backtest +
  node editor + Strategy Critic e2e) AND Phase 5 (7 broker integrations
  - §6.5 safety) under one tag because the product story is one story:
    research with agents → compose workflow → backtest → critic approves →
    paper-execute through real broker. 7 parallel Opus 4.7 teammates +
    10 sequential foundation commits + dedicated §6.5 audit checkpoint
    shipped clean with Tier-1 plugin contract held. **Not "always
    mega-sprint going forward"** — viable when (a) foundation contracts
    can lock cleanly before teammate dispatch, (b) audit fidelity stays
    high (per-phase audit checkpoints, not just per-release), (c) the
    teammate decomposition has clear non-overlapping file ownership.
    Phase-6 (Macro + Research + QuantLib) is closer to a single-phase
    shape; Phase 5.x Tradesa V2 + Phase 6 QuantLib could potentially
    compress if (a)–(c) hold.
- **Teammate agent terminations come in two flavours: socket-closed +
  stream-watchdog. Both are recoverable.** Phase 6 caught one of each:
  Sc died on an API socket close mid-execution after pushing the
  backend slice (Sc's frontend salvaged as a v0.6.1 lead-completion
  task); Q stalled at the 600s stream-watchdog mid-formatting with all
  work locally complete but uncommitted (lead salvaged directly from
  the worktree, committed + pushed to the worktree branch). **Rule for
  teammate dispatch going forward**: brief teammates to push commits
  FREQUENTLY (every concrete deliverable, not at end-of-task) — every
  push is a recovery checkpoint. **Rule for lead audits**: when a
  teammate's notification reports failure, FIRST inspect their worktree
  dir + branch via `git log --oneline -20` + `git status --short` — the
  work may be 95% complete and locally committed even when the API
  level sees an error. The v0.5.0 Teammate S precedent (usage-limit
  termination → lead-completed audit + handoff doc from the integrated
  codebase) generalises.
- **`agent_tools` package refactor side effect — `reset_for_tests` must
  re-register import-time tools.** v0.5.0's flat
  `sidecar/services/agent_tools.py` registered `backtest_summary` at
  module bottom. v0.6.0's F4 refactor split that into a package; the
  `backtest_summary` registration moved into a submodule's import side
  effect. Tests that called `agent_tools.reset_for_tests()` cleared the
  registry without re-importing the submodule, leaving the registry
  empty. The fix lives in `sidecar/services/agent_tools/__init__.py`:
  `reset_for_tests()` now re-registers `backtest_summary` after
  clearing. Future foundation tools that auto-register at import time
  need to be added to the same re-registration list.
- **PyPI naming traps — a package id may not be in the language you
  expect.** v0.6.0 Phase 6 Teammate M caught `fred-mcp-server` on PyPI
  is actually a Node.js MCP server, NOT a Python MCP server. Pivot to
  the in-process Python SDK (`fredapi`) matched ECB/IMF/WB pattern and
  avoided pulling a Node runtime into the Tauri build chain (BLOCKERS-M.md
  T3-M-1). **Rule**: when the plan names a subprocess MCP server,
  verify the language at dispatch time before wiring PyInstaller — a
  3-minute PyPI/GitHub check beats a half-hour debug of a "Python
  package that won't import".
- **XBRL precision must cross the wire as strings.** SEC EDGAR filings
  carry numbers that overflow JavaScript's `Number.MAX_SAFE_INTEGER`
  (AAPL's total-assets cent value is one example). v0.6.0 SEC contracts
  in `types/sec.ts` + `models/sec.py` type these fields as `string`;
  the UI parses to `BigInt` only when computing on them. Any future
  data source with arbitrary-precision values (legal docs, large
  population counts, scientific measurements) should follow the same
  rule.

## Per-phase handoff

Every phase ships `docs/PHASE_N_HANDOFF.md` as a release deliverable; the
phase lead writes it from warm context before closing the build window. The
next phase's lead reads it first to learn what shipped, what was decided
autonomously, what broke, and where their work plugs into existing surfaces.

**This is a standing convention as of v0.4.0.** v0.5.0's mega-sprint shipped
TWO handoff docs — `docs/PHASE_4_HANDOFF.md` and `docs/PHASE_5_HANDOFF.md` —
because two BLUEPRINT phases compressed under one release tag. Each
follows the same 8-section skeleton (Phase-2 + Phase-3 reference shape).
Phase N+1's lead reads `PHASE_N_HANDOFF.md` first, before opening
`BLUEPRINT.md` or `CHANGELOG.md`. The mega-sprint precedent is captured
in CHANGELOG v0.5.0 as the rationale: tightly-coupled phases ship
together when the product story is one story.

Each handoff covers, in order:

1. What N shipped (foundation + per-teammate)
2. Autonomous decisions (Tier-2/3)
3. Known issues carried forward (Phase-N+1 candidates)
4. Plugin contract status (Tier-1 lock verification)
5. Phase-N+1 entry context — where the next phase's work plugs in
6. File / commit pointers for deeper context
7. Verification snapshot at handoff
8. Any coordination lesson learnt the hard way

## Reference docs

- `docs/BLUEPRINT.md` — full architectural blueprint. Read when architectural
  questions arise; do not load by default.
- `CHANGELOG.md` — build-time decisions, failed approaches, and per-phase
  outcomes. Read when you need the _why_ behind a choice.
- `docs/PHASE_N_HANDOFF.md` — the previous phase's handoff. Read first when
  starting Phase N+1. v0.5.0 mega-sprint shipped both
  `docs/PHASE_4_HANDOFF.md` + `docs/PHASE_5_HANDOFF.md`. v0.6.0 ships
  `docs/PHASE_6_HANDOFF.md` (Phase 7 entry point: launch operations).
- `docs/SAFETY_ARCHITECTURE.md` — BLUEPRINT §6.5 enforcement reference.
  Per-guarantee implementation file:line pointers + capture-artifact
  paths + conditional revert procedure. Read before touching anything
  in the broker-execution code path.
- `docs/BROKER_INTEGRATIONS.md` — per-broker setup, credentials,
  paper-vs-live toggling, Kite static-IP UX path, IB Gateway requirement,
  OANDA SDK maintenance callout.
