/**
 * Composer controls collapse ladder (R9 Track C — law §3.4 carried forward).
 *
 * The composer's in-field controls row (+ … depth · model · send) never
 * overlaps at ANY dock width because its presentation is a PURE function of
 * the measured row width. The ladder:
 *
 *   full     ≥ 380px  model = designed full short-form text, depth expands
 *                     to all three stops on hover/focus
 *   compact  ≥ 310px  model text tightens to its leading two words,
 *                     depth still expands
 *   icons    < 310px  model collapses to a 14px icon + tooltip; depth shows
 *                     the active stop ONLY (click cycles N → D → U)
 *
 * Thresholds are designed against measured minimums (caption type, 28px
 * primary squares, gap-2): the expanded depth pill needs ~150px, the full
 * model text ~120px. The 280px dock minimum (≈238px of row width inside the
 * form/field padding) lands on "icons" — every control visible and usable,
 * nothing clipped. `Composer` feeds this from a ResizeObserver; an unmeasured
 * row (SSR, jsdom) assumes room.
 */

export type ComposerControlsStep = "full" | "compact" | "icons";

/** Minimum row width (px, content box) at which each step engages. */
export const COMPOSER_CONTROLS_BREAKPOINTS = {
  full: 380,
  compact: 310,
} as const;

export function composerControlsStepForWidth(width: number): ComposerControlsStep {
  if (!Number.isFinite(width) || width <= 0) {
    // Unmeasured (first paint, SSR, test DOM) — assume room; the observer
    // corrects on the first real layout pass.
    return "full";
  }
  if (width >= COMPOSER_CONTROLS_BREAKPOINTS.full) {
    return "full";
  }
  if (width >= COMPOSER_CONTROLS_BREAKPOINTS.compact) {
    return "compact";
  }
  return "icons";
}

/** How each step renders — consumers read this, never the raw step name. */
export interface ComposerControlsPlan {
  /** Model control density: full designed text, two-word text, or icon+tooltip. */
  model: "full" | "short" | "icon";
  /** Whether the depth pill expands to all three stops on hover/focus.
   *  When false it renders the active stop only and a click cycles the stops. */
  depthExpands: boolean;
}

export function composerControlsPlan(step: ComposerControlsStep): ComposerControlsPlan {
  switch (step) {
    case "full":
      return { model: "full", depthExpands: true };
    case "compact":
      return { model: "short", depthExpands: true };
    case "icons":
      return { model: "icon", depthExpands: false };
  }
}
