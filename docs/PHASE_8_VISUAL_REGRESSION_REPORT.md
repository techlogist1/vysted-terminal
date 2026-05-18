# Phase 8 — Visual Regression Report (T1-visual)

**Date:** 2026-05-18
**Baseline convention:** CLAUDE.md "Visual consistency convention (v0.7.0+)"
**Auditor:** Phase 8 Sonnet 4.6 teammate (t1-visual)
**Scope:** `docs/screenshots/v0.7.0/` canonical-convention audit + Tradesa V2 6-state capture procedure + cross-version consistency spot-check
**Branch:** `worktree-agent-a9943acf46eb61cd6`

## Severity scheme

- **S1** — Blocks a release; convention-compliant re-capture required before tagging.
- **S2** — Convention gap that carries non-trivial regression risk; fix before the next operator-led session.
- **S3** — Convention drift, cosmetic / informational; fix at next re-capture pass.
- **S4** — Note / observation; no action required.

---

## Part A — v0.7.0 canonical-convention compliance

Files audited (5 total):

| File | Description |
|------|-------------|
| `composed/cockpit-1920x1080.png` | First page-load cockpit, no AAPL loaded |
| `composed/cockpit-2560x1440.png` | First page-load cockpit 2560px |
| `composed/cockpit-aapl-1920x1080.png` | Hero shot — AAPL loaded in Equity Overview |
| `composed/cockpit-aapl-2560x1440.png` | Hero shot — AAPL 2560px |
| `cockpit/chart-tab-1920x1080.png` | Zoomed Chart tab with Equity Overview tab visible |

Convention axes checked:
1. Ticker: AAPL primary anchor; watchlist `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT`
2. Theme: dark only
3. Workspace: 5-panel + AI Assistant cockpit; Phase 6/6.5 panels as tabs in slots
4. Populated semantics: real data per protocol; no empty defaults
5. Resolutions: 1920×1080 AND 2560×1440 both present
6. Header: `Vysted Terminal — vX.Y.Z — <Surface>` titlebar always visible
7. Per-release subfolder: `v0.7.0/{composed,cockpit}/` — no overwrites

---

### Findings

---

### Finding T1-workspace-solo-chart: Chart tab is a solo-surface-only shot, missing cockpit context [S3] [status: open]

**Repro:** Open `docs/screenshots/v0.7.0/cockpit/chart-tab-1920x1080.png`. The shot shows the Equity Overview tab label beside Chart — the panel occupies the left column — but no right-column panels (Watchlist, News, Portfolio, AI Assistant) are visible because the capture was a zoomed window view, not the full cockpit.

**Impact:** Axis 3 (Workspace) — solo-panel shots are permitted only as secondary zoomed shots, never as the _primary_ cockpit shot. The convention requires the 5-panel + AI Assistant cockpit shape for every primary capture. The `cockpit/` subfolder currently only contains this one file; there is no full-cockpit Chart capture at 1920×1080 with all 5 panels visible.

**Suggested fix:** Re-capture the Chart tab as a zoomed _secondary_ shot (acceptable as-is per convention), but add a primary full-cockpit capture at 1920×1080 with the Chart slot populated + all other panels visible. Place in `cockpit/cockpit-chart-populated-1920x1080.png`. Note: a 2560×1440 partner is also missing for this subfolder per Axis 5 (both resolutions required for every capture pair).

**Files:** `docs/screenshots/v0.7.0/cockpit/chart-tab-1920x1080.png`
**Re-captured at:** n/a — needs Tauri shell (operator-led)

---

### Finding T1-chart-tab-missing-2560: No 2560×1440 partner for the Chart tab shot [S3] [status: open]

**Repro:** `docs/screenshots/v0.7.0/cockpit/` contains only `chart-tab-1920x1080.png`. There is no `chart-tab-2560x1440.png`.

**Impact:** Axis 5 (Resolutions) — both resolutions are required for every per-surface capture. The v0.2.1 equity overflow bug was invisible at 1920×1080 and only visible at 2560×1440; the dual-resolution requirement exists precisely to catch table/layout overflow that only appears at wider viewports.

**Suggested fix:** Capture `cockpit/chart-tab-2560x1440.png` at the same cockpit state (SPY 1d inside the cockpit slot). Add alongside the existing 1920 shot.

**Files:** `docs/screenshots/v0.7.0/cockpit/chart-tab-1920x1080.png` (partner absent)
**Re-captured at:** n/a — needs Tauri shell (operator-led)

---

### Finding T1-header-absent: None of the 5 v0.7.0 captures show a `Vysted Terminal — vX.Y.Z — <Surface>` OS titlebar [S2] [status: open]

**Repro:** Inspect all 5 v0.7.0 captures. Every screenshot shows the dockview panel layout against a dark background. No OS window frame / titlebar with `Vysted Terminal — v0.7.0 — ...` is visible in any capture. The top of each image begins with the tab row (Chart | Equity Overview, or Watchlist, etc.) — the Tauri window chrome is cropped out.

**Impact:** Axis 6 (Header) — the convention explicitly requires the `Vysted Terminal — vX.Y.Z — <Surface>` titlebar always visible. The v0.7.0 README acknowledges this convention but the captures do not reflect it. The v0.6.0 panels showed it (confirmed in v0.7.0 README "v0.6.0 panels showed it; v0.4.0 chat shots didn't — inconsistency closed in v0.7.0"), yet the v0.7.0 captures themselves are missing it. This is S2 (not S1) because the v0.7.0 captures are the _first_ convention-compliant round and the operator README acknowledges the deferred items; re-capture is already planned for Phase 9.

**Suggested fix:** All 5 captures require re-capture with the OS window frame visible (chrome-devtools `resize_page` approach must avoid cropping the titlebar). Alternatively, if the Tauri window in the web-mode capture doesn't have a titlebar, a v0.7.x re-tag shot adding a visible version label overlay satisfies the spirit of the convention.

**Files:** All 5 v0.7.0 screenshots
**Re-captured at:** n/a — needs Tauri shell (operator-led); deferred to Phase 9 per v0.7.0 README

---

### Finding T1-cockpit-non-hero-incomplete: The pre-AAPL cockpit pair violates "populated semantics" for Equity Overview [S3] [status: open]

**Repro:** Open `docs/screenshots/v0.7.0/composed/cockpit-1920x1080.png` and `cockpit-2560x1440.png`. The Equity Overview left panel shows a blank prompt ("Enter a symbol to load fundamentals, statements, and analyst ratings."). No AAPL ticker is loaded.

**Impact:** Axis 4 (Populated semantics) — the Visual verification protocol requires Equity Overview to show AAPL with all sections populated. The non-hero pair shows an empty default state. Per the convention, empty-state shots "hide bugs that only manifest with real data."

**Context:** The v0.7.0 README explicitly labels these as the "first page load" capture (pre-AAPL); the `cockpit-aapl-*` pair is the hero shot. The non-hero pair was intentional documentation of the initial-load state, not a replacement for the hero shot. Severity is S3 (not S1/S2) because the hero shots (`cockpit-aapl-*`) exist and correctly show AAPL loaded.

**Suggested fix:** Either (a) remove or relocate the non-hero pair to a `v0.7.0/cockpit-initial/` subfolder to keep the `composed/` folder visually unambiguous, or (b) add a README note clarifying these are initial-state captures, not the populated-state canonical shots. The hero pair remains the canonical reference.

**Files:** `docs/screenshots/v0.7.0/composed/cockpit-1920x1080.png`, `docs/screenshots/v0.7.0/composed/cockpit-2560x1440.png`
**Re-captured at:** n/a — no re-capture needed; organizational fix only

---

### Finding T1-equity-overview-unavailable: Several Equity Overview sub-sections show "Unavailable" in hero shots [S3] [status: open]

**Repro:** Open `docs/screenshots/v0.7.0/composed/cockpit-aapl-1920x1080.png`. The Equity Overview panel shows AAPL with price header but sub-sections Valuation Ratings, Analyst Ratings, Income Statement, Balance Sheet, Cash Flow all render "Unavailable" (yfinance intermittency at capture time).

**Impact:** Axis 4 (Populated semantics) — the Visual verification protocol requires Equity Overview to show "AAPL with all sections populated." The current hero shot has AAPL loaded (price header correct) but the section bodies are all blank. The v0.7.0 README acknowledges this: "Some Equity Overview sub-sections render 'Unavailable' because yfinance fundamentals were intermittent at capture time."

**Suggested fix:** Re-capture the hero shots when yfinance is stable (the v0.7.0 README notes this as "a zero-risk polish task"). The v0.3.0 composed shot demonstrates what full Equity Overview population looks like — AAPL with 32 analyst rating changes, income statement rows, P&L rows, balance sheet, cash flow all rendered.

**Files:** `docs/screenshots/v0.7.0/composed/cockpit-aapl-1920x1080.png`, `docs/screenshots/v0.7.0/composed/cockpit-aapl-2560x1440.png`
**Re-captured at:** n/a — needs stable yfinance session + Tauri shell (operator-led)

---

### Finding T1-watchlist-order: Watchlist order differs from canonical convention [S3] [status: open]

**Repro:** Open any v0.7.0 hero shot. The Watchlist panel shows `SPY, QQQ, BTC/USDT, ETH/USDT, NVDA, AAPL` — AAPL is at position 6 (last row visible). The v0.7.0 README acknowledges: "AAPL present; re-ordering the default to put AAPL first is a v0.8 polish task documented in BLOCKERS.md." The canonical convention requires `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT` with AAPL as the primary visual anchor.

**Impact:** Axis 1 (Ticker) — AAPL should be the primary equity anchor appearing first/prominently in every equity-bearing surface. With AAPL at position 6, it does not read as the primary anchor; NVDA at -5.27% draws more visual attention. MSFT is also absent from the watchlist entirely.

**Suggested fix:** Fix the default watchlist order in `src/modules/watchlist/` (BLOCKERS.md v0.8 #2). Then re-capture the cockpit shots. The new order should be `AAPL, MSFT, NVDA, SPY, QQQ, BTC/USDT, ETH/USDT` exactly.

**Files:** All 5 v0.7.0 screenshots (watchlist visible in 4 of 5)
**Re-captured at:** n/a — watchlist reorder is v0.8 code task first

---

### Part A Summary

5 files audited. 5 findings:

| ID | Title | Severity | Status |
|----|-------|----------|--------|
| T1-workspace-solo-chart | Chart tab is solo-surface only, no full-cockpit partner | S3 | open |
| T1-chart-tab-missing-2560 | No 2560×1440 partner for chart-tab shot | S3 | open |
| T1-header-absent | No OS titlebar visible in any capture | S2 | open |
| T1-cockpit-non-hero-incomplete | Pre-AAPL cockpit pair shows empty Equity Overview | S3 | open |
| T1-equity-overview-unavailable | Hero shots have "Unavailable" in all Equity Overview sections | S3 | open |
| T1-watchlist-order | Watchlist order is SPY-first, not AAPL-first | S3 | open |

Theme: AAPL (SPY, QQQ, BTC/USDT, ETH/USDT, NVDA, AAPL watchlist order) and Workspace axes are clean. Dark theme is correct across all shots. Both resolutions exist for the `composed/` pair. No S1 blockers — no re-capture is required before the current release cycle. The S2 header finding is acknowledged in the v0.7.0 README and is already planned for Phase 9.

---

## Part B — Tradesa V2 6-state capture procedure

### Background

The Tradesa V2 wrapper has 6 documented `TradesaConnectionStatus` values (from `types/tradesa_v2.ts`):

| Status | Meaning |
|--------|---------|
| `healthy` | Supabase reachable, fresh heartbeat (<5 min old) |
| `connecting` | Initial probe or post-restart catch-up in flight |
| `unauthenticated` | No credentials in keychain |
| `bot-offline` | Supabase reachable but heartbeat stale (>5 min) |
| `supabase-error` | Supabase REST/Realtime calls failing |
| `partial` | Some endpoints reachable, others not |

The lead captured `supabase-error` from the F7 Chrome fallback (the `invoke` undefined crash in the Tauri-less web mode) at `docs/screenshots/v0.8-pending/phase-8/uc1/tradesa-v2-positions-supabase-error-1920x1080.png`. That capture shows the `_PanelShell` `SupabaseErrorBody` ("Supabase unreachable" heading + "Cannot read properties of undefined (reading 'invoke')" detail + Retry button) correctly rendered with a red dot in `TradesaBotStatusStrip`.

The remaining 5 states need to be captured via mocked-fetch interception in a running Tauri dev session.

### Central state-routing file

All 6 states are rendered by `plugins/tradesa-v2/components/_PanelShell.tsx`. This is the single file to reference for visual signatures — individual panel files (`PositionsPanel.tsx`, `HealthPanel.tsx`, etc.) all use `<PanelShell title="...">` as their outer wrapper and inherit all state UX from it.

The status strip at the top of every panel is `plugins/tradesa-v2/components/TradesaBotStatusStrip.tsx`.

### Mocked-fetch approach

The capture procedure uses the `?sidecar-port=NNNNN` URL fallback added in v0.7.0 F7 (`src/lib/sidecar-client.ts`). With `pnpm tauri dev` running:

1. Open `http://localhost:3000/?sidecar-port=<port>` in a chrome-devtools MCP-attached browser tab.
2. Use `evaluate_script` to intercept `window.fetch` with a custom mock that returns a pre-canned JSON response for `/tradesa-v2/status`.
3. The store's `refreshConnection()` calls `probeStatus()` → `tradesaGet("/tradesa-v2/status")` → `fetch(url, { headers })`. The mock intercepts at the fetch level and returns the desired status JSON.
4. Trigger a refresh (click the reload button in `TradesaBotStatusStrip`) to force a status probe.
5. Capture via `take_screenshot` + `resize_page` at 1920×1080 and 2560×1440.

The fetch-mock script pattern (for `evaluate_script`):

```js
// Install at top of evaluate_script before navigating to the panel
const origFetch = window.fetch;
window.fetch = async (url, opts) => {
  if (String(url).includes('/tradesa-v2/status')) {
    return new Response(JSON.stringify(<STATUS_PAYLOAD>), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  return origFetch(url, opts);
};
```

The `<STATUS_PAYLOAD>` for each state is given in the per-state map below.

### Per-state map

---

#### State 1: `connecting`

**Mock response:** None needed. The `connecting` state is the _initial_ store state before any probe completes. The store initializes with `connection: null`; `_PanelShell` checks `status === "connecting"` which is derived from the null connection (see `useTradesaConnectionState.ts`). Navigate to any Tradesa V2 panel URL before the initial `refreshConnection()` completes to capture this state.

Alternative: Use `evaluate_script` to `_setAdapterForTests` equivalent — call `useTradesaStore.setState({ connection: null })` directly in the browser console after the React tree mounts but before any probe fires.

**Component rendering `connecting`:** `_PanelShell.tsx` → `<SkeletonBody />` — 6 animated `animate-pulse` rows.

**Status strip:** dot is `bg-zinc-500` (muted tone); label reads "Connecting…".

**Visual signature:** The panel body is replaced by 6 horizontally-staggered pulse skeleton rows (no table, no error, no CTA). The status strip shows a grey dot + "Connecting…" label. No mode badge, no heartbeat age, no kill-switch chip.

**Vitest coverage:** `PositionsPanel.test.tsx` → `"renders the skeleton-loader UX while status === 'connecting'"` (`expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument()`). Same pattern exists in all 7 panel test files.

**Suggested capture path:** Navigate to any Tradesa V2 panel immediately after page load, before the 30-second status poll fires. `take_screenshot` as soon as the skeleton is visible.

---

#### State 2: `unauthenticated`

**Mock response for `/tradesa-v2/status`:**
```json
{
  "status": "unauthenticated",
  "message": "No credentials configured.",
  "checked_at": <epoch_ms>,
  "last_heartbeat_at": null,
  "heartbeat_age_s": null,
  "bot_mode": null,
  "kill_switch_engaged": null
}
```

Alternatively: ensure no `tradesa-v2-supabase-url` or `tradesa-v2-supabase-service-role-key` entries in the OS keychain — then `buildAuthHeaders()` returns `{}` and the sidecar's `/tradesa-v2/status` endpoint returns the 200+unauthenticated response natively without mocking.

**Component rendering `unauthenticated`:** `_PanelShell.tsx` → `<UnauthenticatedBody>` — centered content with "Tradesa V2 — {title}" heading, explanation paragraph, "Open Settings" blue CTA button. Opening the CTA renders `<TradesaSettingsDialog>`.

**Status strip:** dot is `bg-zinc-500` (muted); label reads "Not configured".

**Visual signature:** Full panel replaced by centered card: h3 "Tradesa V2 — Live Positions" (or whichever panel), paragraph about observation-only connection, blue "Open Settings" button. Status strip shows grey dot + "Not configured".

**Vitest coverage:** `PositionsPanel.test.tsx` → `"renders 'Open Settings' CTA in the unauthenticated state"` (`expect(screen.getByTestId("tradesa-unauthenticated")).toBeInTheDocument()`).

---

#### State 3: `bot-offline`

**Mock response for `/tradesa-v2/status`:**
```json
{
  "status": "bot-offline",
  "message": "Bot heartbeat stale (>5 min).",
  "checked_at": <epoch_ms>,
  "last_heartbeat_at": <epoch_ms_minus_10_min>,
  "heartbeat_age_s": 600,
  "bot_mode": "paper",
  "kill_switch_engaged": false
}
```

**Component rendering `bot-offline`:** `_PanelShell.tsx` → renders `<BotOfflineBanner ageSeconds={600} />` (banner: "Tradesa V2 bot is offline (no heartbeat in 10 minutes). Showing last-known data — values may be stale.") + the panel body beneath it in 60% opacity / `saturate-50` muted style.

**Status strip:** dot is `bg-red-400` (error tone); label reads "Bot offline". Mode badge "paper" in blue. Heartbeat age shows "heartbeat 10 minutes ago".

**Visual signature:** Narrow red-tinted banner immediately below the status strip, followed by the data table at reduced opacity and desaturated colors. Status strip shows red dot + "Bot offline" + mode badge "paper" + heartbeat age.

**Vitest coverage:** `PositionsPanel.test.tsx` → `"renders the bot-offline banner with stale-minutes copy"` (`expect(screen.getByTestId("tradesa-bot-offline-banner")).toHaveTextContent(/10 minutes/)`).

---

#### State 4: `supabase-error` (already captured)

**Pre-existing capture:** `docs/screenshots/v0.8-pending/phase-8/uc1/tradesa-v2-positions-supabase-error-1920x1080.png`

The capture shows the `invoke` undefined error surfaced by the F7 Chrome fallback (Tauri-less web mode where `invoke` from `@tauri-apps/api/core` is undefined). The error message "Cannot read properties of undefined (reading 'invoke')" appears as the `SupabaseErrorBody` detail paragraph.

**Mock response for a "clean" supabase-error (without the invoke crash):**
```json
{
  "status": "supabase-error",
  "message": "Supabase REST returned 401 Unauthorized.",
  "checked_at": <epoch_ms>,
  "last_heartbeat_at": null,
  "heartbeat_age_s": null,
  "bot_mode": null,
  "kill_switch_engaged": null
}
```

**Component rendering `supabase-error`:** `_PanelShell.tsx` → `<SupabaseErrorBody message={state?.message} onRetry={...} />` — centered card with h3 "Supabase unreachable" in `text-red-300`, detail paragraph, RefreshCw icon + "Retry" button.

**Status strip:** dot is `bg-red-400` (error); label reads "Supabase error".

**Visual signature:** Panel body replaced by centered error card: "Supabase unreachable" heading (red text), message paragraph, "Retry" button with refresh icon. Status strip shows red dot + "Supabase error".

**Vitest coverage:** `_PanelShell.tsx` is exercised via all panel tests that check `tradesa-supabase-error` data-testid. The `TradesaBotStatusStrip` suite covers the `supabase-error` tone indirectly through the status-strip rendering tests.

**Note:** The existing capture at `v0.8-pending/...` was produced by the F7 "Tauri-less web mode" fallback, which cannot call `invoke`. For Phase 9, a clean mocked-fetch capture (without the invoke crash detail) is preferred. A 2560×1440 partner is also absent.

---

#### State 5: `healthy`

**Mock response for `/tradesa-v2/status`:**
```json
{
  "status": "healthy",
  "message": "Bot online; last heartbeat 12s ago.",
  "checked_at": <epoch_ms>,
  "last_heartbeat_at": <epoch_ms_minus_12s>,
  "heartbeat_age_s": 12,
  "bot_mode": "paper",
  "kill_switch_engaged": false
}
```

Additionally mock all data endpoints (`/tradesa-v2/positions`, etc.) to return populated rows using the sample shapes from `_test-helpers.ts`.

**Component rendering `healthy`:** `_PanelShell.tsx` passes through to `children` (the panel-specific body) — no banner, no error, no skeleton. The panel renders its populated table/list.

**Status strip:** dot is `bg-emerald-400` (ok tone); label reads "Bot online". Mode badge "paper" in blue. Heartbeat "heartbeat 12s ago".

**Visual signature:** Full panel body visible with real data. PositionsPanel shows BTCUSDT LONG + ETHUSDT SHORT rows. Status strip shows green dot + "Bot online" + mode badge "paper" + heartbeat timestamp. No banners.

**Vitest coverage:** `PositionsPanel.test.tsx` → `"renders populated table rows when healthy with positions"` (`expect(screen.getAllByTestId("tradesa-position-row")).toHaveLength(2)`). `TradesaBotStatusStrip.test.tsx` → `"renders 'Bot online' label with paper-mode badge in healthy state"`.

**Capture note:** This is the only state that requires real data in the panel body. Populate all 7 panels' data endpoints with the `makeTrade`/`makeDecision`/`makeBotHealth` factory payloads from `_test-helpers.ts`.

---

#### State 6: `partial`

**Mock response for `/tradesa-v2/status`:**
```json
{
  "status": "partial",
  "message": "Some Tradesa V2 endpoints are unreachable — showing partial data.",
  "checked_at": <epoch_ms>,
  "last_heartbeat_at": <epoch_ms_minus_2min>,
  "heartbeat_age_s": 120,
  "bot_mode": "paper",
  "kill_switch_engaged": false
}
```

Additionally: mock some data endpoints to return 502/timeout and others to return data — the `partial` state in production arises when the sidecar probe hits mixed success/failure across the 11 route endpoints.

**Component rendering `partial`:** `_PanelShell.tsx` → `<PartialBanner message={state?.message} />` rendered above the panel body (which is still shown). The amber-tinted banner reads the message; the body continues to render whatever data it has.

**Status strip:** dot is `bg-amber-400` (warn tone); label reads "Partial data". Mode badge "paper" in blue. Heartbeat age shows "heartbeat 2 minutes ago".

**Visual signature:** Narrow amber-tinted banner immediately below the status strip: "Some Tradesa V2 endpoints are unreachable — showing partial data." followed by the panel body at full opacity. Status strip shows amber dot + "Partial data" + mode badge.

**Vitest coverage:** `_PanelShell.tsx` `PartialBanner` component is referenced in the shell code; individual panel tests don't currently cover `partial` state directly. The status strip tone for `partial` = `warn` → amber dot is covered by the `STATUS_TONE` map unit. A dedicated `partial`-state panel test is absent — this is a test coverage gap, not a visual regression risk (the component branch is straightforward).

---

### Tradesa V2 capture checklist summary

| State | Mock needed | Primary panel to capture | Vitest test name |
|-------|-------------|--------------------------|------------------|
| `connecting` | None (initial store state) | Any panel | `PositionsPanel.test.tsx` "renders the skeleton-loader UX while status === 'connecting'" |
| `unauthenticated` | `/status` → `unauthenticated` payload | Any panel (shows CTA) | `PositionsPanel.test.tsx` "renders 'Open Settings' CTA" |
| `bot-offline` | `/status` → `bot-offline` + `heartbeat_age_s: 600` | PositionsPanel | `PositionsPanel.test.tsx` "renders the bot-offline banner" |
| `supabase-error` | `/status` → `supabase-error` payload (or leave invoke undefined) | PositionsPanel | `_PanelShell` + strip tests |
| `healthy` | `/status` → `healthy` + all data endpoints populated | PositionsPanel (2 trades visible) | `PositionsPanel.test.tsx` "renders populated table rows when healthy with positions" |
| `partial` | `/status` → `partial` payload | Any panel | No dedicated panel test — covered at store level |

For a full Phase 9 session, the 6-state pass should capture:
- One primary panel (PositionsPanel recommended — most visually distinct per state)
- At both 1920×1080 and 2560×1440
- Save to `docs/screenshots/v0.7.0/tradesa-v2/<state>-<resolution>.png` (or a new per-operator-session subfolder)

The `supabase-error` capture in `docs/screenshots/v0.8-pending/` counts as the supabase-error state capture; a 2560px partner is still missing.

---

## Part C — Cross-version visual consistency

### Files spot-checked

- `docs/screenshots/v0.6.0/teammate-e/analyst-ratings-1920x1080.png`
- `docs/screenshots/v0.6.0/teammate-m/macro-panel-all-providers-1920x1080.png`
- `docs/screenshots/v0.6.0/teammate-sc/screener-panel-1920x1080.png`
- `docs/screenshots/v0.6.0/teammate-f/sec-filings-panel-1920x1080.png`
- `docs/screenshots/v0.3.0/composed-1920x1080.png`

No v0.6.5 subfolder exists in `docs/screenshots/` (confirmed by glob — no `v0.6.5/` directory).

---

### Finding T1-v060-solo-workspace: v0.6.0 panels are full-window solo captures, not tabs inside the cockpit [S3] [status: open]

**Repro:** Open any v0.6.0 capture (e.g. `analyst-ratings-1920x1080.png`, `macro-panel-all-providers-1920x1080.png`). Every v0.6.0 capture shows a single panel filling the entire browser viewport — no dockview tab row, no watchlist/news/portfolio/AI-assistant columns visible.

**Impact:** Axis 3 (Workspace) — the v0.7.0+ convention requires Phase 6 panels to be captured "as additional tabs in existing slots, NOT full-window." The v0.6.0 captures predate this convention (the convention was codified in v0.7.0) but remain in the screenshot history. Phase 9 re-capture of Phase 6 panels in the canonical cockpit shape is already documented as a BLOCKERS.md v0.8 item #3.

**Context:** These v0.6.0 captures are acknowledged as Pillow stand-ins (v0.6.0 was captured without a live Tauri session for E/F captures; Screener captures were Pillow from v0.6.1). The drift is by design for the v0.6.0 release; the fix is in the Phase 9 live-capture pass.

**Files:** All `docs/screenshots/v0.6.0/` captures
**Re-captured at:** n/a — Phase 9 operator-led session per BLOCKERS.md v0.8 #3

---

### Finding T1-v060-header-absent-preconvention: No titlebar visible in v0.6.0 captures (pre-convention) [S4] [status: open]

**Repro:** Inspect v0.6.0 screenshots. No OS window chrome is visible. The Screener shot has a footer line `Vysted Terminal · v0.6.1 · /screener/run AND-combined criteria · S&P 500 snapshot universe` — the closest thing to a version label, but not the titlebar.

**Impact:** Axis 6 (Header). The convention requiring titlebar was not established until v0.7.0; v0.6.0 shots pre-date it. S4 (informational only — no action needed beyond the already-planned Phase 9 live re-capture).

**Files:** All `docs/screenshots/v0.6.0/` captures
**Re-captured at:** n/a — Phase 9 re-capture will include titlebar per the v0.7.0+ convention

---

### Finding T1-v060-dark-clean: Dark theme compliance — clean [S4]

All v0.6.0 captures audited show dark background (`#09090b` / zinc-950 equivalent). No light-mode captures found. Theme axis is clean for v0.6.0.

---

### Finding T1-v030-composed-clean: v0.3.0 composed shots — mostly compliant for their era [S4]

`docs/screenshots/v0.3.0/composed-1920x1080.png` shows the full cockpit shape (Equity Overview populated with AAPL including 32 analyst ratings, income statement rows, P&L — this is the model of what "fully populated Equity Overview" looks like). Dark theme. AAPL anchor. The watchlist shows SPY, QQQ, BTC/USDT, ETH/USDT, NVDA, AAPL (same default order as v0.7.0). No titlebar visible. Workspace shape matches the 5-panel cockpit. This shot is the historical reference for "what fully-populated Equity Overview looks like" — informational.

---

### Part C Summary

No blocking drift found in v0.6.0 or v0.3.0. All findings are S3/S4 and represent expected pre-convention divergence. v0.6.5 screenshots do not exist in the repo (no `docs/screenshots/v0.6.5/` folder — the Tradesa V2 captures were deferred per the v0.6.5 README and BLOCKERS.md). The Phase 9 operator-led re-capture session already covers the main v0.6.0 drift items (BLOCKERS.md v0.8 #3).

---

## Summary

| Severity | Count | IDs |
|----------|-------|-----|
| S1       | 0     | — |
| S2       | 1     | T1-header-absent |
| S3       | 7     | T1-workspace-solo-chart, T1-chart-tab-missing-2560, T1-cockpit-non-hero-incomplete, T1-equity-overview-unavailable, T1-watchlist-order, T1-v060-solo-workspace, T1-v060-header-absent-preconvention |
| S4       | 2     | T1-v060-dark-clean, T1-v030-composed-clean |

**No S1 blockers.** All v0.7.0 convention gaps are known, acknowledged in the v0.7.0 README, and already tracked in BLOCKERS.md for Phase 9. The single S2 finding (missing titlebar) is the most impactful convention gap — it is the _only_ axis completely unaddressed by the existing v0.7.0 captures.

The Tradesa V2 6-state capture procedure (Part B) provides a complete methodology for Phase 9. The `supabase-error` state already has one capture; 5 remaining states need the mocked-fetch approach with a live Tauri dev session.
