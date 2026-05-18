# Phase 8 Plugin Audit — T4 (plugin contract + runtime)

**Date:** 2026-05-18
**Baseline:** v0.7.0 (commit 947d297)
**Auditor:** Sonnet 4.6 (teammate t4-plugin)
**Branch:** worktree-agent-t4-plugin

## Severity scheme

| Level | Meaning |
|-------|---------|
| S1 | Tier-1 contract violation; runtime crash on plugin load; malformed manifest accepted silently |
| S2 | Plugin imports from host-private surface (`src/lib/`, `src/store/`, `src/components/`); React warnings on mount; hot-reload state loss |
| S3 | Companion-module wiring gap; manifest validation accepts malformed-but-non-load-bearing field; CommandSpec `commandId` collision risk |
| S4 | Cosmetic |

## Scope

Plugins audited:
- `plugins/example/`
- `plugins/openbb-mcp/`
- `plugins/tradesa-v2/`
- `plugins/brokers/alpaca/`
- `plugins/brokers/angelone/`
- `plugins/brokers/ccxt-exec/`
- `plugins/brokers/dhan/`
- `plugins/brokers/ib/`
- `plugins/brokers/kite/`
- `plugins/brokers/oanda/`

Key files read:
- `types/plugin.ts` (Tier-1 locked contract — READ-ONLY for this audit)
- `src/lib/plugin-bootstrap.ts` (BUNDLED_PLUGINS + PLUGIN_COMPANIONS)
- `src/lib/plugin-runtime.ts` (PluginRuntime supervisor)
- `types/plugin-runtime.ts` (PluginManifest schema)
- `src/lib/keychain.ts` + `src/lib/sidecar-client.ts` (host-private surfaces)

---

## Part A — Plugin contract usage (grep audit)

### Grep methodology

Two grep passes over all `.ts` and `.tsx` files under `plugins/`:

1. Pattern: `from\s+["'].*src/(lib|store|components|modules)` — catches relative
   or absolute path reach-arounds into the host source tree.
2. Pattern: `from\s+["']@/` — catches tsconfig path-alias reach-arounds
   (the `@/` alias maps to `src/`).

**Result of pass 1:** Zero matches.

**Result of pass 2:** Two matches:

```
plugins/tradesa-v2/connection.ts:20: import { KEYCHAIN_NAMESPACES, getSecret } from "@/lib/keychain";
plugins/tradesa-v2/connection.ts:21: import { getSidecarBaseUrl, SidecarError } from "@/lib/sidecar-client";
plugins/tradesa-v2/components/TradesaSettingsDialog.tsx:25: import { setSecret } from "@/lib/keychain";
```

Both live inside the `tradesa-v2` plugin. No other plugin imports from host-private surfaces.

---

### Finding T4-connection-keychain: tradesa-v2/connection.ts imports from host-private surfaces [S2] [status: open]

**Plugin:** tradesa-v2
**Part:** A grep
**Repro:**
```
grep -r "@/lib/keychain\|@/lib/sidecar-client" plugins/
```
**Impact:** `plugins/tradesa-v2/connection.ts` imports `KEYCHAIN_NAMESPACES` and `getSecret`
from `@/lib/keychain` and `getSidecarBaseUrl` + `SidecarError` from `@/lib/sidecar-client`.
Both are host-private modules under `src/lib/`. The plugin contract (`types/plugin.ts`) requires
that plugins depend only on the contract types and their own files. Importing host-private
modules creates a compile-time coupling: if the host restructures `src/lib/keychain.ts` or
`src/lib/sidecar-client.ts`, the plugin breaks silently. In a future filesystem-installed plugin
scenario these imports would fail entirely at load time (the host bundle is not in the plugin's
module graph).

**Allowed-exception analysis:** The CLAUDE.md gotcha for companion panels says:
"Imports from `src/lib/<host-private>` like `sidecar-client.ts`, `plugin-bootstrap.ts` are NOT
fine." This import is in `connection.ts`, NOT in `panels.ts`; therefore the companion-file
exception does not apply. The import is a genuine S2 finding.

**Suggested fix:** The correct pattern (established by the broker plugins in `plugins/brokers/`)
is to receive `sidecarBaseUrl` from `PluginConfig.sidecarBaseUrl` at `initialize()` time and
store it in module-local state, then build all URLs from that stored value. For keychain access:
the plugin should request its secrets via `PluginConfig.secrets` (the granted-secret mechanism
already exists in the contract — `PluginConfig.secrets: Record<string, string>`). The `connection.ts`
adapter would then read `config.secrets["supabase-url"]` and `config.secrets["supabase-service-role-key"]`
rather than calling `getSecret` directly. This change requires no contract edit.

**Files:**
- `plugins/tradesa-v2/connection.ts:20-21`

---

### Finding T4-settings-dialog-keychain: tradesa-v2 TradesaSettingsDialog imports setSecret from host-private surface [S2] [status: open]

**Plugin:** tradesa-v2
**Part:** A grep
**Repro:**
```
grep -r "@/lib/keychain" plugins/tradesa-v2/components/
```
**Impact:** `TradesaSettingsDialog.tsx` imports `setSecret` from `@/lib/keychain` to persist
Supabase credentials to the OS keychain. This is the same S2 category: direct dependency on a
host-private module. The dialog is part of the plugin's panel layer (a `FunctionComponent`
exported via `panels.ts`) and should not reach into `src/lib/`.

**Suggested fix:** The `TradesaSettingsDialog` should call a plugin-owned settings API (e.g.
the existing `usePluginsStore` path via `PluginConfig.settings` save, or a dedicated
`saveCredentials(url, key)` function in `connection.ts` that the plugin's `executeCommand`
routes). However, since the plugin has `supportsControlPlane: false`, the correct approach for
v0.6.6+ write scope is to surface a `saveCredentials` command behind a `supportsControlPlane: true`
capability, with the dialog calling `onSave(url, key)` as a prop callback rather than calling
`setSecret` directly. For now (v0.6.5 read-only scope) the minimal fix is to have the dialog
call a function in `connection.ts` that owns the keychain calls — keeping the `@/lib` import
in one file (`connection.ts`) rather than two. That is a partial improvement only; the full fix
is the granted-secret mechanism described in T4-connection-keychain.

**Files:**
- `plugins/tradesa-v2/components/TradesaSettingsDialog.tsx:25`

---

### Finding T4-ccxt-executecommand-dead: ccxt-exec declares supportsControlPlane=false but implements executeCommand [S3] [status: open]

**Plugin:** brokers/ccxt-exec
**Part:** A grep (static analysis)
**Repro:** Read `plugins/brokers/ccxt-exec/index.ts` lines 65-73 (capabilities) + line 209
(executeCommand implementation).
**Impact:** The plugin sets `supportsControlPlane: false` but defines an `executeCommand` method
that handles `"ccxt-exec.halt-all"`. The `moduleForPlugin` function in `plugin-bootstrap.ts`
builds `commandHandlers` only when `supportsControlPlane` is true (line 198-213 of
`plugin-bootstrap.ts`). With `supportsControlPlane: false`, no handler is registered for
`ccxt-exec.halt-all` — the cmd+K palette can display the command (from `getCommands()`) but
pressing it will not invoke `executeCommand`. The halt-all command is silently dead.

**Note:** The plugin comment says "supportsControlPlane stays false until Teammate S exposes
the sidecar commands publicly" — this is intentional as of v0.5.0. However the command is
already defined in `getCommands()` and will appear in the palette. If a user triggers it,
nothing happens (the bootstrap does not route it). This is a user-visible bug: command appears
but never fires.

**Suggested fix:** Either (a) remove the `"ccxt-exec.halt-all"` entry from `getCommands()`
until `supportsControlPlane` flips to `true`, or (b) flip `supportsControlPlane` to `true` now
since `executeCommand` is already implemented and routes only the narrow halt-all path.

**Files:**
- `plugins/brokers/ccxt-exec/index.ts:65-74` (capabilities)
- `plugins/brokers/ccxt-exec/index.ts:96-113` (halt-all command)
- `plugins/brokers/ccxt-exec/index.ts:209-240` (executeCommand)
- `src/lib/plugin-bootstrap.ts:198-213` (commandHandlers gate)

---

### Finding T4-bare-commandids: angelone/kite/dhan use un-namespaced commandIds — collision risk [S3] [status: open]

**Plugin:** brokers/angelone, brokers/kite, brokers/dhan
**Part:** A grep (static analysis)
**Repro:** Grep `commandId:` across `plugins/brokers/` — angelone uses `"connect"`, `"account"`,
`"halt-trading"`; kite uses `"connect"`, `"account"`, `"halt-trading"`, `"static-ip-status"`;
dhan uses `"connect"`, `"account"`, `"halt-trading"`.
**Impact:** Three broker plugins use bare, un-namespaced `commandId` values. The other four
(alpaca, ib, oanda, ccxt-exec) use properly namespaced ids like `"alpaca.connect"`,
`"ib.account"`, etc. If/when these broker plugins are all loaded simultaneously (once they are
added to `BUNDLED_PLUGINS`), the runtime's command-dispatch loop in `plugin-bootstrap.ts`
would build a `commandHandlers` map keyed by `commandId`. With three plugins all declaring
`commandId: "connect"`, only the last one's handler would survive (the map overwrites). The
`executeCommand` dispatch on each plugin is internally correct (the plugin routes on its own
id space), but the bootstrap's `commandHandlers` map is host-wide.

**Suggested fix:** Namespace the commandIds: `"angelone.connect"`, `"kite.connect"`,
`"dhan.connect"`, etc. — matching the pattern established by alpaca, ib, and oanda.

**Files:**
- `plugins/brokers/angelone/index.ts:57,65,73`
- `plugins/brokers/kite/index.ts:74,82,90,98`
- `plugins/brokers/dhan/index.ts:72,80,88`

---

### Per-plugin Part A summary

| Plugin | Imports from src/lib or src/store or src/components | Contract shape | Notes |
|--------|-----------------------------------------------------|---------------|-------|
| example | None | Correct | Clean |
| openbb-mcp | None | Correct | Clean |
| tradesa-v2 | **YES** — connection.ts + TradesaSettingsDialog.tsx | Correct | T4-connection-keychain + T4-settings-dialog-keychain |
| brokers/alpaca | None | Correct | Clean |
| brokers/angelone | None | Correct | Bare commandIds (T4-bare-commandids) |
| brokers/ccxt-exec | None | Correct | supportsControlPlane/executeCommand mismatch (T4-ccxt-executecommand-dead) |
| brokers/dhan | None | Correct | Bare commandIds (T4-bare-commandids) |
| brokers/ib | None | Correct | Clean |
| brokers/kite | None | Correct | Bare commandIds (T4-bare-commandids) |
| brokers/oanda | None | Correct | Clean |

**Part A counts:** S2: 2 findings (tradesa-v2). S3: 2 findings (ccxt-exec, angelone/kite/dhan grouped). S1: 0.

**Worst offender:** tradesa-v2 — two S2 host-private-import findings in `connection.ts` and
`TradesaSettingsDialog.tsx`. Both are intentional couplings that work today but create
fragile host dependency. The `connection.ts` coupling is the more structurally significant one
because it bypasses the granted-secret mechanism the contract already provides for.

---

## Part B — Plugin runtime verification

### B.1 Load via runtime bootstrap

#### `moduleForPlugin` trace (static analysis)

The `moduleForPlugin` function at `src/lib/plugin-bootstrap.ts:188` does the following per plugin:

1. Reads `instance.capabilities.contributesPanels` → calls `getPanels()` if true.
2. Reads `instance.capabilities.contributesCommands` → calls `getCommands()` if true.
3. Returns `null` if both `panels` and `commands` are empty (plugin not added to modules store).
4. Builds `commandHandlers` only when `supportsControlPlane && executeCommand` are both truthy.
5. Looks up `PLUGIN_COMPANIONS[manifest.id]` for panel components.

**example plugin:** `contributesPanels: false`, `contributesCommands: true` → has commands → non-null
module. `supportsControlPlane: true` and `executeCommand` is defined → commandHandlers built for
`"example.hello"`. No panels → `PLUGIN_COMPANIONS` lookup returns undefined gracefully. **PASS.**

**openbb-mcp plugin:** `contributesPanels: false`, `contributesCommands: false` → both empty →
`moduleForPlugin` returns `null`. Plugin is loaded into the runtime (health-checked) but does
not contribute a module. **PASS** — this is the expected behavior for a pure data-source plugin.

**tradesa-v2 plugin:** `contributesPanels: true`, `contributesCommands: true` → both non-empty →
non-null module. `supportsControlPlane: false` → `commandHandlers` NOT built (commands open panels
via `opensPanel`, not via commandId, so this is correct for this plugin's usage). `PLUGIN_COMPANIONS["tradesa-v2"]`
exists → `panelComponents` map populated. **PASS.**

**Broker plugins (all 7):** These are NOT in `BUNDLED_PLUGINS` — they exist as standalone
plugin modules under `plugins/brokers/` but are never imported by `plugin-bootstrap.ts`. They
will not load, health-check, or contribute capabilities at runtime. This is noted as a
separate finding below.

---

### Finding T4-brokers-not-registered: All 7 broker plugins are absent from BUNDLED_PLUGINS [S2] [status: open]

**Plugin:** brokers/alpaca, brokers/angelone, brokers/ccxt-exec, brokers/dhan, brokers/ib, brokers/kite, brokers/oanda
**Part:** B runtime
**Repro:** Read `src/lib/plugin-bootstrap.ts` lines 45-49 — `BUNDLED_PLUGINS` contains only
`example`, `openbb-mcp`, and `tradesa-v2`. No broker plugin is imported or registered.
**Impact:** All 7 broker execution plugins (Phase 5 deliverables) are unreachable at runtime.
Their `initialize()` is never called, their data sources never registered, their cmd+K commands
never appear in the palette. The `executeCommand` safety-layer routing (propose → confirm)
built in v0.5.0 is fully functional in the sidecar, but the host-side plugin layer for it is
disconnected.

This is likely an intentional phase-boundary decision (broker plugins may be gated behind
a broker-connect UI that loads them on demand), but there is no comment in `plugin-bootstrap.ts`
explaining the omission, and the broker plugin manifests declare
`"requiredHostVersion": ">=0.5.0"` suggesting they were intended to be active. Classifying
as S2 because the broker panels/commands are silently absent with no boot-time warning.

**Suggested fix:** Either add all 7 broker plugins to `BUNDLED_PLUGINS` (following the same
static-import pattern as the three existing entries), or add an explanatory comment in
`plugin-bootstrap.ts` documenting that broker plugins are deferred to a future dynamic-load
path and should not be expected in the modules store. If the plugins are intended to be active,
they should also be verified they have no companion panels to add to `PLUGIN_COMPANIONS`.

**Files:**
- `src/lib/plugin-bootstrap.ts:44-49` (BUNDLED_PLUGINS)
- `plugins/brokers/*/index.ts` (all 7, none imported)

---

### B.2 Panel mount verification

#### tradesa-v2 panel component round-trip

`plugins/tradesa-v2/index.ts` declares 7 panels with these `component` ids:

| PanelSpec.id | PanelSpec.component |
|---|---|
| tradesa-v2.positions | tradesa-v2-positions |
| tradesa-v2.trade-history | tradesa-v2-trade-history |
| tradesa-v2.brain | tradesa-v2-brain |
| tradesa-v2.sentinel | tradesa-v2-sentinel |
| tradesa-v2.health | tradesa-v2-health |
| tradesa-v2.settings | tradesa-v2-settings |
| tradesa-v2.meta-agents | tradesa-v2-meta-agents |

`plugins/tradesa-v2/panels.ts` exports `panelComponents` with keys:

| Key in panelComponents | Component |
|---|---|
| tradesa-v2-positions | PositionsPanel |
| tradesa-v2-trade-history | TradeHistoryPanel |
| tradesa-v2-brain | BrainDecisionsPanel |
| tradesa-v2-sentinel | SentinelPanel |
| tradesa-v2-health | HealthPanel |
| tradesa-v2-settings | SettingsPanel |
| tradesa-v2-meta-agents | MetaAgentsPanel |

**Result: 7/7 component ids match.** Every `PanelSpec.component` id has a corresponding
`FunctionComponent` entry in `panels.ts`. No missing entries; no stale entries.

#### example + openbb-mcp panel mount

Neither contributes panels (`contributesPanels: false`). No panel component wiring required.

#### Broker plugins

Not in `BUNDLED_PLUGINS` — panel mount analysis not applicable (also, none contribute panels;
`contributesPanels: false` for all 7).

---

### B.3 Manifest validation

The `PluginManifest` interface (`types/plugin-runtime.ts`) defines these required fields:
`id`, `version`, `name`, `entry`, `requiredHostVersion`; optional: `description`, `author`, `homepage`.

#### example

`manifest.json`:
- `id: "vysted-example"` — matches `pluginId` in `index.ts`. **PASS.**
- `version: "0.1.0"` — matches `version` in `index.ts`. **PASS.**
- `name: "Vysted Example Plugin"` — matches `pluginName`. **PASS.**
- All required fields present. **PASS.**

#### openbb-mcp

`manifest.json`:
- `id: "openbb-mcp"` — matches `pluginId: "openbb-mcp"` in `index.ts`. **PASS.**
- `version: "0.1.0"` — matches. **PASS.**
- All required fields present. **PASS.**

#### tradesa-v2

`manifest.json`:
- `id: "tradesa-v2"` — matches `pluginId: "tradesa-v2"` (via `PLUGIN_ID` constant). **PASS.**
- `version: "0.1.0"` — matches. **PASS.**
- All required fields present. **PASS.**
- `PLUGIN_COMPANIONS["tradesa-v2"]` key matches `manifest.id`. **PASS.**

#### brokers/alpaca

`manifest.json`:
- `id: "broker-alpaca"` — matches `pluginId: "broker-alpaca"`. **PASS.**
- Version matches. **PASS.**

#### brokers/angelone

`manifest.json`:
- `id: "vysted-angelone"` — matches `pluginId: "vysted-angelone"`. **PASS.**

#### brokers/ccxt-exec

`manifest.json`:
- `id: "ccxt-exec"` — matches `pluginId: "ccxt-exec"`. **PASS.**

#### brokers/dhan

`manifest.json`:
- `id: "vysted-dhan"` — matches `pluginId: "vysted-dhan"`. **PASS.**

#### brokers/ib

`manifest.json`:
- `id: "broker-ib"` — matches `pluginId: "broker-ib"`. **PASS.**

#### brokers/kite

`manifest.json`:
- `id: "vysted-kite"` — matches `pluginId: "vysted-kite"`. **PASS.**
- Contains an extra field `"requiresStaticIp": true` not in `PluginManifest` interface.
  See finding below.

#### brokers/oanda

`manifest.json`:
- `id: "broker-oanda"` — matches `pluginId: "broker-oanda"`. **PASS.**

---

### Finding T4-kite-manifest-unknown-field: kite manifest.json contains non-schema field requiresStaticIp [S3] [status: open]

**Plugin:** brokers/kite
**Part:** B manifest validation
**Repro:** Read `plugins/brokers/kite/manifest.json` line 11: `"requiresStaticIp": true`.
**Impact:** `PluginManifest` in `types/plugin-runtime.ts` has no `requiresStaticIp` field. The
bootstrap imports the manifest `as PluginManifest` (if/when this plugin is added to BUNDLED_PLUGINS)
which will compile fine (TypeScript widens the JSON import) but the field is invisible to any
manifest-driven logic. The SEBI static-IP enforcement is implemented as a React component
(`kite-static-ip-banner.tsx` in `src/modules/`) rather than through the manifest, so the field
is currently decorative. However it creates drift between the manifest schema and the stored
JSON — future manifest-validation code might reject unknown fields.

**Suggested fix:** Either add `requiresStaticIp?: boolean` to `PluginManifest` in
`types/plugin-runtime.ts` (Tier-2/3 decision, no contract change needed) or remove the field
from `manifest.json` since the enforcement lives in the component layer. Given the schema is
not Tier-1 locked (only `types/plugin.ts` is), the extension is safe.

**Files:**
- `plugins/brokers/kite/manifest.json:11`
- `types/plugin-runtime.ts:26-43`

---

### B.4 Companion-module map verification

`PLUGIN_COMPANIONS` in `src/lib/plugin-bootstrap.ts:81-83`:

```typescript
const PLUGIN_COMPANIONS: Record<string, { panelComponents: Record<string, FunctionComponent> }> = {
  "tradesa-v2": { panelComponents: tradesaPanelComponents },
};
```

Plugin audit against this map:

| Plugin | contributesPanels | In PLUGIN_COMPANIONS | Status |
|--------|------------------|---------------------|--------|
| example | false | N/A | PASS |
| openbb-mcp | false | N/A | PASS |
| tradesa-v2 | **true** | **YES** | PASS |
| brokers/alpaca | false | N/A | PASS |
| brokers/angelone | false | N/A | PASS |
| brokers/ccxt-exec | false | N/A | PASS |
| brokers/dhan | false | N/A | PASS |
| brokers/ib | false | N/A | PASS |
| brokers/kite | false | N/A | PASS |
| brokers/oanda | false | N/A | PASS |

**Result:** Only tradesa-v2 contributes panels. It is correctly registered in `PLUGIN_COMPANIONS`.
No companion-module wiring gaps. The diagnostic warning path in `moduleForPlugin` (line 224-232
of `plugin-bootstrap.ts`) would not fire for any current plugin.

---

### B.5 Host version consistency

`plugin-bootstrap.ts:39`: `const HOST_VERSION = "0.6.5"` — this is one release behind the
current codebase version (v0.7.0). Plugins are handed `hostVersion: "0.6.5"` via `PluginConfig`.
None of the current plugins gate behavior on `hostVersion`, so there is no runtime impact, but
the constant should be updated to `"0.7.0"`.

---

### Finding T4-host-version-stale: HOST_VERSION constant in plugin-bootstrap.ts is one release stale [S4] [status: open]

**Plugin:** all (bootstrap-level)
**Part:** B runtime
**Repro:** Read `src/lib/plugin-bootstrap.ts:39`: `const HOST_VERSION = "0.6.5"`.
**Impact:** Cosmetic — plugins receive a stale `hostVersion` in their `PluginConfig`. No current
plugin gates behavior on this value, but it will confuse any future plugin that does a semver
check against `hostVersion`. The CLAUDE.md version-bump checklist does not currently include
updating this constant.

**Suggested fix:** Update to `"0.7.0"` and add "update HOST_VERSION in plugin-bootstrap.ts"
to the version-bump checklist in CLAUDE.md.

**Files:**
- `src/lib/plugin-bootstrap.ts:39`

---

### B.6 Hot-reload preservation

**Tradesa-v2 store:** `useTradesaStore` at `plugins/tradesa-v2/store.ts:148` is created with
`create<TradesaState>(...)` at module top-level. Zustand's `create` returns a singleton store
bound to the module instance. On a Next.js hot-reload, the module is re-evaluated and
`create` is called again, producing a NEW store instance. The previous store's data (connection
state, cached positions, etc.) is lost. This is the standard Zustand hot-reload limitation;
it is not specific to the plugin pattern.

**Mitigation present:** The plugin's `initialize()` method calls `useTradesaStore.getState().reset()`
on re-enable, and the panels mount with `useEffect` probes on every mount. So the visible
symptom is a brief "Connecting…" flash rather than a stale or corrupt state.

**Verdict:** No hot-reload state corruption risk (data is discarded cleanly, not left in an
inconsistent state). The flash is cosmetic. No finding needed beyond noting this limitation.

**Broker plugins:** No Zustand stores; no hot-reload state to lose.

---

## Special attention — tradesa-v2 3-layer read-only invariants

The CLAUDE.md "Trading-system wrapper plugins" gotcha specifies three defense-in-depth layers:

### Layer 1: Provider has no write methods on its public surface

Checked via grep on `sidecar/services/tradesa_v2_provider.py` for
`def (insert_|update_|delete_|upsert_|write_|place_|submit_|execute_|create_)`:

**Result: Zero matches.** The provider exposes only read methods. **PASS.**

Cross-check from `plugins/tradesa-v2/connection.ts`: `TradingBotReadAdapter` interface lists
14 read methods, all returning data. No write method is declared. The implementation class
`TradesaV2ConnectionAdapter` has no write methods. **PASS.**

### Layer 2: Router has no non-GET routes

Checked via grep on `sidecar/routers/tradesa_v2.py` for
`@router\.(post|put|patch|delete|head|options)`:

**Result: Zero matches.** Every route on the Tradesa V2 router is a GET. **PASS.**

### Layer 3: capabilities.supportsControlPlane = false

`plugins/tradesa-v2/index.ts:80`: `supportsControlPlane: false`.

The `plugin-bootstrap.ts:198` gate: `if (instance.capabilities.supportsControlPlane && instance.executeCommand)`
— this condition is false for tradesa-v2, so no `executeCommand` handler is registered in
`commandHandlers`. The runtime would never invoke `executeCommand` on this plugin through the
command-palette path.

The plugin does not implement `executeCommand` at all (confirmed by reading
`plugins/tradesa-v2/index.ts` — the exported `tradesaPlugin` object has no `executeCommand`
method). **PASS.**

### 3-layer verdict

**All three layers INTACT.** The tradesa-v2 read-only invariants pass the audit:
- Provider: no write methods
- Router: no non-GET routes
- Plugin capabilities: `supportsControlPlane: false`, `executeCommand` not implemented

---

## Summary

### Finding counts

| Severity | Count | Findings |
|----------|-------|----------|
| S1 | 0 | — |
| S2 | 3 | T4-connection-keychain, T4-settings-dialog-keychain, T4-brokers-not-registered |
| S3 | 3 | T4-ccxt-executecommand-dead, T4-bare-commandids, T4-kite-manifest-unknown-field |
| S4 | 1 | T4-host-version-stale |
| **Total** | **7** | |

### Top 3 by severity

1. **T4-brokers-not-registered [S2]** — All 7 Phase 5 broker plugins are absent from
   `BUNDLED_PLUGINS`. Their cmd+K commands, data sources, and health checks are silently
   unavailable. This is the most impactful finding — if intentional, it needs a comment;
   if unintentional, the bootstrap needs 7 imports + entries.

2. **T4-connection-keychain [S2]** — `plugins/tradesa-v2/connection.ts` imports directly
   from `@/lib/keychain` and `@/lib/sidecar-client` instead of using `PluginConfig.secrets`
   and the `sidecarBaseUrl` from config. Creates host coupling that would break filesystem-
   installed plugins.

3. **T4-settings-dialog-keychain [S2]** — `TradesaSettingsDialog.tsx` imports `setSecret`
   from `@/lib/keychain`. Same coupling category as T4-connection-keychain; the two form a
   pair (both are in tradesa-v2).

### Tier-1 contract status

**10th-consecutive-release lock CONFIRMED EMPTY.** `types/plugin.ts` was not modified in
this audit and requires no changes to resolve any finding. All findings are fixable in
plugin files or bootstrap configuration without touching the contract. The contract is clean
and stable.

### tradesa-v2 3-layer status

**All three layers PASS.** Provider has no write methods. Router has no non-GET routes.
Plugin `supportsControlPlane: false` and `executeCommand` is not implemented.

### Items not audited

- **Sidecar broker adapters** (`sidecar/services/brokers/`) — explicitly out of scope (T2).
- **Broker plugin test files** (`plugins/brokers/*.test.ts`) — audit focused on runtime
  contracts, not test correctness.
- **Actual hot-reload behavior** — source-level analysis only; requires a running
  `pnpm dev` session to confirm the Zustand singleton re-instantiation timing.
- **Manifest `requiredHostVersion` semver enforcement** — the runtime does not currently
  validate `requiredHostVersion` against the `HOST_VERSION` constant at load time; this is a
  latent gap but no existing plugin would fail validation.
