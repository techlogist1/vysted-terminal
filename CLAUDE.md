# Vysted Terminal

Open-source, AI-native finance desktop terminal — Bloomberg-level data coverage,
agent-first, local-first, bring-your-own-keys, with a plugin architecture. Built as
a Tauri desktop app (Rust core + Next.js UI + Python FastAPI sidecar).

> **Redesign in flight.** A "Cursor for finance" reframe (agent-centric hybrid UX,
> MCP-as-universal-tool-layer, minimal-dark UI) is being specified under `specs/` and
> `.specify/`. `docs/CURRENT_STATE.md` is the honest baseline of what exists today and
> what the redesign keeps vs rebuilds. This file tracks **current-state DNA + active
> rules**; build-time history lives in `CHANGELOG.md`.

## Living document

This file is project DNA, not a frozen spec. When a session learns something the next
session needs, update it in the same PR:

- A convention emerged/changed → **Coding standards** or the relevant rule.
- A non-obvious trap was diagnosed → **Gotchas** (one or two lines, the active rule only).
- Model-assignment rules changed → **Model assignment**.

Rules: surgical edits — change the wrong line, don't rewrite sections. Keep it lean and
current-state-only. **History, failed approaches, and per-phase outcomes belong in
`CHANGELOG.md`, not here.** The operator reviews the diff before commit.

## Stack

- **Frontend:** Next.js 16 (App Router, **static export**) + React 19 + TypeScript,
  Tailwind 4 + shadcn/ui, Zustand, Framer Motion, lightweight-charts, `@xyflow/react`.
- **Desktop core:** Tauri 2.x (Rust) — windowing, OS keychain, auto-updater, sidecar +
  MCP-subprocess lifecycle.
- **Sidecar:** Python 3.13 FastAPI on `127.0.0.1` — data + AI compute; the port is
  assigned by the Tauri core at launch. Shipped as a PyInstaller `--onefile` binary.
- **Package manager:** pnpm.

## Layout

- `src/` — Next.js frontend (`modules/` = feature panels, `store/` = Zustand, `lib/` =
  workspace/bootstrap/chart-theme, `components/PanelHost.tsx` = dockview host).
- `src-tauri/` — Rust Tauri core (sidecar spawn, keychain, kill-switch, MCP spawn).
- `sidecar/` — Python FastAPI sidecar (`routers/`, `services/`, `agents/`, `models/`,
  `*_mcp_subprocess/`).
- `types/` — shared TypeScript contracts (`plugin.ts` is Tier-1; `data.ts` mirrors
  `sidecar/models/`).
- `plugins/` — bundled plugins (Tradesa V2, openbb-mcp, brokers, example).
- `styles/` — design tokens. `docs/` — architecture docs. `scripts/` — build/CI scripts.

## Coding standards

- TypeScript strict; no `any` in shared contracts — use `unknown`.
- Prettier + ESLint (TS), rustfmt + clippy (`-D warnings`), ruff (Python) — all CI-enforced.
- Conventional commits; one commit per concrete deliverable. No emojis in code/commits.
- Builds stay green on Windows, macOS, Linux.

## Decision authority (blast-radius tiers)

1. **Locked** — `docs/BLUEPRINT.md` §2. Never reopen unilaterally. (Stack; AGPL-3.0 +
   commercial dual license; MCP server in v1.0.) ⚠️ The redesign vision **changes some
   locked decisions** (e.g. broker order execution moves to deferred/out-of-scope) — such
   reversals are Tier-4: surface to the operator, do not bake in silently.
2. **Spec-derivable** — the brief/blueprint settles it on a careful read. Decide, proceed,
   document only in the commit.
3. **Spec-ambiguous, derives from DNA** — spec silent but positioning (agent-first finance
   sandbox, max extensibility, local-first, BYOK, research-lab voice) points to an answer.
   Decide, record a one-line append to `CHANGELOG.md`/`BLUEPRINT.md`, continue.
4. **High blast radius** — plugin contract (`types/plugin.ts`), licensing, the §6.5 safety
   model, core architecture (layer model, sidecar boundary), or reversing a Locked decision.
   **Block and ask the operator.**

Only Tier 4 surfaces. Tiers 2–3 are autonomous (Tier 3 with a doc trail). `BLOCKERS.md`
is for genuine Tier-4 blocks and hard blockers hit while the operator is unavailable.

## Tier-1 locked files & invariants

Touch these only with operator sign-off:

- **`types/plugin.ts`** — the `VystedPlugin` contract. Six capabilities (data, panels,
  commands, agents, nodes, control plane). Changing it breaks every downstream plugin and
  every phase. Stays serializable (no React types — panels ride the companion map below).
- **§6.5 safety model** (`docs/SAFETY_ARCHITECTURE.md`). Enforced in defense-in-depth, each
  layer catching a different failure mode:
  - **Append-only audit log** — `sidecar/models/audit_log.py` `AUDIT_LOG_DDL` has BEFORE
    UPDATE + BEFORE DELETE `RAISE(ABORT)` triggers on `audit_orders` raising
    `sqlite3.IntegrityError` ("audit log is append-only: … not permitted"). Reader
    connection uses `PRAGMA query_only=ON`. DB-enforced, not convention.
  - **Type gate + grep check** — a confirm-before-place private-method gate plus a
    grep-time audit (`test_safety_end_to_end.py`) over all call sites.
  - **Kill-switch** (`services/kill_switch.py` + `src-tauri/src/kill_switch.rs`).
  - **Read-only trading-wrapper layers** (see Plugins).
    Never weaken a §6.5 safeguard without operator sign-off.
- **CI workflows** (`.github/workflows/`), **Tauri config** (`src-tauri/tauri.conf.json`),
  **licensing** (`LICENSE`, `COMMERCIAL_LICENSE.md`), and **this file**.

## Plugin contract

Plugins implement `VystedPlugin` (`types/plugin.ts`). Because the contract stays
serializable, React panels ship via the **`src/lib/plugin-bootstrap.ts` `PLUGIN_COMPANIONS`
static-import map** (each plugin id → `plugins/<id>/panels.ts` exporting
`Record<string, FunctionComponent>`). Adding a plugin with panels → add to **both**
`BUNDLED_PLUGINS` and `PLUGIN_COMPANIONS` (bootstrap warns at boot if you forget).
**Read-only wrapper plugins** enforce safety in three layers: (a) no
`insert_/update_/delete_/place_/submit_/execute_/create_…` methods on the provider's public
surface (`inspect.getmembers` audit), (b) no non-GET router routes (`router.routes` audit),
(c) `capabilities.supportsControlPlane = false`.

## Multi-agent build discipline (worktree)

Teammate agents dispatched with `isolation: "worktree"` **do not always isolate** — some
(historically Sonnet teammates) write into the lead's **main worktree** or switch its HEAD
onto a shared agent branch, which can sweep uncommitted lead edits into a teammate commit.

- **One isolated worktree per teammate; never the main worktree; never a shared agent
  branch** — each teammate pushes to its own `worktree-agent-<name>`.
- **Before any lead work after dispatch AND before integrating**, run `git worktree list`
  - `git branch`. If main's HEAD moved onto a teammate branch: stash lead files →
    `git checkout main` → `git stash pop`, then confirm no lead file was captured
    (`git log main..<branch> -- <lead-files>` empty = safe).
- **Audit only via `origin/<branch>`.** Discard main-worktree contamination with
  `git restore --source HEAD -- <file>` + `git clean`, then fetch + merge from origin.
- **Brief teammates to push every concrete deliverable** (each push is a recovery
  checkpoint). On a teammate failure notification, FIRST inspect its worktree + branch
  (`git log --oneline -20`, `git status --short`) — work is often 95% done and committed
  even when the API saw a socket-close or stream-watchdog termination.

## Model assignment (multi-phase build)

- **Opus** — lead; owns risk-critical files (plugin contract, CI, Tauri config, licensing,
  §6.5, this file) and reviews every diff before merge.
- **Sonnet** — mechanical work (component JSX, design tokens, boilerplate docs).
- **Haiku** — log parsing, high-volume mechanical scanning.

## Gotchas (active rules)

### Sidecar & distribution

- **Spawn port-owning subprocesses via Tauri Rust `app.shell().sidecar(...)`** (precedent
  `src-tauri/src/openbb_mcp.rs`), never Python `subprocess.Popen` — anyio + `_MEIPASS` +
  Windows handle-inheritance deadlock a `--onefile` server. After spawn, call
  `crate::wait_for_port` (port `0` → routes fall back / 501, graceful degrade).
- **PyInstaller `--onefile` silently drops three things** — audit each new sidecar dep:
  (a) `--copy-metadata` for packages whose `__init__` runs `importlib.metadata.version(...)`
  (`fastmcp, mcp, anyio, httpx, starlette, uvicorn`); (b) `--collect-data` for pkgutil
  resource data inside a package (e.g. `edgar`); (c) `--add-data` for non-package data dirs
  loaded via `Path(__file__).parent` (e.g. `agents/` — was silently unavailable for 3
  releases). `cargo test` never runs the binary; the smoke-test does.
- **`bundle.externalBin` declares 3 sidecars** (main, openbb-mcp, sec-edgar-mcp); all must
  build before `tauri build`. Adding one: `externalBin` + the SCRIPTS list in
  `scripts/ensure-all-sidecars.mjs` + `.gitignore`/`.prettierignore` + `pnpm sidecars:build`.
  The orchestrator is the single entry point — don't chain `ensure-*` scripts inline.
- **Ensure scripts are staleness-aware** (`scripts/sidecar-staleness.mjs`): a binary older
  than its source rebuilds even without `--force`; editing an ensure recipe forces a rebuild.
- **`keyring` Rust crate v3 needs explicit backend features** —
  `["apple-native","windows-native","sync-secret-service","crypto-rust"]`; `set_password`
  silently no-ops on a default-features build.
- **Node scripts that spawn sidecar binaries must tree-kill on teardown** — POSIX
  `detached` groups + `process.kill(-pid)`, Windows `taskkill /F /T`, exit handlers, and a
  pre-flight orphan check. PyInstaller workers orphan and hold the `_MEI` lock otherwise.
- Main sidecar binary footprint target **≤120 MB**.

### Copilot & sidecar code

- **The capability catalog (`sidecar/services/agent_tools/catalog.py`) is the ONE source of
  truth** (Constitution Principle II). `TOOL_SCHEMAS` (`schemas.py`), the custom-agent
  allow-list (`models/custom_agent.KNOWN_TOOL_IDS`), and the external MCP surface all DERIVE
  from it — do not hand-edit those. **To add an agent tool:** (1) register a handler in
  `agent_tools`, (2) add a `Capability` in `catalog.py` (`kind="read_handler"` auto-projects to
  `TOOL_SCHEMAS`, the allow-list, and — unless internal-only — the MCP surface by the SAME
  name), (3) add its id to an agent's `tools` allow-list to make it reachable.
  `test_capability_catalog.py` audits registry⟺catalog parity (SC-006);
  `test_mcp_catalog_parity.py` audits the internal⟺MCP projection (SC-004). The loop only
  calls a tool if the adapter SENT a `tools=` schema; every `services/llm/` adapter must
  `kwargs.pop("tool_ids")`. The assistant tool-call turn rides `metadata["tool_calls"]`, and
  the **tool-RESULT turn carries `metadata["name"]`** (Gemini pairs `function_response` by
  name, not id — omit it and Gemini multi-round breaks). A new first-party agent JSON bumps the
  roster count asserted by `test_agent_runtime`/`test_agents_router`/`test_mcp_server`.
- `agent_tools` is a package — `reset_for_tests()` must re-register import-time tools.
- **Durable Delegate runs execute DETACHED** (`services/run_manager.py` spawns
  `asyncio.create_task` driving `invoke_agent`; state in `services/runs_store.py` SQLite,
  routes in `routers/runs.py`). `run_manager.shutdown()` MUST stay in the `app.py` lifespan
  `finally` or detached tasks leak. A `BudgetGuard` (`services/budget_guard.py`) meters every
  round via `invoke_agent`'s `on_round_usage` callback; the first ceiling breach
  (tokens/spend/wall/steps) aborts the run to `error` with a stated reason + resumable
  checkpoint (SC-008). The runs router is **prefix-less** (`POST /agents/{id}/runs` +
  `/runs/*`); `GET /runs` emits BOTH camelCase + snake_case so either spelling resolves.
- **FastMCP tools must return a dict** (or declare `output_schema`). The data/analysis MCP
  tools are **projected from the catalog** (`mcp_capabilities()`) via
  `FunctionTool(parameters=<schema>, fn=<handler>)` dispatching to the same `agent_tools`
  handler; the agent/workspace/workflow tools stay hand-written + MCP-only. Wrap any bare-list
  REST response at the MCP boundary (e.g. `{"agents": [...]}`); don't change the REST contract.
- **Python 3.13:** use `asyncio.run(...)`, not `asyncio.get_event_loop()` outside a running
  loop (raises `RuntimeError`).
- **`types/data.ts` mirrors `sidecar/models/` by hand** — change both in the same commit.
- **Arbitrary-precision numbers cross the wire as strings** (XBRL/SEC overflow JS
  `Number.MAX_SAFE_INTEGER`); parse to `BigInt` only when computing.

### Frontend

- **dockview is the panel layout engine** (`src/components/PanelHost.tsx`): a module
  registers a `PanelSpec` whose `component` id maps to a React component via
  `VystedModule.panelComponents`. dockview base CSS is imported in `globals.css` before the
  `.dockview-theme-vysted` override; `PanelHost` mounts `DockviewReact` only after modules
  register (keeps static export SSR-safe).
- **`dragDropEnabled: false`** (`tauri.conf.json` `app.windows[0]`) is REQUIRED for
  in-webview HTML5 drag-drop (dockview tab reorder + node-editor palette→canvas) — the
  default `true` installs an OS handler that swallows HTML5 drag (macOS WKWebView too).
- **Persisted UI state rides the workspace blob** (`SerializedWorkspace`,
  `src/lib/workspace.ts`), not localStorage. Add a field → include in `serializeWorkspace`
  - `autosaveLayout`, restore in `deserializeWorkspace` (guard older blobs); if the change
    doesn't move the dockview layout, add a store subscription in `page.tsx` calling
    `autosaveLayout()`.
- **Design token NAMES are historical, not literal** (`amber-*`→coral, `charcoal-*`→espresso,
  `brass-*`/`sage-*`→warm neutrals) so re-skinning re-values `tokens.css` alone. Canvas
  (`lightweight-charts`/drawings) can't read CSS vars — its palette is single-sourced in
  `src/lib/chart-theme.ts`; change BOTH or canvas drifts. _(The redesign replaces this warm
  palette with a Cursor-style minimal-dark one — change both sources together.)_
- **chrome-devtools MCP can't synthesize trusted (`isTrusted`) events** — canvas-interactive
  features (drawings, drag-to-pan, lightweight-charts gestures) need Playwright/native event
  injection for visual regression, not chrome-devtools.

### Broker & credentials

- **BYOK secrets:** the renderer reads the OS keychain (Tauri `keychain_set/get/delete`) and
  passes the secret in the request (a **header** for read-only plugins, never the body); the
  **sidecar cannot read the keychain**. Never log, echo, or persist beyond process memory.
  Loopback transport only. `test_<plugin>_router.py` asserts responses never echo creds.
- **Kite Connect read-only login runs in the SIDECAR** (`services.brokers.kite.
exchange_request_token` via `kiteconnect.generate_session` → `POST /brokers/kite/session`);
  `api_secret` crosses for the exchange only (never stored/echoed). New broker read routes
  are GET-only and duck-type to `account_info()` (no §6.5 ABC change). Manual request_token
  paste is the v1 flow. `static_ip_detector.py` warns on IP mismatch but does NOT pre-block.
- **Granular broker reads** (`/positions` `/holdings` `/margins`) are DISTINCT shapes
  (`models/broker_reads.py`, mirrored in `types/broker-reads.ts`) returned via an adapter
  `positions_info`/`holdings_info`/`margins_info` seam — adapters without it fall back to
  `account_info()` (the route is typed `…Result | AccountSummary`). Still GET-only (no §6.5
  ABC change); every result carries the FR-041 provenance label (`synthetic`/`mode`/`provider`)
  so paper/synthetic values are badged. Adding granular reads to an adapter = add the `*_info`
  method only; the route + frontend `BrokerReadsSection` pick it up by duck-type.

### Versioning & process

- **Version lives in many sources** — `package.json` + `Cargo.toml` + `tauri.conf.json` +
  sidecar `app.py FastAPI(version=…)` + `HOST_VERSION` (`plugin-bootstrap.ts`); `/health`
  derives from `request.app.version`. At bump: grep for stale version strings and run
  `cargo update -p vysted-terminal --offline --manifest-path src-tauri/Cargo.toml`.
- **Long-running commands** (>~30s: pytest suites, sidecar builds) run in the background with
  job-ID tracking; **never pipe a long command through `head`/`tee` in the foreground**
  (deadlocks; also masks the exit code).
- **CORS-error-masks-500:** FastAPI `CORSMiddleware` doesn't add CORS headers to exception
  responses, so a 500 surfaces in the browser as a "CORS policy" error — direct-`curl` the
  endpoint to distinguish a real CORS issue from a 500-without-CORS-headers.

## Verification gates (hard, before every release tag)

- **`pnpm ci-local`** mirrors CI byte-for-byte (install `--frozen-lockfile` →
  ensure-all-sidecars → lint → format:check → typecheck → cargo fmt → clippy `-D warnings` →
  ruff → vitest → cargo test → pytest). If it's skipped or red at tag time, the tag is invalid.
- **`node scripts/smoke-test-sidecars.mjs`** catches the binary-runtime gap `ci-local` can't
  see (spawns each built sidecar, polls `/health`, checks MCP subprocesses survive).
- Cheapest in-sprint guard: `pnpm format:check` before every push to `main`. Before any
  Python commit: `ruff format <files> && ruff format --check sidecar && ruff check sidecar`.

## Deferred / carry-forward

- **MCP cold-bind ~34 s** isolated; concurrent `_MEI` extraction at boot contends for disk,
  so `MCP_PORT_WAIT_SECS=45`. True fix is `--onedir` (kills per-launch extraction) — needs an
  `externalBin`→resource-folder + Rust spawn change that `ci-local` can't verify. See
  `BLOCKERS.md`.
- smoke-test should additionally TCP-probe the claimed MCP port + verify load-bearing
  endpoints (`/agents` count > 0).

## Visual verification

Screenshots used as proof MUST show **populated** panel state (real data), never empty
defaults — empty shots hide layout bugs. Capture dark theme at **both** 1920×1080 and
2560×1440; per-release subfolder under `docs/screenshots/v<tag>/`, **never overwrite**
existing shots. Populated anchors: watchlist `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT,
ETH/USDT`; chart SPY + indicators + VWAP; equity overview AAPL; news with sentiment;
portfolio ≥1 position with P&L. _(The redesign supersedes the warm "Claude after dark"
cockpit convention — update this section when the new shell lands.)_

## Reference docs

- `docs/CURRENT_STATE.md` — honest current-state inventory (read first to learn what exists).
- `docs/BLUEPRINT.md` — original architectural blueprint (§2 locked decisions, §6.5 safety).
- `docs/SAFETY_ARCHITECTURE.md` — §6.5 enforcement, file:line pointers, revert procedure.
- `docs/MCP_INTEGRATION.md`, `docs/SIDECAR_API.md`, `docs/PLUGIN_DEVELOPMENT.md`,
  `docs/BROKER_INTEGRATIONS.md`, `docs/DESIGN_SYSTEM.md` — per-subsystem references.
- `specs/` + `.specify/` — the "Cursor for finance" redesign spec (constitution/spec/clarify).
- `CHANGELOG.md` — build-time decisions and per-phase history (the _why_).
- `docs/archive/` — historical phase handoffs, audits, and bug catalogs.

## Per-phase handoff

Every phase ships `docs/PHASE_N_HANDOFF.md` (kept in `docs/archive/` once superseded). The
lead writes it from warm context before closing the build window; the next lead reads it
first. Eight sections: (1) what shipped, (2) autonomous Tier-2/3 decisions, (3) issues
carried forward, (4) plugin-contract lock verification, (5) next-phase entry context,
(6) file/commit pointers, (7) verification snapshot, (8) coordination lessons.

<!-- SPECKIT START -->

Active redesign spec lives under `specs/` and `.specify/memory/constitution.md`. For the
current-state baseline (architecture, endpoints, subsystems, what works vs is deferred),
read `docs/CURRENT_STATE.md`.

<!-- SPECKIT END -->
