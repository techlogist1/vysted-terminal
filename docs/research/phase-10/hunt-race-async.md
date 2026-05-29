# Phase 10 — Adversarial bug hunt: races, async ordering, lifecycle, cleanup

**Lens:** concurrency / async ordering / lifecycle / resource cleanup across the
frontend boot path, sidecar discovery, panel data-fetch, store hydration, SSE/stream
readers, debounced layout save — and the sidecar lifespan / MCP bind / concurrency.

**Method:** read the actual source, cite `file:line`, verify against code, exclude the
4 already-known live bugs. Baseline: `vitest run src/lib/workspace.test.ts` → 8/8 pass.

## Excluded (already-known live bugs — NOT re-reported)

1. Cold-boot late-bind race → News #38 + Portfolio false-error
   (`docs/research/phase-10/map-sidecar-race.md`). The port is announced before bind;
   `getSidecarBaseUrl` caches off the bare port with no readiness probe; News/Portfolio
   fire one mount fetch with no retry.
2. dockview StrictMode/HMR use-after-dispose crash in `restoreLastSessionOrDefault`
   (`map-boot-layout.md` Mechanism A/B) — the stale closure runs `applyDefaultLayout` /
   `api.fromJSON` on a disposed api → `element.parentElement is null`.
3. MCP subprocess bind nondeterminism (UC1) — documented residual, Rust-side, deferred
   `--onedir` fix.
4. Audit-log cold-DB 500 (#79) — fixed in 9.5; reader `query_only` invariant.

Findings below are **new** and distinct from those.

---

## FINDING 1 — Plugin runtime + 30s health-check interval leak when the boot effect tears down before `bootstrapPlugins()` resolves (HIGH)

**File:** `src/app/page.tsx:37-64` (with `src/lib/plugin-bootstrap.ts:251-304`,
`src/store/plugins.ts:49-50`)

```ts
// page.tsx
let teardown: (() => void) | null = null;
void bootstrapPlugins().then((dispose) => {
  teardown = dispose;                       // assigned only AFTER the async resolves
  ...
});
...
return () => {
  unsubscribeEnabled();
  unsubscribeModules();
  teardown?.();                             // null if cleanup runs before resolve → NO teardown
};
```

`bootstrapPlugins()` is async and `await`s `resolvePersistence()` → `getSidecarBaseUrl()`
(a Tauri IPC round-trip), then loads every bundled plugin and only then resolves with the
`dispose` function. The effect's cleanup captures `teardown` by closure; if the effect
unmounts/re-runs **before** the promise resolves, `teardown` is still `null` and
`teardown?.()` is a no-op.

The App-Router dev server mounts under React StrictMode (confirmed in `map-boot-layout.md`
§3, `node_modules/next/dist/server/config-shared.js`), which runs every mount effect
**mount → cleanup → mount**. The synchronous StrictMode cleanup _always_ fires before the
IPC-bound `bootstrapPlugins()` resolves, so the **first** runtime is never torn down:

- `clearInterval(interval)` in the teardown (`plugin-bootstrap.ts:296`) never runs → the
  first runtime's `setInterval(() => void runtime.healthCheckAll(), 30_000)`
  (`plugin-bootstrap.ts:287-289`) keeps firing forever against the orphaned runtime.
- `detachStore()` (`plugin-bootstrap.ts:297`) never runs → the first runtime's event
  subscription on `usePluginsStore` stays live; the second mount's `attachRuntime`
  overwrites `runtime` in the store (`store/plugins.ts:50` does a bare `set({ runtime })`,
  no detach of the prior), so the store now has two runtimes pushing snapshots.
- `unloadPlugin(...)` for each plugin never runs → plugins from the orphaned runtime are
  never shut down.

Net effect each dev mount (and each HMR reload / fast navigation that unmounts `Page`
before the bootstrap resolves): one orphaned `PluginRuntime` + one orphaned 30s
health-check timer accumulate and never stop. Over a dev session this is an unbounded
leak; `healthCheckAll` hits every plugin's `healthCheck()` (network) on each tick.

**This is independent of StrictMode** — any unmount during the boot async window (HMR,
navigation) reproduces it; StrictMode just makes it deterministic in dev.

**Repro:** `pnpm dev`, open the app, observe two `healthCheckAll` cycles every 30s (or
instrument `bootstrapPlugins` teardown — it logs nothing, but the interval count grows).
Each HMR edit to `page.tsx` adds another orphaned interval.

**Fix:** make the cleanup cancel a not-yet-resolved bootstrap. Track an `alive` flag and,
in the `.then`, if `!alive` immediately call `dispose()` instead of storing it:

```ts
let teardown: (() => void) | null = null;
let alive = true;
void bootstrapPlugins().then((dispose) => {
  if (!alive) {
    dispose();
    return;
  } // unmounted during boot → tear down now
  teardown = dispose;
  useCommandPalette.getState().setCommands(useModulesStore.getState().enabledCommands());
});
return () => {
  alive = false;
  unsubscribeEnabled();
  unsubscribeModules();
  teardown?.();
};
```

Also harden `store/plugins.ts:attachRuntime` to detach a previously-attached runtime's
subscription before overwriting.

**Confidence:** 0.85 (the leak path is unambiguous in code; only the dev-vs-prod
frequency of the trigger varies).

---

## FINDING 2 — KillSwitchToolbar OS-event listener leaks (and can double-fire the kill switch) when the effect tears down inside the `await listen()` window (MEDIUM)

**File:** `src/modules/safety/KillSwitchToolbar.tsx:80-99`

```ts
useEffect(() => {
  let unlisten: (() => void) | null = null;
  let cancelled = false;
  (async () => {
    const api = await getTauriEventApi();
    if (api === null || cancelled) return;                 // cancelled checked HERE...
    unlisten = await api.listen<KillSwitchEventPayload>(    // ...but not after this await
      "kill-switch:requested",
      (event) => { ...; void fire(...); },
    );
  })();
  return () => {
    cancelled = true;
    if (unlisten !== null) unlisten();                     // null during the await window → skipped
  };
}, [fire]);
```

`cancelled` is checked only **before** `api.listen()`. If the cleanup runs while
`api.listen()` is still in flight (its promise pending), the cleanup sees `unlisten === null`
and skips it; then `api.listen()` resolves and assigns `unlisten`, but the cleanup has
already run and will not run again — the Tauri event listener **leaks**. Under StrictMode
(mount → cleanup → mount) and on any panel close/reopen or `fire`-identity change (it is in
the dep array), each occurrence that hits this window adds a permanent listener.

Because the leaked handler calls `void fire("global-shortcut: …", firedBy)` on every
`kill-switch:requested` event, after N leaks a single `Cmd/Ctrl+Shift+K` fires **N**
`POST /safety/kill-switch` requests — and continues firing even after the toolbar panel is
closed (the leaked listener outlives the component). This sits on the §6.5 emergency-stop
surface; even if the endpoint is idempotent, a leaked handler firing the kill switch while
the UI shows nothing is a correctness/UX defect on a safety-critical path.
(`KillSwitchToolbar.tsx` is **not** in the locked §6.5 file set — `kill_switch.rs`,
`audit_log.py`, `broker_base.py`, `types/plugin.ts`, `test_safety_end_to_end.py` are; this
component is fair game.)

**Repro:** mount the toolbar in StrictMode dev where `getTauriEventApi()`/`listen()` resolve
across a tick; the first mount's `listen` resolves after the StrictMode cleanup, leaking one
listener. Or force `fire` to change identity (e.g. a re-render that re-creates it) to re-run
the effect repeatedly and watch listener count climb. Then fire the shortcut and observe
duplicate POSTs.

**Fix:** re-check `cancelled` after the `await api.listen(...)` and unlisten immediately if
cancelled:

```ts
const off = await api.listen(...);
if (cancelled) { off(); return; }
unlisten = off;
```

**Confidence:** 0.75 (the async-cleanup gap is real and standard; the exact frequency
depends on how often `getTauriEventApi`/`listen` resolve past a cleanup tick).

---

## FINDING 3 — Chat streams are uncancellable: closing the panel mid-stream leaks a running fetch, and `/clear` mid-stream re-enables the composer allowing concurrent zombie streams (MEDIUM)

**File:** `src/modules/chat/ChatSidebar.tsx:188-207` (+ `streaming.ts:74-125`,
`store/chat-history.ts:112`)

`StreamingHandlers` supports an optional `signal?: AbortSignal` (`streaming.ts:31`) and
`consumeSseStream` passes it to `fetch` (`streaming.ts:85`). But `ChatSidebar` **never
creates an AbortController and never sets `handlers.signal`** (grep: no `AbortController`,
no `signal`, no `abort` in `ChatSidebar.tsx`). Consequences:

1. **No cancellation on unmount.** Closing/destroying the chat panel mid-stream does not
   abort the fetch. `consumeSseStream` keeps `reader.read()`-ing until the sidecar finishes
   the LLM completion — network stays open and BYOK provider tokens keep being generated and
   billed for a response no one will see. There is no unmount effect that aborts anything.

2. **`/clear` mid-stream re-enables the composer → concurrent streams.** `streaming` is
   derived as `streamingMessageId !== null` (`ChatSidebar.tsx:42`) and gates the composer
   (`disabled={streaming}`, line 291). `/clear` calls `clearHistory()` which sets
   `streamingMessageId: null` and `messages: []` (`chat-history.ts:112`). The in-flight
   `streamChat`/`streamAgentInvocation` is **not** aborted (point 1), but `streaming` is now
   `false`, so the composer is re-enabled while the old stream is still consuming. The user
   can immediately send a new message → a **second** concurrent stream starts. Two streams
   now race into `useChatHistoryStore`. The old stream's `appendDelta(oldId, …)` /
   `finalize(oldId)` no-op against the cleared `messages` (id no longer present), so it does
   not visibly corrupt the new message — but it is a zombie consuming the network/tokens, and
   the design intent ("one stream at a time") is broken by the clear path.

**Repro:** start an agent stream, `/clear` while the `▋` cursor is still pulsing →
composer becomes editable → send another prompt. Two `/llm/chat` (or `/agents/.../invoke`)
streams are open simultaneously against the sidecar. Or close the chat panel mid-stream and
observe (sidecar logs / provider dashboard) the completion still running.

**Fix:** hold a `useRef<AbortController | null>`; abort + replace it at the top of
`handleSend`, pass `controller.signal` into the `handlers` (the wiring already exists in
`consumeSseStream`), abort it in `clearHistory`'s call site, and abort in an unmount
`useEffect` cleanup. This mirrors the correct pattern already used in
`NodeEditorPanel.tsx:333-402` (`runAbortRef`).

**Confidence:** 0.8 (the missing abort and the clear-re-enables-composer path are both
directly verifiable; "zombie billing" is a consequence, not a crash, hence MEDIUM).

---

## FINDING 4 — Shared cached `McpClient` session is mutated without a lock during in-flight calls: a concurrent transport error closes the session out from under other requests, and `close()` exits the anyio context from a different task (MEDIUM)

**File:** `sidecar/services/mcp_client.py:120-173, 230-236` (consumed concurrently via
`sidecar/services/openbb_mcp_provider.py:239-252` → all `/fundamentals`, `/macro`, history,
news openbb paths)

`get_client("openbb-mcp", …)` returns one **module-cached** `McpClient`
(`mcp_client.py:200,214-227`) shared by every concurrent request. Two problems:

1. **`_ensure_session` holds `self._lock` only during `_open()`** (lines 120-126). The
   actual `await session.list_tools()` / `await session.call_tool(...)` (lines 143, 167) run
   **without** the lock, over the **single shared** `ClientSession`/streamable-HTTP transport.
   If any concurrent call hits a transport error, its handler calls `await self.close()`
   (lines 146, 172), which acquires `_lock`, `aclose()`s the exit stack, and sets
   `self._session = None`. Meanwhile **other in-flight calls are still awaiting on the
   now-closed session/streams** → they fail with confusing downstream errors (anyio
   `ClosedResourceError` / `RuntimeError`) that bubble up as `ProviderError`
   (`openbb_mcp_provider.py:248`). So one cold/slow openbb call that times out can poison
   every other openbb request that happened to be in flight — exactly the kind of
   concurrent-panel-open load the cold-boot window produces.

2. **`close()` exits the anyio context from a possibly-different task.** `streamablehttp_client`
   / `stdio_client` / `ClientSession` are anyio task-group-backed async context managers
   entered into `_exit_stack` inside `_open()` (running on whatever request task first opened
   the session). `close()` may be invoked from a **different** task — the shutdown lifespan
   task via `reset_clients()` (`app.py:114` → `mcp_client.py:230-236`), or a different
   concurrent request's error handler. Exiting an anyio cancel scope / task group from a task
   other than the one that entered it raises
   `RuntimeError: Attempted to exit cancel scope in a different task than it was entered in`.
   `close()` swallows it (`except Exception` at line 134, logged at `debug`) and sets
   `_session/_exit_stack = None` anyway — so the underlying transport tasks/sockets are
   **leaked** (never properly unwound) rather than cleanly torn down. On shutdown
   (`reset_clients`) this means the external openbb-mcp transport can leak open, the very
   thing the lifespan `finally` (`app.py:101-114`) is trying to prevent.

**Repro (point 1):** fire several concurrent `GET /fundamentals/<symbol>` while openbb-mcp is
cold/slow so one call exceeds `_REQUEST_TIMEOUT`/init timeout and triggers `close()`; the
sibling concurrent requests fail with transport-closed errors instead of independently
retrying. (`tests/test_openbb_mcp_provider.py` exercises the single-call path, not concurrent
calls sharing a session through an error, so this is uncaught.)

**Fix:** (a) serialize calls per client by holding `self._lock` around the actual
`call_tool`/`list_tools` (or hold a session-generation counter and ignore a `close()` whose
generation no longer matches the live session); (b) drive transport teardown from the task
that owns the session (e.g. run the session inside a dedicated task + queue, or use an
`anyio` task group owned by the client) rather than calling `aclose()` from arbitrary caller
tasks. Minimal mitigation: guard `close()` so it only runs when called from the owning task,
and capture the session generation so a stale error-handler `close()` cannot tear down a
freshly-reopened session.

**Confidence:** 0.6 (point 1 — unlocked shared-session mutation during in-flight calls — is
unambiguous; point 2's cross-task cancel-scope error depends on the exact anyio/MCP-SDK task
topology, which I could not execute here, hence the lower score).

---

## FINDING 5 — PanelHost autosave subscription + debounce timer leak when the panel unmounts inside the `restoreLastSessionOrDefault` await window (LOW–MEDIUM)

**File:** `src/components/PanelHost.tsx:31-65`

```ts
const cleanupRef = useRef<(() => void) | null>(null);
useEffect(() => { return () => { cleanupRef.current?.(); }; }, []);   // unmount cleanup

function handleReady(event) {
  ...
  void restoreLastSessionOrDefault(api, enabledPanelIds).finally(() => {
    let timer = null;
    const subscription = api.onDidLayoutChange(() => { ...debounced autosaveLayout... });
    cleanupRef.current = () => { if (timer) clearTimeout(timer); subscription.dispose(); };
  });
}
```

`cleanupRef.current` is assigned **inside the `.finally()`** of the async
`restoreLastSessionOrDefault`. The component's unmount cleanup
(`useEffect(() => () => cleanupRef.current?.(), [])`) reads `cleanupRef.current` at unmount
time. If the panel unmounts **before** `restoreLastSessionOrDefault` resolves, the unmount
cleanup runs while `cleanupRef.current` is still `null` → no-op. Then `.finally()` runs,
creates the `api.onDidLayoutChange` subscription + holds a `setTimeout` debounce timer, and
assigns `cleanupRef.current` — but the unmount cleanup already fired and will not run again.
The `onDidLayoutChange` subscription and the pending debounce timer are **never disposed**.

This is the cleanup-leak sibling of the known boot-race crash (`map-boot-layout.md`), but it
is a **distinct defect**: the map's fix (store-identity guard against the disposed api) stops
the use-after-dispose _throw_ on `applyDefaultLayout`/`fromJSON`, but does not by itself
dispose the leaked `onDidLayoutChange` subscription created in the `.finally()` after a
too-early unmount. A leaked subscription keeps invoking `autosaveLayout()` (a sidecar POST)
on layout changes of a detached api.

**Repro:** unmount `PanelHost` (StrictMode cleanup, HMR, or navigating away) during the
`/workspace/__autosave__` fetch; the `.finally()` then wires an undisposed subscription +
timer.

**Fix:** in the `.finally()`, before wiring, check the component is still alive (an `alive`
ref set false in the unmount cleanup) AND that the api is still the live one
(`useWorkspaceStore.getState().dockviewApi === api`); if not, dispose immediately and skip.
The robust fix recommended in `map-boot-layout.md` §4.2 (per-mount epoch/abort) closes this
as a side effect.

**Confidence:** 0.6 (leak path is real; overlaps the known boot race's blast radius, and the
recommended boot-race fix may incidentally cover it — hence not HIGH).

---

## FINDING 6 — News manual Retry (`refresh`) bypasses the per-effect cancellation guard → setState after unmount (LOW)

**File:** `src/modules/news/NewsFeedPanel.tsx:184-204`

The mount effect correctly guards staleness with a `cancelled` flag:
`runFetch((next) => { if (!cancelled) setState(next); })` (lines 184-193). But the manual
retry handler calls `runFetch(setState)` **directly** with the raw `setState` and **no
cancellation guard** (lines 201-204):

```ts
const refresh = useCallback(() => {
  setState({ status: "loading" });
  runFetch(setState); // unguarded — applyResult === setState
}, [runFetch]);
```

If the user clicks Retry and then closes the panel before `fetchNews` resolves, `setState`
fires on the unmounted component. React 19 no longer warns, so it's a benign wasted update
today — but it is an inconsistency with the deliberately-guarded mount path and a latent bug
if `setState` is ever replaced with something with side effects.

**Fix:** route `refresh` through the same cancellation discipline (e.g. a shared
`latestRequestId` ref the effect and the retry both check), or have `refresh` set a ref the
effect owns.

**Confidence:** 0.55 (clearly unguarded vs. the mount path; impact is minor under React 19).

---

## Areas checked and found SOUND (no new bug)

- **`WatchlistPanel` polling** (`WatchlistPanel.tsx:86-114`): `inFlightRef` correctly
  prevents overlapping polls; interval is cleared on cleanup. A post-unmount `setRows`/
  `setError` is possible (no abort) but benign under React 19 — not reported as it is the
  same low-grade pattern as Finding 6 and the panel's self-healing is the documented
  resilience.
- **`OrderConfirmationDialog` double-submit** (`OrderConfirmationDialog.tsx:123-139`): gated
  by a local `busy` state set before the `await`; a same-tick double-fire is not realistically
  producible from a single button. Sound enough; not reported.
- **Orders store payload keys** (`store/orders.ts:175` `humanConfirmed`/`confirmNote`) match
  `BrokerConfirmRequest`'s Pydantic aliases (`models/broker.py:157-158`
  `alias="humanConfirmed"`/`alias="confirmNote"`). No mismatch.
- **`mcp_server.get_streamable_http_app()`** caches `_streamable_http_app`
  (`mcp_server.py:62,366-371`); `create_app` mounts it (`app.py:213`) and `_lifespan` runs
  _that same cached instance's_ lifespan (`app.py:99-100`), so the session manager is
  initialised on the mounted app — correct (the comment at `mcp_server.py:361-366` shows this
  was a deliberate fix).
- **`_lifespan` httpx-client close ordering** (`app.py:101-114`): guarded so an `aclose()`
  failure cannot block `reset_clients()` — sound.
- **`workflow.ts runWorkflow`** background `consume()` (`store/workflow.ts:277-308`) is not
  consumed by any mounted component (grep: only `NodeEditorPanel` runs its own
  AbortController-backed `consumeSse`), so its lack of an abort path is currently inert;
  flagged for awareness, not reported as live.

---

## Severity summary

| #   | Finding                                                                                      | Severity   | Confidence | File                                             |
| --- | -------------------------------------------------------------------------------------------- | ---------- | ---------- | ------------------------------------------------ |
| 1   | Plugin runtime + 30s health interval leak (teardown before bootstrap resolves)               | HIGH       | 0.85       | `src/app/page.tsx:37-64`                         |
| 2   | KillSwitchToolbar listener leak → duplicate kill-switch fires                                | MEDIUM     | 0.75       | `src/modules/safety/KillSwitchToolbar.tsx:80-99` |
| 3   | Chat streams uncancellable; `/clear` re-enables composer → concurrent zombie streams         | MEDIUM     | 0.8        | `src/modules/chat/ChatSidebar.tsx:188-207`       |
| 4   | Shared `McpClient` session mutated without lock during in-flight calls; cross-task `close()` | MEDIUM     | 0.6        | `sidecar/services/mcp_client.py:120-173,230-236` |
| 5   | PanelHost autosave subscription/timer leak (unmount in restore await window)                 | LOW–MEDIUM | 0.6        | `src/components/PanelHost.tsx:31-65`             |
| 6   | News manual Retry bypasses cancellation guard                                                | LOW        | 0.55       | `src/modules/news/NewsFeedPanel.tsx:201-204`     |
