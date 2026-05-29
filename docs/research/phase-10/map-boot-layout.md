# Phase 10 — Boot + dockview layout-restore map & root-cause of the boot crash

**Scope:** map the app-boot path and the Phase 9.5 (Track C) layout-restore-on-boot
path, root-cause the live runtime error `applyDefaultLayout / element.parentElement is null`,
and document the named-layout save/load/delete + reset-to-default surfaces.

**Method:** read the actual installed source. dockview is `6.2.2` (`package.json:31`,
`node_modules/dockview/package.json` version `6.2.2`). The React wrapper
`DockviewReact` lives at `node_modules/dockview/dist/esm/dockview/dockview.js`.
`dockview-core` (the layout/gridview engine that emits the actual
`parentElement is null`) is an unbundled peer/dep and is **not installed** in this
travel-rig `node_modules` (partial install), so the minified core line cannot be
cited from disk — the mechanism is established from the React wrapper + the app
code + the operator's verbatim error string.

---

## 1. The boot ordering, traced call-by-call

### 1.1 `src/app/page.tsx` — the page mount effect (runs once on mount)

`Page()` renders `<PanelHost />` inside the flex column (`src/app/page.tsx:124`).
On mount, a single `useEffect(..., [])` (`src/app/page.tsx:24-65`) does, in order:

1. `useModulesStore.getState().registerModules(vystedModules)` (`page.tsx:29`) —
   **synchronous**. This is what flips `modules` from `[]` to the full registry and
   sets every module `enabled: true` (`src/store/modules.ts:49-53`).
2. seed command palette (`page.tsx:30`).
3. `void useAppStore.getState().connectSidecar()` (`page.tsx:31`) — fire-and-forget;
   the sidecar port/health is **not** awaited here.
4. `void bootstrapPlugins().then(...)` (`page.tsx:38-42`) — async; later calls
   `appendModules` which mutates the `modules` slice again (relevant below).

### 1.2 `src/components/PanelHost.tsx` — the gating + dockview mount

`PanelHost` reads `modules` from the store (`PanelHost.tsx:25`). It renders a
"Loading modules…" placeholder while `modules.length === 0`
(`PanelHost.tsx:67-73`) and only renders `<DockviewReact .../>` once modules exist
(`PanelHost.tsx:75-79`). Because `registerModules` runs synchronously inside
page's mount effect, on the very next render `modules.length > 0`, so `DockviewReact`
mounts almost immediately. **There is no `key` on `DockviewReact`** and `components`
is memoised on `[modules]` (`PanelHost.tsx:29`).

### 1.3 `DockviewReact` internal mount (the load-bearing detail)

`node_modules/dockview/dist/esm/dockview/dockview.js:27-111`. The component holds
`domRef` (`:28`) and `dockviewRef` (`:29`). The **empty-dep** init effect
(`:50-111`) is where everything happens:

```js
const api = createDockview(domRef.current, { ...coreOptions, ...frameworkOptions }); // :100
const { clientWidth, clientHeight } = domRef.current;                                // :101
api.layout(clientWidth, clientHeight);                                               // :102
if (props.onReady) { props.onReady({ api }); }                                       // :103-105
dockviewRef.current = api;                                                           // :106
return () => { dockviewRef.current = undefined; api.dispose(); };                    // :107-110  (cleanup)
```

Two facts that decide the root cause:

- **`onReady` fires synchronously inside the mount effect, while `domRef.current` is
  attached to the live DOM** (line 100-104 all run in one tick). So at the instant
  `onReady` runs, the element is connected and sized — `applyDefaultLayout` called
  *synchronously here* (the pre-Track-C behaviour) is safe.
- **The effect's cleanup calls `api.dispose()`** (`:109`), which tears down the
  dockview gridview and detaches its DOM. After dispose, the api's internal grid
  elements are orphaned (`parentElement === null`).

---

## 2. What Phase 9.5 / Track C changed (the regression)

Commit **`40746bd`** — `feat(ux): panel-freedom layouts + discoverable BYOK settings
& onboarding (Track C)` (merged via `644b9b6`). It is the **only** change to
`PanelHost.tsx`'s ready path since the layout shipped (`git log -- src/components/PanelHost.tsx`
shows just `b7572b1` scaffold → `ae4a6b1` default-layout → `40746bd` Track C; no later fix).

The diff replaced a **synchronous** call with an **async, deferred** one. Before:

```js
function handleReady(event) {
  useWorkspaceStore.getState().setDockviewApi(event.api);
  const enabledPanelIds = new Set(...enabledPanels...);
  applyDefaultLayout(event.api, enabledPanelIds);   // SYNC — runs inside the mount effect, element attached
}
```

After (current `PanelHost.tsx:39-65`):

```js
function handleReady(event) {
  const api = event.api;
  useWorkspaceStore.getState().setDockviewApi(api);
  const enabledPanelIds = new Set(...enabledPanels...);
  void restoreLastSessionOrDefault(api, enabledPanelIds).finally(() => {  // ASYNC — addPanel deferred past awaits
    /* wire onDidLayoutChange → debounced autosaveLayout */
  });
}
```

`restoreLastSessionOrDefault` (`src/lib/workspace.ts:158-177`) is `async` and its
**first statement awaits a network round-trip before it ever touches the api**:

```js
const response = await fetch(await workspaceUrl(AUTOSAVE_LAYOUT_NAME)); // :163
if (response.ok) { deserializeWorkspace(workspace); ... return true; }  // :164-171  → api.fromJSON
...                                                                     // catch falls through
applyDefaultLayout(api, enabledPanelIds);                              // :175  → api.addPanel(...)
return false;
```

Both terminal branches mutate the api **after** the await:

- restore branch → `deserializeWorkspace` → `api.fromJSON(workspace.layout)`
  (`src/lib/workspace.ts:83`)
- fallback branch → `applyDefaultLayout` → `api.addPanel({...})` then
  `panel.api.setSize(...)` (`src/config/default-layout.ts:87-111`)

`workspaceUrl()` itself awaits `getSidecarBaseUrl()` (`workspace.ts:93-97`), which
awaits `invoke("get_sidecar_port")` (`src/lib/sidecar-client.ts:63`). At boot the
Tauri core may still be spawning/health-checking the sidecar, so this gap is **not
a microtask — it is an unbounded await** (a Tauri IPC round-trip plus an HTTP
round-trip to a localhost port that may not be listening yet). **The window between
"element mounted / onReady fired" and "addPanel/fromJSON actually runs" is wide
open**, which is exactly what the operator means by "addPanel appears to fire before
the dockview container is mounted" — more precisely, it fires *after the container's
mount effect has already been torn down/re-run*.

---

## 3. Root cause — the precise null-deref site and why it fires "before mount"

The crash is a **use-after-dispose on a detached dockview api**. Two concrete
trigger paths, both opened by the Track-C async deferral:

### Mechanism A — React StrictMode dev double-invoke (the dominant cause)

`next.config.ts` does **not** set `reactStrictMode` (it is `output: "export"` +
`images.unoptimized` only — `next.config.ts`). Next's default is `reactStrictMode: null`
(`node_modules/next/dist/server/config-shared.js:118`), and the App-Router dev server
mounts under React StrictMode. StrictMode intentionally runs every effect
**mount → cleanup → mount** to surface exactly this class of bug. Sequence:

1. `DockviewReact` mount-effect #1 runs: `createDockview` → `api.layout` → `onReady({api:A})`
   fires (`dockview.js:100-104`). `handleReady` kicks off
   `restoreLastSessionOrDefault(A, …)`, which suspends on `await fetch`.
2. StrictMode immediately runs effect-#1 **cleanup**: `dockviewRef.current = undefined;
   A.dispose()` (`dockview.js:107-110`). **Api A's grid DOM is now detached —
   its elements have `parentElement === null`.**
3. StrictMode runs mount-effect #2: a fresh `createDockview` → new api `B` attached
   to the (re-used) `domRef.current`, new `onReady({api:B})`. The store's
   `dockviewApi` is overwritten with `B` (`PanelHost.tsx:41`).
4. The pending `await fetch` from step 1 resolves and the **stale closure** runs
   `applyDefaultLayout(A, …)` → `A.addPanel(...)` / or `A.fromJSON(...)` on the
   **disposed api A**. dockview-core walks A's gridview to insert/position the new
   branch node and dereferences the orphaned element's `parentElement` (null) →
   `TypeError: ... element.parentElement is null`. The stack top is inside
   `applyDefaultLayout` because that is the frame that re-entered dockview after the
   await (matching the operator's `applyDefaultLayout / element.parentElement is null`).

This is deterministic in dev: the dispose in step 2 *always* happens before the
fetch resolves, because a localhost fetch + Tauri IPC is far slower than a synchronous
StrictMode cleanup.

### Mechanism B — module-slice churn / unmount race (can bite prod too)

Even without StrictMode, `PanelHost` can unmount or `DockviewReact` can be torn down
while the fetch is in flight. `bootstrapPlugins().then(...)` (`page.tsx:38`) calls
`appendModules`, mutating `modules` (`store/modules.ts:54-73`); `page.tsx`'s
`unsubscribeModules` (`page.tsx:55-59`) refreshes the palette but does not remount
`PanelHost`. However, any HMR reload, a fast navigation, or the page-effect teardown
(`page.tsx:60-64` → `teardown?.()`) during the boot fetch window detaches the
dockview and the same stale-closure `applyDefaultLayout(A,…)` lands on a disposed api.
Less common than A, but the same defect class, and the reason this should not be
"fixed" by merely disabling StrictMode.

### Why the pre-Track-C code never crashed

Pre-Track-C `applyDefaultLayout(event.api, …)` ran **synchronously inside the
`onReady` call** — i.e. inside `DockviewReact`'s mount effect at lines 100-105, before
any cleanup/dispose could interleave and before the stale-closure window exists. The
regression is purely the introduction of an `await` between `onReady` and the first
`addPanel`.

---

## 4. The fix

### 4.1 Minimal correct fix — guard the deferred mutation against a disposed/replaced api

Make `restoreLastSessionOrDefault` (and the autosave wiring) bail if the api it was
handed is no longer the live one when the await resolves. The store already holds the
current api (`useWorkspaceStore.getState().dockviewApi`), so re-check identity after
the await and skip mutation if it changed:

```ts
// PanelHost.tsx handleReady, after computing enabledPanelIds:
void restoreLastSessionOrDefault(api, enabledPanelIds).finally(() => {
  // If StrictMode/HMR replaced the api while we were awaiting, this api is
  // disposed — do not wire autosave to it.
  if (useWorkspaceStore.getState().dockviewApi !== api) return;
  /* ...existing onDidLayoutChange wiring... */
});
```

and inside `restoreLastSessionOrDefault`, before each api mutation:

```ts
// src/lib/workspace.ts — both branches
if (useWorkspaceStore.getState().dockviewApi !== api) return false; // stale api, skip
deserializeWorkspace(workspace); // or applyDefaultLayout(api, enabledPanelIds)
```

This is the smallest change that stops the use-after-dispose: the stale closure from
the disposed mount-effect #1 sees `dockviewApi === B !== A` and no-ops, while mount
#2's own `onReady` does the real restore against the live api `B`.

(dockview exposes no public `isDisposed`/`disposed` flag on `DockviewApi` we can rely
on across 6.2.2, so the store-identity check is the robust, version-stable signal.)

### 4.2 Robust fix — own the abort + identity guard end-to-end (recommended)

Combine three measures:

1. **Per-mount epoch/abort.** In `PanelHost`, give each `handleReady` an
   `AbortController` (or a monotonically-incrementing `mountEpoch` ref). Pass it to
   `restoreLastSessionOrDefault`; after every await, check `signal.aborted` /
   `epoch === currentEpoch` and return early. Tear the controller down in the
   `DockviewReact` cleanup so a disposed mount can never re-enter dockview.
2. **Store-identity guard** (as in 4.1) as a belt-and-suspenders check inside
   `workspace.ts` mutation points (`api.fromJSON`, `api.addPanel`).
3. **A regression test that mounts a real `DockviewReact`** and asserts no throw when
   the api is disposed mid-restore. The current suite cannot catch this:
   `src/lib/workspace.test.ts` uses a hand-rolled fake api (`createFakeDockviewApi`,
   `:24-35`) whose `fromJSON` just swaps a plain object — it never touches the DOM or
   dispose lifecycle, so the boot race is structurally invisible to it.

`applyDefaultLayout` is also worth hardening defensively (wrap the body so a throw on
a stale api degrades to a no-op rather than an uncaught boot crash), but that treats
the symptom; the identity/abort guard removes the cause.

---

## 5. Named-layout save / load / delete + reset-to-default (Track C surfaces)

All named layouts are sidecar-owned files; the frontend half is `src/lib/workspace.ts`.

### Serialization shape
`SerializedWorkspace` (`workspace.ts:26-40`) = `{ name, layout: api.toJSON(),
enabledModules, chartDrawings? , [key]: unknown }`. `serializeWorkspace`
(`:55-66`) throws `WorkspaceError("The panel layout is not ready yet.")` if
`dockviewApi` is null. `deserializeWorkspace` (`:75-90`) restores enabled-map
**first** (`setEnabledMap`, `:82`) so the layout's panel components resolve, then
`api.fromJSON(layout)` (`:83`), then name, then drawings.

### Save
- **Toolbar "Save layout" button** (`src/app/page.tsx:97-105`) → `openSave`
  (`workspace-dialog-store.ts`) → `WorkspaceDialog` save mode
  (`src/modules/platform/WorkspaceDialog.tsx`) → `saveWorkspace(name)`.
- **Settings → Layouts** name field + Save (`SettingsPanel.tsx:227-249`) →
  `saveWorkspace(name)`.
- `saveWorkspace` (`workspace.ts:116-130`): trims/validates name (empty →
  `WorkspaceError`), `serializeWorkspace`, `POST /workspace` with
  `{ name, workspace }`; non-2xx → `WorkspaceError`.

### List / Load / Delete
- `listWorkspaces` (`workspace.ts:100-110`) `GET /workspace` → `string[]`.
- Settings filters out reserved names via `isReservedLayoutName` (`name.startsWith("__")`,
  `store/workspace.ts:16-18`) so the `__autosave__` slot stays hidden
  (`SettingsPanel.tsx:191`).
- `loadWorkspace` (`workspace.ts:133-149`) `GET /workspace/{name}` → parse →
  `deserializeWorkspace`. Wired from Settings "Load" (`SettingsPanel.tsx:277`) and the
  cmd+K load dialog.
- `deleteWorkspace` (`workspace.ts:207-216`) `DELETE /workspace/{name}`, then `reload()`
  (`SettingsPanel.tsx:285-289`).

### Reset to default
- Settings "Reset to default" button (`SettingsPanel.tsx:250-252`) →
  `useWorkspaceStore.resetToDefaultLayout` (`store/workspace.ts:75-89`):
  `api.clear()` → recompute enabled panel ids → `applyDefaultLayout(api, ids)` →
  `set({ name: "default" })`. This path is **synchronous and safe** (no await), and
  is the same `applyDefaultLayout` the buggy boot path defers.

### Autosave / restore-on-boot
- Reserved slot name `__autosave__` (`store/workspace.ts:13`).
- `autosaveLayout` (`workspace.ts:184-204`): no-op if api null; `POST /workspace`
  under `__autosave__`; best-effort (swallows failures). Wired in `PanelHost`
  via `api.onDidLayoutChange` debounced 1500 ms (`PanelHost.tsx:51-57`,
  `AUTOSAVE_DEBOUNCE_MS = 1500` `:12`) — but only after `restoreLastSessionOrDefault`
  resolves (`.finally`, `:50`).
- `restoreLastSessionOrDefault` (`workspace.ts:158-177`): `GET /workspace/__autosave__`;
  if 200 → restore + present as name `"default"` (`:169`); else/throw → fall through to
  `applyDefaultLayout`. **This is the crash site (§3).**

---

## 6. Why the test suite missed it

`src/lib/workspace.test.ts` only exercises the pure serialize/deserialize/save/load
data round-trip against `createFakeDockviewApi` (`:24-35`), which has no DOM, no
mount lifecycle, and no `dispose`. There is **no test that mounts `DockviewReact`**,
and none that exercises `restoreLastSessionOrDefault` against a real api under a
StrictMode-style double-mount. The boot race is therefore structurally uncatchable by
the current suite — `pnpm ci-local` (which runs vitest, not the GUI) stays green while
the app crashes on launch. Any fix must ship with a real-mount regression test (§4.2.3).

---

## 7. Summary

- **Crash:** `TypeError: element.parentElement is null`, top frame `applyDefaultLayout`,
  on boot.
- **Root cause:** Track C (`40746bd`) replaced the synchronous in-`onReady`
  `applyDefaultLayout(event.api,…)` with `void restoreLastSessionOrDefault(api,…)`,
  which awaits `getSidecarBaseUrl()` + `fetch(/workspace/__autosave__)` **before**
  calling `addPanel`/`fromJSON`. Under React StrictMode's dev mount→cleanup→mount
  (Next default; `reactStrictMode` unset in `next.config.ts`), the first mount's
  `api.dispose()` (`dockview.js:109`) detaches the gridview before the fetch resolves;
  the stale closure then re-enters the **disposed** api, which dereferences an orphaned
  element's null `parentElement`.
- **It is not literally "addPanel before mount"** — it is addPanel on a **disposed/replaced**
  api after the mount effect was torn down. Same observable error, different precise mechanism.
- **Minimal fix:** after each await in `restoreLastSessionOrDefault` (and before wiring
  autosave in `PanelHost`), bail if `useWorkspaceStore.getState().dockviewApi !== api`.
- **Robust fix:** per-mount AbortController/epoch passed into the restore, identity guard
  at every api mutation, plus a real-`DockviewReact`-mount regression test.

**Files:** `src/components/PanelHost.tsx:39-65`, `src/lib/workspace.ts:158-177` (+`:83`,
`:175`), `src/config/default-layout.ts:75-113`, `src/store/workspace.ts:75-89`,
`src/lib/sidecar-client.ts:52-66`, `node_modules/dockview/dist/esm/dockview/dockview.js:50-111`.
**Commit:** `40746bd` (Track C), merged `644b9b6`.
