# R15 census — CODE CRITIQUE: `plugins` (Contract + Bootstrap + Bundled)

**Subsystem:** `plugins` — `types/plugin.ts`, `types/plugin-runtime.ts`, `types/marketplace.ts`,
`src/lib/plugin-{bootstrap,runtime,agents}.ts`, `src/lib/marketplace.ts`,
`src/store/{plugins,marketplace}.ts`, `src/components/PluginManagerPanel.tsx`,
`src/modules/{plugin-manager,marketplace}/*`, `sidecar/{models,routers}/plugins.py`,
`sidecar/services/plugins_store.py`, `plugins/{example,vysted-lenses,vysted-news,yfinance,openbb-mcp}`.
3,653 LOC / 26 files, all read in full.

**Method:** `aposd-critique` skill loaded and followed. Assessment independence: **degraded
(sequential, single agent)** — no sub-agents spawned (R15 worker rule: one bounded job).
Persona A (Strategic Thinker) and Persona B (Tactical Tornado) run as two separate passes over
the same read; the bias that isolation would remove is noted here honestly.

**Evidence run:** `pnpm exec vitest run src/lib/plugin-runtime.test.ts src/store/marketplace.test.ts`
→ 2 files, 39 tests, all green. The behaviours cited below are the LIVE behaviours, not stale reads.

---

## Tactical Tornado verdict

**Risk: medium-high, concentrated at the seams — not inside the runtime.**

`PluginRuntime` itself is the best-built thing here: capability negotiation by flag, bounded
health history, compat rejection before `initialize()`, errors captured into state rather than
thrown. A Tactical Tornado did not write that class.

The debt is entirely in the **three separate callers that each re-derive the runtime's rules by
hand** instead of going through one lifecycle façade:

| Caller | Re-derives | Gets it wrong |
|---|---|---|
| `src/store/marketplace.ts` | install/enable/disable/remove + bridge + agent-sync + broker-disconnect | the reference implementation — mostly right |
| `src/lib/plugin-bootstrap.ts:252-271` | boot-time install/enable decision + bridge | no load-outcome check, no agent sync, double config read |
| `src/components/PluginManagerPanel.tsx:171-185` | enable/disable | calls raw `loadPlugin`/`unloadPlugin` — no persistence, no unbridge, no agent sync, auto-installs brokers |

That is the single root cause behind 5 of the 6 priority issues. The `VystedPlugin` contract is
deep; the **lifecycle** around it is shallow and forked three ways.

Flags found: 11 (information leakage ×3, repetition ×2, conjoined methods ×1, swallowed/ignored
failure ×3, overexposure ×1, obviousness ×1).

---

## Design principles score

| # | Principle | Verdict | Evidence (`file:line`) | Consequence |
|---|---|---|---|---|
| 1 | Strategic over tactical | at-risk | `plugin-bootstrap.ts:264-270` appends the module without reading the `loadPlugin` snapshot that `store/marketplace.ts:147` *does* read | boot path ships a tactical shortcut the marketplace path already outgrew |
| 2 | Deep modules | pass | `plugin-runtime.ts:148-603` — 12 public methods hide lifecycle, compat, health rollover, persistence, capability negotiation | callers say `installPlugin(x)`, not 6 steps |
| 3 | Information hiding | at-risk | `types/plugin-runtime.ts:125-140` `PluginPersistedConfig` is re-encoded by hand in `plugin-bootstrap.ts:42-55` (`PluginConfigUpdateBody`/`PluginConfigResponse`) and again in `sidecar/models/plugins.py:20-36` | a field added to the contract silently drops on the wire in 2 of 3 places |
| 4 | Information leakage | **violate** | "is this plugin on?" lives in `plugins.db.enabled` (`plugins_store.py:38-44`) AND `workspace.enabledModules["plugin:<id>"]` (`workspace.ts:263`). `plugin-runtime.ts:345` writes only the first; `plugin-bootstrap.ts:193-194` writes only the second | the two can disagree; only `store/marketplace.ts:182-183` writes both |
| 5 | General-purpose modules | at-risk | `plugin-runtime.ts:419-461` — five 5-line `collect*` bodies differing only in a flag + a getter name, over the already-general `callIfFlagged` (`:389`) | a 7th capability = 5 new methods + `store/plugins.ts:61-65` + `:85-89` |
| 6 | Different layer, different abstraction | **violate** | `PluginManagerPanel.tsx:178-181` (a React panel) calls the runtime's *primitives* `loadPlugin`/`unloadPlugin`, while `store/marketplace.ts` (the lifecycle layer) calls the *policies* `enablePlugin`/`disablePlugin` | the panel silently skips persistence, unbridge, agent-sync and the FR-051 broker guard |
| 7 | Pull complexity downward | **violate** | `store/marketplace.ts:147,165,241` each repeat `if (snap.state === "active") { bridge…; sync… }`; `plugin-bootstrap.ts:264` forgets it | the guard belongs inside one `enable()` the runtime owns, not in 3 copies + 1 omission |
| 8 | Better together or apart | at-risk | `plugin-bootstrap.ts:220-271` and `store/marketplace.ts:138-175` are conjoined — you cannot understand boot install-state without reading the store's defaults, and vice versa | two readers, four default sites (`plugin-runtime.ts:221`, `:310`, `plugin-bootstrap.ts:262`, `store/marketplace.ts:109`) that disagree (`true` vs `preinstalled`) |
| 9 | Define errors out of existence | **violate** | `plugin-agents.ts:47-63` fires `fetch` and never reads `response.ok`; `plugin-bootstrap.ts:243-245` swallows every keychain error per secret | a rejected agent registration reports success; a plugin shows "Enabled" with no runnable agent |
| 10 | Design it twice | pass | `types/plugin.ts:105-111` — panels ship a serializable `component: string` and React is resolved host-side via `CatalogRow.panelComponents`; the alternative (React types on the contract) was considered and rejected in the header comment | contract stayed serializable across 4 phases |
| 11 | Comments describe non-obvious | at-risk | `store/marketplace.ts:239` "Reload so the plugin resolves the new secrets" — the call below is a **no-op on an active plugin** (`plugin-runtime.ts:199-202`, locked green by `plugin-runtime.test.ts:171-177`) | the comment documents an invariant the code does not hold |
| 12 | Comments first | pass | `types/plugin.ts:1-18`, `types/plugin-runtime.ts:1-12`, `marketplace.ts:1-15` state the Tier-4 boundary before any type | a new contributor learns the blast radius before the code |
| 13 | Choosing names | at-risk | `plugin-runtime.ts:332` `installPlugin` and `:339` `enablePlugin` have byte-identical `patchConfig` bodies; `enablePlugin` is *also* used as "reload" (`store/marketplace.ts:240`) | three meanings, two names, one body |
| 14 | Modifying existing code | at-risk | `marketplace.ts:108` derives `version` from the manifest for openbb/example/brokers but `:93`,`:126`,`:141` hardcode `"1.0.0"` for yfinance/lenses/news — while `plugin-runtime.ts:371` **rejects any manifest/instance version mismatch** | the next version bump breaks the rows that were hand-copied, not the ones that derive |
| 15 | Consistency | **violate** | Disable does 4 things in `store/marketplace.ts:182-185` and 1 thing in `PluginManagerPanel.tsx:180`; bridge is guarded in `store/marketplace.ts:147` and unguarded in `plugin-bootstrap.ts:264` | same user-visible verb, two behaviours, depending on which panel is open |
| 16 | Code should be obvious | at-risk | `plugin-runtime.ts:478-499` captures `record` **before** `await instance.healthCheck()` then writes `{...record, healthHistory}` back — a wholesale write of a pre-await snapshot | reads as "append a sample"; actually reverts any concurrent transition |
| 17 | Design for the future | pass | `types/marketplace.ts:26-36` `CredentialField` — the credentials hub renders any plugin's BYOK form with zero per-source UI (`MarketplacePanel.tsx:274-293`) | adding a broker = one catalog row, no UI code |
| 18 | Performance as design | **violate** | `plugin-bootstrap.ts:252-271` is a strictly serial `for…of await` over 12 plugins; each iteration does `persistence.load` at `:258` **and again** inside `loadPlugin` at `plugin-runtime.ts:220`; `src/lib/sidecar-client.ts` sets no `AbortSignal` anywhere | 24 serialized, unbounded HTTP round-trips gate app boot; a hung sidecar hangs boot forever |

**Summary: 4 pass, 8 at risk, 6 violate (4/18 pass).**

---

## Overall impression

The **contract** is genuinely well designed and the **runtime** is a deep module. What is broken
is the layer between them and the UI: three independent callers each re-derive "what does
enabling a plugin mean", and they disagree. Every one of the six priority issues below is a
consequence of that one missing façade, and the cheapest structural fix is a single
`lifecycle.enable(pluginId)` / `lifecycle.disable(pluginId)` pair that owns persistence + bridge
+ agent-sync + broker-disconnect, with `bootstrapPlugins`, `useMarketplaceStore` and
`PluginManagerPanel` all routed through it. That deletes three copies of the guard and closes
five of the six defects at once.

## What's working

1. **Capability negotiation by flag with error containment.** `plugin-runtime.ts:389-416`
   `callIfFlagged` checks the flag, checks the getter exists, emits `errored` instead of
   throwing, and try/catches the call. A plugin that lies about its capabilities degrades to
   "contributes nothing" instead of taking the host down. Cognitive load stays low because every
   caller gets the same guarantee for free.
2. **Compat rejection before `initialize()`.** `plugin-runtime.ts:366-378` checks id, version and
   host floor and returns an `error` snapshot *before* any plugin code runs
   (`:207-214`). Six tests lock it (`plugin-runtime.test.ts:475-538`). This is exactly
   "define errors out of existence" — an incompatible plugin cannot reach a state where it
   half-works.
3. **The serializable-contract / React-companion split.** `types/plugin.ts:105-111` +
   `marketplace.ts:50-54` keep the Tier-1 contract free of framework types while still shipping
   real panels, and `plugin-bootstrap.ts:159-164` warns at boot when a row forgets its companion
   map. The invariant is enforced by a runtime warning, not only by CLAUDE.md prose.

---

## Priority issues

### [P0] The Plugin Manager toggle bypasses the entire marketplace lifecycle

- **Principle:** 6 (different layer, different abstraction), 15 (consistency)
- **Symptom:** change amplification + unknown unknowns
- **Evidence:** `src/components/PluginManagerPanel.tsx:171-185`

```ts
if (nextEnabled) {
  await runtime.loadPlugin({ manifest: plugin.manifest, instance: plugin.instance });
} else {
  await runtime.unloadPlugin(plugin.manifest.id);
}
```

  vs. `src/store/marketplace.ts:182-185`, which calls `runtime.disablePlugin` **plus**
  `unbridgePluginModule` **plus** `syncPluginAgents(id,false)` **plus** `disconnectBroker`.
- **Why it matters — three separate live defects:**
  1. `unloadPlugin` (`plugin-runtime.ts:278-295`) never touches persistence, so a plugin disabled
     from the Plugin Manager is **active again after restart** (`plugin-bootstrap.ts:262-264`
     reads `plugins.db`, which still says `enabled: true`).
  2. Its panels/commands stay in `useModulesStore` and its agents stay registered in the sidecar
     `custom_agents.db` — the capability the user just turned off is still reachable from cmd+K
     and the chat roster.
  3. Turning the toggle **on** for a broker is worse: the Plugin Manager lists all 12 discovered
     plugins including the 7 never-installed brokers (`plugin-bootstrap.ts:252-255` discovers
     all; `PluginManagerPanel.tsx:153` enables the toggle for any row with an instance). Flipping
     it calls `loadPlugin`, which for a never-persisted plugin defaults to
     `{installed: true, enabled: true}` and **writes that row** (`plugin-runtime.ts:221-232`).
     FR-051's "no broker registered at boot" is then violated on every subsequent launch, through
     a UI that never said "install".
  4. And the reverse toggle is a **dead control**: disable a plugin in the Marketplace
     (persists `enabled:false`), then flip it on in the Plugin Manager → `loadPlugin` reads the
     persisted `false` and returns `stopped` (`plugin-runtime.ts:243-247`) with no error shown.
     The switch springs back and nothing says why.
- **Fix:** route `handleToggle` through `useMarketplaceStore.enable/disable` (the store already
  guards, persists, bridges and syncs). Better: extract those four steps into
  `PluginRuntime.enable/disable` and make the store a thin caller — that also fixes P1 below.

### [P0] `configure()` never re-initializes an already-active plugin — new BYOK secrets never arrive

- **Principle:** 11 (comments describe non-obvious), 9 (define errors out of existence)
- **Symptom:** unknown unknowns
- **Evidence:** `src/store/marketplace.ts:238-244`

```ts
if (enabled) {
  // Reload so the plugin resolves the new secrets via PluginConfig.secrets.
  const snap = await runtime.enablePlugin(row.discovered);
```

  `enablePlugin` → `loadPlugin` (`plugin-runtime.ts:339-342`), and `loadPlugin` returns early
  for an active plugin: `plugin-runtime.ts:199-202`. Locked green by
  `src/lib/plugin-runtime.test.ts:171-177` (`expect(initialize).toHaveBeenCalledOnce()` after two
  `loadPlugin` calls). Verified live: suite passes.
- **Why it matters:** `PluginConfig.secrets` (`types/plugin.ts:42`) is the contract's ONLY
  sanctioned channel for handing a plugin its credentials. For any already-active plugin the
  keychain write lands, `grantedSecretIds` is persisted, the UI reports success — and
  `initialize()` is never called again, so the plugin runs credential-less until the app
  restarts. Today's bundled plugins dodge it only because they read their keys out-of-band
  (`plugins/vysted-news/index.ts:6-11` sends the key as a request header from the sidecar path,
  never from `config.secrets`), which means the contract's designated mechanism is
  **currently unexercised and broken**. The first plugin that trusts the documented channel
  silently gets an empty `secrets` map.
- **Fix:** in `configure`, `await runtime.unloadPlugin(pluginId)` before `enablePlugin`; or give
  the runtime a real `reloadPlugin(plugin)` that unloads-then-loads, and stop overloading
  `enablePlugin` with a third meaning (see principle 13).

### [P1] A preinstalled agent pack's agents are never registered at boot

- **Principle:** 15 (consistency), 4 (information leakage)
- **Symptom:** unknown unknowns
- **Evidence:** `syncPluginAgents` has exactly four production call sites, all in
  `src/store/marketplace.ts:149,167,184,201`. `src/lib/plugin-bootstrap.ts:220-285` never calls
  it. The chat roster reads `useAgentsStore.customAgents`
  (`src/modules/chat/ChatSidebar.tsx:394,531`), which is populated from the sidecar
  `/custom-agents` store — the only thing `syncPluginAgents` writes to.
  `usePluginsStore.agents` (`store/plugins.ts:63`) feeds nothing but a count string in
  `PluginManagerPanel.tsx:42`.
- **Why it matters:** `vysted-lenses` ships `preinstalled: true` (`marketplace.ts:128`) and
  contributes the Quant Tutor (`plugins/vysted-lenses/index.ts:28-47`). On a fresh data
  directory it loads `active`, shows "Pre-installed" in the Marketplace, and appears in the
  Plugin Manager's agent count — but it is **absent from the chat persona roster**, because
  nothing ever POSTs it to `/custom-agents`. The only way to make the product's one reference
  agent plugin runnable is to open the Marketplace and toggle Disable→Enable. That is a
  central product promise ("agents are marketplace plugins, genuinely runnable",
  `plugin-agents.ts:1-11`) failing on the default path.
- **Fix:** call `await syncPluginAgents(row.entry.pluginId, true)` in the boot loop
  (`plugin-bootstrap.ts:266`) alongside the module bridge — or, per P0's fix, make boot call the
  same `lifecycle.enable()` the store calls.

### [P1] The boot path bridges panels/commands without checking whether the plugin loaded

- **Principle:** 7 (pull complexity downward), 1 (strategic over tactical)
- **Symptom:** change amplification
- **Evidence:** `src/lib/plugin-bootstrap.ts:264-270`

```ts
if (installed && enabled) {
  await runtime.loadPlugin(plugin);            // <- return value discarded
  const pluginModule = moduleForPlugin(row);
  if (pluginModule) useModulesStore.getState().appendModules([pluginModule]);
}
```

  Its three siblings all guard: `store/marketplace.ts:147`, `:165`, `:241`
  (`if (snap.state === "active")`), each with the comment "a compat rejection (FR-054) leaves it
  in `error`/`stopped` and contributes nothing".
- **Why it matters:** `plugin-runtime.ts:356-365` documents the FR-054/SC-015 promise that a
  rejected plugin "contributes nothing", and
  `plugin-runtime.test.ts:516` ("an incompatible plugin contributes nothing") asserts it at the
  *runtime* level. The boot path defeats it at the *host* level: a plugin whose `initialize()`
  threw, or whose manifest/instance versions drifted (very reachable — see principle 14: three
  catalog rows hardcode a version string the compat check compares against), still gets its
  panels and slash commands into `useModulesStore`. The user sees panels for a plugin the
  Plugin Manager simultaneously renders in red "error".
- **Fix:** `const snap = await runtime.loadPlugin(plugin); if (snap.state === "active") { … }` —
  one line, and it deletes the asymmetry that makes the codebase's own promise read as a lie.

### [P1] `moduleForPlugin` re-implements capability negotiation without the runtime's error containment

- **Principle:** 4 (information leakage), 5 (general-purpose modules)
- **Symptom:** change amplification + cognitive load
- **Evidence:** `src/lib/plugin-bootstrap.ts:135-138`

```ts
const panels   = instance.capabilities.contributesPanels   ? (instance.getPanels?.()   ?? []) : [];
const commands = instance.capabilities.contributesCommands ? (instance.getCommands?.() ?? []) : [];
```

  vs. the runtime's own `callIfFlagged` (`plugin-runtime.ts:389-416`), which wraps the same call
  in `try/catch` and emits `errored`.
- **Why it matters:** the flag→getter rule is now written in two places and the copy is the
  weaker one. A plugin whose `getPanels()` throws is contained by `collectPanels()` but
  **propagates out of `moduleForPlugin`**, which is called unguarded from the boot loop
  (`plugin-bootstrap.ts:266`) — so one bad third-party getter rejects `bootstrapPlugins()` and
  the host never finishes booting its plugin layer. It is also called from
  `bridgePluginModule`/`unbridgePluginModule` (`:183`, `:198`), so the same throw breaks
  disable. And because the copy is out of band, the "flag set but getter missing" `errored`
  event the runtime emits never fires for the panel/command path.
- **Fix:** have `moduleForPlugin` take the panels/commands from
  `runtime.collectPanels()/collectCommands()` filtered by plugin id, or export `callIfFlagged`
  and use it. While there: the five `collect*` bodies (`plugin-runtime.ts:419-461`) collapse to
  one `collect<T>(flag, getter)` — a 7th capability currently costs 5 new methods plus 2 store
  projections.

### [P2] Two "Open Marketplace" buttons are dead controls

- **Principle:** 16 (code should be obvious), 13 (naming)
- **Symptom:** unknown unknowns
- **Evidence:** `src/components/PluginManagerPanel.tsx:71` and `src/components/SettingsPanel.tsx:1578`
  both call `openPanel("marketplace-panel")`. `openPanel` resolves via
  `findPanel(panelId)` → `collectPanels(modules).find(p => p.id === panelId)`
  (`src/store/workspace.ts:97-100`, `src/store/modules.ts:83`), and the marketplace panel's **id**
  is `"marketplace"` — `"marketplace-panel"` is its `component` key
  (`src/modules/marketplace/index.ts:17,20`; confirmed by `src/lib/layout-templates.ts:46`
  `{ id: "marketplace", component: "marketplace-panel" }`).
- **Why it matters:** `findPanel` returns `undefined` and `openPanel` silently `return`s
  (`workspace.ts:98-100`). The empty-state CTA on the Plugin Manager — literally the surface a
  user lands on when no plugins are loaded — and the Settings escape hatch both do nothing, with
  no error and no console noise. Every other caller in the file uses a real panel id
  (`"settings"`, `"chart"`, `"portfolio"`, `"screener-panel"`).
- **Fix:** `openPanel("marketplace")` in both call sites. Structurally: `openPanel` should not
  fail silently on an unknown id — `console.warn` at minimum, which would have caught this the
  first time it was clicked.

---

## Minor observations

- **`configure()` has no error path at all.** `store/marketplace.ts:220-232` awaits `setSecret`
  in a bare loop; `MarketplacePanel.tsx:257` fires `void configure(...).then(onDone)` with no
  `.catch`. A keychain rejection — the documented macOS `tauri dev` ACL re-prompt is exactly
  this — throws mid-loop: earlier fields are already written, `grantedSecretIds` is never
  persisted, the form stays open, and the user sees no error. `deleteSecret` on the same lines
  *is* guarded (`.catch(() => undefined)`, `:228`), so the asymmetry is visible in one screen.
- **`syncPluginAgents` never reads `response.ok`** (`plugin-agents.ts:47-63`). A 400 from the
  `KNOWN_TOOL_IDS` allow-list (`sidecar/models/custom_agent.py`) or a 409 is indistinguishable
  from success; the plugin reports Enabled with no runnable agent. (Checked: the Quant Tutor's 7
  tool ids are all in the 50-id allow-list today, so this is latent, not firing.)
- **Lost update in `healthCheckOne`.** `plugin-runtime.ts:478-499` captures `record` from the
  `activePlugins()` snapshot, awaits `instance.healthCheck()`, then `this.plugins.set(id,
  {...record, healthHistory})` — a wholesale write of the pre-await object. A `disablePlugin` or
  `transitionToError` that lands during that await is silently reverted to `active`. The health
  poll runs every 30 s (`plugin-bootstrap.ts:40`), so the window is real. Fix: re-read
  `this.plugins.get(id)` after the await, or mutate only `healthHistory`.
- **No timeout on any sidecar call, on the boot-critical path.** `src/lib/sidecar-client.ts`
  contains no `AbortSignal`/`timeout`; `plugin-bootstrap.ts:90-97` (`save`) and `:258`
  (`load`) use bare `fetch`. The boot loop is strictly serial and reads each plugin's config
  **twice** (`plugin-bootstrap.ts:258` and again inside `loadPlugin`, `plugin-runtime.ts:220`),
  so 12 plugins = 24 serialized unbounded round-trips before the app's plugin layer is ready.
  A hung sidecar hangs `bootstrapPlugins()` forever. (`plugins/openbb-mcp/index.ts:90-92` is the
  one place that *does* get this right — `AbortController` + 2 s.)
- **The catalog key invariant is unguarded.** `checkCompatibility` (`plugin-runtime.ts:366-378`)
  asserts `manifest.id === instance.pluginId` but nothing asserts `entry.pluginId === manifest.id`.
  `CATALOG_BY_ID` (`marketplace.ts:330`), `unbridgePluginModule` (`plugin-bootstrap.ts:194`) and
  `stateFor` (`store/marketplace.ts:127`) all key on `entry.pluginId`, while the runtime and
  `moduleForPlugin` (`plugin-bootstrap.ts:166`) key on `manifest.id`/`instance.pluginId`. A
  single typo in a catalog row makes disable a silent no-op. All 12 rows match today; a
  `CATALOG_ROWS.forEach` assertion (or a vitest) would make it structural.
- **`parseSemver` inverts a `<` range.** `plugin-runtime.ts:117` strips `<` along with
  `>=`/`^`/`~`, and `hostSatisfies` then compares with `>=`. A manifest
  `requiredHostVersion: "<0.9.0"` on host `0.8.0` is rejected with
  `requires host version >= <0.9.0`. No manifest uses `<` today; the fix is to drop `<` from the
  character class and reject what the contract says it does not support.
- **Three catalog rows hardcode a version the compat check enforces.** `marketplace.ts:93`,
  `:126`, `:141` write `version: "1.0.0"` by hand; `:108`, `:176`, `:214`… derive it from the
  manifest. Since `plugin-runtime.ts:371` hard-rejects a manifest/instance mismatch, the hand-copied
  rows are a bump away from a boot-time `error` state. Derive all of them.
- **`installPlugin` and `enablePlugin` have identical bodies.** `plugin-runtime.ts:332-342` —
  both `patchConfig({installed:true, enabled:true})` then load; `installPlugin` adds a
  `discover`, which `loadPlugin` already does (`:196-198`). Two names, three callers' meanings
  (install / enable / reload), one body.
- `plugins/example/index.ts:106` returns the shared `dataSources` array directly while
  news/yfinance/openbb all defensive-copy (`vysted-news/index.ts:85` etc.). Harmless today
  (`collectDataSources` spreads into a fresh array) but the example plugin is the reference
  third parties copy.
- **The sidecar half is clean.** `plugins_store.py` migrates the `installed` column idempotently
  (`:53-68`), the router is a thin typed CRUD (`routers/plugins.py`), and the model mirrors the
  TS contract 1:1 with the mirroring rule written down (`models/plugins.py:1-11`). No findings.

---

## Persona walkthroughs

**Tactical Tornado.** They would keep growing `PluginManagerPanel.handleToggle`
(`PluginManagerPanel.tsx:171-185`) into its own policy language — adding a
`if (isBroker) return;` here, a `await persistence.save(...)` there — until the panel holds a
second, divergent copy of the marketplace lifecycle. The same instinct already produced the
`if (snap.state === "active")` guard written out three times in `store/marketplace.ts` and
forgotten once in `plugin-bootstrap.ts:264`. Each copy is individually two lines and
individually defensible; together they are the reason the product's FR-051 and FR-054 promises
are both false on at least one path.

**Strategic Thinker.** They would add exactly one thing: a `PluginLifecycle` seam — most cheaply
four methods *on `PluginRuntime` itself*, since it already owns persistence and state —
`enable(pluginId)`, `disable(pluginId)`, `install(pluginId)`, `remove(pluginId)`, each doing
persist → load/unload → bridge/unbridge → agent-sync → broker-disconnect, and each returning the
final snapshot. `bootstrapPlugins` becomes `for (row of rows) await lifecycle.enableIfInstalled(row)`;
`useMarketplaceStore` becomes a busy-flag wrapper; `PluginManagerPanel.handleToggle` becomes
`lifecycle.enable/disable`. That single seam closes P0(a), P0(b), P1(agents), P1(bridge-guard)
and the information-leakage violation in one change, and it is a *smaller* diff than the
duplication it deletes. The alternative considered — leaving the runtime primitive and making
the *store* the only sanctioned caller (enforced by an eslint no-restricted-import on
`plugin-runtime` outside the store) — is cheaper still but leaves `bootstrapPlugins` importing
the store at boot, which inverts the current dependency direction; the runtime-owned seam is the
better of the two.

## Questions to consider

- If `loadPlugin` is idempotent-by-design, what should `configure()` call? The fact that three
  distinct verbs (install / enable / reload) all resolve to one body is why the secrets bug is
  invisible at the call site.
- Should `openPanel` fail silently on an unknown panel id? Two dead buttons survived review
  because it does.
- Is `usePluginsStore.agents`/`.dataSources` load-bearing at all? `.agents` feeds one count
  string; `.dataSources` feeds nothing outside the same header. If the real roster is the
  sidecar's, the runtime projection is a second source of truth for the same question.

---

**Run notes.** Target `docs/redesign/verification/r15/census/code/plugins.md`; ignore list: none
(`.aposd/critique/ignore.md` absent). Assessment independence: **degraded (sequential)** — no
sub-agents, per R15 worker scope. Snapshot persistence skipped (census run writes its own
artefacts; `.aposd/critique/` not used). Raw findings:
`docs/redesign/verification/r15/census/raw/code-plugins.json` (14 findings, prefix `COD-plugins`).
