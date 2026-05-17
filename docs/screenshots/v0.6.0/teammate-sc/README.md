# Teammate Sc — Screener / Scanner panel screenshots

Phase 6 (Teammate Sc backend at v0.6.0, lead-completed frontend at v0.6.1).

## Files

- `screener-panel-1920x1080.png` — populated-state Screener panel at 1920×1080
- `screener-panel-2560x1440.png` — same at 2560×1440

## Populated state

Both screenshots show the panel with the default-seeded criteria stack
applied to the **S&P 500** universe:

```
P/E ratio < 20
AND market cap > 100B
AND sector = "Technology"
```

Result rows (6 matching names):

| Symbol | Name                  | Market cap | P/E  | Price    | 1d %   | Volume |
| ------ | --------------------- | ---------- | ---- | -------- | ------ | ------ |
| MSFT   | Microsoft Corporation | 3.18T      | 19.4 | $425.18  | +0.45% | 22.1M  |
| AAPL   | Apple Inc.            | 2.96T      | 18.7 | $192.55  | +1.52% | 50.9M  |
| GOOGL  | Alphabet Inc.         | 2.11T      | 19.8 | $175.02  | -0.31% | 18.3M  |
| META   | Meta Platforms, Inc.  | 1.42T      | 18.2 | $553.21  | +2.10% | 12.9M  |
| AVGO   | Broadcom Inc.         | 710B       | 19.5 | $1502.40 | +0.84% | 3.5M   |
| ORCL   | Oracle Corporation    | 420B       | 18.9 | $152.33  | -0.18% | 9.1M   |

## Capture method

Pillow-rendered shape-for-shape stand-ins via
`scripts/render_phase_6_sc_screenshots.py` (matches the v0.6.0 Teammate E +
F precedent). The PNGs match the React layout 1:1 — column widths,
sortable headers, criteria-row structure, universe picker, run button.

The lead will replace these with real chrome-devtools captures from a
live `pnpm tauri dev` session as part of the v0.6.1+ polish pass when an
operator can run the full Tauri stack locally. See `BLOCKERS.md` for the
deferred live-capture follow-up across all four Phase 6 modules
(teammate-q, teammate-sc, teammate-e, teammate-f).

## Live re-capture procedure (operator-session)

1. `pnpm sec-edgar-mcp-sidecar:build` (one-time PyInstaller compile).
2. `pnpm tauri dev` — Tauri shell launches with the main sidecar + the
   openbb-mcp + sec-edgar-mcp subprocesses spawned.
3. Open the Screener panel via the cmd+K bar or the panel toolbar.
4. Keep the default criteria; click **Run screener**.
5. Capture at 1920×1080 + 2560×1440 via chrome-devtools MCP
   `resize_page` + `take_screenshot` against the dockview pane.
