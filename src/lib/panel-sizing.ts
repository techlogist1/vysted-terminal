import type { IDockviewPanel } from "dockview";

/**
 * Host-side minimum panel sizes (px), keyed by `PanelSpec.component`. Enforced
 * via dockview's per-panel `setConstraints` so a squeezed cockpit can never
 * collapse a panel into overlapping/illegible content — content-heavy panels
 * (chart, settings, marketplace) get a wider floor; rail panels a tighter one.
 *
 * This lives in the HOST, not in `PanelSpec` (`types/plugin.ts` is Tier-1
 * LOCKED), so the plugin contract stays byte-for-byte untouched. Anything not
 * listed gets `DEFAULT_PANEL_MIN_SIZE`.
 */
export const PANEL_MIN_SIZE: Record<string, { minimumWidth: number; minimumHeight: number }> = {
  // --- Default-cockpit panels ---
  // chart: ONE h-7 toolbar row (R9 — symbol/timeframe/tools, ~44px) + earned
  // chip/inspector rows above/below the canvas. 360 wide is the toolbar's
  // declared one-row floor (its §3.4 collapse ladder bottoms out at the ⋯
  // step); 360 tall keeps ~260px of legible canvas under the chrome.
  "chart-panel": { minimumWidth: 360, minimumHeight: 360 },
  "equity-overview-panel": { minimumWidth: 340, minimumHeight: 200 },
  "watchlist-panel": { minimumWidth: 264, minimumHeight: 140 },
  "news-panel": { minimumWidth: 280, minimumHeight: 160 },
  // portfolio: a named-portfolio header (~48px) + the flex-wrap add-holding form
  // (~150px) sit above the holdings table / empty state, so a low floor squeezed
  // the content (and the empty-state CTA) into a sliver in the default rail.
  "portfolio-panel": { minimumWidth: 520, minimumHeight: 320 },

  // --- Wide content panels (fixed-width aside / canvas + a results floor) ---
  // Each width = the panel's hardcoded fixed column(s) + a usable second pane,
  // so the `flex-1` results/canvas section never collapses to 0 at the min.
  "node-editor-panel": { minimumWidth: 560, minimumHeight: 320 }, // palette 224 + props 256 + 80 canvas
  "option-pricer-panel": { minimumWidth: 640, minimumHeight: 320 }, // w-80 aside (320) + 320 results
  "bond-pricer-panel": { minimumWidth: 640, minimumHeight: 300 }, // w-80 aside (320) + 320 results
  "yield-curve-panel": { minimumWidth: 640, minimumHeight: 360 }, // w-80 aside (320) + 320 chart
  "greeks-dashboard-panel": { minimumWidth: 600, minimumHeight: 280 }, // w-72 aside (288) + 312 heatmap
  "backtest-panel": { minimumWidth: 680, minimumHeight: 340 }, // w-72 aside (288) + 392 results
  "screener-panel": { minimumWidth: 580, minimumHeight: 360 }, // 384px criteria grid + padding + remove
  "sec-filings-panel": { minimumWidth: 480, minimumHeight: 300 },
  "option-chain-panel": { minimumWidth: 480, minimumHeight: 300 }, // scrolling chain table
  "earnings-calendar-panel": { minimumWidth: 560, minimumHeight: 240 },
  "analyst-ratings-panel": { minimumWidth: 420, minimumHeight: 260 },
  "macro-panel": { minimumWidth: 400, minimumHeight: 300 },

  // --- Primary-content / config panels (opened from the palette) ---
  "settings-panel": { minimumWidth: 480, minimumHeight: 300 },
  "marketplace-panel": { minimumWidth: 380, minimumHeight: 300 },
  "agent-builder-panel": { minimumWidth: 380, minimumHeight: 280 },
  "plugin-manager-panel": { minimumWidth: 340, minimumHeight: 200 },

  // --- Research surfaces ---
  // Prose surfaces (the published brief, the notes editor): floors that keep
  // a readable line length and a few lines of text visible.
  "brief-panel": { minimumWidth: 380, minimumHeight: 260 },
  "notes-panel": { minimumWidth: 320, minimumHeight: 200 },
};
export const DEFAULT_PANEL_MIN_SIZE = { minimumWidth: 300, minimumHeight: 180 };

/** Clamp a panel's minimum size so it can't be dragged into overlap. Guarded:
 *  a dockview throw on one panel (e.g. a disposed/edge state) must not abort a
 *  whole-layout sweep, leaving later panels unconstrained. */
export function applyPanelConstraints(panel: IDockviewPanel): void {
  try {
    const size = PANEL_MIN_SIZE[panel.api.component] ?? DEFAULT_PANEL_MIN_SIZE;
    panel.api.setConstraints(size);
  } catch {
    // best-effort; a single panel failing to clamp must not break the others.
  }
}

/**
 * Re-affirm constraints AND grow any panel a saved blob restored below its
 * minimum (dockview's `fromJSON` restores exact sizes, and constraints only
 * clamp *future* sash drags — they don't retroactively grow an under-min
 * panel). PanelHost runs it after every `fromJSON` (boot restore and named
 * layout loads alike) so a sub-min blob snaps up to a legible size.
 */
export function enforceConstraintsAfterRestore(panel: IDockviewPanel): void {
  try {
    const size = PANEL_MIN_SIZE[panel.api.component] ?? DEFAULT_PANEL_MIN_SIZE;
    panel.api.setConstraints(size);
    // Grow a panel restored below its minimum on BOTH axes — `setConstraints`
    // only clamps future sash drags, it doesn't retroactively grow an under-min
    // panel a saved blob restored too small (e.g. a blob saved before min-sizes
    // existed, or one saved while the panel was squeezed).
    if (panel.api.width > 0 && panel.api.width < size.minimumWidth) {
      panel.api.setSize({ width: size.minimumWidth });
    }
    if (panel.api.height > 0 && panel.api.height < size.minimumHeight) {
      panel.api.setSize({ height: size.minimumHeight });
    }
  } catch {
    // best-effort; one panel throwing must not abort the post-restore sweep.
  }
}
