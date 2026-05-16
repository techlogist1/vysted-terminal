# Plugin Development

Vysted Terminal is built around a stable plugin contract. Every panel,
data source, command, agent, node-editor block, and control-plane action
that a third party adds to the terminal flows through that single
contract. This guide is for plugin authors building against it.

## What ships in v0.3.0

- The contract — `types/plugin.ts` — locked. It defines the six
  capabilities a plugin can contribute (data, panels, commands, agents,
  nodes, control plane), the lifecycle hooks (`initialize`, `shutdown`,
  `healthCheck`), and the negotiation flags that make every capability
  optional.
- The runtime — `src/lib/plugin-runtime.ts` — the loader that discovers,
  instantiates, supervises, and surfaces plugins through their lifecycle.
- The manager UI — `src/components/PluginManagerPanel.tsx` — what users
  see in the terminal: each loaded plugin's state, health, metadata, and
  an enable/disable toggle.
- Two reference plugins — `plugins/example/` and `plugins/openbb-mcp/`
  (Phase 3 replacement for the retired `plugins/openbb/`) — exercise
  the contract end-to-end and are the best starting point for reading.
- Bundled-import loading — plugins ship under `plugins/<id>/` in the
  repo. Filesystem-installed plugins, signing, and a marketplace are
  out of scope until v1.0+.

## File layout

A plugin lives in `plugins/<plugin-id>/`:

```
plugins/openbb-mcp/
  manifest.json   # PluginManifest (see types/plugin-runtime.ts)
  index.ts        # exports a VystedPlugin instance as default
```

The manifest is read by the runtime at discovery time and is what the
plugin manager UI shows the user before the plugin is instantiated. The
entry module is imported lazily and instantiated on `loadPlugin()`.

## The manifest

```json
{
  "id": "openbb-odp",
  "version": "0.1.0",
  "name": "OpenBB ODP",
  "entry": "./index.ts",
  "requiredHostVersion": "0.3.0",
  "description": "OpenBB Platform data, wrapped as a Vysted data plugin.",
  "author": "Vysted Team",
  "homepage": "https://github.com/techlogist1/vysted-terminal"
}
```

The `id` and `version` MUST match the `VystedPlugin.pluginId` and
`VystedPlugin.version` exported by `entry`. The runtime asserts this on
load and refuses to start a plugin that disagrees with its own manifest.

## The contract

Every plugin exports a `VystedPlugin` (see `types/plugin.ts`). The
minimal shape:

```typescript
import type { VystedPlugin } from "@/../types/plugin";

const plugin: VystedPlugin = {
  pluginId: "my-plugin",
  pluginName: "My Plugin",
  pluginType: "data-source",
  version: "0.1.0",

  capabilities: {
    contributesData: true,
    contributesPanels: false,
    contributesCommands: false,
    contributesAgents: false,
    contributesNodes: false,
    supportsControlPlane: false,
  },

  async initialize(_config) {
    // Establish connections, warm caches, start subscriptions.
  },

  async shutdown() {
    // Tear down connections, stop timers, release resources.
  },

  async healthCheck() {
    return { status: "healthy", checkedAt: Date.now() };
  },

  getDataSources() {
    return [
      {
        id: "my-prices",
        label: "My Prices",
        kinds: ["equity"],
        realtime: false,
      },
    ];
  },
};

export default plugin;
```

## Capability negotiation

The runtime calls a getter ONLY when the matching `capabilities` flag
is `true`. So `getPanels?` is only invoked if `contributesPanels`. A
plugin that sets a flag without providing the matching getter
transitions to `error` state — but other capabilities still work.

Concretely: a plugin that contributes data AND commands sets
`contributesData=true` and `contributesCommands=true`. It MUST then
implement both `getDataSources()` and `getCommands()`. The runtime never
calls `getPanels()` on it because `contributesPanels=false`.

This is what `plugins/example/` proves end-to-end: it sets two
capability flags, contributes one `DataSource` + one `CommandSpec`, and
the runtime catalogs both without ever calling the panel/agent/node
getters.

## Lifecycle

```
discovered  →  initializing  →  active
                    │             │
                    ↓             ↓
                  error      stopping → stopped
```

- **discovered.** Manifest validated; instance not yet imported. The
  plugin manager shows the plugin as "loadable" but not running.
- **initializing.** `initialize(config)` is in flight. Throwing here
  transitions to `error` with the captured message.
- **active.** `initialize()` resolved. The runtime registers the
  plugin's contributions (panels into `useModulesStore`, data sources /
  agents / nodes into `usePluginsStore`).
- **stopping.** `shutdown()` is in flight.
- **stopped.** Capabilities deregistered. The plugin can be reloaded
  cleanly.
- **error.** Either `initialize` or `shutdown` or `healthCheck` threw.
  The plugin manager surfaces the error message.

The runtime polls `healthCheck()` every 30 seconds and stores the most
recent 20 samples per plugin so the manager UI can show a trend.

## Persistence

Per-plugin config (the `enabled` flag, plugin-private settings, granted
secret IDs) is persisted by the sidecar — NOT by browser storage. The
runtime reads/writes through a `PluginPersistenceAdapter`; in production
this routes through the `/plugins/{id}/config` sidecar endpoint
(SQLite-backed at `~/.vysted-terminal/plugins.db`).

If you need to persist plugin-specific data BEYOND config, follow the
same pattern: define a sidecar router + service, mirror the
workspace_store / portfolio_db structure, and never reach for browser
storage. Tauri's WebView does not surface localStorage / sessionStorage
to plugins.

## Bundling: in-process vs separate-process

Most plugins will live entirely in-process — a TypeScript entry, no
extra Python dependencies. The `plugins/example/` plugin is the
reference for that pattern.

Plugins that need heavy Python dependencies fall into two camps:

1. **Compatible with the main sidecar's pins.** Add the dependency to
   `sidecar/requirements.txt`, write a service / router under
   `sidecar/`, and proxy from the plugin's TS entry.
2. **Incompatible with the main sidecar's pins** (the OpenBB case).
   Ship the dependency as its own Python sidecar in
   `sidecar/<plugin>_subprocess/`, packaged as a separate PyInstaller
   `--onefile` binary by `scripts/ensure-<plugin>-sidecar.mjs` (mirror
   `ensure-openbb-mcp-sidecar.mjs`). The subprocess MUST be spawned by
   the Tauri Rust core via `tauri::api::shell` — see
   `src-tauri/src/openbb_mcp.rs` for the reference. **Never use Python
   `subprocess.Popen` for a separate-process plugin on Windows**: it
   deadlocks under PyInstaller `--onefile` for any FastAPI-backed
   server with anyio in the dep tree (CLAUDE.md Gotcha).

The `plugins/openbb-mcp/` plugin, together with
`sidecar/openbb_mcp_subprocess/` and `src-tauri/src/openbb_mcp.rs`, is
the reference for the separate-process pattern.

## MCP plugins

Phase 3 added two MCP integration paths:

- **Vysted as MCP server.** The sidecar exposes its data + agent
  surface as MCP tools via a FastMCP application mounted at `/mcp`
  over the Streamable-HTTP transport. External MCP clients (Claude
  Desktop via `mcp-remote`, Claude Code natively) consume Vysted by
  pointing at `http://127.0.0.1:<sidecar-port>/mcp/`. See
  `docs/MCP_INTEGRATION.md` for the client config.
- **Vysted as MCP client.** The sidecar's `services/mcp_client.py`
  wraps the official `mcp` Python SDK and connects to external MCP
  servers over stdio or Streamable-HTTP. The `openbb-mcp` plugin is
  the reference consumer: it routes the OpenBB Platform's tool
  surface through this wrapper.

When you author a plugin that needs to talk to an external MCP server,
follow the openbb-mcp pattern:

1. Spawn the external MCP server via Tauri Rust `Command::new` (a
   `src-tauri/src/<plugin>.rs` mirroring `openbb_mcp.rs`), with the
   bundled binary built by `scripts/ensure-<plugin>-sidecar.mjs`.
2. Expose the child port to the Python sidecar via an env var the
   Rust spawn helper sets — the sidecar reads it lazily on first call.
3. In the sidecar, wrap the MCP tool surface in a small provider
   module (mirror `services/openbb_mcp_provider.py`) that translates
   MCP `call_tool` responses into the Vysted Pydantic shapes.
4. In the plugin entry, surface a `healthCheck()` that hits a sidecar
   `/<plugin>/status` endpoint reporting child-process health.

## Testing

- TypeScript-side: vitest. Test capability negotiation, lifecycle
  transitions, and any custom logic. `plugins/example/example.test.ts`
  is a starting point.
- Python-side (if your plugin has a sidecar component): pytest with
  monkeypatched providers. `sidecar/tests/test_openbb_mcp_provider.py`
  is a starting point.

The sidecar test suite mocks every external network call — no test
should hit a live API. Plugin authors should follow the same rule.

## Plugin patterns

By v0.6.5 four distinct plugin shapes have shipped in the repo, each
solving a different "how does Vysted talk to this thing" problem. New
plugin authors pick the closest pattern and adapt.

### 1. In-process data-source plugin (`plugins/example/`)

The simplest shape. The plugin's TypeScript entry imports a few utilities
and exposes a `DataSource`. No Python sidecar component, no subprocess.
Use this when your data source ships as a pure-JavaScript / NPM-installable
package, or when the data is computed locally.

### 2. Sidecar provider plugin (`plugins/openbb-mcp/`, retired Phase-2 `plugins/openbb/`)

The plugin's TypeScript entry is thin; the heavy lifting lives in a
sidecar service + router (`sidecar/services/<plugin>_provider.py` +
`sidecar/routers/<plugin>.py`) that exposes a typed REST surface. Use
this when the data source is a Python library or REST API the sidecar
can reach in-process.

### 3. MCP-subprocess plugin (`plugins/openbb-mcp/`, `plugins/sec-edgar-mcp/`)

When the upstream dependency conflicts with the main sidecar's pins
(the OpenBB case, the SEC EDGAR case), ship it as its own PyInstaller
`--onefile` binary under `sidecar/<plugin>_subprocess/`. Spawn via the
Tauri Rust core (`Command::new`) — **never via Python `subprocess.Popen`**
on Windows (CLAUDE.md Gotcha). The sidecar talks to it as an MCP client
via `sidecar/services/mcp_client.py`.

### 4. Trading-system wrapper plugin (`plugins/tradesa-v2/`, new in v0.6.5)

A first-class pattern for surfacing an external trading bot — your own
or a third party's — as a Vysted plugin. The wrapper is observation-only
by default (READ-ONLY); write capability is added later under §6.5
safety-layer review.

**Layout:**

```
plugins/<bot-id>/
  manifest.json                    # standard PluginManifest
  index.ts                         # VystedPlugin entry; declares panels +
                                   #   data + commands capabilities
  connection.ts                    # implements TradingBotReadAdapter
                                   #   interface against the bot's data
                                   #   surface (REST / Supabase / MCP / ...)
  store.ts                         # Zustand store: connection state +
                                   #   per-panel FetchState<T> + polling
                                   #   cadences
  useTradesaConnectionState.ts     # shared connection-state hook
  panels.ts                        # companion panel-components map
  components/
    BotStatusStrip.tsx             # always-visible header (mode, kill-switch,
                                   #   heartbeat age) every panel mounts
    <Panel1>.tsx ... <PanelN>.tsx  # one component per PanelSpec
  <bot>-v2.test.ts                 # Vitest: identity, capability negotiation,
                                   #   lifecycle, graceful-degradation mapping
```

**Sidecar side** (mirrors pattern 2):

```
sidecar/services/<bot>_provider.py # read-only wrapper over the bot's
                                   #   data surface; NO insert_/update_/
                                   #   delete_/upsert_ methods on the
                                   #   public API surface (audit-tested)
sidecar/routers/<bot>.py           # FastAPI router under /<bot>/*;
                                   #   every endpoint is GET only
                                   #   (audit-tested)
sidecar/models/<bot>.py            # Pydantic mirrors with
                                   #   ConfigDict(extra="forbid")
sidecar/tests/test_<bot>_provider.py
sidecar/tests/test_<bot>_router.py
```

**Defense-in-depth for read-only** (v0.6.5 enforces three layers):

1. **Provider** has no write methods on its public surface
   (`tests/test_<bot>_provider.py::test_no_write_methods_on_provider_surface`
   greps the class via `inspect.getmembers`).
2. **Router** has no non-GET routes (`tests/test_<bot>_router.py
::test_no_non_get_routes_under_<bot>_prefix` walks `router.routes`).
3. **Plugin contract** sets `supportsControlPlane=false` — the runtime
   refuses to call `executeCommand` even if the method existed.

**Credential flow** (mirror Phase 3 BYOK LLM pattern):

- Renderer reads the OS keychain via `src/lib/keychain.ts::getSecret`
  using `KEYCHAIN_NAMESPACES.pluginSecret(<plugin-id>, <secret-key>)`
  at plugin initialize.
- Frontend passes credentials in request headers on every fetch
  (`X-<Bot>-*`). Sidecar never reads keychain directly (only Tauri Rust
  can). Headers travel over 127.0.0.1 loopback only.
- Sidecar never logs, echoes, or persists the credentials beyond
  process memory.

**Graceful degradation** (every wrapper plugin must handle):

The wrapper exposes a `TradesaConnectionStatus`-shaped enum with at
least these six states:

- `healthy` — upstream reachable, bot heartbeat fresh
- `connecting` — initial probe in flight
- `unauthenticated` — no credentials in keychain
- `bot-offline` — upstream reachable but bot heartbeat is stale
- `<upstream>-error` — credentials or transport failure
- `partial` — some endpoints reachable, others not

Every panel renders dedicated UX for each state. The plugin never
crashes Vysted Terminal on an outage, never retries-loop, always
surfaces a clear reason the user can act on.

**Companion `panels.ts` glue:** plugins that contribute panels via
`getPanels()` ship a sibling `panels.ts` exporting
`Record<string, FunctionComponent>` (panel-id → component map). The
host's `src/lib/plugin-bootstrap.ts` reads it via `PLUGIN_COMPANIONS`
and merges into the synthesized `VystedModule`. The locked contract
(`types/plugin.ts`) stays serializable — no React types leak in.

**TauricResearch and future trading-system plugins** follow this exact
shape — write `connection.ts` against the bot's data surface, supply a
`panels.ts` and per-panel components, declare the same capability flags,
register in `BUNDLED_PLUGINS` + `PLUGIN_COMPANIONS`. The whole pattern
is contract-stable; new wrappers add zero pressure to `types/plugin.ts`.

## Roadmap

These are out of scope for v0.3.0 but on the BLUEPRINT:

- Filesystem-installed plugins (drop-in `plugins/<id>/` outside the
  repo at runtime).
- Signed plugins.
- An online plugin marketplace (v2.0+).
- Phase 3 will add agent / node-editor consumers for the
  `usePluginsStore` registries that this phase wires but does not yet
  display.
- A future Tauri-spawned subprocess pattern (Rust `Command::new`) to
  resolve the OpenBB Windows hang documented in BLOCKERS.md.

If you're authoring a plugin against v0.3.0 and these limits matter to
you, file a `Tier-4` request via an issue — extending the contract is a
high-blast-radius decision and goes through the operator (per CLAUDE.md
"Decision authority").
