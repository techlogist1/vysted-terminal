# Phase 10 Adversarial Bug Hunt — Error Handling / User-Facing Error Surfaces / Cold-Boot & Degraded States

Lens: swallowed errors, misleading messages, missing error banners, panels that show "failed" without
recovery, unhandled rejections, error states that never recover when the dependency comes back up.
Scope: frontend (`src/`) + Python sidecar (`sidecar/`). Every claim cites `file:line` against the
actual source on disk. The §6.5 LOCKED files (`sidecar/models/audit_log.py`, `kill_switch.py`,
`broker_base.py`, `types/plugin.ts`, `tests/test_safety_end_to_end.py`) were treated as read-only —
all findings below are in NON-locked files.

---

## Summary of findings (by severity)

| #   | Severity | Title                                                                                                                                            | File                                                                     |
| --- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| 1   | HIGH     | Sidecar connection error is set but never rendered — no global banner, no retry, no reconnect                                                    | `src/store/app.ts` + `src/app/page.tsx`                                  |
| 2   | HIGH     | Kill-switch fire failure is silently swallowed — panic button shows no error when the halt does NOT propagate                                    | `src/modules/safety/KillSwitchToolbar.tsx`                               |
| 3   | HIGH     | Chart "Retry" button is a no-op when the symbol is unchanged                                                                                     | `src/modules/chart/ChartPanel.tsx`                                       |
| 4   | MEDIUM   | Chat assistant message stuck `pending` forever + composer locked forever if SSE stream ends without a terminator frame                           | `src/modules/chat/streaming.ts` + `ChatSidebar.tsx`                      |
| 5   | MEDIUM   | `getSecret` rejection in chat send is an unhandled rejection — user message left dangling, no error                                              | `src/modules/chat/ChatSidebar.tsx`                                       |
| 6   | MEDIUM   | Broker mode toggle (paper↔live) + read-only toggle silently no-op on failure — unhandled rejection, no UI feedback                               | `src/modules/broker-connect/BrokerConnectPanel.tsx`                      |
| 7   | MEDIUM   | Screener universe load failure is fully swallowed — panel shows nothing, "Run" still enabled against empty universe                              | `src/store/screener.ts` + `ScreenerPanel.tsx`                            |
| 8   | MEDIUM   | Broker refresh error rendered as "No brokers reported by sidecar." — masks a connection failure as an empty state                                | `src/modules/broker-connect/BrokerConnectPanel.tsx`                      |
| 9   | MEDIUM   | Workflow run overlay stuck on "running" forever if the run SSE ends without a terminal event                                                     | `src/modules/node-editor/NodeEditorPanel.tsx`                            |
| 10  | LOW      | First-party agents fail silently with a misleading "static catalog fallback" comment that does not exist                                         | `src/modules/chat/ChatSidebar.tsx` + `src/store/agents.ts`               |
| 11  | LOW      | Watchlist first-load failure shows "Loading quotes…" forever beneath an error banner; dropped per-symbol quotes show permanent "—" with no cause | `src/modules/watchlist/WatchlistPanel.tsx` + `sidecar/routers/quotes.py` |
| 12  | LOW      | KeyEntryDialog conflates "sidecar/provider transport error" with "your key is invalid"                                                           | `src/components/KeyEntryDialog.tsx`                                      |

---

## HIGH severity

### 1. Sidecar connection error is set but never rendered anywhere

**Files:** `src/store/app.ts:24-34`, `src/app/page.tsx:24-65`

`connectSidecar` is the app's one liveness handshake with the Python sidecar:

```ts
// src/store/app.ts
connectSidecar: async () => {
  set({ sidecarStatus: "connecting", sidecarError: null });
  try {
    const baseUrl = await getSidecarBaseUrl();
    await sidecarApi.health();
    set({ sidecarBaseUrl: baseUrl, sidecarStatus: "connected", sidecarError: null });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    set({ sidecarStatus: "error", sidecarError: message });   // <-- set, never read
  }
},
```

It is invoked exactly once, fire-and-forget, on mount: `page.tsx:31` `void useAppStore.getState().connectSidecar();`

A repo-wide grep proves **nothing consumes `sidecarStatus` or `sidecarError`**:

```
$ grep -rn "sidecarStatus\|sidecarError" src --include=*.tsx --include=*.ts | grep -v .test.
src/store/app.ts:12,14,22,23,25,29,32   # definitions + writes only
```

No component subscribes to `useAppStore` for status. `page.tsx` imports it only to call `connectSidecar`.

**Consequences (cold-boot / degraded):**

- On the documented cold-boot race (the sidecar `--onefile` `_MEI` extraction + MCP contention; see the
  CLAUDE.md "MCP cold-bind is ~34s" gotcha), the one-shot `health()` can fail. The status flips to
  `"error"` and **stays there forever** — there is no reconnect loop, no retry button, and no banner.
- Each data panel independently shows its own "failed to load" and then degrades/recovers on its own
  poll cadence, but the user gets **no single, authoritative "the data engine is starting / is down"
  signal**. A first-launch user whose sidecar lost the bind window sees a wall of red panel errors with
  no explanation that they share one root cause and will clear on relaunch.
- `connectSidecar`'s own doc-comment says "Safe to call repeatedly," but there is no caller that ever
  calls it a second time.

**Repro:** Launch with the sidecar slow to bind (or kill the sidecar after boot). Every panel errors;
no global banner appears; nothing ever re-probes `/health`; bringing the sidecar back up does not flip
the app out of the error state (the only recovery is per-panel manual retry, where one exists).

**Fix:** Render a global connection banner driven by `sidecarStatus` (in `page.tsx`, above/below
`OnboardingBanner`). On `"error"`, show a "Data engine unreachable — Retry" affordance that re-invokes
`connectSidecar`, and run a bounded backoff re-probe loop while in `connecting`/`error` so the app
self-heals when the sidecar finishes binding. This is the natural home for the cold-boot UX.

---

### 2. Kill-switch fire failure is silently swallowed (safety-UX)

**File:** `src/modules/safety/KillSwitchToolbar.tsx:58-74` (toolbar) + `src/store/safety.ts:210-241` (store)

`store/safety.ts` deliberately makes `fireKillSwitch` / `resetKillSwitch` _throw_ on failure (they do not
write `killSwitchError`):

```ts
// src/store/safety.ts:217-219
if (!response.ok) {
  throw new Error(`kill-switch fire failed (${response.status})`);
}
```

The toolbar then swallows that throw and shows nothing:

```ts
// src/modules/safety/KillSwitchToolbar.tsx:64-71
try {
  const result = await fireKillSwitch(reason, firedBy);
  setBanner(result);
} catch {
  setBanner(null); // <-- failure path: clears the banner, shows NOTHING
} finally {
  setBusy(false);
}
```

`handleReset` (lines 105-113) is worse — no `catch` at all, so a failed reset is an unhandled rejection.

**Consequences:** The kill switch is the single most safety-critical control in the app (BLUEPRINT §6.5 #5
— "halt all trading"). If the sidecar is unreachable, the safety bus errors, or the POST returns non-2xx,
the user clicks "Halt All Trading", sees it flash `Firing…`, and it returns to the normal **armed** state
with **zero feedback that the halt did not reach any broker**. During a runaway-AI / fat-finger event the
operator would believe trading was halted when it was not. The OS-shortcut path (`Cmd/Ctrl+Shift+K`,
lines 88-91) has the same silent-failure behavior.

`store/safety.ts` and `KillSwitchToolbar.tsx` are frontend files — NOT in the LOCKED §6.5 set
(`audit_log.py`, `kill_switch.py`, `broker_base.py`, `types/plugin.ts`, `test_safety_end_to_end.py`),
so this is fixable without touching a locked surface.

**Repro:** Stop the sidecar (or block `/safety/kill-switch`). Click "Halt All Trading." Button briefly
shows "Firing…", then silently returns to armed — no error, no toast.

**Fix:** On the catch path, surface a prominent persistent error state (a red "KILL SWITCH FAILED TO FIRE
— RETRY" banner is the right altitude here, not a silent reset). Add a `catch` to `handleReset`. Consider
having the store set a `killSwitchError` on the fire/reset paths so the surface is store-driven and
consistent with `refreshKillSwitchStatus`.

---

### 3. Chart "Retry" button is a no-op when the symbol is unchanged

**File:** `src/modules/chart/ChartPanel.tsx:1030-1041`

The price-history error state renders a Retry button:

```tsx
{priceState === "error" ? (
  ...
  <Button size="sm" variant="outline" onClick={() => setSymbol((current) => `${current}`)}>
    Retry
  </Button>
) : null}
```

`setSymbol((current) => `${current}`)` sets state to the **same string value**. React bails out of a state
update that returns `Object.is`-equal state, so no re-render happens and the price-loading effect
(`useEffect(..., [symbol, timeframe])` at lines 285-327) does **not** re-run. The Retry button does nothing.

**Consequences:** The most common failure (transient sidecar/history error on the default `SPY` chart at
cold boot) leaves the user with a dead Retry button. The only workaround is re-typing the symbol or
toggling the timeframe — both of which actually change a dependency. The button looks like recovery but
isn't.

**Repro:** Boot with the sidecar history endpoint failing → chart shows "Failed to load price history."

- Retry. Bring the endpoint back up, click Retry → nothing happens. Change the timeframe → it loads.

**Fix:** Make Retry force a refetch independent of `symbol`. Add a `reloadNonce` state
(`const [reloadNonce, setReloadNonce] = useState(0)`), include it in the price effect deps, and have Retry
do `setReloadNonce((n) => n + 1)`.

---

## MEDIUM severity

### 4. Chat message stuck `pending` forever + composer locked forever on a truncated SSE stream

**Files:** `src/modules/chat/streaming.ts:74-125`, `src/modules/chat/ChatSidebar.tsx:42,166-207,291`

`consumeSseStream` only calls `onError`/terminates abnormally on a `fetch` throw or a non-ok response. If
the stream opens 200-OK, emits some `delta` frames, then the connection **closes without ever sending a
`done` or `error` frame** (sidecar crash mid-stream, worker recycle, network drop), the read loop simply
hits `done` and returns normally:

```ts
// streaming.ts:100-119 — loop exits on reader `done`, no synthetic terminal event
const { done, value } = await reader.read();
if (done) { break; }
...
// finally: reader.releaseLock();  -- returns cleanly, no onDone / onError fired
```

The chat-history reducer only clears `pending` / `streamingMessageId` from `finalizeAssistantMessage`
(on `done`) or `failAssistantMessage` (on `error`) — `chat-history.ts:98-111`. Neither fires.

**Consequences:**

- The assistant message stays `pending: true` forever → the blinking `▋` cursor never stops
  (`ChatSidebar.tsx:265-268`).
- `streamingMessageId` stays non-null → `streaming` is `true` (`ChatSidebar.tsx:42`) → the composer is
  **disabled forever** (`disabled={streaming}`, line 291). The user cannot send another message and has no
  way to recover except reloading the app.

Note: the _sidecar_ LLM route is robust (it wraps the generator and always emits an error+done frame on
exception — `sidecar/routers/llm.py:79-82`). The hole is the transport/process-death case the route can't
cover, plus any provider adapter that ends its async generator without yielding a `done`.

**Repro:** Start a chat stream, then kill the sidecar process mid-response. The message keeps its blinking
cursor and the composer stays greyed out indefinitely.

**Fix:** After the read loop completes in `consumeSseStream`, track whether a terminal (`done`/`error`)
event was dispatched; if not, synthesize `onError(new Error("stream ended unexpectedly"))` (or an
`onDone`). Equivalently, have `ChatSidebar`'s handler treat normal stream completion without a `done` as a
failure so `failAssistantMessage` runs and unlocks the composer.

---

### 5. `getSecret` rejection during chat send is an unhandled rejection

**File:** `src/modules/chat/ChatSidebar.tsx:145-163`, `289`

In `handleSend`:

```ts
appendUser(prompt);                                   // line 145 — user msg already on screen
...
if (requiresKey) {
  apiKey = await getSecret(KEYCHAIN_NAMESPACES.llmProvider(provider));  // line 159 — can REJECT
  if (!apiKey) { setStatusLine(...); return; }
}
```

`getSecret` (`src/lib/keychain.ts:55-58`) is a thin `invoke("keychain_get")`. `invoke` **rejects** if the
Tauri command errors (keychain locked / OS denial / Tauri unavailable). It is not wrapped in try/catch, and
`handleSend` is invoked as `void handleSend(text)` (line 289), so the rejection becomes an unhandled
promise rejection.

**Consequences:** The user's message is already appended (line 145), but the assistant message is never
begun (that's after line 159). The user sees their prompt with **no response, no error, no status line** —
just silence — and the rejection is logged only to the console. (Contrast: a `null` key is handled
gracefully at line 160; a _thrown_ error is not.)

**Repro:** On macOS, lock the login keychain (or simulate an `invoke` rejection) and send a chat message.
The user bubble appears; nothing else happens.

**Fix:** Wrap the `getSecret` call in try/catch and route failures into `setStatusLine(...)` (or begin the
assistant message and `fail` it) so the keychain failure is visible.

---

### 6. Broker mode (paper↔live) and read-only toggles silently no-op on failure

**File:** `src/modules/broker-connect/BrokerConnectPanel.tsx:230-237`

```ts
const handleModeToggle = useCallback(async () => {
  const next: BrokerMode = state.mode === "paper" ? "live" : "paper";
  await setMode(state.broker, next); // no try/catch
}, [setMode, state.broker, state.mode]);

const handleReadOnlyToggle = useCallback(async () => {
  await setReadOnly(state.broker, !state.readOnly); // no try/catch
}, [setReadOnly, state.broker, state.readOnly]);
```

`setMode` / `setReadOnly` (`src/store/brokers.ts:106-136`) **throw** on a non-ok response and also `await
refreshOne` (which can throw). The toggle handlers do not catch.

**Consequences:** Clicking "Go live" / "Go paper" / "Read-only" when the sidecar rejects or is down throws
an unhandled rejection with **no UI feedback**. The mode badge does not change (the throw happens before
the optimistic refresh succeeds), so a user who clicks "Go live" and gets a silent failure may not notice
the badge still says `paper` — or, more dangerously, glance away assuming the toggle took. This is a
safety-relevant control (paper↔live).

**Repro:** Block `POST /brokers/{id}/mode` (or stop the sidecar) and click "Go live." Nothing visible
changes; console logs an unhandled rejection.

**Fix:** Wrap both handlers in try/catch and surface the failure on the broker row (there is already a
`state.error` rendering path at line 250 — route the message there, or add a transient inline error).

---

### 7. Screener universe load failure is fully swallowed

**Files:** `src/store/screener.ts:143-180` (`loadUniverse`), `src/modules/screener/ScreenerPanel.tsx:35-105`

`loadUniverse` discards the error entirely:

```ts
// src/store/screener.ts:169-172
} catch {
  set((state) => ({
    universeStatus: { ...state.universeStatus, [id]: "error" },   // status only, no message
  }));
  return null;
}
```

And `ScreenerPanel` **never reads `universeStatus`** — it only reads `universeMeta[universe]` and renders
the ticker count _gated on truthiness_:

```tsx
// ScreenerPanel.tsx:72-76
{
  universeInfo && universe !== "custom" && (
    <span>
      {universeInfo.symbols.length} tickers · {universeInfo.asset_class}
    </span>
  );
}
```

**Consequences:** On a universe-fetch failure (e.g. sidecar cold-boot, `/screener/universe` 502), the
panel shows **no ticker count, no error, nothing** — the universe picker just silently has no metadata.
Worse, the "Run screener" button stays **enabled** (`disabled={status === "loading"}` only — `status` is
the _run_ status, not the universe status), so the user can run a screen against a universe that failed to
load. Whether that produces an empty result or a confusing error depends on the backend, but either way
the root cause (universe load failed) is invisible.

**Repro:** Boot with `/screener/universe` failing, open the Screener panel. No ticker count appears; the
panel looks idle; clicking "Run screener" produces a confusing result with no hint the universe never loaded.

**Fix:** Capture the error message in the catch (mirror `runScreener`), and have `ScreenerPanel` read
`universeStatus[universe]` to render a "couldn't load universe — retry" affordance and to disable Run while
the selected non-custom universe is in `"error"`/unloaded state.

---

### 8. Broker refresh failure rendered as an empty state ("No brokers reported by sidecar.")

**File:** `src/modules/broker-connect/BrokerConnectPanel.tsx:154-158`

```tsx
{
  primary.length === 0 && (
    <p>{status === "loading" ? "Loading…" : "No brokers reported by sidecar."}</p>
  );
}
```

`refreshBrokers()` is fire-and-forget (line 122). The brokers store sets `status: "error"` with a message
on failure (`src/store/brokers.ts:62-64`), but the panel only distinguishes `"loading"` from everything
else. On an `"error"` status with an empty `byId`, the panel prints **"No brokers reported by sidecar."**

**Consequences:** A sidecar connection failure is displayed as a _successful empty result_ — a misleading
message. The user thinks the app genuinely found no brokers (and there is no retry), when in fact the
fetch failed. `store.error` is populated but never surfaced.

**Repro:** Boot with `/brokers` failing. Open Broker Connections → "No brokers reported by sidecar." with
no error indication and no retry.

**Fix:** Branch on `status === "error"` to render the stored `error` message + a Retry that calls
`refreshBrokers()` again.

---

### 9. Workflow run overlay can hang on "running" forever on a truncated run stream

**File:** `src/modules/node-editor/NodeEditorPanel.tsx:333-385` + `consumeSse:789-828`

`consumeSse` (like the chat one) returns normally when the reader hits `done`, with no synthetic terminal
event. `handleRun` only flips to `"error"` if `fetch`/non-ok throws or the loop throws:

```ts
// NodeEditorPanel.tsx:367-369 — happy path just drains the stream
await consumeSse(response.body, (event) => {
  setRunState((prev) => applyEvent(prev, event));
});
// no terminal-event check after consumeSse returns
```

If the `/workflow/run` SSE emits `run-start` + some `node-*` frames and then the connection closes without
a `run-complete` or `run-error` (sidecar crash / worker recycle), `applyEvent` never moves the run out of
`"running"` (`workflow-run-overlay.tsx:94-106` only transitions on those two events).

**Consequences:** The overlay's status badge stays `running`, the "Run again" footer never appears
(`onRerun` is gated on `runState.status !== "running"`, line 497), and the toolbar Run button stays
disabled (`disabled={... runState.status === "running"}`, line 440). The workflow surface is wedged until
the user clicks the overlay's × (which aborts) — but the visual lies, claiming the run is still in flight.

**Repro:** Start a workflow run, kill the sidecar mid-run. Overlay sits on "running" with N/N never
completing; Run button stays disabled.

**Fix:** After `consumeSse` resolves, if `runState.status` is still `"running"` (no `run-complete`/
`run-error` seen), set it to `"error"` with a "run stream ended unexpectedly" message.

---

## LOW severity

### 10. First-party agents fail silently behind a misleading "static catalog fallback" comment

**Files:** `src/modules/chat/ChatSidebar.tsx:73-77`, `src/store/agents.ts:174-216`

```ts
// ChatSidebar.tsx:73-77
// Fetch agents + providers once on mount. Failures are silent — the static
// catalogs in the stores are the fallback.
useEffect(() => { void refreshAgents(); void refreshProviders(); }, [...]);
```

The comment claims a "static catalog fallback," but `useAgentsStore` initializes `firstPartyAgents: []`
(`agents.ts:175`) — there is **no static catalog**. `refreshFirstParty` sets `firstPartyError` on failure
(`agents.ts:212-215`), but `ChatSidebar` never reads it.

**Consequences:** If `/agents` fails at cold boot, the agent picker silently shows only "No agent (raw
chat)" — every first-party agent (Buffett, Dalio, Druckenmiller, Graham, …) is absent with no indication
of _why_. The user assumes the product ships no agents. The misleading comment will also send the next
maintainer looking for a fallback that doesn't exist. (There IS a real "bundle didn't include the agents
dir → `/agents` returns `[]`" failure mode documented in the CLAUDE.md v0.8.0 gotcha — which this silent
path would also hide.)

**Fix:** Either surface `firstPartyError` in the picker header (small "agents failed to load — retry"),
or correct the comment. At minimum, distinguish "no agents configured" from "agent fetch failed."

### 11. Watchlist: "Loading quotes…" forever on first-load failure; dropped per-symbol quotes show silent "—"

**Files:** `src/modules/watchlist/WatchlistPanel.tsx:86-114,160-164`, `src/modules/watchlist/api.ts:30-64`,
`sidecar/routers/quotes.py:39-60`

Two compounding issues:

1. **First-load failure → permanent "Loading…":** `rows` starts `null`; on a failed refresh only `error`
   is set, `rows` stays `null` (`WatchlistPanel.tsx:95-97`). The render shows the error banner **and**
   "Loading quotes…" simultaneously (lines 154-164), which is confusing. The 5s poll does keep retrying
   (so it self-heals when the sidecar recovers), but the interim UI claims it's still loading.

2. **Silently dropped symbols:** the batch `/quotes` endpoint swallows per-symbol failures server-side —
   `quotes.py:59-60` returns only `isinstance(result, Quote)` results, dropping any symbol that raised.
   `fetchWatchlistQuotes` then maps the missing symbol to `quote: null` (`api.ts:56-62`), and the row
   renders a permanent "—" (`WatchlistPanel.tsx:193,205`) with **no indication the lookup failed** vs.
   "no data exists." A typo'd or delisted ticker looks identical to a transient provider hiccup.

**Fix:** (1) Show the error banner _instead of_ the loading text when `rows === null && error !== null`,
and add a Retry. (2) Distinguish "quote dropped/failed" from "no data" — either have the batch endpoint
report which symbols failed, or render a distinct per-row "failed" affordance.

### 12. KeyEntryDialog conflates transport/provider errors with "your key is invalid"

**File:** `src/components/KeyEntryDialog.tsx:150-163,74-78`

`postValidate` maps a non-ok sidecar response to `{ ok: false, detail: "sidecar returned <status>" }`
(lines 158-160). The dialog renders that under `status === "invalid"` (lines 74-77, 119-121) — i.e. it
tells the user the **key** was rejected. But a 502 there means the _sidecar/provider_ errored during the
probe (e.g. provider rate-limited the models-list call), not that the key is bad.

**Consequences:** A user with a perfectly valid key whose provider is momentarily unreachable is told
"Key was not accepted by the provider" / "sidecar returned 502" and is **blocked from saving** a good key.
The genuine network-down case (fetch throws) does fall to the `save-error` branch (line 84) — but the
non-ok-response case is mislabeled as a key problem.

**Fix:** Distinguish HTTP/transport failures (5xx, network) from provider-rejected (the `ok:false` the
provider actually returned) and label them differently — e.g. "Couldn't reach the validator — try again"
vs. "The provider rejected this key."

---

## Notes / things checked that are FINE (to avoid re-flagging)

- `sidecar/routers/news.py:99` calls `news_provider.fetch_news` with no try/except, BUT
  `news_provider.fetch_news` only ever raises `ProviderError` (it catches every per-source exception —
  `news_provider.py:247,263`, and raises `ProviderError` only when _all_ sources fail, line 307). The
  app-level `@app.exception_handler(ProviderError)` (`app.py:180-183`) turns that into a clean 502. Safe.
- `sidecar/routers/quotes.py` batch swallow is intentional (one bad symbol shouldn't fail the batch) — the
  problem is purely that the _frontend_ doesn't distinguish dropped-from-batch vs no-data (finding #11).
- `sidecar/routers/sec_filings.py:45-65` has an unusually _honest_ 501 message for the cold-start MCP-bind
  race — good model for the rest of the app.
- `OrderConfirmationDialog.tsx`, `BrokerOrderEntry.tsx`, `GreeksDashboard.tsx` / quant store,
  `MacroPanel`, `SecFilingsPanel`, `NewsFeedPanel` all surface inline errors with a working
  retry/resubmit affordance — these are the good baseline the weaker surfaces should match.
- `lib/sidecar-client.ts:94-104` normalizes a malformed/truncated 200 body into a `SidecarError(502)` —
  good defensive handling.
- `src/lib/sidecar-client.ts:107` `openCryptoStream` (WebSocket helper) appears unused by any panel
  (watchlist polls `/crypto/ticker` instead) — dead code, not an error-surface bug, but worth a cleanup
  pass since it has no reconnect/onerror handling and could mislead a future author into thinking the
  crypto stream is wired.
