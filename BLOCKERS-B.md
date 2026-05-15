# BLOCKERS-B — Teammate B (Plugin Runtime) self-report

Branch: `worktree-agent-B`. Forked from `origin/main` at `3384054`
(F1+F2+F3 foundation).

## Final commit list

```
a01fdd2 feat(plugins): in-memory persistence fallback for browser-only dev
6f145a7 feat(plugins): minimal example plugin proving runtime end-to-end
c490134 feat(plugins): plugin manager panel UI
db7251a feat(plugins): bridge plugin contributions into module + plugin stores
e173c16 feat(plugins): PluginRuntime class with capability negotiation
4433687 feat(plugins): sidecar-owned per-plugin config persistence
```

Six commits, one per concrete deliverable, plus one residual fix
discovered during visual verification (the in-memory persistence
fallback for browser dev).

## What shipped

- **`PluginRuntime` class** (`src/lib/plugin-runtime.ts`) — pure-TS,
  no Tauri invoke. `discover()`, `loadPlugin()`, `unloadPlugin()`,
  `healthCheckAll()`, capability-negotiation accessors
  (`collectDataSources`, `collectPanels`, `collectCommands`,
  `collectAgents`, `collectNodes`). 24 dedicated tests.
- **Capability negotiation by flag** — every getter is gated on the
  matching `capabilities.contributesX`; a flag set with a missing
  getter emits an `errored` event but does not throw, and other
  capabilities still work.
- **Lifecycle states tracked** with rolling health history
  (`HEALTH_HISTORY_LIMIT = 20`). Typed `PluginRuntimeEvent`s emitted
  on every transition; listener errors do not poison runtime state.
- **`appendModules()`** added to `useModulesStore` (extends, doesn't
  replace; preserves pre-existing `enabled[id]` for workspace replay).
- **`usePluginsStore`** — React projection of the runtime: loaded
  plugins, dataSources, agents, nodes. `attachRuntime()` subscribes
  the store to runtime events.
- **Plugin Manager panel** (`src/components/PluginManagerPanel.tsx`)
  — lifecycle state badge, metadata (name, version, author, id,
  description), enable/disable toggle, error message banner,
  health-history strip with per-sample tone.
- **`pluginManagerModule`** registered in `src/modules/index.ts` —
  reachable via cmd+K (`/plugins`).
- **Sidecar-owned per-plugin config persistence** — SQLite at
  `~/.vysted-terminal/plugins.db`, `/plugins` router with GET/POST/
  DELETE for `PluginConfigPayload`, mirrors workspace_store /
  portfolio_db pattern. 15 sidecar tests.
- **`plugins/example/`** — minimal plugin proving the contract:
  declares `contributesData=true` + `contributesCommands=true`,
  exports one `DataSource` (`example-prices`), one slash command
  (`/example` → `Example: Hello`), real lifecycle methods that flip
  `healthCheck()` status, `executeCommand` handling. Loaded
  automatically at host startup. 6 dedicated tests.
- **`bootstrapPlugins()`** wires the runtime into the host: builds
  the runtime, attaches it to `usePluginsStore`, loads bundled
  plugins, bridges their contributions into `useModulesStore`,
  starts the 30s health-check loop. Returns a teardown function the
  page-level effect cleanup runs.
- **`page.tsx`** runs `bootstrapPlugins()` on mount and refreshes the
  command palette whenever the modules slice changes.
- **In-memory persistence fallback** — `pnpm dev` (no Tauri) now
  loads plugins as `active` instead of `error`; production
  (sidecar-backed) is unchanged.

## Tier-3 / Tier-2 calls (autonomous)

- **In-memory persistence fallback at bootstrap.** Tier-3:
  spec-ambiguous, derives from DNA (the runtime should work in dev
  mode for visual verification, not just production). Logged in
  the commit message.
- **`appendModules` precedence rule.** Tier-3: pre-existing
  `enabled[id]` entries win over the new module's "true" default
  (so a workspace that toggled a plugin off survives a re-launch).
  Logged in the test name + comment.
- **Plugin commands bridge through the module registry, not a
  parallel registry.** Tier-2: the plan says the commands flow
  through `useModulesStore` via `appendModules()`. Implemented
  exactly that — `bootstrapPlugins` constructs a `VystedModule` for
  each plugin and appends it.
- **`usePluginsStore` carries the data-source / agent / node
  aggregates.** Tier-2: the plan says these are not yet consumed by
  Phase-2 UI but the wiring proves the contract. Implemented as a
  Zustand store that subscribes to runtime events and re-pulls
  on every event.

## Tier-4 items (none)

`types/plugin.ts` was not edited. `git diff origin/main..HEAD --
types/plugin.ts` is empty:

```
$ git diff origin/main..HEAD -- types/plugin.ts
(no output)
```

No licensing, sidecar boundary, or core architecture changes.

## Final check status

Frontend (worktree root):

```
pnpm typecheck   ✓ clean
pnpm lint        ✓ clean
pnpm format:check ✓ clean
pnpm test        ✓ 14 files, 106 tests pass
```

Sidecar (sidecar venv):

```
pytest sidecar         126 passed, 1 failed (PRE-EXISTING — see below)
ruff check sidecar     ✓ clean
ruff format --check    ✓ clean
```

### Pre-existing test failure (NOT in scope)

`sidecar/tests/test_health.py::test_health_reports_active_providers`
fails on this machine because `openbb-core` is locally installed in
`sidecar/.venv`, so the openbb provider reports `available` instead of
`deferred-to-phase-2`. Verified pre-existing by stashing all my
changes and re-running — the test fails the same way.

This is owned by Teammate C (OpenBB Data Plugin per plan §3.A2 and
§3.C). Not blocking.

## Visual verification

Captured to `docs/screenshots/v0.3.0/teammate-b/`:

- `plugin-manager-{1920,2560}.png` — plugin manager panel showing
  the Vysted Example Plugin loaded with ACTIVE badge, full metadata
  (v0.1.0, author, id, description), green health-history pip,
  "1 active of 1 loaded · 1 data sources · 0 agents · 0 nodes"
  summary.
- `cmdk-example-{1920,2560}.png` — cmd+K palette filtered on
  "example" showing the plugin's slash command `Example: Hello`
  with description "Print a greeting from the example plugin to
  the console."

Both at 1920×1080 and 2560×1440. The Phase-1 panels in the rest of
the screen show error states ("Failed to load …") because `pnpm dev`
runs without Tauri spawning the sidecar — this is unrelated to the
plugin runtime and matches Phase-1 behaviour. The plugin manager
itself is fully populated, which is what this verification is for.

## What deferred (none in scope)

Nothing in scope was deferred. Every success-checklist item from the
brief is shipped:

- [x] PluginRuntime class with discover/load/unload/healthCheck
- [x] Capability negotiation works (only flagged getters are called)
- [x] Lifecycle states tracked, events emitted
- [x] Plugin panels/commands bridge into existing module registry
- [x] usePluginsStore for data sources / agents / nodes
- [x] Plugin manager UI panel
- [x] Sidecar-owned per-plugin config persistence (no browser storage)
- [x] Example plugin loads end-to-end
- [x] No regression on Phase 1 (all Phase-1 tests still pass)
- [x] All checks green
- [x] Populated screenshots at both resolutions
- [x] Pushed to `origin/worktree-agent-B`
- [x] Final BLOCKERS-B.md self-report (this file)

## Notes for the lead audit

- `src/modules/index.ts` and `src/store/modules.ts` were both
  modified by Teammate B as the plan permits (one-line append +
  `appendModules` extension). Teammates A and C don't touch
  either file — should integrate cleanly.
- The plugin manager's `panelComponents` is intentionally empty
  on the runtime-bridged module: the actual panel components are
  resolved through `useModulesStore.findPanel(panelId)` which
  searches all modules' `panels`; a plugin that contributes a
  `PanelSpec` would need its own registered React component map —
  out of scope for the example plugin (no panels), in scope for
  Phase 3+ when filesystem plugins land.
- The sidecar `/plugins` router handles only the persistence shape
  — it does NOT instantiate or run plugins. The runtime stays
  TypeScript-only on purpose.
