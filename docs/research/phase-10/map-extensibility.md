# Phase 10 — Extensibility / Customizability Surface Map

**Scope:** Map every extensibility, customizability, command-palette, and
data-connector surface in the Vysted Terminal monorepo for the "Cursor for
trading" customizability track. Document what exists, what is user-facing vs
developer-only, and where the gaps are for a build-your-own / sandboxable feel.
Every claim is cited to `file:line` against the actual source as of the working
tree at 2026-05-29 (HOST_VERSION 0.8.0).

`types/plugin.ts` is LOCKED — this report does not propose contract changes; it
documents how the contract is (and is not) wired into the host.

---

## 0. Executive summary

The platform has a **well-built developer-facing extension contract** (the six
capabilities in `types/plugin.ts`) and a **solid layout-customization layer**
(dockview + named workspaces + module toggles + cmd+K). But the chain from
"contract capability" → "thing the user can actually see and use" is **only
fully wired for 3 of the 6 capabilities**:

| Capability        | Collected by runtime                                       | Surfaced to user                                       | Status              |
| ----------------- | ---------------------------------------------------------- | ------------------------------------------------------ | ------------------- |
| **panels**        | yes (`collectPanels`) → `useModulesStore`                  | yes (dockview, via cmd+K command)                      | **wired**           |
| **commands**      | yes (`collectCommands`) → `useModulesStore`                | yes (cmd+K palette)                                    | **wired**           |
| **control plane** | yes (`executeCommand` via command handler)                 | yes (cmd+K)                                            | **wired**           |
| **nodes**         | yes (`collectNodes`) → `usePluginsStore.nodes`             | **partial** (node palette; double-render bug)          | **wired-but-buggy** |
| **data**          | yes (`collectDataSources`) → `usePluginsStore.dataSources` | **NO** — count only; no picker, no routing             | **dead-ends**       |
| **agents**        | yes (`collectAgents`) → `usePluginsStore.agents`           | **NO** — count only; chat picker reads sidecar instead | **dead-ends**       |

The `data` and `agents` registries are collected, stored, and counted but **have
no consumer that turns them into a usable feature**. This is a _known, documented_
deferral — `docs/PLUGIN_DEVELOPMENT.md:368-370` literally says "Phase 3 will add
agent / node-editor consumers for the `usePluginsStore` registries that this
phase wires but does not yet display." Node consumers shipped; data and agent
consumers never did.

For a "build-your-own / sandboxable" feel, the **three biggest gaps** are:

1. No data-connector routing — `DataSource` is registry-only; every panel
   hardcodes sidecar REST endpoints, so a plugin's data source can never feed a
   first-party panel.
2. No generic "add panel" gallery — panels are reachable **only** by a hand-
   authored cmd+K command per panel; `PanelSpec.defaultSize`/`icon` are dead
   metadata.
3. Plugin-contributed agents never reach the chat picker; broker execution
   plugins exist on disk but are not bundled/loaded.

---

## 1. The plugin contract (`types/plugin.ts`) — the six capabilities

The contract is the developer-facing extension surface. It is serializable by
design (no React types) — `types/plugin.ts:104-110` notes the `component` field
is a string id resolved host-side at mount.

- **Capability declaration** — `PluginCapabilities` (six booleans):
  `contributesData`, `contributesPanels`, `contributesCommands`,
  `contributesAgents`, `contributesNodes`, `supportsControlPlane`
  (`types/plugin.ts:59-66`).
- **data** → `DataSource` (`types/plugin.ts:76-87`): `id`, `label`, `kinds`
  (`DataSourceKind = equity|crypto|macro|news|fundamentals|custom`,
  `types/plugin.ts:73`), `realtime`, `description`. Getter `getDataSources()`
  (`types/plugin.ts:236`).
- **panels** → `PanelSpec` (`types/plugin.ts:94-111`): `id`, `title`, `icon?`,
  `defaultSize?`, `singleton?`, `component`. Getter `getPanels()`
  (`types/plugin.ts:239`).
- **commands** → `CommandSpec` (`types/plugin.ts:118-133`): `id`, `trigger`,
  `title`, `description?`, `icon?`, `commandId?`, `opensPanel?`. Getter
  `getCommands()` (`types/plugin.ts:242`).
- **agents** → `AgentSpec` (`types/plugin.ts:143-158`): `id`, `name`,
  `philosophy`, `systemPrompt`, `tools[]`, `defaultProvider`, `icon?`. Getter
  `getAgents()` (`types/plugin.ts:245`).
- **nodes** → `NodeSpec` (`types/plugin.ts:175-188`): `id`, `label`, `category`
  (`trigger|action|transform|condition|output`), `inputs`/`outputs`
  (`NodePort`), `description?`. Getter `getNodes()` (`types/plugin.ts:248`).
- **control plane** → `executeCommand(commandId, args): CommandResult`
  (`types/plugin.ts:254`) + real-time `subscribe(channel, cb): Unsubscribe`
  (`types/plugin.ts:251`).
- **Lifecycle** — `initialize(PluginConfig)` / `shutdown()` / `healthCheck()`
  (`types/plugin.ts:228-230`). `PluginConfig` (`types/plugin.ts:32-43`) hands
  the plugin a private `dataDir`, opaque `settings`, the `sidecarBaseUrl`, the
  `hostVersion`, and keychain-resolved `secrets`.

**Audience:** developer-only. There is no in-app UI to author a plugin; a plugin
is a TypeScript file under `plugins/<id>/` statically imported into the host
build (see §4).

---

## 2. The module registration system (in-app analogue of the contract)

First-party features ship as **`VystedModule`s**, the host-side analogue of the
plugin panel/command capabilities. A module reuses the locked `PanelSpec` /
`CommandSpec` and adds the two host-side concerns the serializable contract
omits: React components and command handlers.

- `VystedModule` shape (`src/lib/module-registry.ts:15-36`): `id`, `title`,
  `panels[]`, `commands[]`, `panelComponents` (`Record<string,
FunctionComponent>`), optional `commandHandlers`.
- Flatteners: `collectPanels` / `collectCommands` / `collectPanelComponents` /
  `collectCommandHandlers` (`src/lib/module-registry.ts:39-66`).
- The 19-module registry (`src/modules/index.ts:55-78`): chart, watchlist,
  news, portfolio, equity-overview, chat, platform, plugin-manager,
  agent-builder, node-editor, backtest, broker-connect, safety, macro, sec,
  quant, earnings, analyst-ratings, screener.
- The module store (`src/store/modules.ts:46-85`): holds modules + an `enabled`
  map; `registerModules` (all start enabled), `appendModules` (plugin runtime
  uses this — append-only, dedup by id, `src/store/modules.ts:54-73`),
  `setModuleEnabled`, `enabledPanels()`, `enabledCommands()`, `findPanel()`,
  `commandHandler()`.

**Key architectural point:** plugin panels/commands and first-party
panels/commands flow through the **same** store. `moduleForPlugin()`
(`src/lib/plugin-bootstrap.ts:188-241`) synthesizes a `VystedModule` from a
loaded plugin and appends it via `appendModules`. The store doc calls this out:
"there is no second registry the host has to special-case"
(`src/lib/plugin-bootstrap.ts:181-182`; `src/store/plugins.ts:22-24`).

---

## 3. Command palette (cmd+K) — the discovery surface

This is the most complete user-facing extensibility surface.

- **Component** — `src/components/CommandPalette.tsx`. Global `cmd/ctrl+K`
  listener toggles it (`CommandPalette.tsx:21-30`). Radix dialog + Framer
  Motion; an `<input>` with arrow-key navigation (it is **not** the `cmdk`
  library — it's a hand-rolled filtered list, `CommandPalette.tsx:61-148`).
- **Filtering** — case-insensitive substring on `command.title` OR
  `command.trigger` (`CommandPalette.tsx:70-80`). No fuzzy match, no grouping,
  no `description`-based search, no icon rendering.
- **State** — `useCommandPalette` (`src/store/command-palette.ts:20-26`): holds
  `open` + the aggregated `commands` list.
- **Execution** — `executeCommand()` (`src/lib/commands.ts:10-19`): if
  `command.opensPanel` → `useWorkspaceStore.openPanel(id)`; else if
  `command.commandId` → look up the control-plane handler via
  `useModulesStore.commandHandler(commandId)` and call it. Mirrors the two
  contract paths exactly.
- **Population + sync** — `src/app/page.tsx:24-64`. Seeded from
  `enabledCommands()` on mount, re-seeded after `bootstrapPlugins()` resolves,
  and kept live by two store subscriptions: one on the `enabled` slice (module
  toggle / workspace load) and one on the `modules` slice (plugin append). So a
  disabled module's commands disappear and a plugin's commands appear without a
  reload.

**Plugin → palette path is real:** `moduleForPlugin` collects the plugin's
`getCommands()` (`src/lib/plugin-bootstrap.ts:191-193`) and wires control-plane
handlers that fire-and-forget `executeCommand` (`plugin-bootstrap.ts:197-213`).
Tradesa V2 contributes 7 `opensPanel` commands (`plugins/tradesa-v2/index.ts:181-236`),
the example plugin one control-plane command (`plugins/example/index.ts:38-47`).

**Gap / smell:** the header "Open panel ⌘K" button (`src/app/page.tsx:84-95`)
implies a panel launcher, but it just opens the same command palette. There is
no dedicated panel gallery (see §6).

---

## 4. Plugin runtime + bootstrap (loader, lifecycle, persistence)

### 4.1 Bootstrap (`src/lib/plugin-bootstrap.ts`)

- **`BUNDLED_PLUGINS`** (`plugin-bootstrap.ts:45-49`) — the static discovery
  list. Exactly **3** plugins: `example`, `openbb-mcp`, `tradesa-v2`. New
  first-party plugins are appended here.
- **`PLUGIN_COMPANIONS`** (`plugin-bootstrap.ts:81-83`) — static map of
  plugin-id → `{ panelComponents }`. Only `tradesa-v2` has an entry. This is the
  host-side glue that binds React components to a plugin's `PanelSpec.component`
  ids without leaking React into the locked contract (documented at
  `plugin-bootstrap.ts:51-83`; CLAUDE.md "Plugin-companion panel-components map"
  gotcha). It is **static, not dynamic-import-by-id** — Next.js static export
  can't resolve runtime plugin-id dispatch (`plugin-bootstrap.ts:62-67`).
- **Persistence** — sidecar-backed via `/plugins/{id}/config`
  (`plugin-bootstrap.ts:99-139`; sidecar router `sidecar/routers/plugins.py`),
  with an in-memory fallback when run outside Tauri (`plugin-bootstrap.ts:148-176`).
- **`bootstrapPlugins()`** (`plugin-bootstrap.ts:251-304`) — builds the runtime,
  attaches it to `usePluginsStore`, loads every bundled plugin, bridges
  panels/commands into `useModulesStore`, starts a 30s health-check loop.

### 4.2 Runtime (`src/lib/plugin-runtime.ts`)

- Lifecycle supervisor with states `discovered → initializing → active →
stopping → stopped` (+ `error`); capability negotiation **by flag, not method
  shape** (`plugin-runtime.ts:10-24, 259-286`). A flag set without its getter
  emits an `errored` event but doesn't crash the plugin.
- **Capability aggregators** (`plugin-runtime.ts:288-331`): `collectDataSources`,
  `collectPanels`, `collectCommands`, `collectAgents`, `collectNodes` — each
  walks active plugins and calls the getter only when the flag is set.
- Health rollover (20 samples, `plugin-runtime.ts:53, 342-373`); pure TypeScript,
  no Tauri invoke (`plugin-runtime.ts:117-119`).

### 4.3 Plugin store (`src/store/plugins.ts`)

- Projects the runtime into React: `plugins`, `dataSources`, `agents`, `nodes`
  (`plugins.ts:30-78`). Re-pulls on every runtime event.
- **The store's own doc admits the dead-ends** (`plugins.ts:14-20`): dataSources
  "Phase 3 surfaces these in the data-source picker"; agents "Phase 3 surfaces
  these in the AI chat sidebar"; nodes "Phase 4 surfaces these in the node
  editor palette." Only the node line came true.

### 4.4 Plugin Manager UI (`src/components/PluginManagerPanel.tsx`)

The only user-facing plugin surface. Lists loaded plugins with state, health
strip, metadata, enable/disable toggle (`PluginManagerPanel.tsx:20-163`). The
data/agents/nodes registries appear **only as a count string** —
`` `${dataSources.length} data sources · ${agents.length} agents · ${nodes.length}
nodes` `` (`PluginManagerPanel.tsx:37`). There is no drill-down, no per-source
detail, no enable-per-source.

---

## 5. Data-connector / data-source architecture — **the biggest gap**

**`DataSource` is a registry abstraction with zero runtime consumers.** It is
collected (`plugin-runtime.ts:289-295`), stored (`plugins.ts:32, 56, 73`), and
counted (`PluginManagerPanel.tsx:37`) — and that is the entire lifecycle.

- **No data-source picker** exists anywhere. The only string match for "picker"
  is the aspirational comment in `src/store/plugins.ts:15`. Phase 3 promised it
  (`docs/PLUGIN_DEVELOPMENT.md:368-370`); it never shipped.
- **No routing from `DataSource.id` to a fetch.** Panels fetch by calling
  hardcoded sidecar REST endpoints directly: the watchlist resolves equities
  through `/quotes` and crypto through `/crypto/ticker`
  (`src/modules/watchlist/api.ts:1-50`, via `sidecarApi.quotes` /
  `sidecarApi.cryptoTicker`). The `provider` is a server-side concern baked into
  the `Quote`/`OHLCVSeries` Pydantic models (`types/data.ts:21, 39`), not chosen
  by a `DataSource.id`. There is no indirection where a panel says "give me
  equity data from source X."
- **The sidecar owns the actual data layer**, exposed as ~24 typed REST routers
  (`sidecar/routers/`: quotes, history, indicators, fundamentals, news, macro,
  sec*filings, earnings, screener, quant, crypto, brokers, ...). These are the
  \_real* data connectors, but they are **first-party, compiled into the sidecar
  binary**, not pluggable at runtime.
- **Plugins that contribute data sources** (example: `example-prices`
  `plugins/example/index.ts:28-36`; openbb-mcp: equity/fundamentals/macro
  `plugins/openbb-mcp/index.ts:51-70`; tradesa-v2: `tradesa-v2-decisions` etc.
  `plugins/tradesa-v2/index.ts`; all 7 broker plugins) declare `DataSource`
  metadata, but a panel cannot consume any of it. The data flows, if at all,
  through the plugin's own panels hitting the plugin's own sidecar router (the
  "sidecar provider plugin" pattern, `docs/PLUGIN_DEVELOPMENT.md:247-253`), not
  through the `DataSource` registry.

**Implication for "Cursor for trading":** there is currently no way for a user to
say "use my Polygon key as the equity quote source" and have the chart/watchlist
pick it up. The data-connector story is "developer ships a new sidecar router +
a plugin panel," not "user wires a connector." The `DataSource` contract is
ready for it; the host plumbing is not.

---

## 6. Panel / layout customization primitives (BLUEPRINT §5.2)

This is the **strongest** customizability layer and it is genuinely user-facing.

### 6.1 What works

- **dockview layout engine** (`src/components/PanelHost.tsx`): drag-dock, split,
  tab-group, resize. `dragDropEnabled:false` in Tauri config makes HTML5 DnD work
  (CLAUDE.md gotcha). Components resolved from the merged module map
  (`PanelHost.tsx:29`).
- **Named workspaces** (`src/lib/workspace.ts`): save/load/delete/list to the
  sidecar `/workspace` endpoints. A workspace captures the dockview layout +ﾠthe
  modules `enabled` map + per-chart drawings (`workspace.ts:26-40, 55-90`).
  Surfaced in Settings → Layouts (`src/components/SettingsPanel.tsx:180-305`).
- **Autosave / restore-last-session** — reserved `__autosave__` slot, debounced
  1500ms, restored on launch with default-layout fallback
  (`workspace.ts:158-204`; `PanelHost.tsx:39-65`).
- **Module enable/disable** — Settings → Modules
  (`SettingsPanel.tsx:311-364`). A disabled module contributes no panels and no
  cmd+K commands (`modules.ts:77-82`). `platform` is locked on
  (`SettingsPanel.tsx:326, 350`).
- **Default first-launch layout** (`src/config/default-layout.ts`) — BLUEPRINT
  §5.1 cockpit, skips panels whose module is disabled.

### 6.2 Gaps vs BLUEPRINT §5.2 (`docs/BLUEPRINT.md:331-338`)

- **"pop-out to second window"** (§5.2 line 332) — not implemented. No
  multi-window code; dockview is single-host.
- **No "add panel" gallery.** Opening a panel requires a cmd+K command with
  `opensPanel` set. Every first-party module hand-authors a 1:1 panel-open
  command (verified: 17 modules each have `#panels == #opensPanel-commands`;
  quant 4/4, broker-connect 2/2). This means:
  - `PanelSpec.defaultSize` is **dead metadata** — `workspace.ts:46-71`
    `addPanel({id, component, title})` never passes width/height from it, and
    `PanelHost`/`default-layout` never read it. (Layout sizing is done via
    hardcoded fractions in `default-layout.ts`.)
  - `PanelSpec.icon` and `CommandSpec.icon` are **never rendered** — the command
    palette ignores `command.icon` entirely (`CommandPalette.tsx:128-143`).
  - A plugin author who forgets to also ship an `opensPanel` command produces a
    panel the user can never open (no menu lists it).
- **"Module-specific settings (chart timeframe defaults, color schemes per
  module)"** (§5.2 line 338) — not a general mechanism. Module state lives in
  per-module Zustand stores; there is no settings-schema surface a module/plugin
  declares to get a settings UI for free.
- **Workspace export/import as files** (§5.2 line 335) — partially: workspaces
  persist as sidecar JSON and the `SerializedWorkspace` shape is file-ready
  (`workspace.ts:26-40`), but there is no file-system import/export button in the
  UI; only sidecar-named save/load.

---

## 7. Screener / watchlist — user-facing data customization primitives

- **Screener criteria builder** (`src/modules/screener/ScreenerCriteriaBuilder.tsx`)
  — a genuine user-facing "build a query" surface. Discriminated-union criteria
  (numeric ops gt/lt/gte/lte/between, string-eq, set-in) AND-combined; add/remove
  rows; field menus over the `Fundamentals` columns
  (`ScreenerCriteriaBuilder.tsx:21-49, 270-300`). Contract in
  `types/screener.ts:48-92`. **Custom universe** = user-pasted ticker list
  (`types/screener.ts:16-34, 83-92`). Limitation: AND-only, no OR / nested
  grouping (`types/screener.ts:88`).
- **Watchlist** (`src/modules/watchlist/`) — user-editable symbol list in
  `useSymbolsStore` (`src/store/symbols.ts`); fetches live quotes via
  hardcoded `/quotes` + `/crypto/ticker` (`watchlist/api.ts`). Per §5, the
  source is fixed; the user customizes _what_ symbols, not _which provider_.

These are the closest thing to "sandboxable / build-your-own" today, but each is
a bespoke per-module UI, not a generic primitive.

---

## 8. Node editor (workflow composition) — partial plugin surface + a bug

- **Node registry** (`src/modules/node-editor/node-registry.ts`): 10 built-in
  node types (`BUILT_IN_NODE_IDS`, lines 52-63) defined as `NodeSpec` so plugin
  nodes drop in without a shape diff. `buildRegistry(pluginNodes)` unions
  built-ins with plugin nodes, dropping id-collisions in favor of built-ins
  (`node-registry.ts:298-308`).
- **Config-form schema** is a host-side companion (`BUILT_IN_NODE_CONFIG_FIELDS`,
  `node-registry.ts:173-267`) — deliberately NOT on `NodeSpec` because the
  contract must stay wire-serializable (`node-registry.ts:14-19`). **Plugin
  nodes fall back to a free-form key/value editor** (`node-registry.ts:316-330`)
  — so a plugin node works but gets a worse authoring UX than a built-in.
- **Plugin nodes ARE consumed** — `usePluginsStore.nodes` →
  `buildRegistry` → palette + canvas renderer
  (`NodeEditorPanel.tsx:113-114`; `VystedNode.tsx:23`). This is the one deferred
  registry that got its consumer.

### 8.1 BUG — node palette double-renders plugin nodes (medium)

`src/modules/node-editor/node-palette.tsx`: `groupByCategory(registry)` already
includes plugin entries (since `buildRegistry` returns them), so plugin nodes
render as proper **draggable** `PaletteCard`s inside their category section
(`node-palette.tsx:44, 57-78`, card at line 73). Then lines **79-94** render a
_second_ "Plugin Nodes" section mapping `pluginEntries` to bare, **non-draggable**
`<span>` labels that show only `entry.pluginId` — no label, no drag handler, no
`PaletteCard`. Result: every plugin node appears twice (once usable, once a
dead duplicate). The second section looks like an unfinished stub.

---

## 9. AI agents — authoring surface vs plugin dead-end

Two distinct agent surfaces, only one of which is wired to plugins:

- **Custom Agent Builder** (`src/modules/agent-builder/`, BLUEPRINT Module 36) —
  the real user-facing "build your own agent without code" surface. Form for
  id/name/philosophy/systemPrompt/tools/provider; sidecar-backed SQLite via
  `agents_store`; ids prefixed `custom:`. Unioned into the chat picker through
  `GET /custom-agents` (`src/modules/agent-builder/index.ts:5-49`;
  `src/store/agents.ts:1-30, 142-161`).
- **Chat sidebar agent picker** reads **`useAgentsStore`** — i.e. sidecar
  `/agents` (first-party JSON configs) + `/custom-agents` (builder output)
  (`src/modules/chat/ChatSidebar.tsx:10, 323-332`; `src/store/agents.ts:7-13`).
- **DEAD-END:** `usePluginsStore.agents` (the `collectAgents` registry) is **not
  merged into the chat picker or the agents store** — verified by grep: nothing
  references `state.agents`/`collectAgents` in `chat/`, `agent-builder/`, or
  `store/agents.ts`. A plugin can declare `contributesAgents:true` and ship an
  `AgentSpec`, and the runtime will collect it, but the user will never see it in
  chat. Tradesa V2 explicitly keeps `contributesAgents:false` because of this
  ("chat-sidebar integration risk... v0.6.6+ scope",
  `plugins/tradesa-v2/index.ts:68-73`).

---

## 10. MCP integration — the orthogonal extensibility axis

`docs/PLUGIN_DEVELOPMENT.md:192-220` + `docs/MCP_INTEGRATION.md`:

- **Vysted as MCP server** — sidecar exposes data + agents as MCP tools at
  `/mcp` (Streamable-HTTP). External clients (Claude Desktop/Code) can drive
  Vysted. This is real extensibility _outward_ but not user-configurable in-app.
- **Vysted as MCP client** — `sidecar/services/mcp_client.py`; the `openbb-mcp`
  plugin is the reference consumer. Adding an MCP data source is a
  developer task (new Rust spawn helper + sidecar provider), not a user one.

---

## 11. Bundling / distribution gaps (developer-facing)

- **Broker execution plugins are written but NOT loaded.** `plugins/brokers/`
  contains alpaca, angelone, ccxt-exec, dhan, ib, kite, oanda — all implementing
  `getDataSources()` etc. — but **none are in `BUNDLED_PLUGINS`**
  (`plugin-bootstrap.ts:45-49` lists only example/openbb-mcp/tradesa-v2).
  Verified by grep: no broker import in `plugin-bootstrap.ts`. The v1.0 §6.5
  broker execution surface exists on disk but is not wired into the host runtime
  in this working tree. (They may be loaded by a path not yet present, or gated
  for a later phase — but as of this tree they are dead code from the host's POV.)
- **No filesystem-installed / signed / marketplace plugins.** All plugins are
  statically compiled into the host build (`docs/PLUGIN_DEVELOPMENT.md:23-25,
360-372`). There is **no runtime sandbox** — a plugin is in-process TypeScript
  with full host access. "Sandboxable" in the product positioning currently means
  _layout sandbox_, not _code sandbox_. For a true "Cursor for trading" plugin
  ecosystem (untrusted third-party plugins), there is no isolation boundary,
  capability-scoping enforcement at runtime, or signature verification.

---

## 12. What is user-facing vs developer-only (summary table)

| Surface                                 | User-facing?                  | Where                                      |
| --------------------------------------- | ----------------------------- | ------------------------------------------ |
| cmd+K command palette                   | **User**                      | `CommandPalette.tsx`, header `page.tsx:84` |
| dockview drag/split/tab/resize          | **User**                      | `PanelHost.tsx`                            |
| Named workspaces (save/load/reset)      | **User**                      | Settings → Layouts                         |
| Module enable/disable                   | **User**                      | Settings → Modules                         |
| BYOK provider keys (keychain)           | **User**                      | Settings → AI Providers                    |
| Screener criteria builder               | **User**                      | `ScreenerCriteriaBuilder.tsx`              |
| Custom Agent Builder                    | **User**                      | `agent-builder` module                     |
| Watchlist symbol editing                | **User**                      | `watchlist` module                         |
| Node editor (built-in nodes)            | **User**                      | `node-editor` module                       |
| Plugin Manager (enable/disable, health) | **User (read-mostly)**        | `PluginManagerPanel.tsx`                   |
| Writing a plugin (`VystedPlugin`)       | **Developer**                 | `plugins/<id>/`, static import             |
| Data-source registration                | **Developer (and dead-ends)** | `getDataSources()` → count only            |
| Plugin agent registration               | **Developer (and dead-ends)** | `getAgents()` → count only                 |
| Sidecar data routers / MCP connectors   | **Developer**                 | `sidecar/routers/`, `mcp_client.py`        |
| Pop-out second window                   | **Not implemented**           | —                                          |
| Add-panel gallery                       | **Not implemented**           | —                                          |
| Workspace file import/export            | **Not implemented (UI)**      | shape ready in `workspace.ts`              |

---

## 13. Prioritized gaps for the "build-your-own / sandboxable" track

1. **Data-connector routing (highest leverage).** Make `DataSource` real: a
   resolver that maps a `DataSource.id` to a fetch, a picker UI in Settings/
   plugin-manager, and a per-data-kind "active source" selection that
   first-party panels honor. Today `DataSource` is inert metadata
   (§5). Contract is ready (`types/plugin.ts:76-87`); no contract change needed.
2. **Generic "add panel" gallery.** Surface `enabledPanels()` with
   `PanelSpec.title`/`icon`/`defaultSize` in a real launcher (the header "Open
   panel" button is the natural home). Wire `defaultSize` into
   `workspace.openPanel`'s `addPanel` call. Removes the hand-authored 1:1 panel-
   open command boilerplate and revives 2 dead contract fields (§6.2).
3. **Surface plugin agents in chat.** Merge `usePluginsStore.agents` into the
   chat picker (a third optgroup beside first-party/custom). Known v0.6.6+
   deferral (§9; `plugins/tradesa-v2/index.ts:68-73`).
4. **Fix node-palette double-render bug** (§8.1) — delete the redundant
   non-draggable "Plugin Nodes" section in `node-palette.tsx:79-94`.
5. **Plugin settings-schema surface.** A declarative per-plugin/per-module
   settings form (the contract already hands plugins opaque `settings`, but
   there's no UI to edit them — `PluginConfig.settings` is write-by-sidecar-only).
6. **Sandbox / trust boundary** for the eventual third-party ecosystem
   (filesystem-installed, signed, capability-enforced-at-runtime plugins) — all
   roadmap, none present (§11; `docs/PLUGIN_DEVELOPMENT.md:360-372`).
7. **Wire (or explicitly gate) the broker execution plugins** — they exist on
   disk but aren't bundled (§11).

---

## Appendix — files read

`types/plugin.ts`, `types/data.ts`, `types/screener.ts`,
`src/lib/plugin-bootstrap.ts`, `src/lib/plugin-runtime.ts`,
`src/lib/module-registry.ts`, `src/lib/commands.ts`, `src/lib/workspace.ts`,
`src/store/modules.ts`, `src/store/plugins.ts`, `src/store/command-palette.ts`,
`src/store/workspace.ts`, `src/store/agents.ts`, `src/components/CommandPalette.tsx`,
`src/components/PluginManagerPanel.tsx`, `src/components/SettingsPanel.tsx`,
`src/components/PanelHost.tsx`, `src/app/page.tsx`, `src/config/default-layout.ts`,
`src/modules/index.ts`, `src/modules/platform/index.ts`,
`src/modules/agent-builder/index.ts`, `src/modules/node-editor/node-registry.ts`,
`src/modules/node-editor/node-palette.tsx`,
`src/modules/screener/ScreenerCriteriaBuilder.tsx`,
`src/modules/watchlist/api.ts`, `plugins/example/index.ts`,
`plugins/openbb-mcp/index.ts`, `plugins/tradesa-v2/index.ts`,
`docs/PLUGIN_DEVELOPMENT.md`, `docs/BLUEPRINT.md` §5/§4 customization.
