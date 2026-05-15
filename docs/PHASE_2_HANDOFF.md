# Phase 2 Handoff (v0.3.0 → Phase 3)

**Read this first** if you are the Phase 3 lead. Everything you need to know
about what Phase 2 shipped, decided, and left pending — captured from warm
context immediately after the v0.3.0 tag (commit `b0f501d`, tag `b6c49da`).

---

## What v0.3.0 shipped

### Foundation (lead, pre-teammate dispatch)

- `9ffe187` — `fix(yfinance): normalize dot-tickers (BRK.B → BRK-B)`. Resolves
  a v0.2.1-verification backlog item; threads `_normalize_symbol` through
  every public `get_*` in `services/yfinance_provider.py`.
- `d9a2898` — `feat(types): plugin-runtime support types`. New
  `types/plugin-runtime.ts` introduces `PluginManifest`, `LoadedPluginState`,
  `LoadedPlugin`, `HealthSample`, `PluginRuntimeEvent`,
  `PluginPersistedConfig`. Wraps the locked `VystedPlugin` contract; does
  NOT modify it.
- `3384054` — `feat(types): chart drawing-tool spec`. New
  `types/drawings.ts` defines `DrawingKind`, `DrawingPoint`, `DrawingStyle`,
  `DrawingSpec`, `WorkspaceDrawings`.

### Teammate A — Chart Features (`1190b6f` → `c5c6762` merge)

- 30 new indicators across six categories (Moving Averages, Momentum,
  Volatility, Volume, Trend, Statistical) → 50 total in `_BUILDERS`.
- 10 drawing tools as `ISeriesPrimitive` instances under
  `src/modules/chart/drawings/`. Toolbar UI, drawing inspector, click-to-
  create, Esc/Delete keys, lock toggle.
- Drawing persistence through `.vysted-workspace` JSON (`SerializedWorkspace.
chartDrawings` is optional — older workspaces apply cleanly with explicit
  reset).
- Multi-chart sync — chart panel `singleton: false`; `useChartSyncBus` with
  three independent flavors (crosshair / visibleRange / symbol).
- Comparison overlay — second-symbol line on the same chart, normalize
  toggle `(close[i]/close[0]-1)*100` ridden on its own `priceScaleId: 'left'`.
- 33 new frontend tests, 31 new sidecar tests.

### Teammate B — Plugin Runtime (`1190b6f` merge)

- `PluginRuntime` (`src/lib/plugin-runtime.ts`) — pure TypeScript, no Tauri
  invoke. Capability negotiation by flag, lifecycle states with bounded
  health history (20 samples), typed `PluginRuntimeEvent`s, listener-error
  isolation.
- `useModulesStore.appendModules()` — extends without replacing; preserves
  `enabled[id]` from workspace replay; deduplicates on plugin id.
- `usePluginsStore` (`src/store/plugins.ts`) — React projection of the
  runtime: `loadedPlugins`, `dataSources`, `agents`, `nodes`. The latter
  three are not yet consumed by Phase-2 UI but the wiring proves the
  contract — Phase 3 plugs into them without a runtime change.
- Plugin Manager Panel (`src/components/PluginManagerPanel.tsx` + `src/
modules/plugin-manager/`) — lifecycle state badge, metadata, error banner,
  health-history strip, enable/disable toggle. Reachable via cmd+K
  (`/plugins`).
- Sidecar-owned per-plugin config — SQLite `plugins_store` + `/plugins`
  router. Mirrors `workspace_store` / `portfolio_db`. **No new browser
  storage.**
- `plugins/example/` — minimal plugin proving the contract end-to-end:
  declares `contributesData` + `contributesCommands` +
  `supportsControlPlane`, exports one `DataSource` and one slash command
  (`/example`).
- `bootstrapPlugins()` (`src/lib/plugin-bootstrap.ts`) wires the runtime
  into `src/app/page.tsx`; falls back to in-memory persistence when Tauri is
  absent so `pnpm dev` loads plugins as `active`.

### Teammate C — OpenBB ODP Plugin (`c769426` merge — Tier 2 separate-process)

- `plugins/openbb/` — exports a `VystedPlugin` declaring `pluginType:
"data-source"`, `contributesData=true`. `getDataSources()` enumerates
  equity / fundamentals / macro classes.
- `sidecar/openbb_subprocess/` — its own venv, packaged as its own
  PyInstaller `--onefile` binary by `scripts/ensure-openbb-sidecar.mjs`.
  Subprocess uses `RouterLoader.from_extensions()` +
  `CommandRunner.sync_run` (NOT `import openbb` — meta-package codegen is
  fatal under read-only `_MEIPASS`).
- `provider_registry` gains OpenBB-prefer wrappers for fundamentals /
  income statement / balance sheet / cash flow / analyst rating, each
  falling back to yfinance on `ProviderError` (logged at WARNING).
- New `get_macro_series` — OpenBB-only, clean `ProviderError` when the
  plugin is unavailable.
- FastAPI lifespan calls `openbb_provider.shutdown()` on app shutdown so
  `pnpm tauri dev` restarts do not orphan the OpenBB binary.
- Bundle delta: +43 MB on Windows (the OpenBB subprocess binary). Main
  sidecar binary unchanged at 56.9 MB.

### Lead release work (`b0f501d`)

- Version bump 0.2.1 → 0.3.0 across `package.json`, `Cargo.toml`,
  `Cargo.lock`, `tauri.conf.json`, sidecar `FastAPI(version=...)`.
- `CHANGELOG.md` v0.3.0 entry — full per-teammate decomposition,
  decisions log, failed approaches, known issues, verification matrix.
- `docs/BLUEPRINT.md` Phase 2 row marked shipped (with bundling-tier +
  binary-delta detail); Phase 3 row gains the `openbb-mcp-server`
  availability note.
- `docs/PLUGIN_DEVELOPMENT.md` (NEW) — author-facing guide.
- `BLOCKERS.md` aggregated from per-teammate self-reports (which were
  removed; salient detail preserved in merge commits + this doc).
- `docs/screenshots/v0.3.0/composed-{1920x1080,2560x1440}.png` — cross-
  cutting populated-state shots.
- `3e8f9bd` follow-up — CLAUDE.md gains two Phase-2 Gotchas (chrome-
  devtools MCP `isTrusted`; `subprocess.Popen` Windows deadlock).

---

## Architectural decisions made autonomously (Tier-2/3, no Tier-4)

Each decision is recorded in the commit body or CHANGELOG; restated here so
Phase 3 understands the precedent.

1. **Plugin loader: bundled-import, not filesystem-installed.** Phase 2
   ships a runtime that loads first-party plugins from `plugins/<id>/` in
   the repo via static import. Filesystem-installed plugins, sandboxing,
   and signing are out of scope until v1.0+. The runtime is real and
   capability-correct; only the discovery surface is bundled.
2. **OpenBB: Tier 2 (separate-process), not Tier 1 (bundle-in).** Pivoted
   after `pnpm sidecar:build` hit `ResolutionImpossible`: `openbb-core
1.6.9` strictly pins `fastapi <0.129` and `uvicorn <0.41`, both
   incompatible with Vysted's main-sidecar pins. Downgrading would have
   leaked strict pinning into every Vysted release. The §A2 escape hatch
   in the v0.3.0 plan exists for exactly this case.
3. **Drawings as `ISeriesPrimitive`.** The same pattern the existing
   `IchimokuCloudPrimitive` and `VolumeProfilePrimitive` use. Each drawing
   kind = one renderer class; renderer state is plain serialisable data
   so workspace round-trip is trivial. All ten renderers in one
   `renderers.ts` (each ~30 lines) so the FIB_LEVELS constant + the
   kind→renderer mapping in `factory.ts` are trivially shared.
4. **Multi-chart sync as opt-in bus.** `useChartSyncBus` Zustand store
   broadcasts `crosshair` / `visibleRange` / `symbol` events;
   subscribers self-identify by `source` to skip self-echoes; three
   flavors are independent toggles per chart instance. Chart panel
   `singleton: true` → `singleton: false`; `useWorkspaceStore.openPanel`
   mints a unique panel id when the spec is non-singleton.
5. **Comparison overlay as same-instance line series.** Second symbol
   fetches its own OHLCV at the active timeframe, optionally normalises,
   renders as a line series on the same chart (normalised line rides its
   own `priceScaleId: 'left'` so the candle scale is unaffected). One
   overlay symbol at a time in v0.3.0.
6. **Sidecar-owned plugin config persistence.** Mirrors the Phase-1
   `workspace_store` / `portfolio_db` pattern — SQLite at
   `~/.vysted-terminal/plugins.db`, `/plugins` router with GET/POST/
   DELETE for `PluginConfigPayload`. Per the locked stack constraints, no
   browser storage is added.
7. **`category` field on `IndicatorDef` (TS only, not Pydantic).** The
   sidecar already returns enough (`name` + `panel`); category is a pure
   UI grouping concern. Keeps the wire payload lean and avoids cross-
   language model sync.
8. **Subprocess lifecycle owned by main sidecar, not by plugin.** The
   plan's "launched on plugin enable, killed on plugin disable" needs a
   cross-process control plane Phase 2 doesn't ship. Lazy-launch on first
   request + main-sidecar shutdown is semantically equivalent for the
   v0.3.0 bundled-only-plugins regime and reuses Tauri's stdin-EOF
   watchdog pattern.

---

## Known issues carried forward (both Phase-3 candidates, NOT blockers)

### 1. OpenBB Windows `subprocess.Popen` deadlock

When the main Vysted sidecar lazy-launches the OpenBB subprocess via
`subprocess.Popen(...)`, the subprocess never finishes prewarm. The same
binary launched via PowerShell `Start-Process` reaches HTTP/200 in 3–4 s.
Cached-failure logic ensures the registry's yfinance fallback is fast on
subsequent calls — users still get fundamentals/macro data; the OpenBB
subprocess is a dormant performance optimisation that lights up only when
the launch path is fixed.

**Suspected cause.** OpenBB-core uses `anyio.from_thread.BlockingPortal`,
which spins an event loop on a worker thread. PyInstaller `--onefile`
extracts to `_MEIPASS` (additional thread/lock interactions). Combined
with `subprocess.Popen`'s default Windows handle inheritance (different
from `Start-Process`), the prewarm deadlocks.

**Phase 3 fix candidate.** Spawn the OpenBB subprocess as a sibling to the
main sidecar via the `tauri-plugin-shell` mechanism that already supervises
the main sidecar — Rust's `Command::new(...)` instead of Python's
`subprocess.Popen`. This is now the standard pattern (CLAUDE.md gotcha)
for any subprocess that owns its own port/lifecycle.

Full investigation in `BLOCKERS.md`.

### 2. chrome-devtools MCP cannot synthesise trusted user events

lightweight-charts (and any canvas-interactive feature) rejects synthesised
mouse events via the standard `isTrusted` check. The MCP cannot exercise
click-to-create gestures for drawings, drag-to-pan on charts, etc.
Drawings have full unit-test canvas-call coverage and the toolbar UI +
drawing-inspector populated screenshots prove the wiring; an end-user
`pnpm tauri dev` session demonstrates them live.

**Phase 3 fix candidate.** If a chart visual regression suite is added,
use Playwright with native event injection (or equivalent real-event
tooling). Recorded in CLAUDE.md gotchas.

---

## Plugin contract status

- **`types/plugin.ts` is unchanged in v0.3.0.** Verified across every
  teammate branch and the release commit (`git diff origin/main..HEAD --
types/plugin.ts` empty at every step). Tier-1 lock held.
- **The contract already supports Phase 3.** `capabilities.contributesAgents`
  - `getAgents()` is the registration surface Phase 3's pre-built agents +
    Custom Agent Builder will consume. `capabilities.contributesNodes` +
    `getNodes()` is for Phase 4's node editor. `subscribe()` and
    `executeCommand()` already exist for streaming + control-plane.
- **Runtime wiring is in place.** `usePluginsStore.agents` and
  `usePluginsStore.nodes` are populated by `PluginRuntime` whenever a
  plugin sets the matching capability flag — Phase 3 just consumes them;
  no runtime change required.
- **If Phase 3 genuinely needs a contract extension, that is Tier-4.** Log
  to `BLOCKERS.md`, design around the contract first, surface to the
  operator. The 6 capabilities + lifecycle hooks were designed for full
  v1.0 scope (per BLUEPRINT §3.3) — extension should not be the first move.

---

## Phase 3 entry context — where the AI layer plugs in

Per BLUEPRINT §7 Phase 3, the AI layer adds: multi-LLM provider
integration, 12 pre-built agents shipped as configs, Custom Agent
Builder UI, per-panel AI context wiring, MCP server. Mapping each to
existing Phase-2 surfaces:

### Pre-built agents

`AgentSpec` (`types/plugin.ts` + BLUEPRINT §3.4) is already the config
shape. The 12 agents ship as plugin-contributed agents via `getAgents()`
on a "vysted-agents" first-party plugin (or as a config registry the host
loads directly). `usePluginsStore.agents` holds the union; the chat
sidebar reads from it.

### Custom Agent Builder UI

A new module under `src/modules/agent-builder/` that writes user-defined
`AgentSpec`s to a sidecar-owned store (mirror `plugins_store.py`). The
agent runtime reads from both first-party agents + user agents +
plugin-contributed agents.

### Multi-LLM provider integration

A new `useLLMProvidersStore` (mirror `usePluginsStore` shape). Per BYOK
constraint, secrets resolved via OS keychain through the existing
`PluginConfig.secrets` mechanism — see how the runtime injects
`secrets: Record<string, string>` at `initialize()` time.

### MCP server

The OpenBB subprocess pattern (`sidecar/openbb_subprocess/`) is the
template. The MCP server lives in `sidecar/mcp_subprocess/` (or in the
main sidecar if its deps are compatible — first attempt should be
in-process per Tier-1 in plan §A2). `openbb-mcp-server` ships as its own
PyPI package and can be wrapped via the same separate-process pattern,
exposing OpenBB's data layer to external AI tools — see BLUEPRINT §7
Phase 3 row note. Decide between embedding (one MCP) vs federating
(Vysted MCP + OpenBB MCP exposed side-by-side) at Phase-3 planning time.

### Per-panel AI context wiring

The chart-sync bus (`src/store/chart-sync.ts`) is the reference for an
opt-in event bus that subscribers join by `source`. A panel-context bus
following the same shape lets each panel publish its current state
(symbol, timeframe, selection) and lets the AI sidebar subscribe to
whichever panel the user has focused. Same Zustand opt-in pattern.

### Bridges Phase 3 will write into

- `useModulesStore.appendModules()` for plugin-contributed agent panels
  (mirrors how the plugin manager itself was added in Phase 2).
- `usePluginsStore.agents` is the existing list — already populated by
  the runtime; consume it.
- New sidecar router under `sidecar/routers/` for LLM proxying / MCP
  control plane / agent execution. Follow the `plugins.py` router
  conventions (typed Pydantic request/response models in
  `sidecar/models/`, service layer in `sidecar/services/`, mocked tests
  in `sidecar/tests/`).

---

## File / commit pointers for deeper context

- `CHANGELOG.md` v0.3.0 entry — full ship log
- `docs/BLUEPRINT.md` §7 Phase 3 row — scope you are about to execute
- `docs/PLUGIN_DEVELOPMENT.md` — plugin author guide; reference plugins
  are `plugins/example/` and `plugins/openbb/`
- `BLOCKERS.md` — open Phase-3 follow-ups
- `CLAUDE.md` Gotchas — Phase-2 lessons (dockview, isTrusted,
  subprocess.Popen)
- `b0f501d` — v0.3.0 release commit
- `b6c49da` — `v0.3.0` tag
- `3e8f9bd` — Phase-2 residual lessons commit (CLAUDE.md gotchas)
- Per-teammate merge commits: `1190b6f` (B), `c5c6762` (A), `c769426` (C)
- Foundation commits: `9ffe187` (BRK.B), `d9a2898` (plugin-runtime
  types), `3384054` (drawings types)

---

## Verification snapshot at handoff

Pulled from `b0f501d` (the release commit) and the `3e8f9bd` housekeeping
follow-up — both on `origin/main`:

- `pnpm typecheck` / `lint` / `format:check` clean
- `pnpm test` — 17 files, **139 tests pass**
- `pytest sidecar` — **190 tests pass**
- `cargo fmt --check` / `cargo clippy -- -D warnings` clean; `cargo test`
  1 passed
- `pnpm sidecar:build` — main sidecar `--onefile` 56.9 MB
- `pnpm openbb-sidecar:build` — OpenBB subprocess `--onefile` 43 MB
- `git diff origin/main..HEAD -- types/plugin.ts` empty (Tier-1 locked)
- CI green on Win / macOS / Linux (Windows verified locally; matrix on CI)
