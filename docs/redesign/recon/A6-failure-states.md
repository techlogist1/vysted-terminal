# Recon — A6:failure-states

AgentBuilder renders both saved and error states with a "Try again" button. Clean.

I now have a complete picture. Let me compile the ranked blueprint. The codebase is unusually disciplined — most surfaces have all four states. The real offenders are the **fire-and-forget async paths** where failures vanish: portfolio quote fetch, delegate-run poller/answer, and the Exa key save. Let me verify the portfolio `fetchPositionQuotes` has no catch (confirmed at lines 92-98) and check the AnalystRatings per-tab retry gap one more time — already confirmed there's no retry button, only re-submit.

Here is the blueprint.

---

# Track-3 Empty/Loading/Error/Unavailable Audit — Implementation Blueprint

## (1) Findings — what exists today

The frontend is **unusually disciplined**: chart, watchlist, news, equity-overview, screener, sec, macro, earnings, backtest, quant (all 4), analyst-ratings, portfolio table, BriefPanel, KeyEntryDialog, agent-builder, ConnectCard all have **distinct EMPTY vs LOADING (skeleton) vs ERROR+Retry** states, and several use a shared `useRetryOnSidecarReady` self-heal for the ~34s cold-bind. The real Track-3 violations are **fire-and-forget async paths whose failures vanish** — not missing UI states.

**Worst offenders (ranked):**

1. **`src/lib/delegate-runs.ts:131` (poller) + `:174` (`answerDelegateRun`) + `:186` (`resumeDelegateRun`)** — bare `catch { return }` / "poll will reconcile". High-traffic: every Delegate run depends on the poller. If `/runs` polling throws repeatedly the rail **freezes "running" forever** with no signal; if `answerDelegateRun` POST fails, the user clicks Submit (AgentsRail.tsx:143), the input clears, the run stays paused — **nothing tells them it failed**. This is a human-in-the-loop dead-end.

2. **`src/modules/portfolio/PortfolioPanel.tsx:92-98`** — `fetchPositionQuotes(...).then(setQuotes)` has **no `.catch`**. A rejected quote fetch is swallowed; every Price/Mkt-val/P&L cell shows `—` forever, indistinguishable from "quote unavailable". The panel has an `error` state var but it's only used for form validation, never for the quote fetch. No retry, no "couldn't reach quote service" message.

3. **`src/components/SettingsPanel.tsx:298-311` `handleSaveExa` (+ `handleRemoveExa` :313-321)** — no `catch`. A keychain `setSecret` failure throws, `finally` clears busy, `refreshExa` then shows "not configured" with **no error** — the user thinks the save worked but the key vanished. Contrast the sibling LLM `KeyEntryDialog` (handles `save-error` explicitly).

4. **`src/modules/chat/ChatSidebar.tsx:513` `launchDelegateRun(...)`** — fire-and-forget `void`. `delegate-runs.ts` does call `endRun(localId, "error", …)` internally on failure (line 97/110), so this surfaces in the rail — **acceptable**, noted only to confirm it's covered.

5. **`src/modules/analyst-ratings/AnalystRatingsPanel.tsx:130-134`** — `tabError` renders inline but has **no Retry button**; recovery requires re-submitting the symbol. Minor (the three slices auto-fetch on symbol change), but inconsistent with every other panel.

6. **`src/modules/research/BriefPanel.tsx`** — no LOADING state. A brief either exists or shows `EmptyState`. Research runs stream through the ChatSidebar's `ResearchActivity`, so the in-flight state lives there — **acceptable by design**, not a fix.

**Non-issues confirmed clean:** ChartPanel (loading/error+retry/`allFailed`/compare-state flag), WatchlistPanel, NewsFeedPanel (backoff auto-retry), EquityOverviewPanel, all quant panels (role="alert" + empty), node-editor catches (all surface messages), workflow SSE malformed-frame (console.warn, line 270), AgentBuilder (saved+error+Try-again).

## (2) Exact change plan

**Edit `src/lib/delegate-runs.ts`:**

- Add a module-level `let pollFailures = 0;`. In `pollDelegateRuns` catch (`:131`): `pollFailures++; if (pollFailures >= 5) { for each active run with sidecarRunId → store.updateRun(local.id, { detail: "Lost contact with the run — the sidecar may be down. Status may be stale." }); }`. Reset `pollFailures = 0` on the success path (after line 133). Keeps the run visible but **honestly badges staleness** instead of a frozen live readout.
- `answerDelegateRun` (`:166`) and `resumeDelegateRun` (`:180`): change signature to `Promise<{ ok: boolean; error?: string }>`; on success return `{ ok: true }`, in catch return `{ ok: false, error: err instanceof Error ? err.message : "Request failed" }`. Also check `response.ok` and return the failure.

**Edit `src/modules/chat/AgentsRail.tsx:137-167`:**

- `RunRow` gains `const [answerError, setAnswerError] = useState<string|null>(null)`. In the submit (`:140`): `const r = await answerDelegateRun(...); if (!r.ok) { setAnswerError(r.error ?? "Couldn't send your answer — retry."); return; } setAnswer("");`. Render `answerError` below the form as `text-negative text-[0.6rem]`. Removes the silent dead-end.

**Edit `src/modules/portfolio/PortfolioPanel.tsx:88-103`:**

- Add `const [quotesError, setQuotesError] = useState(false)`. Wrap the `.then` with `.catch(() => { if (!cancelled) setQuotesError(true); })` and `setQuotesError(false)` in the then. Render a dismissible banner (reuse the existing `error` banner pattern at :435) when `quotesError && holdings.length > 0`: `"Couldn't refresh live quotes — values shown without market data."` with a Retry that bumps a `quotesNonce` added to the effect deps. Distinguishes "fetch failed" from "no holdings".

**Edit `src/components/SettingsPanel.tsx` `WebSearchSection` (:298-321):**

- Add `const [exaError, setExaError] = useState<string|null>(null)`. Wrap `handleSaveExa`/`handleRemoveExa` bodies in `try { setExaError(null); … } catch (e) { setExaError(e instanceof Error ? e.message : "Couldn't save the key to the keychain."); }`. Render `exaError` as `text-negative text-xs` near the Exa input. Mirrors `KeyEntryDialog`'s `save-error`.

**Edit `src/modules/analyst-ratings/AnalystRatingsPanel.tsx:130-134`:**

- Add a Retry button beside `{tabError}` calling a new `retryTab()` that re-invokes the active tab's getter (`getHistory(symbol)` / `getPriceTargets(symbol)` / `getIndividual(symbol)`).

## (3) Risks + safe fallback

- **Poller staleness badge (Risk: false-positive on one transient blip).** Mitigated by the `>= 5` consecutive-failure threshold and reset-on-success — a single dropped poll never badges. Fallback: run stays visible; only `detail` text changes, never the status, so a recovered poll silently clears it.
- **`answerDelegateRun` signature change (Risk: breaks callers).** Only caller is `AgentsRail.tsx:143`; `resumeDelegateRun` callers are `delegate-runs.ts:186` (self) — grep `answerDelegateRun|resumeDelegateRun` before edit. Return-value is additive (callers can ignore it), so safe.
- **Portfolio quote error (Risk: banner flicker during the 5s-ish refetch).** Only show when `holdings.length > 0` and gate on the catch; the existing `—` placeholders already cover the loading gap, so the banner is purely additive.
- **Exa key catch (Risk: none).** Pure additive error surface; matches an existing pattern.
- **§6.5 untouched:** none of these touch orders, the diff gate, audit log, or any Tier-1 file. All edits are renderer-only error surfacing.

## (4) Verification

- **vitest:** `pnpm vitest run src/modules/chat/AgentsRail src/modules/portfolio src/components/SettingsPanel src/lib` — add a test that mocks `answerDelegateRun` → `{ok:false}` and asserts the error text renders + input is NOT cleared; mock `fetchPositionQuotes` reject and assert the quote-error banner appears with holdings present. Existing `delegate-runs` test (if any) — assert `pollDelegateRuns` doesn't throw and sets `detail` after 5 rejects (mock `fetch` reject).
- **curl (poller honesty):** `curl -s localhost:$PORT/runs` while a delegate run is live → confirm shape `{runs:[…]}`; then kill the sidecar mid-run and confirm the rail row gains the stale-detail text (rig).
- **rig (tauri-mcp):** `start_session` → open Delegate mode, launch a run, kill sidecar → `screenshot` shows stale badge not frozen-live; pause a run, stop sidecar, submit an answer → `snapshot` shows the answer error, input retained. Settings → Exa: with keychain access denied, save a key → error visible.
- **Gate:** `pnpm format:check && pnpm lint && pnpm typecheck` (renderer-only, no Rust/Python touched, so `cargo`/`ruff`/smoke-test unaffected).

**In short:**

- The codebase is genuinely strong on EMPTY/LOADING/ERROR UI states; the gaps are **swallowed fire-and-forget async failures**, not missing components.
- Top 3 fixes: delegate-run poller/answer silent-fail (`delegate-runs.ts` + `AgentsRail.tsx`), portfolio quote fetch no-catch (`PortfolioPanel.tsx:92`), Exa key save no-catch (`SettingsPanel.tsx:298`).
- All fixes are renderer-only, additive, and touch no Tier-1/§6.5 files.
- `Confidence: 8/10` — high on the offenders found; the 2-point gap is panels I sampled by grep rather than full-read (GreeksDashboard/YieldCurve/OptionPricer empty-state wording, marketplace/plugin-manager) and the exact `useRetryOnSidecarReady` failure-latch behavior, which I confirmed by usage but did not read line-by-line.
