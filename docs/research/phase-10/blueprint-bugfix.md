# Phase 10 — Bug-fix track: ordered execution blueprint

**Author:** Bug-fixes track architect. **Baseline:** HEAD `0.8.0`, `pnpm typecheck`
clean (verified this session), `pnpm test` 612 green per `hunt-regression-95.md`.
Every claim below was re-verified against the actual source this session (file:line
cited). The lead builds directly from this — no stubs, exact diffs.

**§6.5 LOCKED-file audit (mandatory gate):** NONE of the eight fixes below touch a
locked file. The locked set is `sidecar/models/audit_log.py`, `sidecar/models/kill_switch.py`
(+ `src-tauri/src/kill_switch.rs`), `sidecar/models/broker_base.py`, `types/plugin.ts`,
`tests/test_safety_end_to_end.py`. Fix 8 (KillSwitchToolbar) touches the **frontend**
safety surface `src/modules/safety/KillSwitchToolbar.tsx`, which is explicitly NOT in
the locked set (confirmed: the locked safety files are Rust/Python + the contract +
the e2e test). Fix 6 (icon render) and Fix 7 (defaultSize) deliberately do **not**
edit `types/plugin.ts` — the `icon?` and `defaultSize?` fields already exist there
(`types/plugin.ts:99-102`, `:127-128`, `:156-157`); both fixes are pure consumer-side.

---

## Ordering rationale (dependency + risk)

The boot crash (Fix 1) is sequenced first and **alone** because it blocks GUI
verification of literally everything else: the app crashes on launch under
`pnpm tauri dev` (StrictMode), so no other fix can be screenshot-verified until it
lands. Fix 2 (sidecar readiness) is second because it unblocks *populated* GUI
verification (per the CLAUDE.md visual protocol — empty panels hide bugs), and
because three later error-surface fixes are only observable against a live sidecar.
Fix 3 (settings) and the remaining fixes are independent and ordered by
severity/blast-radius. The two HIGH leak fixes (Fix 1 epoch work, Fix 5 plugin
leak) share the same StrictMode-async-teardown root pattern and are sequenced
adjacently so the lead builds the mental model once.

| # | Title | Severity | Files | Verify by |
|---|-------|----------|-------|-----------|
| 1 | Boot crash: use-after-dispose in `restoreLastSessionOrDefault` (+ plugin-component-missing variant) | HIGH | `PanelHost.tsx`, `workspace.ts`, (test) | build + `tauri dev` boot + screenshot |
| 2 | Cold-boot bind race: News/Portfolio latch permanent error | HIGH | `sidecar-client.ts`, `NewsFeedPanel.tsx`, `PortfolioPanel.tsx`, (test) | curl + `tauri dev` cold-boot + populated screenshot |
| 3 | Settings double-scrollbar/blue-void + "Set default" Ollama-only | HIGH(UX) | `SettingsPanel.tsx`, `globals.css` | screenshot scroll + screenshot all rows |
| 4 | Plugin runtime + 30s health-interval leak on early teardown | HIGH | `page.tsx`, `store/plugins.ts` | unit test (interval-count) + dev console |
| 5 | KillSwitchToolbar OS-listener leak → multi-fire | MEDIUM | `KillSwitchToolbar.tsx`, (test) | unit test + dev shortcut |
| 6 | Node palette redundant non-draggable "Plugin Nodes" section | MEDIUM | `node-palette.tsx`, `node-palette.test.tsx` | test + screenshot palette |
| 7 | `command.icon` / `PanelSpec.icon` never rendered | LOW | `CommandPalette.tsx`, new `src/lib/lucide-dynamic.tsx` | screenshot cmd+K |
| 8 | `PanelSpec.defaultSize` never applied | LOW | `store/workspace.ts` (functional wire) | screenshot panel size |

---

## FIX 1 — Boot crash (use-after-dispose) — HIGH, build-blocking

### Root cause (verified)

`PanelHost.handleReady` (`src/components/PanelHost.tsx:39-65`) fires
`void restoreLastSessionOrDefault(api, enabledPanelIds).finally(...)` at line 50.
`restoreLastSessionOrDefault` (`src/lib/workspace.ts:158-177`) **awaits a network
round-trip before touching the api**: `await fetch(await workspaceUrl(AUTOSAVE_LAYOUT_NAME))`
at `workspace.ts:163` (`workspaceUrl` → `getSidecarBaseUrl` → `invoke("get_sidecar_port")`,
`sidecar-client.ts:63`). Both terminal branches mutate the api **after** that await:
`deserializeWorkspace` → `api.fromJSON` (`workspace.ts:83`) and the fallback
`applyDefaultLayout(api, …)` → `api.addPanel` (`workspace.ts:175`,
`default-layout.ts`).

Under React StrictMode (Next App-Router dev default; `reactStrictMode` unset in
`next.config.ts`), `DockviewReact`'s mount effect runs mount → cleanup → mount; the
cleanup calls `api.dispose()` (`node_modules/dockview/dist/esm/dockview/dockview.js:107-110`)
which detaches the gridview (orphaned element `parentElement === null`). The stale
closure from mount #1 then re-enters the **disposed** api once the fetch resolves →
`TypeError: element.parentElement is null` with `applyDefaultLayout` on the stack.
This is deterministic in dev (localhost fetch + IPC is always slower than the
synchronous StrictMode cleanup). Full mechanism in `map-boot-layout.md` §3.

**Second, compounding variant** (`hunt-regression-95.md` BUG-1): plugin panel
components register *asynchronously* via `bootstrapPlugins().then(...)`
(`page.tsx:38`, which appends modules only after `getSidecarBaseUrl()` + `loadPlugin`
resolve — `plugin-bootstrap.ts:277-284`). If `__autosave__` references a plugin panel
(`tradesa-*`), `api.fromJSON` throws synchronously inside dockview's eager
`createComponent` because `props.components[name]` is `undefined`. The throw is caught
by the `try/catch` at `workspace.ts:162-174`, **but `fromJSON` has already partially
mutated the grid**, and the un-guarded `applyDefaultLayout(api,…)` at `workspace.ts:175`
(outside the try) then runs against a half-deserialized grid.

The store already holds the current api (`useWorkspaceStore.getState().dockviewApi`,
set at `PanelHost.tsx:41`), so api-identity is the robust, version-stable disposed
signal (dockview 6.2.2 exposes no public `isDisposed`).

### Exact code change

**1a — `src/lib/workspace.ts`: guard every api mutation behind a liveness re-check,
and make the fallback start from a clean grid so a partial `fromJSON` can't corrupt it.**

Replace `restoreLastSessionOrDefault` (lines 158-177) with:

```ts
export async function restoreLastSessionOrDefault(
  api: DockviewApi,
  enabledPanelIds: Set<string>,
): Promise<boolean> {
  // The fetch below awaits a Tauri IPC + localhost round-trip. Under
  // StrictMode/HMR the dockview api can be disposed and replaced while we
  // wait, so re-check that THIS api is still the live one before every
  // mutation — touching a disposed api throws `element.parentElement is null`.
  const isLive = () => useWorkspaceStore.getState().dockviewApi === api;
  try {
    const response = await fetch(await workspaceUrl(AUTOSAVE_LAYOUT_NAME));
    if (!isLive()) {
      return false; // api was disposed/replaced during the fetch
    }
    if (response.ok) {
      const workspace = (await response.json()) as SerializedWorkspace;
      if (!isLive()) {
        return false;
      }
      // Skip-to-default if the saved layout references a component that is not
      // yet registered (plugin panels register async after handleReady) — a
      // missing component makes dockview throw mid-`fromJSON`, corrupting the
      // grid for the fallback below.
      if (layoutReferencesUnknownComponent(api, workspace.layout)) {
        applyDefaultLayout(api, enabledPanelIds);
        return false;
      }
      deserializeWorkspace(workspace);
      useWorkspaceStore.getState().setName("default");
      return true;
    }
  } catch (error) {
    // Restore failed — log (Track A discipline) then fall through to default.
    console.warn("[workspace] session restore failed; using default layout.", error);
  }
  if (!isLive()) {
    return false;
  }
  // Always re-base the fallback on a clean grid so a partial fromJSON can't
  // leave a corrupt grid under addPanel.
  api.clear();
  applyDefaultLayout(api, enabledPanelIds);
  return false;
}
```

Add the helper above `restoreLastSessionOrDefault` (uses dockview's public
`api.options` is not available; instead read the component map off the live module
registry the same way `PanelHost` builds it):

```ts
import { collectPanelComponents } from "@/lib/module-registry";
// ...
/**
 * True when the serialized layout references a panel component id that is not
 * currently registered. dockview instantiates content eagerly during fromJSON,
 * so an unknown component throws synchronously and half-mutates the grid.
 */
function layoutReferencesUnknownComponent(
  _api: DockviewApi,
  layout: SerializedDockview,
): boolean {
  const known = new Set(Object.keys(collectPanelComponents(useModulesStore.getState().modules)));
  const panels = (layout as { panels?: Record<string, { contentComponent?: string }> }).panels;
  if (!panels) {
    return false;
  }
  return Object.values(panels).some(
    (panel) => panel.contentComponent !== undefined && !known.has(panel.contentComponent),
  );
}
```

(`SerializedDockview.panels[id].contentComponent` is the dockview 6.2.2 field that
records the component id; verify the exact key against
`node_modules/dockview-core/.../dockviewComponent.js toJSON` at build time — if the
core package is not installed on the travel rig, fall back to reading
`panel.params?.component`/`contentComponent` defensively, treating an unreadable
shape as "unknown" so we conservatively skip-to-default rather than risk the throw.)

**1b — `src/components/PanelHost.tsx`: bail the autosave wiring if the api was
replaced while restore was in flight, and key the autosave-subscription cleanup so a
too-early unmount can't leak it (`hunt-race-async.md` Finding 5).**

Replace `handleReady` (lines 39-65) with an epoch-guarded version:

```ts
const mountEpoch = useRef(0);

useEffect(() => {
  const epoch = ++mountEpoch.current;
  return () => {
    // Bump on unmount so any in-flight restore for this epoch no-ops.
    if (mountEpoch.current === epoch) {
      mountEpoch.current++;
    }
    cleanupRef.current?.();
    cleanupRef.current = null;
  };
}, []);

function handleReady(event: DockviewReadyEvent) {
  const api = event.api;
  const epoch = mountEpoch.current;
  useWorkspaceStore.getState().setDockviewApi(api);
  const enabledPanelIds = new Set(
    useModulesStore.getState().enabledPanels().map((panel) => panel.id),
  );
  void restoreLastSessionOrDefault(api, enabledPanelIds).finally(() => {
    // If StrictMode/HMR replaced the api or unmounted us while awaiting, this
    // api is disposed — do not wire autosave to it.
    if (mountEpoch.current !== epoch || useWorkspaceStore.getState().dockviewApi !== api) {
      return;
    }
    let timer: ReturnType<typeof setTimeout> | null = null;
    const subscription = api.onDidLayoutChange(() => {
      if (timer) {
        clearTimeout(timer);
      }
      timer = setTimeout(() => void autosaveLayout(), AUTOSAVE_DEBOUNCE_MS);
    });
    cleanupRef.current = () => {
      if (timer) {
        clearTimeout(timer);
      }
      subscription.dispose();
    };
  });
}
```

This single epoch ref closes the boot crash (mutation guard via the `isLive` check
in 1a + the `.finally` bail here) AND the autosave-subscription leak (Finding 5: a
unmount-during-restore bumps the epoch so `.finally` no-ops instead of wiring a
subscription the already-fired unmount cleanup can't reach).

### Test to add

`src/lib/workspace.test.ts` (extend) — the existing suite uses a hand-rolled fake api
(`createFakeDockviewApi`, lines 24-35) with no dispose lifecycle, which is exactly
why the boot race is invisible to CI (`map-boot-layout.md` §6). Add two pure-logic
tests that DON'T need a real DOM:

```ts
it("skip-to-default when restore's api is no longer the live api", async () => {
  // Arrange: store.dockviewApi points at a DIFFERENT api than the one passed in.
  const passedApi = makeApi();           // not set as the store's live api
  useWorkspaceStore.getState().setDockviewApi(makeOtherApi());
  fetchMock.mockResolvedValueOnce(okJson(savedWorkspace));
  const restored = await restoreLastSessionOrDefault(passedApi, new Set());
  expect(restored).toBe(false);
  expect(passedApi.fromJSON).not.toHaveBeenCalled();
  expect(passedApi.addPanel).not.toHaveBeenCalled();
});

it("skip-to-default (clean grid) when saved layout references an unknown component", async () => {
  const api = makeApi();
  useWorkspaceStore.getState().setDockviewApi(api);
  fetchMock.mockResolvedValueOnce(okJson(workspaceWithPluginPanel)); // contentComponent: "tradesa-x"
  const restored = await restoreLastSessionOrDefault(api, new Set(["chart"]));
  expect(restored).toBe(false);
  expect(api.fromJSON).not.toHaveBeenCalled();
  expect(api.clear).not.toHaveBeenCalled();          // unknown-component path returns before clear
  expect(api.addPanel).toHaveBeenCalled();           // applyDefaultLayout ran
});
```

(Extend `createFakeDockviewApi` with `addPanel`/`clear`/`getPanel` vi.fn() spies; the
existing fake only has `toJSON`/`fromJSON`.)

**Optionally** add a real-DockviewReact-mount regression test
(`src/components/PanelHost.test.tsx`) that renders `<PanelHost/>`, resolves the fetch
after dispatching an unmount, and asserts no unhandled rejection. **Caveat for the
lead:** jsdom (the configured env, `vitest.config.ts:8`) does not compute layout, so
`DockviewReact`'s `domRef.current.clientWidth/Height` are `0` and `createDockview`
may behave oddly; the dockview-core engine is also not installed on this travel rig
per `map-boot-layout.md`. Treat the real-mount test as best-effort — the two
pure-logic tests above are the load-bearing regression guard and are CI-portable.

### Verification

1. `pnpm typecheck && pnpm test && pnpm build` (static export compiles).
2. Lead runs `pnpm tauri dev` — app must boot to the 5-panel cockpit with **no**
   `element.parentElement is null` in the devtools console (this is the gate that
   unblocks every other fix's GUI verification).
3. computer-use screenshot of the booted cockpit (populated per CLAUDE.md visual
   protocol once Fix 2 lands).

---

## FIX 2 — Cold-boot bind race: News + Portfolio latch permanent error — HIGH

### Root cause (verified, `map-sidecar-race.md`)

Rust announces the **port number** before the sidecar binds: `pick_free_port()`
binds `:0`, reads, **releases** (`src-tauri/src/lib.rs:23-29`), stores it
(`lib.rs:137-138`), and `get_sidecar_port` returns the integer with no liveness
guarantee (`lib.rs:115-118`). The main sidecar is spawned only **after** a blocking
MCP-supervisor join (`lib.rs:181-182, 201`) that can take tens of seconds cold
(`MCP_PORT_WAIT_SECS=45 × 2`; measured ~34s/MCP on M1, contended — CLAUDE.md gotcha).
The frontend caches the base URL off the bare port with **no `/health` probe**
(`sidecar-client.ts:33, 52-66`) and `sidecarGet` does a single fetch with **no retry**
(`sidecar-client.ts:71-104`). News fetches once on mount keyed by symbol list
(`NewsFeedPanel.tsx:184`), Portfolio once via a stable `useCallback` (`PortfolioPanel.tsx:67`)
— both latch a permanent error. Watchlist survives only because it polls every 5s.

### Exact code change

**2a — `src/lib/sidecar-client.ts`: gate the cached base URL on a real `/health`
probe with bounded backoff, shared across all callers.** This is the load-bearing
fix — every panel funnels through `getSidecarBaseUrl()`, so one change fixes all
panels and the cost is paid once per session.

Replace lines 33 + 52-66:

```ts
let readyPromise: Promise<string> | null = null;

/** Resolve the port → base URL (incl. the dev ?sidecar-port= fallback). */
async function resolvePortToBaseUrl(): Promise<string> {
  if (typeof window !== "undefined" && !("__TAURI_INTERNALS__" in window)) {
    const urlParam = new URLSearchParams(window.location.search).get("sidecar-port");
    if (urlParam && /^\d+$/.test(urlParam)) {
      return `http://127.0.0.1:${urlParam}`;
    }
  }
  const port = await invoke<number>("get_sidecar_port");
  return `http://127.0.0.1:${port}`;
}

/**
 * Resolve (and cache) the sidecar base URL, gated on a real /health probe so
 * the first successful resolution implies the sidecar is actually listening.
 * Cold boot can be tens of seconds (MCP join + uvicorn startup), so budget
 * generously with exponential backoff. Shared promise: concurrent panel mounts
 * await the same probe instead of each firing a doomed fetch.
 */
export function getSidecarBaseUrl(): Promise<string> {
  if (readyPromise) {
    return readyPromise;
  }
  readyPromise = resolveAndAwaitReady().catch((error: unknown) => {
    readyPromise = null; // re-armable: a later caller / manual Retry re-probes
    throw error;
  });
  return readyPromise;
}

async function resolveAndAwaitReady(): Promise<string> {
  const base = await resolvePortToBaseUrl();
  const deadline = Date.now() + 120_000;
  let delay = 250;
  for (;;) {
    try {
      const response = await fetch(new URL("/health", base).toString());
      if (response.ok) {
        return base;
      }
    } catch {
      // Connection refused — sidecar not bound yet.
    }
    if (Date.now() > deadline) {
      throw new SidecarError(503, "The data engine did not become ready in time.");
    }
    await new Promise((resolve) => setTimeout(resolve, delay));
    delay = Math.min(delay * 1.6, 2_000);
  }
}
```

`sidecarGet` / `openCryptoStream` / `sidecarApi.health` need **no change** — they
already `await getSidecarBaseUrl()` first. Note `sidecarApi.health` now hits `/health`
*twice* on the first connect (once inside the gate, once from `connectSidecar`); that
is harmless and the gate's result is cached.

**2b — defense-in-depth: News + Portfolio auto-retry their first load** so a transient
post-ready blip self-heals (matching Watchlist).

`src/modules/news/NewsFeedPanel.tsx` — the mount effect at lines 184-197 currently runs
`runFetch` once per `symbolsKey`. Add a bounded retry inside the effect's error path
(keep the manual Retry button as the final fallback). Concretely, thread a retry
counter/`setTimeout` into the `applyResult` error branch — re-`runFetch` up to ~4
times with backoff (1s, 2s, 4s) before surfacing the terminal error block.

`src/modules/portfolio/PortfolioPanel.tsx` — wrap `load()` (lines 54-67) so a failed
first load schedules a re-run on a short backoff before latching the error block.

**2c (recommended, also closes `hunt-error-surfaces.md` #6):** also fix the News
**manual Retry** unguarded-setState (`NewsFeedPanel.tsx:201-204`) by routing `refresh`
through the same `cancelled`/request-id guard the mount path uses — fold it into 2b
since you're already touching that file.

### Test to add

`src/lib/sidecar-client.test.ts` (new): with `vi.useFakeTimers()` and a `fetch` mock
that rejects N times then resolves `{ ok:true }` on `/health`, assert
`getSidecarBaseUrl()` resolves to the base URL only after the successful probe, that a
rejection nulls `readyPromise` (re-armable), and that concurrent callers share one
in-flight probe (single `invoke` call). Stub `invoke` like `workspace.test.ts:10-13`.

### Verification

1. `curl http://127.0.0.1:<port>/health` against a live `tauri dev` returns 200 —
   confirms the gate's success path.
2. Cold-boot `pnpm tauri dev`: News (#38) and Portfolio must populate without a red
   error and without a manual Retry click. Capture the populated 5-panel cockpit
   screenshot (AAPL anchor, News 3-5 articles, Portfolio ≥1 AAPL position) at both
   1920×1080 and 2560×1440 per the visual protocol.

---

## FIX 3 — Settings double-scrollbar/blue-void + "Set default" Ollama-only — HIGH (UX)

Two independent bugs, same file. Verified in `map-settings.md`.

### 3a — Double scrollbar / blue void

**Root cause:** `SettingsPanel`'s root is `bg-charcoal-900 h-full w-full overflow-y-auto`
(`SettingsPanel.tsx:41`) — scroll container #2 — nested inside dockview's leaf
`.dv-view` which is itself `overflow:auto` with no background (dockview.css). Two
scrollbars on one axis; the unpainted `.dv-view` over-scroll region falls through to
the WKWebView default backdrop (the "blue void"). `SettingsPanel.tsx:41` and
`PluginManagerPanel.tsx:31` are the only two panels that put scroll on the `h-full`
root; every other panel roots as non-scrolling `bg-charcoal-900 flex h-full w-full
flex-col` and scrolls an inner body.

**Exact change** — `src/components/SettingsPanel.tsx:40-58`:

```tsx
// before (line 41 + wrapper)
<div className="bg-charcoal-900 h-full w-full overflow-y-auto">
  <div className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
    {/* header + sections */}
  </div>
</div>

// after
<div className="bg-charcoal-900 flex h-full w-full flex-col overflow-hidden">
  <div className="min-h-0 flex-1 overflow-y-auto">
    <div className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
      {/* header + sections */}
    </div>
  </div>
</div>
```

`overflow-hidden` on the root clips at the painted charcoal box (kills the void); the
single inner `min-h-0 flex-1 overflow-y-auto` is the only scroll container.

**Belt-and-suspenders (recommended, also fixes the latent `PluginManagerPanel`):** add
to `src/app/globals.css` inside the Vysted theme block so any future panel's
over-scroll never shows the WKWebView default:

```css
.dockview-theme-vysted .dv-view {
  background-color: var(--color-charcoal-900);
}
```

### 3b — "Set default" only renders on Ollama

**Root cause:** `SettingsPanel.tsx:128` gates the button on `(configured || !needsKey)
&& !isDefault`. Only Ollama has `requiresKey:false` (`llm-providers.ts:36-41`), so on a
fresh install with no keys it is the only row where `(configured || !needsKey)` is
true. Picking a default is a free preference (`setDefaultProviderId` has no
precondition, `llm-providers.ts:75`); the button should show on every non-default row.

**Exact change** — `src/components/SettingsPanel.tsx:128`:

```tsx
// before
{(configured || !needsKey) && !isDefault && (

// after
{!isDefault && (
```

(`configured` becomes unused only inside the button predicate but is still read at
lines 118/145/147, so no lint fallout.)

### Test to add

`src/components/SettingsPanel.test.tsx` (new): render `ProvidersSection` with the
default store state (no keys), assert a "Set default" button is present for a
key-requiring provider (e.g. OpenAI) and absent for the current default (Anthropic).
Stub `useProviderKeysStore.refresh` / `getSecret`. (Scroll/void is CSS — verify
visually, not in a unit test.)

### Verification

- Screenshot Settings panel scrolled to the bottom: one scrollbar, charcoal all the
  way down, no blue void.
- Screenshot the AI Providers list on a fresh profile: "Set default" visible on every
  non-default row, not just Ollama; clicking it moves the `default` badge.

---

## FIX 4 — Plugin runtime + 30s health-interval leak on early teardown — HIGH

### Root cause (verified, `hunt-race-async.md` Finding 1)

`page.tsx:37-64`: `teardown` is assigned only inside `bootstrapPlugins().then(...)`
(line 39). `bootstrapPlugins` awaits `getSidecarBaseUrl()` (an IPC round-trip) before
resolving (`plugin-bootstrap.ts:251-304`). The effect cleanup (`page.tsx:60-64`) calls
`teardown?.()`, which is `null` if cleanup runs before the async resolve — which under
StrictMode it always does. So mount #1's runtime is never torn down: its
`setInterval(() => void runtime.healthCheckAll(), 30_000)` (`plugin-bootstrap.ts:287-289`)
fires forever, and `attachRuntime` overwrites `runtime` with no detach of the prior
(`store/plugins.ts:49-50` — verified: bare `set({ runtime })`). Each HMR edit /
unmount-during-boot adds another orphaned runtime + interval (unbounded; each tick is
network).

### Exact code change

**4a — `src/app/page.tsx:37-64`: track an `alive` flag; dispose immediately if the
effect already tore down.**

```ts
let teardown: (() => void) | null = null;
let alive = true;
void bootstrapPlugins().then((dispose) => {
  if (!alive) {
    dispose(); // unmounted during the boot async window — tear down now
    return;
  }
  teardown = dispose;
  useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
});
// ...subscriptions unchanged...
return () => {
  alive = false;
  unsubscribeEnabled();
  unsubscribeModules();
  teardown?.();
};
```

**4b — `src/store/plugins.ts:49-65`: detach the prior runtime's subscription before
overwriting (defense-in-depth — once 4a disposes the orphan this is belt-and-suspenders,
but it makes `attachRuntime` correct on its own).**

Hold the unsubscribe in a module-scoped ref and call it before re-attaching:

```ts
let detachPrevious: (() => void) | null = null;
// inside attachRuntime(runtime):
attachRuntime: (runtime) => {
  detachPrevious?.();        // detach a previously-attached runtime's subscription
  set({ runtime });
  const refresh = () => { /* unchanged */ };
  refresh();
  const unsubscribe = runtime.subscribe(() => refresh());
  detachPrevious = unsubscribe;
  return () => {
    if (detachPrevious === unsubscribe) {
      detachPrevious = null;
    }
    unsubscribe();
  };
},
```

### Test to add

`src/app/page.test.tsx` or a focused `plugin-bootstrap.test.ts`: mock
`bootstrapPlugins` to return a deferred promise resolving to a `dispose` spy; mount
`<Page/>` then unmount before resolving; resolve the promise; assert `dispose` was
called exactly once (the early-teardown path). Plus a `store/plugins.test.ts`:
`attachRuntime(a)` then `attachRuntime(b)` calls `a`'s `subscribe`-returned
unsubscribe once.

### Verification

- Unit tests above.
- Dev: instrument `healthCheckAll` (temporary `console.count`) under StrictMode — must
  see exactly one cycle per 30s, not two. Remove the instrumentation before commit.

---

## FIX 5 — KillSwitchToolbar OS-listener leak → multi-fire — MEDIUM

### Root cause (verified, `hunt-race-async.md` Finding 2)

`src/modules/safety/KillSwitchToolbar.tsx:80-99`: `cancelled` is checked **before**
`await api.listen(...)` (line 85) but **not after** (line 88). If cleanup runs while
`api.listen()` is pending, `unlisten` is still `null` so cleanup skips it (lines 93-98);
the listen then resolves and assigns `unlisten`, but cleanup already ran → permanent
leaked Tauri listener. Each leaked handler calls `fire()` on every
`kill-switch:requested`, so N leaks = N concurrent `POST /safety/kill-switch` per
shortcut press, firing even after the toolbar is closed. This is a safety-surface
defect; **`KillSwitchToolbar.tsx` is NOT in the locked §6.5 set** (the locked safety
files are `kill_switch.rs`/`audit_log.py`/`broker_base.py`/`types/plugin.ts`/
`test_safety_end_to_end.py`).

### Exact code change — `KillSwitchToolbar.tsx:83-92`

Re-check `cancelled` after the listen resolves and unlisten immediately if so:

```ts
(async () => {
  const api = await getTauriEventApi();
  if (api === null || cancelled) {
    return;
  }
  const off = await api.listen<KillSwitchEventPayload>("kill-switch:requested", (event) => {
    const firedBy = event.payload?.firedBy ?? "user-keyboard";
    void fire(`global-shortcut: ${firedBy}`, firedBy);
  });
  if (cancelled) {
    off();
    return;
  }
  unlisten = off;
})();
```

### Test to add

`src/modules/safety/KillSwitchToolbar.test.tsx` (extend or new): mock
`@tauri-apps/api/event` so `listen` returns a deferred promise resolving to an
`unlisten` spy; mount the toolbar, unmount before the listen resolves, then resolve;
assert the `unlisten` spy was called (the leak path). Because the import is dynamic
(`getTauriEventApi`, line 39-46), `vi.mock("@tauri-apps/api/event", ...)` with a
controllable deferred is the cleanest seam.

### Verification

- Unit test above.
- Dev: open the safety toolbar, force a StrictMode re-mount (HMR edit), press
  `Cmd+Shift+K`, confirm exactly one `POST /safety/kill-switch` in the network panel
  (not N). Do NOT fire against a live broker — paper/disconnected only.

---

## FIX 6 — Node palette redundant non-draggable "Plugin Nodes" section — MEDIUM

### Root cause (verified, `node-palette.tsx`)

`groupByCategory(registry)` (line 44) already buckets plugin entries into their
`NodeSpec.category` and renders them as draggable `PaletteCard`s (line 73), which carry
a `source === "plugin"` badge (lines 123-125). The extra block at lines 79-94 maps
`pluginEntries` to bare `<span>` labels showing only `entry.pluginId` — no `spec.label`,
no `draggable`, no drag handler. Each plugin node thus appears twice: once functional,
once as a dead duplicate label.

### Exact code change — `src/modules/node-editor/node-palette.tsx`

Delete lines 79-94 (the entire `{pluginEntries.length > 0 && ( … )}` section) and
delete the now-unused binding `const pluginEntries = registry.filter(...)` at line 45.

### Test to update

`src/modules/node-editor/node-palette.test.tsx:38-45`: the third test asserts
`screen.getByTestId("palette-section-plugin")` is in the document. After deleting the
section, that assertion must go. Replace it with an assertion that the plugin node
renders as a draggable card in its category (it already asserts
`palette-card-${pluginNode.id}` at line 41 — keep that) and that there is **no**
`palette-section-plugin`:

```ts
it("renders plugin-contributed nodes as draggable cards in their category with a badge", () => {
  const registry = buildRegistry([pluginNode]);
  render(<NodePalette registry={registry} />);
  expect(screen.getByTestId(`palette-card-${pluginNode.id}`)).toBeInTheDocument();
  expect(screen.queryByTestId("palette-section-plugin")).not.toBeInTheDocument();
});
```

### Verification

- `pnpm test` (the updated palette test).
- Screenshot the node editor palette with a plugin loaded (tradesa-v2): each plugin
  node appears exactly once, as a draggable card with the "plugin" badge.

---

## FIX 7 — `command.icon` / `PanelSpec.icon` never rendered — LOW

### Root cause (verified, `CommandPalette.tsx:128-143`)

The palette renders `command.title` (line 138) and `command.description` (lines 139-141)
but never `command.icon`. Every module populates kebab-case Lucide names (verified:
`line-chart`, `test-tube`, `user-plus`, `settings`, `save`, `folder-open`, `sparkles`,
`plug`, `send`, `calendar`, `users`, …). `command` is a `CommandSpec`
(`command-palette.ts:9`), which carries `icon?: string` (`types/plugin.ts:127-128`).
`lucide-react@1.14.0` ships a `DynamicIcon` (verified: `node_modules/lucide-react/dynamic.mjs`)
that takes a kebab-case `name` prop — a perfect match. **No contract edit** (`icon?`
already exists).

### Exact code change

**7a — new shared resolver `src/lib/lucide-dynamic.tsx`** (agents/panels also carry
icon strings — `hunt` verifierNote — so extract once):

```tsx
import { DynamicIcon, type IconName } from "lucide-react/dynamic";

/**
 * Render a Lucide icon from a kebab-case name string (the form every module/
 * plugin stores in `CommandSpec.icon` / `PanelSpec.icon`). Unknown or absent
 * names render nothing so a bad icon string never breaks the row.
 */
export function LucideGlyph({ name, className }: { name?: string; className?: string }) {
  if (!name) {
    return null;
  }
  return <DynamicIcon name={name as IconName} className={className} fallback={() => null} />;
}
```

(Confirm the exact export name `DynamicIcon` + `IconName` against
`node_modules/lucide-react/dynamic.d.ts` at build time; `lucide-react/dynamic` is the
documented subpath for 1.x. The `fallback` prop avoids a thrown error on an unknown
name. `DynamicIcon` lazy-loads, so wrap the palette list in a `<Suspense>` if the
build complains — see verification.)

**7b — `src/components/CommandPalette.tsx`** render it in the button row (lines 128-143).
Change the button's inner layout to a horizontal flex with the glyph left of the title:

```tsx
<button
  key={command.id}
  type="button"
  onClick={() => run(index)}
  onMouseEnter={() => setHighlight(index)}
  className={`flex w-full items-center gap-3 px-5 py-2 text-left font-mono ${
    index === highlight ? "bg-charcoal-800" : ""
  }`}
>
  <LucideGlyph name={command.icon} className="text-charcoal-400 size-3.5 shrink-0" />
  <span className="flex min-w-0 flex-col gap-0.5">
    <span className="text-charcoal-100 text-sm">{command.title}</span>
    {command.description ? (
      <span className="text-charcoal-400 text-xs">{command.description}</span>
    ) : null}
  </span>
</button>
```

Import `LucideGlyph` from `@/lib/lucide-dynamic`. `PanelSpec.icon` has no current
render surface (no add-panel gallery exists — `map-settings.md`), so leave it; the
shared `LucideGlyph` is ready when a gallery ships. Do not invent a gallery here
(out of scope, and Fix 8 wires panel sizing separately).

### Test to add

`src/components/CommandPalette.test.tsx` (extend if present, else new): set commands
with a known `icon` (e.g. `"line-chart"`), open the palette, assert an `svg` renders
inside that command's button. Because `DynamicIcon` is lazy, the test may need
`await screen.findBy...` and a `<Suspense>` wrapper; if lazy-loading is awkward under
vitest, the lighter assertion is that `LucideGlyph` returns `null` for `undefined` and
a non-null element for a string (unit-test `LucideGlyph` directly).

### Verification

- `pnpm typecheck && pnpm build` — confirm `lucide-react/dynamic` resolves under the
  static-export build (this is the real risk; if Next's RSC/static export trips on the
  lazy import, fall back to a static `import { icons } from "lucide-react"` name→component
  map in `lucide-dynamic.tsx` instead of `DynamicIcon`).
- Screenshot cmd+K: each command shows its glyph left of the title.

---

## FIX 8 — `PanelSpec.defaultSize` never applied — LOW

### Root cause (verified, `store/workspace.ts:46-71`)

`openPanel` calls `api.addPanel({ id, component, title })` (lines 62, 70) with no size
derived from `spec.defaultSize`. No layout code reads `PanelSpec.defaultSize`;
`default-layout.ts` uses hardcoded fractions. Every module fills the field (e.g.
platform settings `{w:4,h:5}`, `modules/platform/index.ts`) with no effect.

### Decision

The honest options (verifierNote): (a) document the field as advisory — but the JSDoc
lives at `types/plugin.ts:102`, a LOCKED file, so I will NOT touch it; or (b) wire it
functionally host-side. **Choose (b)** — it makes the field meaningful without
touching the contract, and the user's build philosophy ("no dead metadata, full
scope") favors the wire-up. Mirror `default-layout.ts`'s post-add `setSize` approach
(the team found it more reliable than `addPanel` `initialWidth/Height` per the
verifierNote).

### Exact code change — `src/store/workspace.ts:46-71`

After each `api.addPanel(...)`, if `spec.defaultSize` is present, set the created
panel's size (grid units → px via the leaf's current pixel size; dockview redistributes
proportionally, so this sets a starting ratio, not a hard lock — acceptable and honest):

```ts
openPanel: (panelId) => {
  const api = get().dockviewApi;
  if (!api) {
    return;
  }
  const spec = useModulesStore.getState().findPanel(panelId);
  if (!spec) {
    return;
  }
  const applySize = (panel: ReturnType<DockviewApi["addPanel"]>) => {
    if (!spec.defaultSize) {
      return;
    }
    // Grid units → px. dockview redistributes proportionally; this seeds the
    // initial ratio rather than pinning exact dimensions.
    const unit = 80; // px per grid unit; matches default-layout's scale
    panel.api.setSize({ width: spec.defaultSize.w * unit, height: spec.defaultSize.h * unit });
  };
  if (spec.singleton !== false) {
    const existing = api.getPanel(panelId);
    if (existing) {
      existing.api.setActive();
      return;
    }
    applySize(api.addPanel({ id: spec.id, component: spec.component, title: spec.title }));
    return;
  }
  const uniqueId = `${spec.id}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
  applySize(api.addPanel({ id: uniqueId, component: spec.component, title: spec.title }));
},
```

(Confirm `panel.api.setSize` signature against dockview 6.2.2 `DockviewPanelApi` at
build time — `setSize({ width?, height? })` is the 6.x API. The `unit` constant should
match whatever px-per-grid-unit `default-layout.ts` effectively uses; pick a value that
reads sensibly, this is an advisory seed not a hard contract.)

### Test to add

`src/store/workspace.test.ts` (new or extend): fake api with `addPanel` returning a
panel whose `api.setSize` is a spy; call `openPanel("quant")` (defaultSize `{w:9,h:8}`),
assert `setSize` called with the converted dimensions; call `openPanel` for a panel with
no `defaultSize`, assert `setSize` not called.

### Verification

- Unit test above.
- Screenshot: open Quant via cmd+K (defaultSize `{w:9,h:8}`) and a smaller panel; the
  larger panel visibly docks bigger than the smaller. (dockview proportional
  redistribution means it's a ratio, not exact px — that's expected and documented in
  the code comment.)

---

## Cross-cutting notes for the lead

- **Build order in one branch:** land Fix 1 first and verify the boot, then Fix 2 and
  verify populated panels, then Fixes 3-8 in any order (independent). One commit per
  fix per the project's conventional-commit / one-deliverable rule.
- **`pnpm ci-local` is the hard pre-tag gate** (CLAUDE.md). The new tests (Fixes 1, 2,
  4, 5, 6, 7, 8) all run under vitest in `ci-local`; run `pnpm format:check` before
  every push (the v0.8.1 lesson).
- **Static-export risk concentrated in Fix 7** (`lucide-react/dynamic` lazy import under
  Next 16 static export). Verify `pnpm build` after Fix 7; the static name-map fallback
  is the escape hatch.
- **Not in scope here** (other tracks / deferred): the broader error-surface findings
  (`hunt-error-surfaces.md` #1 global sidecar banner, #2 kill-switch silent-swallow, #3
  chart Retry no-op, #4/#9 truncated-SSE hangs, #5 getSecret unhandled rejection, #6
  broker toggle silent no-op, #7 screener universe, #8 broker empty-state), the chat
  abort/zombie-stream finding (`hunt-race-async.md` #3), the MCP shared-session lock
  (#4), and the regression-hunt BUG-2/4/5/7 (autosave-of-default, save≠active,
  reset-incomplete, defaultProviderId not persisted). Flag #2 (kill-switch fire failure
  silently swallowed, `KillSwitchToolbar.tsx:64-71` + `handleReset` no catch) as a
  **strong same-file follow-on to Fix 5** — the lead may want to fold a visible
  "KILL SWITCH FAILED TO FIRE — RETRY" banner into the Fix 5 commit since it touches the
  same component and is the same safety surface. None of these touch locked files.

## §6.5 lock re-confirmation

No fix edits `sidecar/models/audit_log.py`, `sidecar/models/kill_switch.py`,
`src-tauri/src/kill_switch.rs`, `sidecar/models/broker_base.py`, `types/plugin.ts`, or
`tests/test_safety_end_to_end.py`. Fix 8 explicitly avoids the `types/plugin.ts:102`
JSDoc by choosing the host-side functional wire-up. Fix 5/follow-on touches only the
frontend `KillSwitchToolbar.tsx`, which is not locked.
