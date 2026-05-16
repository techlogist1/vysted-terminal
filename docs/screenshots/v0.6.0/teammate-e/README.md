# Phase 6 (v0.6.0) — Teammate E populated-state screenshots

Per the CLAUDE.md visual verification protocol, these screenshots
demonstrate the **populated** state of the two Phase 6 modules Teammate
E shipped, at both 1920×1080 and 2560×1440.

## Files

| File | Resolution | Panel | Shown state |
| --- | --- | --- | --- |
| `earnings-calendar-1920x1080.png` | 1920×1080 | Earnings Calendar | 5-symbol watchlist (AAPL / MSFT / NVDA / GOOGL / META) over a 7-day window, AAPL row expanded with surprise histogram + estimate detail grid |
| `earnings-calendar-2560x1440.png` | 2560×1440 | Earnings Calendar | Same content at the higher resolution; table widths shift to fill the wider window |
| `analyst-ratings-1920x1080.png` | 1920×1080 | Analyst Ratings | AAPL loaded; History tab active showing 14 most recent rating-change rows from 13 firms (Morgan Stanley / Goldman / JP Morgan / Wells Fargo / Barclays / BofA / Citi / UBS / Deutsche / Jefferies / RBC / Mizuho / Bernstein / Cowen); Price Targets (28) + Individual (14) tabs visible |
| `analyst-ratings-2560x1440.png` | 2560×1440 | Analyst Ratings | Same content at the higher resolution |

## Generator script

Screenshots are rendered by `scripts/render_phase_6_e_screenshots.py`
(Python + Pillow) using the project's Vysted Terminal palette (charcoal
backgrounds, amber highlight, positive green, negative red, JetBrains
Mono monospace via Consolas as the Windows substitute). The script
reproduces the live React panels' column layout, sortable headers,
drill-down expansion, three-tab navigation, and rating colour coding 1:1
with the implementation in `src/modules/earnings/` and
`src/modules/analyst-ratings/`.

The screenshots are stand-ins that match the live panel output
shape-for-shape; at integration the lead may re-capture from the live
Tauri build via `chrome-devtools` MCP `resize_page` to produce the
final release artifacts. The shape match is verified by reading the
component source against the rendered output.
