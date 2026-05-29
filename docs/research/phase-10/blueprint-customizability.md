# Phase 10 — Customizability / Extensibility Blueprint

**Track:** "Cursor for trading" feel — make the terminal feel build-your-own,
sandboxable, and driveable-by-keyboard.
**Date:** 2026-05-29 · **Host:** v0.8.0 (`HOST_VERSION`, `plugin-bootstrap.ts:39`)
**Author:** customizability-track architect (headless, source-verified)

`types/plugin.ts` is **LOCKED (Tier-4)**. Every design below extends the platform
through **host-side glue** — module registration, plugin-bootstrap companions,
new Zustand stores, new host components, and **optional sidecar metadata that the
contract does not bind to** — never through a contract change. Where a temptation
to edit the contract exists, this doc says so and routes around it.

Every claim is cited to `file:line` against the working tree.

---

## 0. What I verified before designing (adversarial pass)

These are the load-bearing facts the build depends on. All confirmed in source:

1. **The palette is hand-rolled substring match, not a library.** No `cmdk`/`fuse`/
   `fuzzy` in `package.json` (grep: empty). Filtering is `title.includes ||
trigger.includes` (`CommandPalette.tsx:75-79`). `command.description` is
   _rendered_ (`:139-141`) but **not searched**; `command.icon` is **never read
   anywhere** (grep on `CommandPalette.tsx`: no `.icon`). So palette upgrades are
   pure host logic on an already-aggregated `CommandSpec[]`.
2. **`PanelSpec.defaultSize` is dead metadata.** 23 modules + tradesa-v2 declare it
   (grep: `defaultSize` across `src/modules/*/index.ts` + `plugins/tradesa-v2`),
   but `workspace.openPanel` → `api.addPanel({id, component, title})`
   (`workspace.ts:62, 70`) never passes width/height, and `default-layout.ts` sizes
   via hardcoded fractions (`:68-72`). Reviving it is free UX.
3. **Panels are reachable ONLY via a hand-authored `opensPanel` command.** There is
   no generic "add panel" surface. The header "Open panel ⌘K" button just opens the
   palette (`page.tsx:85-96`). `enabledPanels()` exists (`modules.ts:81`) but has no
   consumer that lists panels for opening.
4. **`DataSource` is registry-only — zero data routing.** `provider_registry.py`
   hardcodes asset-class dispatch (equity→yfinance, crypto→ccxt, fundamentals→
   openbb-mcp-or-yfinance; `:35-72`). No `DataSource.id` → fetch indirection exists.
   The plugin store's own doc admits the dead-end (`plugins.ts:14-20`). The
   PluginManager shows data sources as a **count string only** (`PluginManagerPanel.tsx:37`).
5. **Plugin agents never reach chat.** The picker reads only `useAgentsStore`
   (first-party + custom) — `ChatSidebar.tsx:44-46, 323-338` — never
   `usePluginsStore.agents`. Confirmed dead-end.
6. **Workspace persistence is opaque + extensible with no sidecar change.**
   `SerializedWorkspace` carries an index signature (`workspace.ts:38-40`); the
   sidecar `save_workspace(name, workspace: dict)` writes the body verbatim
   (`workspace_store.py:65-68`, `routers/workspace.py:53-60`). New keys ride along
   for free. There is **no file import/export UI** — only sidecar-named save/load
   in Settings → Layouts (`SettingsPanel.tsx:180-305`).
7. **Node palette double-renders plugin nodes (live bug).** `buildRegistry` already
   unions plugin entries into category groups rendered as draggable `PaletteCard`s
   (`node-palette.tsx:57-78`). Lines `79-94` render a _second_ "Plugin Nodes" section
   as bare, **non-draggable** `<span>`s showing only `pluginId`. Every plugin node
   appears twice; the duplicate is a dead stub.
8. **Settings is a flat 4-section scroll page** (`SettingsPanel.tsx:53-56`:
   Providers · Layouts · Modules · About). About to gain 3-4 more surfaces — past
   the scroll threshold the Fincept study flagged.

---

## 1. The prioritized build set (user value vs build cost)

I am **not** proposing everything in the brief's candidate list. Two candidates are
deliberately deferred with justification (§9). The high-value set, ranked by
`value ÷ cost`:

| #     | Feature                                                                            | User value                            | Build cost | Verdict             |
| ----- | ---------------------------------------------------------------------------------- | ------------------------------------- | ---------- | ------------------- |
| **A** | **Command palette → "command for any action" + fuzzy/category/recents**            | Very high (this _is_ the Cursor feel) | Low–Med    | **BUILD FIRST**     |
| **B** | **Panel/widget gallery + revive `defaultSize`**                                    | High                                  | Low        | **BUILD**           |
| **C** | **Workspaces as first-class objects: file export/import + share + duplicate**      | High                                  | Low        | **BUILD**           |
| **D** | **Saved watchlists + saved screens as first-class objects**                        | High                                  | Med        | **BUILD**           |
| **E** | **Data-connector hub (real `DataSource` routing + default-per-kind + provenance)** | Very high, but …                      | High       | **BUILD (scoped)**  |
| **F** | **Theme customization hooks (accent + density, CSS-var driven)**                   | Med                                   | Low        | **BUILD (thin)**    |
| **G** | **Settings IA → left-rail shell** (host for A–F)                                   | Med (enabler)                         | Low        | **BUILD**           |
| **H** | Fix node-palette double-render                                                     | Low (correctness)                     | Trivial    | **BUILD (cleanup)** |
| —     | Per-session MCP tool activation                                                    | High (later)                          | High       | **DEFER (§9)**      |
| —     | Plugin sandbox / signing / marketplace                                             | Foundational (later)                  | Very high  | **DEFER (§9)**      |

The through-line: **A + B + C + D make the app feel driveable and yours within one
sprint at low cost; E is the one expensive, high-value bet worth taking because the
study (OpenBB §2.2 coverage map, Fincept §2 connector registry) and the map (§5
"biggest gap") all converge on it.** F and G are cheap polish/enablers. H is a
correctness fix riding along.

---

## 2. Feature A — Command palette as the universal action driver ⭐ build first

### 2.1 The gap

The palette today is a flat substring filter over commands aggregated from enabled
modules (`CommandPalette.tsx`, `command-palette.ts`). To feel like Cursor it needs:
fuzzy ranking, category grouping, recents, icon rendering, description search, and —
critically — **enough commands registered that the palette can drive _any_ action**
(open any panel, run any screen, connect any source, toggle any module, switch
theme). The contract (`CommandSpec`, `types/plugin.ts:118-133`) is already rich
enough (`id, trigger, title, description?, icon?, commandId?, opensPanel?`). No
contract change.

### 2.2 What to build — all host-side

**A1. Fuzzy ranking + description search + icon render** — rewrite the filter in
`CommandPaletteBody` (`CommandPalette.tsx:70-80`). Add a small fuzzy matcher (do
**not** add a dependency — ship a ~40-line subsequence scorer; the codebase avoids
new deps and a fzf-style subsequence match is trivial). Score against
`trigger` (highest weight) → `title` → `description` (lowest), with relevance
ordering: exact-trigger → trigger-prefix → title-prefix → subsequence. Render
`command.icon` (Lucide name → dynamic `lucide-react` icon) in the row
(`:128-143`), reviving the dead contract field.

**A2. Category grouping.** The host knows which module each command came from
(commands flow through `useModulesStore`). Add an optional `category` derivation:
group rows under the contributing module's `title`. This needs the palette to know
command→module provenance. Cheapest path: have `useCommandPalette.setCommands`
accept `Array<{ command: CommandSpec; category: string }>` instead of bare
`CommandSpec[]`, and have `page.tsx` build that mapping from
`useModulesStore.enabledModules()` (it already iterates modules). **No contract
change** — category lives in the palette view-model, not on `CommandSpec`.

**A3. Recents + frecency.** New tiny store slice `recentCommandIds: string[]` in
`command-palette.ts`, bumped in `executeCommand` (`commands.ts:10`). Show a
"Recent" group at top when the query is empty. Persist to the sidecar via a new
`/ui-prefs` blob (§6) so recents survive relaunch.

**A4. The action-coverage expansion — make "command for any action" literally
true.** Audit every user-facing action and ensure a command exists. Concretely,
add a new first-party module `command-actions` (a `VystedModule` with **commands +
handlers, no panels**) that registers control-plane commands for the actions that
currently have _no_ palette entry:

- `theme.set-accent` / `theme.toggle-density` (Feature F)
- `workspace.export` / `workspace.import` / `workspace.duplicate` (Feature C)
- `panel.open-gallery` (Feature B)
- `connector.open-hub` (Feature E)
- `watchlist.new` / `screen.save-current` (Feature D)
- `module.toggle <id>` family (one per module, generated from the registry)

These are `commandId` commands whose handlers call the relevant store action —
exactly the existing pattern (`module-registry.ts:35`, `commands.ts:15-18`).

**A5. Parameterized commands — DEFER but leave the seam.** "open chart AAPL",
"/connect alpaca" need a parameter slot the locked `CommandSpec` lacks (Fincept
§3 `ParameterSlot`, OpenBB has none of this). Adding it is Tier-4. Do **not** do it
now. Instead, the palette's `run()` (`CommandPalette.tsx:82-89`) can detect a
trailing token after a known trigger and stash it in a host-side `commandArgs`
map keyed by `commandId`, read by the handler — a host-only convention that needs
no contract field. Mark this clearly as a stopgap until a deliberate contract
revision.

### 2.3 Files

- **Modify** `src/components/CommandPalette.tsx` — fuzzy scorer, grouping, icon
  render, recents group.
- **Modify** `src/store/command-palette.ts` — richer command view-model
  (`{command, category}`), `recentCommandIds`, `pushRecent`.
- **Modify** `src/lib/commands.ts` — `pushRecent(command.id)` on execute; host-side
  `commandArgs` stopgap.
- **Modify** `src/app/page.tsx` — build the `{command, category}` view-model from
  `enabledModules()` and re-seed on the same two subscriptions already present
  (`page.tsx:48-59`).
- **Create** `src/modules/command-actions/index.ts` — the coverage-expansion module
  (commands + handlers, no panels). Register in `src/modules/index.ts`.
- **Create** `src/lib/fuzzy.ts` — dependency-free subsequence scorer + tests.
- **Create** `src/lib/fuzzy.test.ts`, `src/components/CommandPalette.test.tsx`
  (ranking order, recents, category grouping).

---

## 3. Feature B — Panel / widget gallery + revive `defaultSize`

### 3.1 The gap

Opening a panel requires a hand-authored `opensPanel` command per panel. A plugin
author who ships a `PanelSpec` without a matching command produces an unopenable
panel. `PanelSpec.icon`/`defaultSize` are dead. The header "Open panel" button is a
misnomer (it opens the palette).

### 3.2 What to build

**B1. Panel gallery component** — a new host component `PanelGallery.tsx` that lists
`useModulesStore.enabledPanels()` (`modules.ts:81`) as cards: `title`, `icon`
(Lucide), originating module title, and an "Add" action calling
`useWorkspaceStore.openPanel(spec.id)`. Group by module. This is the natural home
for the header button — repoint `page.tsx:87` `onClick` from `openPalette(true)` to
open the gallery (keep ⌘K bound to the palette; the gallery gets its own command
`panel.open-gallery` from Feature A4 + a header button labeled "Add panel").

**B2. Revive `defaultSize`.** In `workspace.openPanel` (`workspace.ts:46-71`), read
`spec.defaultSize` and pass it to `api.addPanel` as `initialWidth`/`initialHeight`
(dockview supports these). Guard for absence. This makes plugin-contributed panels
land at a sensible size instead of a dockview default. Note the `default-layout.ts`
proportional-redistribution caveat (`:14-21`) — `initialWidth` is a hint, not exact,
which is fine for ad-hoc panel adds (the cockpit default still uses explicit
`setSize`).

**B3. Surface the gallery in two places** — header "Add panel" button + a
`panel.open-gallery` command (Feature A4). The gallery is a **singleton dockview
panel** itself (or a Radix dialog — prefer dialog so it overlays any layout without
consuming a dock slot).

### 3.3 Files

- **Create** `src/components/PanelGallery.tsx` + `.test.tsx`.
- **Create** `src/store/panel-gallery.ts` (open/close, like `command-palette.ts`).
- **Modify** `src/lib/workspace.ts` `openPanel` — wire `defaultSize` →
  `initialWidth/initialHeight`. (NB: `openPanel` lives in `src/store/workspace.ts`,
  not `lib/workspace.ts` — verified `workspace.ts:46`. Edit the **store** file.)
- **Modify** `src/store/workspace.ts` — `openPanel` reads `spec.defaultSize`.
- **Modify** `src/app/page.tsx` — header "Add panel" button → gallery; render
  `<PanelGallery/>` next to `<CommandPalette/>`.

---

## 4. Feature C — Workspaces as first-class, shareable objects

### 4.1 The gap

Workspaces save/load/delete to the sidecar by name (Settings → Layouts). There is
**no file export/import**, no duplicate, no sharing. The `SerializedWorkspace` shape
is already file-ready (`workspace.ts:26-40`) and the sidecar body is opaque
(`workspace_store.py:65-68`) — so this is pure frontend work plus optional Tauri FS.

### 4.2 What to build

**C1. Export to `.vysted-workspace` file.** `serializeWorkspace(name)` already
builds the full payload (`workspace.ts:55-66`). Add `exportWorkspace(name)`:
serialize → JSON → trigger a download (in-browser `Blob` + anchor for `pnpm dev`;
in Tauri, use the `@tauri-apps/plugin-dialog` save dialog + `plugin-fs` write — the
app already depends on Tauri plugins for keychain). Provenance/version stamp: add
`hostVersion: HOST_VERSION` and `exportedAt` to the payload via the index signature
(no sidecar change — `workspace.ts:38-40` allows it).

**C2. Import from file.** `importWorkspace(file)`: read JSON → validate it has
`layout` + `enabledModules` → `deserializeWorkspace` (`workspace.ts:75-90`) → offer
to save under a name. Reject mismatched `hostVersion` major with a warning, don't
hard-fail (forward-compat: the shape is additive).

**C3. Duplicate.** `duplicateWorkspace(name, newName)` = load body, re-save under a
new name. One sidecar round-trip, no new endpoint.

**C4. Surface.** Add Export / Import / Duplicate buttons to the Layouts section
(`SettingsPanel.tsx:180-305`, per-row Export + Duplicate, a top-level Import) and
register `workspace.export/import/duplicate` commands (Feature A4).

**C5. Sharing = the exported file IS the share unit.** No server, no accounts
(local-first DNA). A user sends the `.vysted-workspace` file; the recipient imports.
Document that secrets are **never** in a workspace (it carries only layout +
`enabledModules` + chart drawings — verified `workspace.ts:31-37`), so sharing is
safe by construction. This is the OpenBB-study lesson applied (§6 "export shapes,
not secret values").

### 4.3 Files

- **Modify** `src/lib/workspace.ts` — `exportWorkspace`, `importWorkspace`,
  `duplicateWorkspace`; stamp `hostVersion`/`exportedAt` into the payload.
- **Create** `src/lib/workspace-file.ts` — Tauri-dialog/FS vs browser-Blob
  download/upload split (mirrors the `resolvePersistence` env-split pattern in
  `plugin-bootstrap.ts:166-176`).
- **Modify** `src/components/SettingsPanel.tsx` `LayoutsSection` — export/import/
  duplicate buttons.
- **Create** `src/lib/workspace.test.ts` additions (round-trip export→import).

---

## 5. Feature D — Saved watchlists & saved screens as first-class objects

### 5.1 The gap

- **Watchlist:** one global symbol list in `useSymbolsStore` (`symbols.ts:40-57`),
  **not persisted at all** (in-memory, seeded from `DEFAULT_SYMBOLS`). The user can
  edit _what_ symbols but cannot save _named_ lists or switch between them.
- **Screener:** rich criteria builder (`ScreenerCriteriaBuilder.tsx`,
  `types/screener.ts:48-92`) with universe + AND-criteria, but the draft lives in
  `useScreenerStore` (`screener.ts:98-101`) and is **not saveable** — no named
  screens, no persistence. Re-build the screen every session.

Both are the closest thing to "build-your-own" today (map §7) but neither is a
saved object. Making them first-class is high user value.

### 5.2 What to build — one shared "saved objects" sidecar store

**D1. Generic saved-objects sidecar endpoint.** Add `sidecar/routers/saved_views.py`

- `services/saved_views_store.py` mirroring `workspace_store` exactly (opaque JSON
  keyed by `(kind, name)`, file or SQLite-backed). Routes:
  `GET /saved-views/{kind}` (list names), `GET /saved-views/{kind}/{name}`,
  `POST /saved-views/{kind}`, `DELETE /saved-views/{kind}/{name}`. `kind ∈
{"watchlist","screen"}` (extensible). This generalizes the workspace pattern rather
  than building two bespoke persistence layers. Mount in `app.py` (one-line
  `include_router`, per the router convention `routers/workspace.py:6-8`).

**D2. Watchlists.** New `src/store/watchlists.ts` (named lists) layered over
`useSymbolsStore`: `savedLists: Record<name, SymbolEntry[]>`, `activeListName`,
`saveCurrentAs(name)`, `loadList(name)`, `deleteList(name)`, persisted via
`/saved-views/watchlist`. The watchlist panel gains a list picker dropdown in its
header. The default list seeds the first one.

**D3. Saved screens.** New `src/store/saved-screens.ts`: persist
`{universe, customSymbols, criteria, limit}` (the `ScreenerRequest` shape minus
results, `types/screener.ts:83-92`) via `/saved-views/screen`. The screener panel
header gains "Save screen as…" + a saved-screens dropdown that hydrates the criteria
builder. This is what makes a screen a reusable object instead of a one-shot query.

**D4. Commands.** `watchlist.new`, `watchlist.switch <name>`, `screen.save-current`,
`screen.load <name>` (Feature A4 + parameterized stopgap A5).

### 5.3 Files

- **Create** `sidecar/routers/saved_views.py`, `sidecar/services/saved_views_store.py`,
  `sidecar/tests/test_saved_views.py`. **Modify** `sidecar/app.py` (one-line mount).
- **Create** `src/store/watchlists.ts` + `.test.ts`, `src/store/saved-screens.ts` +
  `.test.ts`.
- **Modify** `src/modules/watchlist/WatchlistPanel.tsx` — list picker header.
- **Modify** `src/modules/screener/ScreenerPanel.tsx` — save/load screen header.
- **Modify** `src/lib/sidecar-client.ts` — `savedViews` accessor group (mirror the
  existing `sidecarApi` pattern).

---

## 6. Feature E — Data-connector hub (the one expensive, high-value bet) ⭐

### 6.1 The gap (map §5, study OpenBB §2.2, Fincept §2)

`DataSource` (`types/plugin.ts:76-87`) is inert: collected (`plugin-runtime.ts`
`collectDataSources`), stored (`plugins.ts:32`), counted (`PluginManagerPanel.tsx:37`)
— and nothing else. First-party panels fetch hardcoded sidecar endpoints via
`provider_registry.py`'s asset-class dispatch (`:35-72`); there is no
`DataSource.id` → fetch indirection, no "which source serves equity", no default-
per-kind, no provenance in responses. A user cannot say "use Polygon for equities."

The contract is ready (`DataSource` has `id`/`label`/`kinds`/`realtime`). **No
contract change needed.** The plumbing is what's missing.

### 6.2 Scope discipline

Do **not** build OpenBB's full TET pipeline or Fincept's 78 connectors. Build the
**routing layer + hub UI + provenance envelope** so the _mechanism_ is real, and ship
it with the connectors that already exist (yfinance, ccxt, openbb-mcp + the broker
data sources). New connectors then arrive as thin plugins through `contributesData`
(which is _better_ than Fincept's static self-registration — study Fincept §2.5).

### 6.3 What to build

**E1. A connector-resolution layer in the host — `src/lib/connectors.ts`.**
A registry view-model over `usePluginsStore.dataSources` (`plugins.ts:32`) **plus**
the first-party built-in sources (yfinance/ccxt/openbb-mcp, which today aren't even
`DataSource`s — register them as host-side `DataSource` records in a new
`FIRST_PARTY_DATA_SOURCES` constant so they appear in the hub alongside plugin
sources). Compute the **coverage map** (OpenBB §2.2 `CommandMap.provider_coverage`):
`Record<DataSourceKind, DataSource[]>` — "which sources can serve equity / crypto /
macro / news / fundamentals." This is derived, never hand-maintained.

**E2. Default-source-per-kind selection.** New `src/store/connectors.ts`:
`activeSourceByKind: Record<DataSourceKind, sourceId>`, persisted via the
`/saved-views` store from D1 (`kind: "connector-prefs"`) or a dedicated `/ui-prefs`
blob. The user picks "equity → openbb-mcp-equity (fallback yfinance)."

**E3. Honor the selection at fetch time — sidecar side.** This is the load-bearing
piece. Generalize `provider_registry.py` so dispatch reads an **active-source hint**
instead of hardcoding. Concretely: the frontend passes the chosen `source_id` as a
request param/header (e.g. `?source=openbb-mcp-equity`), and `provider_registry`
maps `source_id → provider callable`, falling back to the current hardcoded default
when absent. **This keeps every existing call working** (no source = today's
behavior) while making selection real. The provider functions already exist
(`yfinance_provider`, `ccxt_provider`, `openbb_mcp_provider`); this is wiring a
lookup, not new providers.

**E4. Provenance + soft-warning envelope (OpenBB §3.3 `OBBject`).** Wrap data
responses as `{results, provider, warnings}` so a panel can render "source: yfinance
(degraded — openbb-mcp down)." The registry already _informally_ does fallback
logging (`provider_registry.py:62-65`); formalize it into the response. **Scope
this to NEW/changed routes only** — do not break the 24 existing typed routers in one
sprint. Apply the envelope to the routes the hub actually drives (quotes, history,
fundamentals) and leave the rest for follow-up. This also resolves the FastMCP
"must return a dict" gotcha generally (CLAUDE.md).

**E5. The hub UI — Gallery + Connections (Fincept §2).** New
`src/components/ConnectorHub.tsx` (a settings sub-section or its own panel):

- **Gallery view:** browse all `DataSource`s grouped by `kind` (the coverage map),
  with `label` + `description` + `realtime` badge + originating plugin.
- **Connections view:** per-kind "active source" picker with the default-+-fallback
  selection (E2). A "Test" affordance per source (calls a representative endpoint
  and shows ok/degraded) — the study's `ConnectionTester` lesson (Fincept §2.3),
  scoped to a health ping, not a full per-connector probe.
- Replaces the dead count string in PluginManager (`PluginManagerPanel.tsx:37`)
  with a "Manage connectors →" link into the hub.

**E6. Connect cards with onboarding metadata (OpenBB §1.4 `instructions`).** When a
`DataSource` needs a key, the hub should tell the user _which_ key and _how_ to get
it. The locked `DataSource` lacks `instructions`/`website`/`credentialFields` —
adding them is Tier-4. **Route around it:** ship the onboarding metadata as a
**host-side companion map** keyed by `sourceId`, exactly like `PLUGIN_COMPANIONS`
binds panel components (`plugin-bootstrap.ts:81-83`). New
`src/lib/connector-companions.ts`: `Record<sourceId, {instructions?, website?,
credentialFields?}>`. The contract stays serializable; the rich onboarding lives
host-side. This is the cleanest Tier-3 move and it's the exact pattern the codebase
already uses for the panel-component gap.

### 6.4 What this explicitly does NOT do (and why)

- **No standard-model binding / TET pipeline** (OpenBB §1.3). That enforces that two
  equity providers return identical shapes. Valuable, but it's a sidecar-wide
  refactor and the codebase already hand-mirrors models (`types/data.ts` ↔
  `sidecar/models/`, CLAUDE.md). Defer to a sidecar-only follow-up; note it.
- **No per-route `exposeToAgents` default-deny** (OpenBB §4.3). That touches the §6.5
  safety story and `types/plugin.ts` — coordinate with the §6.5 owner separately.
- **No `obbject_extension` output-hook capability** (OpenBB §2.3). That's a 7th
  capability → Tier-4 contract change. Out of scope.

### 6.5 Files

- **Create** `src/lib/connectors.ts` (coverage map + `FIRST_PARTY_DATA_SOURCES`),
  `src/lib/connector-companions.ts` (onboarding metadata), `src/store/connectors.ts`
  (active-source-per-kind), `src/components/ConnectorHub.tsx` + tests.
- **Modify** `sidecar/services/provider_registry.py` — `source_id`-aware dispatch
  with fallback to today's default; **Modify** `sidecar/routers/quotes.py`,
  `history.py`, `fundamentals.py` — accept optional `source` param + return the
  provenance envelope. **Modify** `sidecar/models/` + `types/data.ts` — add the
  `{results, provider, warnings}` wrapper type (kept in sync per CLAUDE.md gotcha).
- **Modify** `src/components/PluginManagerPanel.tsx` — count string → hub link.
- **Modify** `src/modules/watchlist/api.ts` + chart/equity-overview fetchers — pass
  the active `source` for their kind (optional; backward-compatible).

---

## 7. Feature F — Theme customization hooks (thin)

### 7.1 The gap

Theme is dark-only and hardcoded; light theme is a Tier-4 BLOCKER until v1.1
(CLAUDE.md visual convention). But cheap _within-dark_ customization (accent color,
density) is a real "make it mine" win that doesn't touch the light-theme blocker.

### 7.2 What to build

**F1. CSS-variable-driven accent + density.** `styles/` already uses design tokens.
Expose `--accent` (currently amber-400 everywhere) and a density scale as CSS vars
on `:root`. New `src/store/theme.ts`: `accent`, `density`, persisted via the
`/ui-prefs` / `/saved-views` blob. A small Settings → Appearance section with an
accent swatch row + density toggle. Commands `theme.set-accent`,
`theme.toggle-density` (Feature A4).

**F2. Do NOT add light theme.** It's a documented Tier-4 BLOCKER. Accent/density are
intra-dark and safe.

### 7.3 Files

- **Create** `src/store/theme.ts` + `.test.ts`, `src/components/AppearanceSection.tsx`.
- **Modify** `styles/` token file — promote accent + density to CSS vars (the lead
  identifies the exact token file; `globals.css` imports tokens).
- **Modify** `src/app/layout.tsx` (or wherever `:root` vars are set) — apply
  persisted theme vars on mount.

---

## 8. Feature G — Settings IA → left-rail shell (enabler) + Feature H — node-palette fix

### 8.1 Settings left-rail

The flat 4-section page (`SettingsPanel.tsx:53-56`) is about to host Appearance,
Integrations/Connectors, and saved-objects management — 7+ sections. Restructure to
a left-rail + content-pane (Fincept §4 IA). Sections:
`AI Providers · Appearance · Layouts · Modules & Plugins · Connectors · Saved Views ·
About`. Each existing section component drops in unchanged behind the rail.

**Files:** **Modify** `src/components/SettingsPanel.tsx` — wrap the existing section
components in a left-nav + `useState` active-section pane. Pure presentational
refactor; the section components (`ProvidersSection`, `LayoutsSection`,
`ModulesSection`, `AboutSection`) are reused as-is, plus the new
`AppearanceSection`, `ConnectorHub`, and a `SavedViewsSection`.

### 8.2 Node-palette double-render fix (H)

Delete the redundant non-draggable section. In `node-palette.tsx`, remove lines
`79-94` (the `pluginEntries.length > 0 && <section data-testid="palette-section-
plugin">…` block) and the now-unused `const pluginEntries` (`:45`). Plugin nodes
already render as draggable `PaletteCard`s inside their category groups via
`buildRegistry`/`groupByCategory` (`:57-78`). Update/adjust any test asserting the
`palette-section-plugin` testid.

**Files:** **Modify** `src/modules/node-editor/node-palette.tsx`,
`src/modules/node-editor/node-palette.test.tsx` (if it asserts the dead section).

---

## 9. Deliberately deferred (with justification)

1. **Per-session MCP tool activation** (OpenBB §4.1). High value as the MCP surface
   grows across openbb-mcp + sec-edgar-mcp, but it's sidecar+MCP-layer work
   orthogonal to the "feel" of customizability and the surface isn't large enough yet
   to blow context. Defer to a dedicated AI-track sprint.
2. **Plugin sandbox / signing / filesystem-installed marketplace** (map §11). The
   "sandboxable" product word currently means _layout sandbox_, not _code sandbox_ —
   plugins are in-process TypeScript with full host access, statically bundled
   (`BUNDLED_PLUGINS`, `plugin-bootstrap.ts:45-49`). A real trust boundary
   (capability enforcement at runtime, signature verification, dynamic load) is a
   large architecture effort and a Tier-4-adjacent decision. Out of scope for this
   track; flag it as the prerequisite for any third-party ecosystem.
3. **Standard-model binding for `DataSourceKind`** (OpenBB §1.3) and **agent metadata
   enrichment** (`category`/`capabilities`/`requiredKeys`, Fincept §1) — both are
   sidecar-internal / Tier-2 follow-ups that the Connector-hub and a future
   persona-picker sprint can layer on without contract changes. Noted, not built here.

---

## 10. The plugin-agents dead-end — a near-free win to fold in

The chat picker reads only first-party + custom (`ChatSidebar.tsx:44-46`); plugin
`AgentSpec`s collected into `usePluginsStore.agents` never appear (map §9; tradesa-v2
keeps `contributesAgents:false` because of it). This isn't strictly a
"customizability" feature but it's a one-component change that completes a contract
capability and reinforces the extensibility story:

- **Modify** `src/modules/chat/ChatSidebar.tsx` — add a third `<optgroup label=
"Plugin agents">` reading `usePluginsStore.agents` (mapped to the picker's
  `AgentSummary` shape via a small adapter — `AgentSpec` → summary, mirroring
  `customSpecToSummary` in `agents.ts:121-132`). The chat send path already resolves
  a system prompt; plugin agents carry `systemPrompt` directly on `AgentSpec`
  (`types/plugin.ts:151`), unlike first-party agents whose prompt is sidecar-side.

Include only if the sprint has room — it's low-cost and closes a documented gap, but
it's adjacent to the AI track, so it's a "fold-in if convenient," not a core item.

---

## 11. Build order (dependency-aware)

1. **G (Settings left-rail)** first — it's the shell the new sections live in; cheap,
   unblocks parallel work on F/E-UI/D-UI.
2. **A (palette)** + **H (node-palette fix)** — independent, high-value, low-risk.
3. **B (panel gallery + defaultSize)** — independent.
4. **C (workspace export/import/share)** — independent, frontend + thin Tauri FS.
5. **D (saved watchlists/screens)** — needs the shared `/saved-views` sidecar store;
   build that store first, then the two frontend stores in parallel.
6. **E (connector hub)** — the big one; sequence its sidecar `provider_registry`
   change + envelope before the hub UI. Reuses D's `/saved-views` for prefs.
7. **F (theme)** — anytime after G; trivial.
8. **§10 plugin-agents** — fold in if room.

A–D + G + H are one comfortable sprint of mostly-host-side work with held contract.
E is the second sprint's centerpiece (sidecar + host). Everything stays inside the
LOCKED `types/plugin.ts`: every contract-adjacent need (command category, command
args, connector onboarding metadata, theme) is met by a **host-side companion map or
view-model**, the exact pattern the codebase already established with
`PLUGIN_COMPANIONS`.

---

## Appendix — files read (all working tree @ v0.8.0)

`types/plugin.ts`, `types/screener.ts`, `src/lib/plugin-bootstrap.ts`,
`src/lib/module-registry.ts`, `src/lib/commands.ts`, `src/lib/workspace.ts`,
`src/components/CommandPalette.tsx`, `src/components/SettingsPanel.tsx`,
`src/components/PanelHost.tsx`, `src/components/PluginManagerPanel.tsx`,
`src/store/command-palette.ts`, `src/store/modules.ts`, `src/store/workspace.ts`,
`src/store/plugins.ts`, `src/store/agents.ts`, `src/store/symbols.ts`,
`src/store/screener.ts`, `src/config/default-layout.ts`, `src/app/page.tsx`,
`src/modules/index.ts`, `src/modules/watchlist/api.ts`,
`src/modules/screener/ScreenerPanel.tsx`, `src/modules/chat/ChatSidebar.tsx`,
`src/modules/node-editor/node-palette.tsx`,
`src/modules/node-editor/node-registry.ts`, `sidecar/routers/workspace.py`,
`sidecar/routers/quotes.py`, `sidecar/routers/plugins.py`,
`sidecar/services/provider_registry.py`, `sidecar/services/workspace_store.py`,
`sidecar/app.py`, `plugins/openbb-mcp/index.ts`, `package.json`; prior reports
`map-extensibility.md`, `study-fincept.md`, `study-openbb.md`.
