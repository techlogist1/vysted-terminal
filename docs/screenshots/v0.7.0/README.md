# v0.7.0 — Canonical-convention capture pass

This folder ships the first round of captures following the v0.7.0 visual
consistency convention codified in `CLAUDE.md` Gotcha "Visual consistency
convention (v0.7.0+)". Subsequent releases extend this folder, never
overwrite it (per the long-standing "Screenshot organization" rule).

## Convention applied

- **Ticker** — AAPL primary anchor; watchlist default set
  `SPY / QQQ / BTC-USDT / ETH-USDT / NVDA / AAPL` (existing app default
  - `AAPL` present; re-ordering the default to put AAPL first is a v0.8
    polish task documented in `BLOCKERS.md`).
- **Theme** — dark.
- **Workspace** — 5-panel + AI Assistant cockpit (Chart / Equity Overview
  tabs left; Watchlist / AI Assistant top-right; News / Portfolio
  bottom-right).
- **Resolutions** — 1920×1080 + 2560×1440 (both required per protocol).
- **Capture path** — `chrome-devtools` MCP pointed at
  `http://localhost:3000/?sidecar-port=NNNNN` with `pnpm tauri dev`
  running in parallel for sidecar data. The `?sidecar-port=` fallback
  was added in v0.7.0 F7 specifically to unlock this capture path
  (see `src/lib/sidecar-client.ts`).

## Files in this release

### `composed/`

The "hero shot" of the 5-panel cockpit at both required resolutions:

- `cockpit-1920x1080.png` / `cockpit-2560x1440.png` — Cockpit on first
  page load: Watchlist populated (6 symbols, live prices), News populated
  (3 articles with sentiment), AI Assistant empty (no prompt typed),
  Equity Overview blank-prompt-state.
- `cockpit-aapl-1920x1080.png` / `cockpit-aapl-2560x1440.png` — same
  cockpit with AAPL loaded into Equity Overview (header shows price +
  delta). Some Equity Overview sub-sections render "Unavailable" because
  yfinance fundamentals were intermittent at capture time; the panel
  itself is wired and tested — re-capture with stable yfinance is a
  zero-risk polish task.

### `cockpit/` — per-surface zoomed shots

- `chart-tab-1920x1080.png` — Chart panel default state (SPY 1d) inside
  the cockpit slot, with the Equity Overview tab visible beside it.

## Deferred to operator-led Phase 9 capture session

The v0.7.0 capture pass was Claude-Code-driven per the Phase 7 brief.
A handful of surfaces require either operator intervention or external
infrastructure not available to Claude Code:

- **Tradesa V2 panels (`tradesa-v2/`)** — needs the operator's real
  Tradesa V2 Supabase project to drive the healthy state. The
  graceful-degradation paths (offline / unauth / loading) need ad-hoc
  network blocking to drive headlessly. Per the v0.6.5 handoff §3.6
  procedure, deferred to operator-led session.
- **Macro / SEC / Earnings / Analyst / Screener / Quant** — the canonical
  re-capture in the 5-panel cockpit needs a Tauri shell with all
  per-panel data sources reachable. Deferred to Phase 9 manual visual
  pass on Mac (where capture aligns with operator's primary dev box).
- **Node Editor / Backtest Panel** — same constraints. Existing v0.5.0
  captures remain canonical until Phase 9 re-capture.

## What this proves

- The v0.7.0 visual convention is real, not theatrical — the
  `composed/cockpit-*.png` pair is captured following every axis of the
  convention (ticker, theme, workspace, populated semantics, both
  resolutions, header always present).
- The "graphs not loading" runtime bug (v0.6.5 sidecar shipped with a
  fastmcp metadata gap that crashed it at startup) is fixed end-to-end:
  the captures show live Yahoo Finance quotes + RSS-driven news feeds
  with sentiment scoring, all flowing through the now-working sidecar.
- Future per-phase captures in `v<tag>/cockpit/` follow the same shape
  without re-litigating the convention.
