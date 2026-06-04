# Vysted rebuild — verified handoff (Part 3)

**Branch:** `003-vysted-rebuild` · **Date:** 2026-06-04 · **Verifier:** Opus 4.8 lead
**Method:** drove the **live running app** (dev build on `localhost:3000`, tauri-mcp
`evaluate_script` + `get_logs`) + **direct sidecar calls** (`127.0.0.1:49615`, loopback)
+ source root-cause. Screenshot evidence: `docs/redesign/verification/live-shell-2560.png`.

> **Ground truth about the running instance — read first.** The webview reflects the
> **latest frontend** (Next dev HMR is live — my today's `New Research Space` command is
> present in ⌘K, proving it). But the **sidecar is a STALE binary**: a screener run
> evaluated **only 100 symbols** (the old bundled `sp500.json`), so the committed full-500
> universe + batching + OR-grammar are **green in unit tests but NOT running live here**.
> A `tauri dev` / sidecar rebuild is required to exercise those server-side.
> The two concurrently-running app instances (dev debug + a release bundle, PID 13766)
> also make native-window capture ambiguous — see "Could not verify".

This document is deliberately blunt. A real bug flagged here is worth more than a clean
report. Three sections: **genuinely working** (with evidence), **still broken / half-built**
(every reproducible issue), **could not verify** (flagged, never reported as done).

---

## ✅ GENUINELY WORKING — verified with evidence

### 1. Proposal / permission bar — the longest-living bug — ROOT-CAUSED, correct
**Verdict: working. No phantom.** Empirically: opening a panel as a user (clicked
**Open News Feed** in ⌘K) produced **no** proposal bar and **no** Accept/Reject gate — the
panel opened directly. Root cause confirmed in code:
- The **only** function that stages a proposal is `enqueueChange` (`src/store/proposed-changes.ts`).
  It is called from exactly two places: the agent stream's `onToolUse`
  (`src/modules/chat/ChatSidebar.tsx:694`, gated on `isHostActionMutation`) and
  `enqueueSlashChange` (an explicit user `/command`). A plain user panel-open goes through
  `useWorkspaceStore.openPanel` **directly** — it never touches the proposal pipeline.
- **AUTO vs ASK never phantom:** on enqueue, `proposed-changes.ts:79` immediately
  `accept()`s non-order changes when autonomy is `auto` → they leave the pending set, so the
  review bar renders nothing. ASK leaves them pending for review. The status-line code
  (`ChatSidebar.tsx:387-392`) explicitly avoids the lingering "review below" phantom line.
- **§6.5 floor intact:** orders are excluded from auto-apply (`proposed-changes.ts:79`) **and**
  `accept()` routes every order through `routeOrderProposal` → the confirm-before-place dialog
  regardless of mode. The AI never reaches `confirm_and_place`.
- *Not exercised live:* the agent→bar→resolve round-trip (needs an LLM run — see §research).
  The logic is conclusive and the user path is empirically clean.

### 2. Enter-to-send — fixed
`ChatSidebar.tsx:1316-1344`: when no picker is open the composer submits **explicitly** on
`Enter && !event.shiftKey` (with a comment naming "the enter-to-send bug" — it no longer
relies on the unreliable controlled-input form default). Shift+Enter is reserved for newline.

### 3. `/` slash commands — discoverable, NOT clipped
Live: typing `/` in the composer opened the picker showing `/research`, `/deep`,
`/deep heavy` **with full descriptions**; the token set `/research /screen /export /deep
/compare /chart` all present and fully rendered (no clipping).

### 4. ⌘K command palette — opens, rich, searchable
Live: 90 entries (panels + commands), proper search input *"Search commands, panels,
symbols, agents…"*, each row with title + description + shortcut + category badge.
**My today's `New Research Space` command is present** (proves HMR is serving latest code).
*Caveat:* close-on-select couldn't be confirmed via the rig (untrusted events don't drive
Radix's dismiss) — see "Could not verify".

### 5. Chart series / "empty series 502" — NOT reproduced; data healthy
`GET /history/SPY?timeframe=1d&range=6mo` → HTTP 200, **124 OHLCV bars**, fresh, full
OHLCV + provenance. `GET /quotes/SPY` → price 754.24, provider yfinance, HTTP 200. The 502
was intermittent and is **not present now** — flag for monitoring, not reproducible here.

### 6. Deep-research engine / Tongyi "fallback" — working as designed, honestly labelled
`GET /system/deepresearch/probe`:
- **No key:** `tongyi.configured:false, live:false, usingFallback:false` → note "Add an
  OpenRouter key (BYOK) to route deep research through Tongyi." It does **not** falsely claim
  Tongyi is live.
- **With a key:** `configured:true, live:false, usingFallback:true,
  resolvedModel:"minimax/minimax-m3"` → note "Tongyi unavailable on OpenRouter right now —
  using minimax/minimax-m3." This is the **intended honest fallback** (the Tongyi slug is
  listed-but-unrouted on OpenRouter). The "fallback" the operator saw is correct behaviour.
- ⚠️ **Doc drift:** `CLAUDE.md` says the fallback is "honest Qwen-A3B" — the live fallback
  target is now **minimax/minimax-m3**. Update that line.

### 7. Visual identity / composer / autonomy controls — live
Screenshot (`verification/live-shell-2560.png`): minimal-dark indigo chrome, mark-only brand
(no wordmark), the agent composer with empty-state guidance, **Deep research** toggle,
**ASK/AUTO** autonomy pill, model chip (`deepseek-v4-flash`), send affordance.

---

## ❌ STILL BROKEN / HALF-BUILT — every reproducible issue

### A. Screener sparseness — MAJOR, live, root-caused
The primary fundamentals provider `openbb-mcp` returns **null** for the
profitability/health/growth fields:
- `GET /fundamentals/AAPL` (provider `openbb-mcp`): `pe_ratio` ✓ but `roe=None`,
  `profit_margin=None`, `debt_to_equity=None`, `revenue_growth=None`.
- `GET /fundamentals/RELIANCE` (provider `openbb-mcp`): **all null** (empty card).
- `GET /fundamentals/ROUTE` (provider **`yfinance`** — openbb had no data so it fell back):
  **full fields** — `roe=0.097, profit_margin=0.054, debt_to_equity=0.015,
  revenue_growth=-0.038, pe=13.88`.

**Consequence (reproduced):** a screen of `roe > 0.15` over the universe returns **0
results** (the field is null for every openbb-served symbol). `pe<25 AND roe>0.15` → 0. So
**5 of 8 presets** (quality, value, garp, dividend, margins) come back **empty**.

**Root cause:** the openbb-mcp → yfinance fallback only fires when openbb-mcp **throws**.
When openbb returns the symbol with the screener-grade fields *null* (AAPL) or an essentially
empty 200 (RELIANCE), it's treated as success and the richer yfinance path never runs. The
fix is a provider-registry change: fall back (or merge) when the openbb result is missing the
screener-grade fields, not only on exception. *(Out of scope to fix now — flagged per "stop
after the handoff".)*

### B. `dividend_yield` unit bug — live
`GET /fundamentals/AAPL` → `dividend_yield = 0.35` from openbb-mcp. The field is a **fraction**
(0.0035 would be ~0.35%); 0.35 implies a **35%** yield — ~100× too high. openbb-mcp appears to
emit a percent into a fraction-typed field. Any "dividend > 3%" screen / the overview yield
cell will be wrong for openbb-served symbols.

### C. Stale sidecar binary — blocks live verification of my Part-1 server work
The running sidecar evaluated **100** symbols (old bundled `sp500.json`), not the committed
**506**. So full-500 universe + the `_cached_pair` batching layer + OR-grammar `group` are
**unit-test-green but not live**. Rebuild the sidecar (`pnpm sidecars:build` / restart
`tauri dev`) to exercise them in the running app.

### D. Equity-Overview statements — duplicate-key risk (likely the "6 Next.js errors")
The statements **data** endpoint is healthy (`GET /fundamentals/AAPL/income` → HTTP 200, 5
periods, 39 lines). The `StatementTable` (`src/modules/equity-overview/EquityOverviewPanel.tsx:208`)
keys rows by **`key={line.label}`**. Financial statements routinely repeat line labels (e.g.
multiple "Other"/"Total" rows) → React **duplicate-key errors** (plausibly the 6 reported) +
possible row mis-association. **Low severity** (console errors / mis-render), **not a hard
crash** — I could not force a hard crash. Fix: key by `index` or `label + index`. *(A hard
crash, if it still occurs on a specific symbol, needs Playwright trusted events to repro — see
"Could not verify".)*

### E. News panel renders empty despite data
`GET /news?limit=5` → HTTP 200, **5 items** (real headlines). But the live News panel showed
an empty "NEWS FEED" on open (screenshot). Likely needs an explicit Refresh or a symbol
context — it didn't auto-populate from the available global feed on open.

---

## ⚠️ COULD NOT VERIFY — needs Lokavya's manual check or the next-session stack
*(Reported honestly as unverified — NOT as working.)*

1. **Research "Route Mobile" → brief with real DATA + real SOURCES (#5).** Could not run a
   live research pass this session: the default model is `deepseek-v4-flash` (OpenRouter,
   needs a BYOK key) and no key is wired to the foreground request. The prior "0 sources /
   structured only" symptom — whether the web-search floor fires and cites sources — **needs a
   manual run with a key**, or a fresh session with the research model configured. **Flagged,
   not done.**
2. **Screener row → cockpit drill, populated (#6).** Frontend wiring (`row click →
   loadSymbolIntoChart`) is covered by tests + code, but a live drill would show sparse/empty
   rows because the backend is stale (100 symbols) + sparse fundamentals (§A). Re-verify after
   a sidecar rebuild + the §A fix.
3. **Equity Overview, fully populated, live (#7).** Could not load a symbol into the panel via
   the rig — dockview only mounts the active panel's content and untrusted synthetic events
   don't reliably activate a tab or drive the autocomplete-submit. (And US large-caps are
   sparse via openbb-mcp anyway — §A.) Needs Playwright trusted events or a manual check.
4. **Quarterly-statements HARD crash (#9).** Could not force a hard crash (data is healthy; the
   table code is null-guarded). If a hard crash still reproduces on a specific symbol, it needs
   Playwright trusted events to drive the overview symbol-submit + statement render. The
   duplicate-key issue (§D) is the concrete code-level finding.
5. **Date-change error (#10).** Could not drive the chart's date/timeframe picker via the rig
   (untrusted events + canvas-interactive). Needs Playwright trusted events or a manual check.
6. **New macOS menu-bar modes (#12).** Native Computer Use was **not surfaced this session**
   (MCP/native tools load at session start; it was confirmed available — CLI v2.1.162 ≥ the
   2.1.85 threshold — but added/approved mid-session). The `install_layout_menu` modes need a
   **fresh session with Computer Use**, or a manual menu-bar check.
7. **⌘K palette close-on-select.** The palette stayed open after a selection via the rig, but
   that is the untrusted-event limitation (Radix dismiss needs trusted events), not a
   confirmed bug. Needs Playwright to confirm.

---

## Verification toolchain (committed)
- **Playwright MCP** (`@playwright/mcp`) — in the committed `.mcp.json`, project-scoped
  (⏸ pending the one-time operator approval). Covers the Tier-1 gaps above (trusted events).
- **Tiering + load-timing caveat:** `docs/redesign/VERIFICATION_STACK.md`.
- **To re-verify everything live:** approve the project MCP servers, **rebuild the sidecar**,
  start a **fresh** `claude` session (so Playwright + Computer Use tools surface), then drive
  the items in "Could not verify".

## Suggested fix priority (next session — NOT started, per the stop instruction)
1. **§A provider fallback** (openbb→yfinance on null screener-grade fields) — unblocks the
   screener + overview + 5 presets. Highest leverage.
2. **§B dividend_yield unit** normalisation at the openbb-mcp boundary.
3. **§D** `StatementTable` key fix (`label + index`).
4. Rebuild the sidecar so §C (full-500 + batching + OR-grammar) goes live.
5. **§E** News panel auto-populate on open.
