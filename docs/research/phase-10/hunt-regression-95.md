# Phase 10 — Adversarial Regression Hunt: Phase 9.5 Overnight Session

**Lens:** regressions introduced by the Phase 9.5 overnight session (Track A bug
fixes `a96782f`, Track C panel-freedom/settings/onboarding `40746bd`, Track D
"INSTRUMENT" design system `4932fab`).

**Method:** read the actual diffs of the six Phase-9.5 commits, traced the runtime
paths into dockview-core/dockview-react source, ran `pnpm typecheck` (clean),
`pnpm lint` (clean), `pnpm test` (612 passed), `pnpm build` (static export
compiles), and inspected the emitted CSS in `out/`.

**Known live bugs (operator-reported, treated as confirmed Phase-9.5 regressions):**
boot crash, Settings double-scrollbar, "set-as-default only works for Ollama".
This report nails the root cause of the boot crash (it is NOT generic — it is the
autosave-restore-vs-plugin-registration race) and surfaces additional NEW
regressions the operator has not yet reported.

The Phase-9.5 morning report and bug catalog audit the *pre-Track-C/D* commit
(`46f0a33`), so none of these Track-C/D regressions were caught by that pass — the
catalog explicitly defers every drag/typing/GUI item to OPERATOR-MANUAL, and
Track C/D landed after it.

---

## BUG-1 (HIGH) — Boot crash: autosave restores a plugin panel before the plugin's component is registered → dockview throws during `fromJSON`

**Files:**
- `src/components/PanelHost.tsx:50` (`restoreLastSessionOrDefault(api, …)` in `handleReady`)
- `src/lib/workspace.ts:158-174` (`restoreLastSessionOrDefault` → `deserializeWorkspace` → `api.fromJSON`)
- `src/lib/workspace.ts:81` (`deserializeWorkspace` → `api.fromJSON(workspace.layout)`)
- `src/lib/plugin-bootstrap.ts:251-282` (`bootstrapPlugins` is async; appends plugin modules only after `getSidecarBaseUrl()` + `loadPlugin` resolve)

**Root cause (verified against dockview source):**
`bootstrapPlugins()` in `page.tsx` is fired with `void bootstrapPlugins().then(...)`
and is fully async — it awaits `resolvePersistence()` (which awaits
`getSidecarBaseUrl()`) and then `await runtime.loadPlugin(...)` *before* calling
`useModulesStore.getState().appendModules([pluginModule])`. So plugin panel
components (e.g. tradesa-v2's `panelComponents`, wired via `PLUGIN_COMPANIONS`)
are NOT in the `components` map until well after the sidecar port resolves.

`DockviewReact` mounts as soon as `modules.length > 0` (after the *synchronous*
`registerModules(vystedModules)`), so `handleReady` fires and calls
`restoreLastSessionOrDefault(api, …)` while the plugin components are still absent.
If the autosaved `__autosave__` layout contains a plugin panel (the user opened a
tradesa-v2 panel last session and it was debounce-saved), `api.fromJSON()`
re-creates that panel. dockview instantiates panel content **eagerly** during
`fromJSON`:

- `dockview-core/.../deserializer.js:31` `panel.init(...)` →
- `dockview-core/.../dockviewPanelModel.js:70` `createContentComponent` →
- `dockview/.../dockview.js:97` `createComponent` → `new ReactPanelContentPart(id, props.components[name], …)` with `props.components[name] === undefined` →
- `dockview/.../reactContentPart.js:30` `init` → `new ReactPart(…, undefined, …)` →
- `dockview/.../react.js:96` `ReactPart` ctor calls `this.createPortal()` →
- `dockview/.../react.js:115` `if (!isReactComponent(this.component)) throw new Error('Dockview: Only React.memo(...), React.ForwardRef(...) and functional components are accepted as components')`.

That throw is synchronous inside `api.fromJSON()`. It is caught by the `try/catch`
in `restoreLastSessionOrDefault` — BUT `fromJSON` has already partially mutated the
dockview grid before throwing, so the subsequent `applyDefaultLayout(api,
enabledPanelIds)` (line 173, OUTSIDE the try) runs `api.addPanel(...)` against a
half-deserialized/corrupt grid. Best case the restored session is silently lost;
worst case `addPanel` throws uncaught and React blanks the whole app (no error
boundary wraps `PanelHost`). This matches the reported "boot crash".

**Repro:** launch app → open a tradesa-v2 plugin panel → drag/dock anything (so the
debounced autosave fires) → quit → relaunch. On relaunch the autosave layout
references `tradesa-*` panels whose components register asynchronously after
`handleReady`, so `fromJSON` throws.

**Severity:** HIGH — crashes/blanks the cockpit on relaunch for any user who used a
plugin panel; this is the new always-on persistence path so it is on the default
launch flow once a plugin panel has ever been opened. Confidence 0.82 (the throw
path is source-confirmed; the only uncertainty is whether the partial-`fromJSON` +
`applyDefaultLayout` recovers gracefully or hard-crashes — both are regressions).

**Fix:** restore the autosaved layout only after `bootstrapPlugins()` resolves, OR
gate the restore on every referenced component existing in the current `components`
map and skip-to-default otherwise, OR wrap `PanelHost` in a React error boundary
that falls back to `applyDefaultLayout` on a clean (cleared) grid. Cleanest:
sequence the restore behind plugin bootstrap — have `page.tsx`'s
`bootstrapPlugins().then(...)` signal readiness, and have `handleReady` wait for it
(or have the restore call `api.clear()` before `applyDefaultLayout` in the catch so
the fallback always starts from a clean grid).

---

## BUG-2 (MEDIUM) — Autosave persists the *default* layout on first launch, defeating its own "first autosave reflects a genuine user change" guarantee

**Files:** `src/components/PanelHost.tsx:51-64`, `src/lib/workspace.ts:181-205` (`autosaveLayout`)

**Root cause:** the comment at `PanelHost.tsx:48-49` claims the subscription is
attached *after* restore "so the first autosave reflects a genuine user change, not
the restore itself." That only suppresses the *synchronous* layout events fired
during `applyDefaultLayout`/`fromJSON`. dockview also emits `onDidLayoutChange`
asynchronously from its own ResizeObserver-driven relayout/settling **after** mount
(after the `.finally()` has already subscribed). Those fire the 1500 ms debounce →
`autosaveLayout()` writes the *untouched default layout* into `__autosave__`. So a
user who never customizes anything still gets an autosave slot, and the "fall back
to default when none exists" branch becomes effectively dead after first launch.

**Severity:** MEDIUM — mostly benign, but it (a) makes BUG-1 reachable even for users
who never explicitly saved a layout, (b) means "Reset to default" + relaunch does
not actually return to a pristine default (the stale autosave wins), and (c)
silently issues a sidecar POST on every boot. Confidence 0.7 (the exact set of
post-mount async layout events is dockview-version-dependent, but at minimum the
initial post-layout settle fires).

**Fix:** track a "user has interacted" flag (first real `onDidLayoutChange` after a
small settle delay, or hook into actual drag/dock/close events) before enabling
autosave; or compare the serialized layout against the just-restored one and skip
the no-op write.

---

## BUG-3 (MEDIUM) — "Set default" provider button is hidden for every key-requiring provider until a key is configured, so on first run only Ollama is selectable as default

**File:** `src/components/SettingsPanel.tsx:128` — `{(configured || !needsKey) && !isDefault && (...)}`

**Root cause:** the button renders only when `configured === true` (key present in
keychain) OR `!needsKey` (Ollama). `status` starts `{}` and is filled by `refresh()`
probing the keychain; for the common first-run state (no keys configured yet — which
is *exactly* when a user is in Settings deciding their default), every key-requiring
provider has `configured === false`, so its "Set default" button is suppressed.
Ollama is the only provider with `requiresKey: false`
(`src/store/llm-providers.ts:36-41`), so it is the only row that ever shows "Set
default" before a key exists. This precisely reproduces the operator's
"set-as-default only works for Ollama" report.

The deeper issue: `defaultProviderId` defaults to `"anthropic"`
(`llm-providers.ts:74`), and once a configured provider IS set as default the button
correctly works — so this is a *discoverability/ordering* defect, not a dead handler.
But the chat path silently falls back: `ChatSidebar` reads `defaultProviderId`,
which can point at an unconfigured provider, then blocks with "no API key set for
…" (`ChatSidebar.tsx:155-163`).

**Severity:** MEDIUM — the headline default-provider picker is unusable for the
intended first-run flow; users perceive the feature as broken. Confidence 0.85.

**Fix:** always render "Set default" (it is a pure preference, not gated on a key) —
or, better, only show it for `configured || !needsKey` but ALSO surface that the
chosen default needs a key. Note `defaultProviderId` is also NOT persisted anywhere
(plain in-memory `set`), so the chosen default is lost on relaunch — see BUG-7.

---

## BUG-4 (MEDIUM) — Saving a named layout does not update the active workspace name, so the just-saved layout is never marked "active" and an immediate re-save/overwrite UX is confusing

**Files:** `src/components/SettingsPanel.tsx:233-237` (save form), `src/lib/workspace.ts:111-127` (`saveWorkspace` — never calls `setName`)

**Root cause:** the LayoutsSection "active" badge is driven by
`useWorkspaceStore(s => s.name)` (`SettingsPanel.tsx:185`, `:270`). On launch the
restore path sets `name` to `"default"` (`workspace.ts:166`). When the user saves
"My Cockpit", `saveWorkspace("My Cockpit")` persists it but never calls
`setName`, so the active name stays `"default"`. The new entry appears in the list
WITHOUT the "active" badge, even though it is literally the current layout. The only
way the badge moves is via `loadWorkspace` (which DOES call `setName` through
`deserializeWorkspace`). Inconsistent: save ≠ active, load = active.

**Severity:** MEDIUM (UX correctness). Confidence 0.9 — `saveWorkspace` provably
never touches `setName`; `loadWorkspace`/`deserializeWorkspace` does.

**Fix:** `saveWorkspace` (or the form's `onSubmit`) should
`useWorkspaceStore.getState().setName(trimmed)` after a successful save.

---

## BUG-5 (LOW) — `resetToDefaultLayout` does not reset the modules `enabled` map or chart drawings, so "Reset to default" after loading a module-disabling workspace yields a layout missing panels

**File:** `src/store/workspace.ts:75-89` (`resetToDefaultLayout`)

**Root cause:** `resetToDefaultLayout` calls `api.clear()` + `applyDefaultLayout` but
computes `enabledPanelIds` from the *current* `enabledModules()`. If the user
previously loaded a workspace that disabled modules (`setEnabledMap` from
`deserializeWorkspace`), those modules stay disabled, so "Reset to default" produces
a default layout with panels silently skipped (`default-layout.ts:80-82`
`if (!enabledPanelIds.has(panel.id)) continue;`). It also leaves stale
`chartDrawings` in the store. A user expecting "Reset to default" to return to the
factory cockpit gets a partial one.

**Severity:** LOW (needs a module-disabling workspace first; modules can only be
toggled in Settings). Confidence 0.75.

**Fix:** `resetToDefaultLayout` should re-enable all first-party modules (or at least
recompute against the full registry) and clear chart drawings, to be a true reset.

---

## BUG-6 (LOW) — `restoreLastSessionOrDefault` swallows the autosaved `enabledModules`/`chartDrawings` silently when `fromJSON` partially applies, and never logs the failure

**File:** `src/lib/workspace.ts:159-176`

**Root cause:** the `catch {}` is empty (only a comment). When restore fails for ANY
reason — malformed JSON, missing component (BUG-1), schema drift — the user's saved
session is discarded with zero diagnostics, and `setEnabledMap(workspace.enabledModules)`
may have ALREADY run before `api.fromJSON` threw (`deserializeWorkspace.ts:82` runs
`setEnabledMap` *before* `api.fromJSON` at line 83), leaving the modules store in the
restored state while the layout falls back to default — an inconsistent half-applied
state. Track A's own theme this phase was "stop swallowing failures silently"
(plugin-bootstrap port-0 logging, SSE malformed-frame logging); this new restore
path regressed that discipline.

**Severity:** LOW (diagnostics + minor state inconsistency). Confidence 0.8 — the
ordering in `deserializeWorkspace` (setEnabledMap then fromJSON) is explicit.

**Fix:** log the caught error (`console.warn`), and in the catch reset the modules
store / clear the grid before `applyDefaultLayout` so the fallback is fully
consistent.

---

## BUG-7 (MEDIUM) — `defaultProviderId` chosen via the new picker is not persisted; it resets to "anthropic" on every relaunch

**Files:** `src/store/llm-providers.ts:74-75` (`defaultProviderId: "anthropic"`,
`setDefaultProviderId: (id) => set({ defaultProviderId: id })`), `SettingsPanel.tsx:131`

**Root cause:** the Track-C Settings "default-provider picker" is a brand-new
user-facing affordance, but the store it writes to has no persistence — it is a plain
in-memory Zustand value seeded to `"anthropic"`. Every relaunch resets the user's
chosen default. Worse, `useLLMProvidersStore.refresh()` (called at app startup from
ChatSidebar) replaces `providers` but leaves `defaultProviderId` — so the only reason
it isn't *also* clobbered is luck. The picker therefore looks functional in-session
but silently forgets the choice across launches, which (combined with BUG-3) makes
the whole "AI Providers default" surface feel broken.

**Severity:** MEDIUM — a new headline Settings control with no persistence.
Confidence 0.9.

**Fix:** persist `defaultProviderId` (sidecar workspace blob, or keychain-adjacent
preference). Note the autosave/workspace blob already persists `enabledModules` +
`chartDrawings` — the default provider could ride along the same channel, or a small
prefs endpoint.

---

## BUG-8 (LOW) — Design system: `body > * { z-index: 1 }` forces a stacking context on every direct body child (including Radix dialog/portal roots), changing overlay stacking app-wide

**File:** `src/app/globals.css:90-94`

**Root cause:** Track D added a fixed `body::before` grain overlay (`z-index: 0`) and
`body > * { position: relative; z-index: 1 }` to keep content above it. Radix
(shadcn) Dialog/Popover/Tooltip portals render as **direct children of `body`**, so
they now all receive `position: relative; z-index: 1` and form sibling stacking
contexts. Within a single shared `z-index: 1` tier, overlays stack purely by DOM
order. The internal `z-50` etc. on dialog content only matters *within* each portal's
own context, not across portals. The CommandPalette, WorkspaceDialog, and
KeyEntryDialog all portal to body; their relative stacking is now DOM-order-dependent
rather than honoring their internal z-index intents. This is a latent layering
regression (e.g. KeyEntryDialog opened from inside the CommandPalette flow, or a
tooltip over a dialog).

**Severity:** LOW (no crash; manifests as occasional overlay-behind-overlay). Needs
live GUI confirmation. Confidence 0.55 — depends on portal mount order which I could
not drive headlessly.

**Fix:** scope the grain-vs-content layering to the app shell only
(`main { position: relative; z-index: 1 }` instead of `body > *`), leaving portal
roots untouched so their own z-index stacking is preserved.

---

## BUG-9 (LOW, design-system polish) — global `font-feature-settings: "calt" 0` disables contextual alternates everywhere; header `h-8 → h-9` + new onboarding banner reduce panel vertical space

**Files:** `src/app/globals.css:61-63` (`"calt" 0`), `src/app/page.tsx:73` (`h-9`
header) + `:118` (`<OnboardingBanner />` adds a `py-2` row)

**Root cause / note:** `"calt" 0` globally disables ligatures/contextual alternates,
which is deliberate for tabular gauge readouts but also kills JetBrains Mono's coding
ligatures in any code-like surface (node-editor expressions, JSON views). The toolbar
grew from `h-8` to `h-9` and the onboarding banner adds a persistent row until a key
is configured — together they shrink the dockview viewport, which on first launch
(no key → banner shown) is the worst case. Not a bug per se; flagged because the
visual-verification gate is operator-manual and these are app-wide changes.

**Severity:** LOW (cosmetic/intentional). Confidence 0.6.

---

## Verified NON-issues (checked and cleared)

- **Tailwind utilities for the new tokens** (`text-lume`, `bg-charcoal-925`,
  `text-charcoal-300`, `hud-label`, `tick-rule`, `instrument-bezel`) ARE emitted in
  the built CSS (`out/_next/static/chunks/*.css`), and the new token vars
  (`--color-charcoal-875/925/300/500`, `--color-lume`, `--color-brass-*`,
  `--ease-instrument`) are all defined. No missing-class invisible-styling regression.
- **dockview theme cascade order:** `.dockview-theme-vysted` (byte offset ~157378)
  appears AFTER `.dockview-theme-dark` (~65227) in the same bundled CSS file, so the
  Vysted override still wins the equal-specificity cascade. The `#252526` value seen
  for `--dv-tabs-and-actions-container-background-color` is the base dark theme's,
  correctly overridden.
- **`OnboardingBanner` `useProviderKeysStore(s => s.hasAnyKey())`** returns a stable
  primitive boolean, so no Zustand getSnapshot re-render loop.
- **No circular import** between `store/workspace`, `lib/workspace`, and
  `config/default-layout` (default-layout imports only dockview types).
- **`KeyEntryDialog.onSaved` → `refreshOne`** correctly flips status to "configured",
  which hides the onboarding banner — that wiring works.
- typecheck / lint / 612 vitest / static build all green at HEAD (`4dba230`).

---

## Priority for the operator

1. **BUG-1** (boot crash) — confirmed root cause; gate restore behind plugin
   bootstrap or add an error boundary + clean-grid fallback.
2. **BUG-3 + BUG-7** (default-provider picker unusable + not persisted) — together
   these make the headline new Settings surface look broken.
3. **BUG-2** (autosave-of-default) — makes BUG-1 reachable for non-customizing users
   and breaks "Reset to default" durability.
4. **BUG-4 / BUG-6 / BUG-5 / BUG-8 / BUG-9** — correctness/polish follow-ups.
