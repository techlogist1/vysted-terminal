# Phase 10 — Sidecar lifecycle + port discovery map & cold-boot "failed to load" root-cause

**Scope:** Map the main-sidecar spawn / port-assignment / port-announce path (Rust),
the frontend port-discovery + HTTP client, and the News + Portfolio panel fetch code.
Root-cause the cold-boot "failed to load" on News and Portfolio. Design the fix.

**Verdict:** Confirmed late-bind race. The Tauri core hands the frontend the sidecar
**port number** the instant the frontend asks for it — but that port number is _picked_
(`bind(0)` → read → release) **before** the Python sidecar process is even spawned, and
the sidecar process is in turn spawned only **after** the two MCP supervisors finish a
blocking, up-to-90s-each port wait. The frontend's port resolver does **no readiness
probe and no retry**, and the panels fetch on mount with **no retry/backoff**. News and
Portfolio fetch exactly once and latch a permanent error; Watchlist survives the same
race only because it polls every 5s and self-heals.

---

## 1. The Rust sidecar lifecycle (src-tauri/src/lib.rs)

### 1.1 Port is picked at setup, _before_ the sidecar exists

```
lib.rs:23   fn pick_free_port() -> u16        // bind 127.0.0.1:0, read port, RELEASE it
lib.rs:137  let port = pick_free_port();
lib.rs:138  app.manage(SidecarPort(port));    // port is now in Tauri state, queryable
```

`pick_free_port()` (lib.rs:23-29) binds to `:0`, reads the OS-assigned port, then drops
the listener — so the port is **free again** the moment it is returned. Nothing is
listening on it yet. It is immediately stored in Tauri state (`SidecarPort`, lib.rs:20)
and is from this instant returnable to the frontend.

### 1.2 `get_sidecar_port` returns the number with no liveness guarantee

```
lib.rs:115  #[tauri::command]
lib.rs:116  fn get_sidecar_port(port: tauri::State<'_, SidecarPort>) -> u16 { port.0 }
```

This command answers immediately with the integer. It does **not** verify the sidecar
is bound. There is no `is_ready` flag, no event, no gating — the port is "announced"
(available to the frontend via `invoke`) from lib.rs:138 onward, long before bind.

### 1.3 The main sidecar spawns _after_ a blocking MCP join (the latency amplifier)

```
lib.rs:169  let openbb_thread = thread::spawn(move || { openbb_mcp::spawn(&openbb_handle) });
lib.rs:174  let sec_thread    = thread::spawn(move || { sec_edgar_mcp::spawn(&sec_handle) });
lib.rs:181  let _ = openbb_thread.join();   // BLOCKS setup until openbb binds or times out
lib.rs:182  let _ = sec_thread.join();      // BLOCKS setup until sec-edgar binds or times out
...
lib.rs:201  let (mut rx, child) = sidecar.spawn().expect("failed to spawn the Python sidecar");
```

`openbb_mcp::spawn` / `sec_edgar_mcp::spawn` are **synchronous and block on
`wait_for_port_with_retries`** before returning:

```
openbb_mcp.rs:140  let bound = wait_for_port_with_retries(port, MCP_PORT_WAIT_SECS, MCP_PORT_WAIT_ATTEMPTS, ...)
lib.rs:79          MCP_PORT_WAIT_SECS: u64 = 45;
lib.rs:84          MCP_PORT_WAIT_ATTEMPTS: u32 = 2;     // → up to 90s per MCP
```

The two MCP spawns run on parallel threads, but `lib.rs:181-182` **joins both before the
main sidecar is spawned** (the env-var ordering requirement noted in lib.rs:179-182 and
openbb_mcp.rs:82-85). Per the CLAUDE.md "Phase 9.5" gotcha, cold MCP bind on macOS M1 is
~34s each and contended; worst case the join takes tens of seconds, up to ~90s if an MCP
never binds. **The main `vysted-sidecar` process is not even launched (lib.rs:201) until
that join completes.** Then uvicorn inside it still needs to import the app graph and call
`uvicorn.run(...)` (sidecar/main.py:105) before it binds the announced port.

So the window between "frontend can read the port" (lib.rs:138, ~0 ms into setup) and
"something is listening on that port" (uvicorn bind, after the MCP join + sidecar boot)
is **not milliseconds — it is seconds to tens of seconds on a cold boot.**

### 1.4 The only bind check is a fire-and-forget log line

```
lib.rs:219  thread::spawn(move || {
lib.rs:220      if wait_for_port(port) {                    // 15s probe
lib.rs:221          println!("[vysted] Python sidecar healthy on 127.0.0.1:{port}");
lib.rs:223      } else { eprintln!("... did not come up ..."); }
lib.rs:225  });
```

`wait_for_port` (lib.rs:54, 15s) is used **only to print a log line**. Its result is never
surfaced to the frontend, never stored in state, never emitted as an event. The frontend
has no way to observe it.

---

## 2. Frontend port discovery + HTTP client (src/lib/sidecar-client.ts)

### 2.1 Base URL is resolved from the port number and cached forever — no readiness, no retry

```
sidecar-client.ts:33  let cachedBaseUrl: string | null = null;
sidecar-client.ts:52  export async function getSidecarBaseUrl(): Promise<string> {
sidecar-client.ts:53    if (cachedBaseUrl !== null) return cachedBaseUrl;       // cached after first call
...
sidecar-client.ts:63    const port = await invoke<number>("get_sidecar_port"); // returns instantly (§1.2)
sidecar-client.ts:64    cachedBaseUrl = `http://127.0.0.1:${port}`;            // cached; NO probe
sidecar-client.ts:65    return cachedBaseUrl;
```

This resolves successfully the instant the Tauri core is up — because all it needs is the
_number_, which is available from lib.rs:138. It performs **no `/health` probe** and
**caches the URL permanently**, so it can never block on or detect the sidecar not being
ready.

### 2.2 `sidecarGet` does a single fetch and throws on failure — no retry/backoff

```
sidecar-client.ts:71  export async function sidecarGet<T>(path, params?): Promise<T> {
sidecar-client.ts:72    const base = await getSidecarBaseUrl();
sidecar-client.ts:81    const response = await fetch(url.toString());   // ONE attempt
sidecar-client.ts:82    if (!response.ok) { ... throw new SidecarError(...); }
```

Grep confirms **zero** `retry` / `backoff` / `setTimeout` / `poll` / `waitFor` anywhere in
`src/lib/sidecar-client.ts` or `src/store/app.ts`. A fetch against a port with nothing
listening rejects (`fetch` throws `TypeError: Failed to fetch` / `ECONNREFUSED`), and that
rejection propagates straight to the caller as a non-`SidecarError`.

### 2.3 The app store "connection status" is computed once and read by no panel

```
store/app.ts:24  connectSidecar: async () => {
store/app.ts:27    const baseUrl = await getSidecarBaseUrl();
store/app.ts:28    await sidecarApi.health();                       // one-shot, no retry
store/app.ts:29    set({ ..., sidecarStatus: "connected" });
store/app.ts:32    catch → set({ sidecarStatus: "error" });
```

`connectSidecar()` is called exactly once on mount (page.tsx:31) and is **never retried**.
Grep for consumers of `sidecarStatus` returns only page.tsx:31 (the call site) — **no
panel reads `sidecarStatus`**. Panels do not wait for "connected"; they mount and fetch
independently the moment dockview lays them out. `PanelHost` mounts dockview as soon as
`modules.length > 0` (PanelHost.tsx:67), which is unrelated to sidecar readiness. So even
the one health check that exists is decorative — it gates nothing.

---

## 3. News + Portfolio fetch paths — the panels that latch the error

### 3.1 News — single fetch on mount, keyed by symbol list, no retry

```
NewsFeedPanel.tsx:135  const [state, setState] = useState<LoadState>({ status: "loading" });
NewsFeedPanel.tsx:170  const runFetch = useCallback((applyResult) => {
NewsFeedPanel.tsx:172    fetchNews(newsSymbols)
NewsFeedPanel.tsx:173      .then((items) => applyResult({ status: "ready", items }))
NewsFeedPanel.tsx:174      .catch((error) => applyResult({ status: "error", message: errorMessage(error) }));
NewsFeedPanel.tsx:184  useEffect(() => { ... runFetch(...) }, [symbolsKey]);   // runs once per symbol list
```

`fetchNews` → `sidecarGet<NewsItem[]>("/news", ...)` (news/api.ts:21-25). On the cold-boot
race the `fetch` rejects (connection refused) → `errorMessage(error)` (NewsFeedPanel.tsx:112)
returns **"Could not reach the news service."** (because a connection-refused `TypeError`
is **not** a `SidecarError`). The panel renders the error block + a manual **Retry** button
(NewsFeedPanel.tsx:225-236). The effect only re-runs when `symbolsKey` changes
(NewsFeedPanel.tsx:197) — so absent a watchlist edit or a manual Retry click, **the error is
permanent.**

### 3.2 Portfolio — single `load()` on mount, two chained fetches, no retry

```
PortfolioPanel.tsx:54  const load = useCallback(async () => {
PortfolioPanel.tsx:56    const stored = await fetchPositions();              // GET /portfolio/positions
PortfolioPanel.tsx:57    const quotes = await fetchPositionQuotes(stored);   // GET /quotes/* (best-effort)
PortfolioPanel.tsx:58    setSummary(buildPortfolioSummary(stored, quotes));
PortfolioPanel.tsx:60    catch (err) { setSummary(null); setError(message); }
PortfolioPanel.tsx:67  useEffect(() => { void load(); }, [load]);            // runs ONCE
```

`fetchPositions` → `sidecarGet<Position[]>("/portfolio/positions")` (portfolio/api.ts:14-16).
On the race this rejects → catch sets `summary=null` + `error` and renders the error block +
**Retry** (PortfolioPanel.tsx:242-248). `load` is `useCallback([], ...)` so its identity is
stable → **the effect never re-runs**; the error is permanent until manual Retry.
(`fetchPositionQuotes` swallows per-symbol failures and returns nulls — portfolio/api.ts:69 —
so the failure point that latches is `fetchPositions`, the first hard GET.)

### 3.3 Why Watchlist (and Chart) appear to survive — they don't depend on it being a one-shot

- **Watchlist** polls on a 5s `setInterval` (WatchlistPanel.tsx:108-110, `POLL_INTERVAL_MS = 5_000`).
  The first poll fails during the race, but the **next poll 5s later self-heals** once uvicorn
  has bound. It also never clears `rows` on error (WatchlistPanel.tsx:95-97 only setError),
  so it sits on "Loading quotes…" and recovers without user action. This is the accidental
  retry loop News and Portfolio lack.
- **Chart** re-fetches whenever `[symbol, timeframe]` changes (ChartPanel.tsx:329); if the
  default symbol's first fetch races the bind it can also show an error, but interacting with
  the chart (symbol/timeframe change) re-triggers it. It is less obviously "stuck" than News
  / Portfolio, whose only re-trigger is a manual Retry or a watchlist edit.

**This asymmetry is exactly the operator's report: News + Portfolio are the one-shot-on-mount
fetchers with no interval, so they are the panels that visibly latch "failed to load."**

---

## 4. Root cause (precise)

Two independent gaps combine:

1. **Rust announces a port, not a ready service.** `pick_free_port()` (lib.rs:23) reserves
   a port and stores it (lib.rs:137-138) _before_ the sidecar is spawned, and the spawn
   itself (lib.rs:201) is delayed behind a blocking, up-to-90s MCP-supervisor join
   (lib.rs:181-182; openbb_mcp.rs:140 with `MCP_PORT_WAIT_SECS=45 × 2`). The only bind
   verification (lib.rs:219-225) is a log-only side thread the frontend can't see.

2. **Frontend assumes the port implies a live server.** `getSidecarBaseUrl()` resolves and
   caches off the bare port with no probe (sidecar-client.ts:52-65); `sidecarGet` fetches
   once with no retry (sidecar-client.ts:71-104); the `sidecarStatus` "connection lifecycle"
   is one-shot (store/app.ts:24-34) and read by no panel.

Result: News (NewsFeedPanel.tsx:184) and Portfolio (PortfolioPanel.tsx:67) fire their single
mount fetch into a socket with nothing listening, the `fetch` is refused, and they latch a
permanent error until the user clicks Retry. Watchlist masks the same bug behind its 5s poll.

---

## 5. The fix

The clean, minimal fix targets the frontend boundary (where the gap is universal across all
panels) plus an optional Rust readiness signal. Recommended layering:

### 5.1 Primary fix — make `getSidecarBaseUrl()` await readiness once (frontend, blast-radius-safe)

Gate the _cached_ base URL on a real `/health` probe with bounded retry/backoff, so the
first successful resolution implies the sidecar is actually listening. Because every panel
funnels through `getSidecarBaseUrl()` (and `sidecarGet` calls it), one change fixes all
panels at once and the cache means the cost is paid exactly once per session.

```ts
// src/lib/sidecar-client.ts
let readyPromise: Promise<string> | null = null;

export function getSidecarBaseUrl(): Promise<string> {
  if (readyPromise) return readyPromise; // single in-flight resolution, shared by all callers
  readyPromise = resolveAndAwaitReady().catch((e) => {
    readyPromise = null; // allow a later caller / manual Retry to re-arm
    throw e;
  });
  return readyPromise;
}

async function resolveAndAwaitReady(): Promise<string> {
  const base = await resolvePortToBaseUrl(); // existing port-resolution logic (incl. dev ?sidecar-port=)
  // Poll /health until the sidecar actually binds. Cold boot can be tens of
  // seconds (MCP join + uvicorn startup), so budget generously with backoff.
  const deadline = Date.now() + 120_000;
  let delay = 250;
  for (;;) {
    try {
      const r = await fetch(new URL("/health", base).toString());
      if (r.ok) return base; // bound + healthy → cache wins
    } catch {
      /* connection refused — sidecar not bound yet */
    }
    if (Date.now() > deadline) throw new SidecarError(503, "sidecar did not become ready");
    await new Promise((res) => setTimeout(res, delay));
    delay = Math.min(delay * 1.6, 2_000); // exponential backoff, capped at 2s
  }
}
```

Key properties:

- Replaces the permanent `cachedBaseUrl` (sidecar-client.ts:33) with a shared `readyPromise`
  so concurrent panel mounts all await the _same_ readiness probe instead of each firing a
  doomed fetch.
- On failure it nulls the promise (re-armable) — a manual Retry or a later panel mount
  triggers a fresh probe rather than being stuck on a poisoned cache.
- The dev `?sidecar-port=` fallback (sidecar-client.ts:56-62) folds into
  `resolvePortToBaseUrl()` unchanged.
- `sidecarGet` / `sidecarSend` / `openCryptoStream` need **no change** — they already
  `await getSidecarBaseUrl()` first, so they now transparently wait for readiness.

### 5.2 Secondary fix — let News + Portfolio retry their own first load (defense in depth)

Even with §5.1, add a bounded auto-retry so a transient post-ready blip self-heals (matches
Watchlist's resilience). Minimal version: on the mount effect's error path, schedule one
delayed re-run.

- **News** (NewsFeedPanel.tsx:184-197): in the `applyResult` error branch, `setTimeout` a
  re-`runFetch` a few times with backoff before surfacing the terminal error + Retry.
- **Portfolio** (PortfolioPanel.tsx:67-72): wrap `load()` so a failed first load re-tries on
  a short backoff before latching the error block.

(Manual Retry stays as the final fallback.)

### 5.3 Optional Rust hardening — announce readiness, not just the port

If you want the core to be the source of truth (cleaner long-term), have Rust emit a Tauri
event once `wait_for_port(port)` succeeds (lib.rs:220) and have the frontend await it:

- Replace the log-only side thread (lib.rs:219-225) with: on bind success, `app.emit(
"sidecar-ready", port)`; on failure, `app.emit("sidecar-failed", ...)`.
- Add a `get_sidecar_ready` command (or a `Mutex<bool>` in state) so a frontend that mounts
  _after_ the event already fired can still query the latched state (avoids the event-vs-mount
  race in the other direction).
- Frontend `getSidecarBaseUrl()` then awaits the event/flag instead of polling `/health`.

This is **not strictly required** — §5.1 alone fully closes the user-visible bug and is
lower blast-radius (no Rust change, no Tauri event contract). §5.3 is the "do it right at the
core" option if the team prefers the readiness signal to live in Rust. The two are
compatible: §5.1's `/health` poll is the portable fallback, §5.3 is the fast-path signal.

**Recommendation:** Ship §5.1 (the universal frontend gate) + §5.2 (News/Portfolio
self-heal). §5.1 is the load-bearing change; it converts every panel's first fetch from
"fire into a dead socket" to "await a real readiness probe," which is precisely the missing
piece. Defer §5.3 unless the team wants the readiness signal owned by the Rust core.

---

## 6. Evidence index (file:line)

| Claim                                                         | Location                                             |
| ------------------------------------------------------------- | ---------------------------------------------------- |
| Port picked + released before sidecar exists                  | src-tauri/src/lib.rs:23-29, 137                      |
| Port stored in state, queryable immediately                   | src-tauri/src/lib.rs:138, 20                         |
| `get_sidecar_port` returns number, no liveness                | src-tauri/src/lib.rs:115-118                         |
| MCP join blocks before main sidecar spawn                     | src-tauri/src/lib.rs:181-182, 201                    |
| MCP spawn blocks on up-to-90s port wait                       | src-tauri/src/lib.rs:79, 84; openbb_mcp.rs:140       |
| Bind check is log-only, not surfaced                          | src-tauri/src/lib.rs:219-225                         |
| uvicorn binds only after sidecar boot                         | sidecar/main.py:105                                  |
| Base URL cached off bare port, no probe                       | src/lib/sidecar-client.ts:33, 52-65                  |
| `sidecarGet` single fetch, no retry                           | src/lib/sidecar-client.ts:71-104                     |
| No retry/backoff in client or app store                       | grep: none in sidecar-client.ts / store/app.ts       |
| `connectSidecar` one-shot, status read by no panel            | src/store/app.ts:24-34; only consumer page.tsx:31    |
| News: single mount fetch, manual Retry only                   | src/modules/news/NewsFeedPanel.tsx:184-197, 225-236  |
| News connection-refused → "Could not reach the news service." | src/modules/news/NewsFeedPanel.tsx:112-116           |
| Portfolio: single `load()` on mount, stable callback          | src/modules/portfolio/PortfolioPanel.tsx:54-72       |
| Portfolio first hard GET that latches error                   | src/modules/portfolio/api.ts:14-16                   |
| Watchlist self-heals via 5s poll                              | src/modules/watchlist/WatchlistPanel.tsx:14, 103-114 |
| Panels mount on modules, not sidecar status                   | src/components/PanelHost.tsx:67-77                   |
