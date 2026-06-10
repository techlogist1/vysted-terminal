/**
 * Meta-row collapse ladder (R8 — law §3.4): the composer meta row never
 * overlaps at ANY dock width because its presentation is a PURE function of
 * the measured row width. The ladder:
 *
 *   full      ≥ 470px  full labels, depth text label, lens/model at wide caps
 *   short     ≥ 380px  labels stay, depth label drops, lens/model caps tighten
 *   icons     ≥ 250px  mode/lens/model collapse to 12px icons + tooltips
 *   overflow  ≥ 170px  autonomy + model fold into a "⋯" popover
 *   two-row   < 170px  everything stays reachable across two clean 24px rows
 *
 * Thresholds are designed against measured chip minimums (caption type,
 * hairline borders, gap-1.5): icons-only needs ~244px, the overflow row
 * ~152px. The 280px dock minimum (≈256px of row width inside px-3) lands on
 * "icons" — every control visible, nothing clipped. `ComposerMetaRow` feeds
 * this from a ResizeObserver; an unmeasured row (SSR, jsdom) assumes room.
 */

export type MetaRowStep = "full" | "short" | "icons" | "overflow" | "two-row";

/** Minimum row width (px, content box) at which each step engages. */
export const META_ROW_BREAKPOINTS = {
  full: 470,
  short: 380,
  icons: 250,
  overflow: 170,
} as const;

export function metaRowStepForWidth(width: number): MetaRowStep {
  if (!Number.isFinite(width) || width <= 0) {
    // Unmeasured (first paint, SSR, test DOM) — assume room; the observer
    // corrects on the first real layout pass.
    return "full";
  }
  if (width >= META_ROW_BREAKPOINTS.full) {
    return "full";
  }
  if (width >= META_ROW_BREAKPOINTS.short) {
    return "short";
  }
  if (width >= META_ROW_BREAKPOINTS.icons) {
    return "icons";
  }
  if (width >= META_ROW_BREAKPOINTS.overflow) {
    return "overflow";
  }
  return "two-row";
}

/** How each step renders — the row consumes this, never the raw step name. */
export interface MetaRowPlan {
  /** Chip content density: text labels, tighter labels, or icon+tooltip. */
  labels: "full" | "short" | "icons";
  /** The depth slider's text label ("NORMAL") renders only at the full step. */
  showDepthLabel: boolean;
  /** Autonomy + model fold into the "⋯" overflow popover. */
  overflowMenu: boolean;
  /** Wrap into two stacked 24px rows instead of clipping. */
  twoRow: boolean;
}

export function metaRowPlan(step: MetaRowStep): MetaRowPlan {
  switch (step) {
    case "full":
      return { labels: "full", showDepthLabel: true, overflowMenu: false, twoRow: false };
    case "short":
      return { labels: "short", showDepthLabel: false, overflowMenu: false, twoRow: false };
    case "icons":
      return { labels: "icons", showDepthLabel: false, overflowMenu: false, twoRow: false };
    case "overflow":
      return { labels: "icons", showDepthLabel: false, overflowMenu: true, twoRow: false };
    case "two-row":
      return { labels: "icons", showDepthLabel: false, overflowMenu: false, twoRow: true };
  }
}
