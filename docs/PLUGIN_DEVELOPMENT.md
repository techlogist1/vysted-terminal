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
- Two reference plugins — `plugins/example/` and `plugins/openbb/` —
  exercise the contract end-to-end and are the best starting point for
  reading.
- Bundled-import loading — plugins ship under `plugins/<id>/` in the
  repo. Filesystem-installed plugins, signing, and a marketplace are
  out of scope until v1.0+.

## File layout

A plugin lives in `plugins/<plugin-id>/`:

```
plugins/openbb/
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
   `<plugin>/subprocess/`, packaged as a separate PyInstaller
   `--onefile` binary by `scripts/ensure-<plugin>-sidecar.mjs` (mirror
   `ensure-sidecar.mjs`). The main Vysted sidecar lazy-launches the
   subprocess on first request and proxies HTTP through it.

The OpenBB plugin (`plugins/openbb/` + `sidecar/openbb_subprocess/`) is
the reference for the separate-process pattern. Read its CHANGELOG
v0.3.0 entry, BLOCKERS.md, and the subprocess `main.py` for the full
walk-through, including the known Windows `subprocess.Popen` issue and
its Phase-3 fix candidates.

## Testing

- TypeScript-side: vitest. Test capability negotiation, lifecycle
  transitions, and any custom logic. `plugins/example/example.test.ts`
  is a starting point.
- Python-side (if your plugin has a sidecar component): pytest with
  monkeypatched providers. `sidecar/tests/test_openbb_provider.py` is
  a starting point.

The sidecar test suite mocks every external network call — no test
should hit a live API. Plugin authors should follow the same rule.

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
