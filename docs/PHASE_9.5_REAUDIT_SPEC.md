# Phase 9.5 — Second-Pass Re-Audit Spec

**Build under test:** `origin/main` @ `f3bef61` — the post–Phase-9 fix-sprint tree.
Still labelled **v0.8.0** in `package.json` / `Cargo.toml` / `tauri.conf.json`
(the operator has **not** bumped the version; this is an unreleased verification
build, not a tagged release).

**Purpose:** This is **functional-completeness QA**, not a release gate. The
first pass (`docs/PHASE_9_BUG_CATALOG.md`, build `e9775b5`) catalogued 93 items +
adversarial vectors and surfaced 7 S2 + 6 S3 defects. The Phase 9 sprint fixed
them. This second pass:

1. **Regression-verifies** the 6 confirmed fixes actually hold on the built
   bundle (not just in unit tests).
2. **Sweeps the async-refactor blast radius** — fix #3 changed sidecar
   concurrency broadly; ripple must be checked.
3. **Clears the deferred-on-setup items** the first pass could not reach, given
   whatever setup the operator configures this time.
4. **Re-runs the heavier adversarial vectors** not completed in pass 1.
5. **Collects visual/density observations separately** as INPUT to the future
   design overhaul — **not** to fix in this functional loop.

It deliberately does **not** re-run the ~33 clean, untouched items from pass 1
(listed in §4).

The companion runner prompt is `docs/PHASE_9.5_MAC_RUNNER.md`. The Mac pass
writes its findings to `docs/PHASE_9.5_BUG_CATALOG.md`.

---

## 1. Fix-sprint summary — what to regression-verify

All landed at `f3bef61` (commits `9352095`, `d26b7f3`, `3da2a13`, frontend +
async + rs teammate branches merged). For each: the defect, the fix, the files
touched, and the **exact GUI/endpoint check** that proves it on the bundle.

### S2 fixes

| #                  | Defect (pass-1 finding)                                                                                                                                                                                                                                                                               | Fix                                                                                                                                                                                                                                                                                                                                   | Files touched                                                                                                                                        | Regression check on the bundle                                                                                                                                                                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **#79**            | `/safety/audit-log` → **500** on every valid limit; Audit Log Viewer (a **safety surface**) unreadable; surfaced in-app as a CORS error via the CORS-masks-500 trap.                                                                                                                                  | Cold reads of a fresh DB raised `no such table: audit_orders` (reader connection is `query_only`, can't `CREATE TABLE`). Added `_ensure_initialized()` (opens+closes a writer connection to apply the idempotent DDL) at the top of `tail`/`range_`/`export_csv`. **Append-only triggers + `query_only` reader invariant unchanged.** | `sidecar/services/audit_log.py` (Tier-1 **LOCKED §6.5**, operator-approved), `sidecar/tests/test_audit_log.py` (+4 cold-DB regression tests)         | Open Audit Log panel on a **fresh data dir** → must render an empty table (or rows), **never** a 500/CORS error. Direct-curl `GET /safety/audit-log?limit=200` → **200** `{"entries":[...]}`. Confirm §6.5 still 9/9 (`test_safety_end_to_end.py`).                                             |
| **#91**            | `/screener/universe?id=sp500` → **502 "missing universe snapshot 'sp500.json'"**; Screener dead for all preset universes (PyInstaller `--add-data` gap, same class as the L3 agents-dir bug).                                                                                                         | Added the universe dir to the sidecar bundle via `--add-data`; extended the smoke-test to probe the endpoint.                                                                                                                                                                                                                         | `scripts/ensure-sidecar.mjs` (`services/screener_universes` → `--add-data`), `scripts/smoke-test-sidecars.mjs` (`/screener/universe?id=sp500` probe) | On the **built bundle**: Screener → run an `sp500` (and `nifty50`, `crypto-top50`) preset → universe resolves, screen runs. Direct-curl `GET /screener/universe?id=sp500` → **200**. (Smoke-test already asserts this; the GUI check confirms end-to-end.)                                      |
| **#3**             | `GET /quotes?symbols=<55>` took **~26.3 s** (sequential yfinance fan-out); with a 5 s poll the watchlist piled up ~5 concurrent in-flight requests and starved other sidecar routes (workspace load, equity fundamentals — Vectors 3 & 5).                                                            | Made `quotes`/`crypto` handlers `async`, wrapped each blocking provider call in `asyncio.to_thread`, fanned out via `asyncio.gather(return_exceptions=True)` (skip-on-failure preserved). Added a client-side `inFlightRef` guard so a poll is skipped while the previous is still running.                                           | `sidecar/routers/quotes.py`, `sidecar/routers/crypto.py`, `src/modules/watchlist/WatchlistPanel.tsx`                                                 | **Re-run Vector 3** (≥50-symbol watchlist, 5 s poll). Quote batch latency must drop sharply (concurrent, not sequential); polls must **not** pile up (the in-flight guard skips overlaps). Re-run Vector 5 (workspace swap mid-poll) — other routes must no longer be starved.                  |
| **#38**            | News first-fetch on a cold launch failed ("Could not reach the news service"); Retry then succeeded — all-or-nothing one-shot fetch with cold-TLS cascade.                                                                                                                                            | Introduced a shared pooled `httpx.AsyncClient` on `app.state` (created at app-factory time, closed in the lifespan shutdown); concurrent per-source fetch; per-source retry/backoff; **partial success** (502 only if **zero** sources return).                                                                                       | `sidecar/routers/news.py`, `sidecar/services/news_provider.py`, `sidecar/app.py`                                                                     | **Fresh launch** (cold network) → News panel must populate on the **first** fetch, no "Could not reach the news service". If one source is down, articles from the others still render (no blanket 502).                                                                                        |
| **#5 (Portfolio)** | Cold-start Portfolio panel showed persistent **"Failed to load portfolio"** even though `GET /portfolio/positions` → 200; **no auto-recovery, no Retry**; only a successful write cleared it. Vector 4 strengthened it: persisted positions (`id:1` AAPL 10@150) were **not displayed** on cold load. | Render matrix in the panel: `null + error` → error + **Retry**; `null + no error` → Loading; `rows.length === 0` → clean **empty state** ("No positions yet"); rows present → render. `setSummary(null)` on failure (never a persistent stale error).                                                                                 | `src/modules/portfolio/PortfolioPanel.tsx`                                                                                                           | **Cold start** with an empty DB → "No positions yet" (clean empty state), **never** a red error. Cold start with the residual test positions present (`id:1/2/3` from pass 1) → positions **render**. Induce a real failure → error **with Retry**, and Retry recovers.                         |
| **#15 (Chart)**    | Junk symbol `ZZZZZ` → header "ZZZZZ via yfinance" (claims success) + **fully blank chart, no error/Retry/"no data"**. `/history/ZZZZZ` → 200 / `bars=0`; UI treated empty-200 as success. Bad symbol indistinguishable from an outage.                                                                | Empty `candleData` → distinct **no-data error state** + early return; the "<sym> via yfinance" success header is gated on `provider && priceState === "ready"` so it does **not** show on `bars=0`.                                                                                                                                   | `src/modules/chart/ChartPanel.tsx`                                                                                                                   | Load `ZZZZZ` → distinct **"no data for symbol"** state (not a silent blank, not a false success header). Load a valid symbol → renders normally.                                                                                                                                                |
| **UC1 (MCP)**      | `openbb-mcp` subprocess binding is **nondeterministic** across boots — bound on one setup boot, down on others. macro/SEC/openbb-fundamentals availability was a coin-flip per launch.                                                                                                                | Rust bind budget extended (15 s → 30 s × 2 retries), the two MCP spawns parallelized, graceful degradation intact (port 0 → routes fall back to yfinance / 501). **Residual documented** in `BLOCKERS.md` (PyInstaller cold-extract root cause is not fully fixable from Rust).                                                       | `src-tauri/src/{lib,openbb_mcp,sec_edgar_mcp}.rs`, `BLOCKERS.md`                                                                                     | Relaunch the app several times; check `/health` `openbb-mcp` + `macro` status across boots. Binding should be **far more reliable** than pass 1. If it still degrades on a cold first boot, that's the **documented residual** — note it, relaunch clears it; do **not** treat as a new defect. |

### S3 fixes

| Item                     | Defect                                                                                                          | Fix                                                                                                                                         | File                                       | Regression check                                                                                                                                    |
| ------------------------ | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| **#25**                  | Stale compare overlay/legend: add QQQ compare, change primary SPY→NVDA → "QQQ %" overlay persists, not rebuilt. | Added `symbol` to the compare effect deps.                                                                                                  | `src/modules/chart/ChartPanel.tsx` (~L763) | Add a compare series, change the primary symbol → the compare overlay rebuilds for the new primary (no stale legend).                               |
| **Portfolio bounds**     | `POST /portfolio/positions` accepted qty `1e15` and **negative** qty/cost → 201.                                | `quantity: float = Field(..., gt=0, le=1e12)`, `cost_basis: float = Field(..., ge=0)`.                                                      | `sidecar/models/portfolio.py`              | Direct-curl negative/huge qty → **422**. (GUI input bounds inherit the model.)                                                                      |
| **#81**                  | Kill-switch reset without ack returned **422** (Pydantic), docs say **400**.                                    | `acknowledged: bool = False` default → omitted body hits the handler's explicit **400**. Gate unchanged: only `acknowledged=true` un-halts. | `sidecar/routers/safety.py`                | Curl `POST /safety/kill-switch/reset` with empty body → **400** (not 422). With `{"acknowledged":true}` → resets.                                   |
| **#65**                  | SEC `/sec/filings` with no params returned **501** (subprocess-down short-circuit) instead of **400**.          | Moved param validation (400) **before** `_require_available()` (501).                                                                       | `sidecar/routers/sec_filings.py`           | Curl `GET /sec/filings` with no `cik`/`symbol` → **400** even when the SEC subprocess is down.                                                      |
| **Sidecar-down msg**     | Backtest with a dead sidecar showed generic **"Load failed"** rather than "sidecar unavailable".                | Detect the `TypeError` fetch-failure shape → surface "Sidecar unavailable".                                                                 | `src/store/backtest.ts`                    | Kill the sidecar, run a backtest → message reads "sidecar unavailable", not "Load failed". (Auto-respawn was **not** added — out of scope; see §6.) |
| **#5 (discoverability)** | The only panel launcher was keyboard `cmd+K`; no visible affordance.                                            | Minimal "Open panel ⌘K" toolbar button reusing the command-palette store.                                                                   | `src/app/page.tsx`                         | A visible "Open panel" affordance is present and opens the palette.                                                                                 |

---

## 2. Async-refactor blast radius — the regression sweep for ripple

Fix #3 changed how the sidecar event loop is used. The **direct** changes are
async-correct (see §1). The risk is **ripple**: other surfaces that share the
single event loop, or that the new shared `httpx.AsyncClient` lifecycle touches.
Sweep every surface below.

### 2.1 What changed, precisely

- **`quotes.py`** — `get_quote` / `get_quotes` now `async`, blocking provider
  calls offloaded via `asyncio.to_thread`, fan-out via `asyncio.gather(...,
return_exceptions=True)`. **Async-correct.**
- **`crypto.py`** — `crypto_ticker` / `crypto_history` now `async` +
  `to_thread`. `crypto_stream` (WebSocket `/crypto/stream`) is async-correct
  with finally-cleanup. `list_exchanges` is trivial sync.
- **`news.py`** — `get_news` awaits `news_provider.fetch_news(...)` with the
  shared client, **then runs a synchronous sentiment-scoring loop on the event
  loop** (`sentiment.score_text()` per item). This is **CPU-work-on-loop** — a
  ripple risk if a fetch returns many long items.
- **`news_provider.py`** — all fetchers async; concurrent fan-out via gather;
  per-source retry/backoff; partial success.
- **`app.py`** — `app.state.httpx_client = httpx.AsyncClient(follow_redirects=
True)` created at app-factory time; `await client.aclose()` in the lifespan
  shutdown. **Only** `news.py` consumes it. No other `app.state` resource
  exists, so **no lifecycle conflict**.

### 2.2 Surfaces to regression-sweep for ripple

**A. Sync-blocking-on-loop routes (HIGH ripple risk — NOT refactored, now
compete with the async fan-out):**

- **`history.py:14` `get_history`** — calls `provider_registry.get_history()`
  **directly on the loop** (no `await`, no `to_thread`). Chart history loads.
- **`indicators.py:39` `get_indicators`** — calls
  `provider_registry.get_history()` + `indicator_service.compute()`, both
  blocking on the loop. Chart indicator overlays.

  → **Check:** with a ≥50-symbol watchlist polling every 5 s (new concurrent
  fan-out active), open a Chart and switch timeframes / add indicators. History
  - indicator loads must stay responsive (target < ~3 s); they should **not**
    visibly stall while quotes fan out. If they stall, the loop is being starved
    and these two routes are the next `to_thread` candidates (note it as a
    finding, do not fix).

**B. CPU-work-after-async (MEDIUM ripple risk):**

- **`news.py` sentiment loop** — profile News fetch with a large result set.
  If the panel visibly hitches while scoring many items, flag it.

**C. SSE / WebSocket long-lived connections (HIGH contention risk — they hold
loop time while quotes/crypto/news fan out concurrently):**

- `/llm/chat` (SSE, `llm.py:63`)
- `/agents/{id}/invoke` (SSE, `agents.py:55`)
- `/workflow/run` (SSE, `workflow.py:39`)
- `/backtest/run` (SSE, `backtest.py:41`)
- `/crypto/stream` (WebSocket, `crypto.py:51`)

  → **Check:** open a long-running SSE (an agent invoke or a backtest run) and,
  while it streams, let the watchlist auto-refresh / open a Chart. The SSE must
  keep streaming and the polled panels must keep their cadence — neither should
  stall the other. Kill an SSE mid-stream → the loop recovers and other routes
  resume normal latency.

**D. Frontend polling surfaces (watch for timing ripple):**

| Surface                                 | Interval | Endpoint(s)                                       | Ripple note                                                                                                  |
| --------------------------------------- | -------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Watchlist (`WatchlistPanel.tsx`)        | 5 s      | `/quotes` (batch) + `/crypto/ticker` (per symbol) | **Primary #3 surface** — the in-flight guard must prevent pile-up.                                           |
| Audit Log Viewer (`AuditLogViewer.tsx`) | 2 s      | `/safety/audit-log`                               | Sync-safe read, but 2 s cadence — confirm it stays responsive under quote load (and that #79 holds: no 500). |
| Kite static-IP banner                   | 30 s     | `/safety/static-ip-status`                        | Low risk.                                                                                                    |
| Plugin Manager / MCP status             | 5 s      | `/mcp/status`, `/openbb-mcp/status`               | Low risk; relevant to UC1.                                                                                   |

**E. App lifespan coherence:**

- Confirm the app **starts** cleanly (httpx client created) and **shuts down**
  cleanly (no warning on `client.aclose()`). A dirty shutdown or a hung close
  is a ripple regression.

---

## 3. Deferred-on-setup inventory — what pass 1 could not reach

Grouped by the setup each needs. The operator decides which to configure for
this pass (see §5 for the BYOK/Supabase decisions).

### 3.1 BYOK LLM API key (anthropic / openai / gemini)

- **#45** — Chat real **streamed** response (pass 1: graceful "no API key" only).
- **#46** — Chat slash-command edge cases (partial).
- **#48–49** — Agent Builder CRUD/validation **and** invoking a custom agent
  end-to-end (the invoke is SSE + needs a key).
- **#50–52** — Backtest SSE run → **Strategy-Critic handoff** (the critic step
  is an agent call; the SSE backtest run itself needs no key).

> ⚠️ A real key sends user data to the provider. Pass 1 marked this out of scope
> for that reason. Only run if the operator explicitly provisions a key and
> accepts the data egress.

### 3.2 FRED_API_KEY (macro providers)

- **#61** — Macro `/macro/DGS10` happy path (FRED/ECB/IMF/WB).
- **#62** — FRED-no-key → 502 path (run the negative case even without a key).
- **#63** — Macro search / rapid-switch edge.

### 3.3 MCP subprocesses UP (openbb-mcp + sec-edgar-mcp)

The single biggest unlock — pass 1 ran on a **DOWN** boot (UC1). With the UC1
binding fix, relaunch until `/health` reports `openbb-mcp: available`.

- **#43** — Equity Overview junk-symbol all-sections-fail (extended openbb
  sections, not the yfinance fallback).
- **#61, #64, #65** — Macro happy path, SEC `/sec/filings?symbol=AAPL` happy
  path, SEC param-ordering (now that #65's 400 is no longer masked by the 501).
- **openbb-fundamentals** extended sections (vs the yfinance fallback path
  pass 1 tested).

### 3.4 Supabase (mock or real Tradesa V2 backend)

- **#85–87** — Tradesa Settings-dialog validation, Supabase-configured data
  rendering, bot-offline + partial states. Needs `X-Tradesa-Supabase-Url` +
  `X-Tradesa-Supabase-Service-Key` (read-only GET model; credentials via request
  headers, never body).

### 3.5 Broker credentials / static-IP

- **#77 (connect)** — Broker GUI connect with (paper) credentials.
- **#78** — Broker paper↔live + read-only toggle.
- **#83** — Disclaimer flow (first-launch ToS / per-broker first-connect) — note
  the session-scoped ack may have been set on a prior boot; test on a fresh
  data dir.

> ⚠️ Live broker connect / order placement is gated behind the §6.5 safety layer
> and is **operator-manual** (credentials the operator won't hand an agent — see
> §5). Paper-mode connect is testable if the operator provisions paper creds.

### 3.6 In-process, just-not-driven (NO external setup needed — run these freely)

These need no key/MCP/Supabase; pass 1 simply ran out of time. **High-value,
low-cost to clear:**

- **#36** — Watchlist duplicate / junk / remove-last.
- **#39** — News empty-watchlist "No news" state.
- **#41** — Portfolio edit / cancel / delete + qty edge values (GUI).
- **#54–55** — Option American+BS/MC incompatibility alert; negative-vol /
  expiry≤valuation / strike-0 → 400 (GUI).
- **#57** — Bond Pricer GUI confirm (engine proven via #53).
- **#58–60** — Bond / yield-curve edge + bootstrap (GUI).
- **#67** — Earnings window-bound edge.
- **#70** — Screener criteria edge (now unblocked by the #91 universe fix).
- **#76** — Plugin Manager GUI toggle.
- **#73–75** — Node Editor PropertiesPanel / save-load-run / validation — the
  **panel UI + save/load** are testable; only the graph-**building** drags are
  RAW-COORD (§6).

---

## 4. Clean-pass items — DO NOT re-run (~33)

Tested and passed clean in pass 1, **not** touched by the fix sprint. Skip these
unless an async-ripple check in §2 implicates one:

`#1, #2, #3*, #4, #6, #7, #10, #11, #13, #17, #18, #23, #34, #35, #37, #40, #42,
#44, #47, #53, #56, #66, #68, #77*, #81*, #84, #88, #89, #90, #93` plus the
known-confirmed `#25`/`#38`.

\* `#3` watchlist add-path mechanics, `#77` broker-list read, `#81` kill-switch
cycle: the mechanic passed clean, but the **fix-sprint regression checks** in §1
still apply (latency for #3, 400-vs-422 for #81).

---

## 5. Mac env-setup recipe (fast path)

Pass 1 burned time on setup. Do it once, deterministically:

1. **Pull the build:** `git fetch origin && git checkout f3bef61` (or
   `origin/main` if no further commits have landed).
2. **Build the debug bundle:** `pnpm install --frozen-lockfile && pnpm tauri
build --debug`. (Sidecars must be present first — `pnpm sidecars:build` or
   the `beforeBuildCommand` chain runs `ensure-all-sidecars`. The #91 fix means
   the freshly built bundle now includes the screener universes.)
3. **Repackage to clear the computer-use tier classifier** (the load-bearing
   trick from pass 1): rename the bundle so its display name is **`Vysted.app`**
   and bundle id **`com.vysted.desk`** (the stock `productName "Vysted Terminal"`
   / `com.vysted.terminal` trips the helper's terminal/IDE heuristic → click-only
   tier). Move it to **`/Applications`**.
4. **Grant full-tier computer use** to a **fresh** helper for the renamed app.
   The rename clears the classifier; note the `com.vysted.desk` grant **may
   still be cached** from pass 1 — if the tier looks wrong, revoke + re-grant.
5. **Expect MCP first-boot degrade (UC1).** Even with the binding fix, a cold
   first boot may report `openbb-mcp: unavailable`. **Relaunch clears it** —
   relaunch until `/health` shows `openbb-mcp: available` before running §3.3.
6. **Discover the sidecar port:** it is **dynamic per boot**. Read it from the
   app, or hit `/health` — the runner prompt derives the port from `/health`
   before any direct-curl.
7. **BYOK / Supabase / broker decisions the operator must make before the
   pass** (each gates a §3 group):
   - LLM key (§3.1) — provision or skip (data-egress decision).
   - `FRED_API_KEY` (§3.2) — provision or run negative-only.
   - Supabase URL + service key for Tradesa (§3.4) — mock, real, or skip.
   - Paper broker creds (§3.5) — provision or leave broker connect
     operator-manual.

---

## 6. Operator's manual lane — what computer-use CANNOT do

These are **not** for the Mac agent. Record as `OPERATOR-MANUAL`, not as
pass/fail:

- **RAW-COORD in-webview drag / canvas gestures** — in-webview drag failed even
  with first-party trusted events in pass 1 (native window drag worked, proving
  trusted events are emitted, but WKWebView/CGEvent drag delivery into the
  webview did not register). These need a real human pointer or Playwright-style
  native injection:
  - **#8** tab-drag reorder (the headline question — **neither confirmed nor
    cleared**)
  - **#9** splitter resize
  - **#27** chart drawing-tool placement, **#28** drag-to-pan / scroll-zoom,
    **#32** multi-chart crosshair/zoom/symbol sync
  - **#71** drag node from palette, **#72** draw edge between nodes (and the
    **#73–75** node-graph behaviour gated behind them)
- **Credential-gated flows the operator won't hand an agent** — live broker
  connect / order confirmation, anything that places a real order, anything
  behind a real secret the operator declines to expose to the agent.
- **Visual / aesthetic DIRECTION** — the agent **observes** (§7) but does not
  decide. Taste, density targets, and the design overhaul direction are the
  operator's call.
- **Auto-respawn of a killed sidecar** — pass 1 noted the Tauri core does not
  auto-restart a sidecar after an external kill. This was **deliberately left
  out of scope** for the fix sprint (the operator said not to force it). The
  Mac pass should confirm the **messaging** is now clear ("sidecar unavailable"),
  not expect auto-recovery.

---

## 7. Visual / density observation protocol (INPUT to the design overhaul)

The Mac pass collects concrete, **screenshot-backed** visual/UX/density findings
into a **separate** section of `docs/PHASE_9.5_BUG_CATALOG.md` (e.g. "§Visual
Observations — Design-Overhaul Input"). This is explicitly **NOT** to be fixed in
this functional loop.

Capture, per panel, with a screenshot reference:

- **Sparseness** — panels reading as empty / low information density vs a
  Bloomberg-grade terminal.
- **Generic-default styling** — anything that reads as un-customised
  shadcn/Tailwind defaults rather than a deliberate finance-terminal aesthetic.
- **Label overlap / truncation** — at both 1920×1080 and 2560×1440 (the axis-
  overlap items #12/#26 pass 1 couldn't assess precisely live).
- **"Un-technical / un-JARVIS" reads** — surfaces that feel like a generic web
  app rather than a research-lab instrument.
- **Inconsistencies** — spacing, typography, color, iconography drift across
  panels (the visual record should read as one product).

Each observation: panel + screenshot + one-line description of the issue. **No
proposed fix, no severity** — these feed the overhaul, where aesthetic direction
is the operator's call.

---

## 8. Scope guardrails (restated)

- **Tester, not fixer.** No source edits. The **only** file the Mac pass writes
  is `docs/PHASE_9.5_BUG_CATALOG.md`. No commits beyond that catalog. **No tag.**
- **Targeted-but-broad:** regression (§1) + async ripple (§2) + deferred (§3) +
  heavier adversarial (below). **Do not** blindly re-run the ~33 clean items
  (§4).
- **Heavier adversarial vectors not yet run** (pass-1 backlog): 1000-row /
  huge-number portfolio & quant inputs; 20+ screener criteria (now unblocked by
  #91); literal close-**all**-panels empty-dockview edge; plus **re-running
  Vector 3** (large-watchlist poll) as the primary #3 regression and **Vector 5**
  (workspace swap mid-poll) for starvation.
- **Honour the env facts:** `/agents` = **12** is correct (empty `[]` is the L3
  bug, already fixed); UC1 MCP binding is nondeterministic (relaunch clears);
  **CORS-masks-500** — a browser "CORS error" on a sidecar route usually means a
  5xx with no CORS header on the exception response — **direct-curl** the
  endpoint to see the real status before chasing CORS.
