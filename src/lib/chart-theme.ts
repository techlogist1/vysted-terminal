/**
 * Canvas palette -- the single source of truth for every `lightweight-charts`
 * surface and drawing primitive.
 *
 * Canvas elements render to a `<canvas>` bitmap and CANNOT read CSS custom
 * properties, so each chart/drawing file used to hard-code its own copy of the
 * palette -- which is exactly how values silently drifted off-palette. This
 * module mirrors `styles/tokens.css` (R6 "Pure Black" -- pure neutral grayscale,
 * faithful OpenCode dark) once; when a token changes, update both the CSS token
 * AND its constant here -- but only here, not in 12 files (FR-030: re-skin the
 * canvas + tokens in lockstep).
 *
 * NOTE: the export NAMES (`ACCENT_CORAL`, `coralFill`, ...) are historical and
 * kept so the 12 importing files don't churn -- the chart is now MONOCHROME, so
 * they carry NEUTRAL grays (distinct lightness for overlaid indicators), not a
 * hue. P&L green/red are the only saturated colors (data, never chrome). Read
 * the role, not the name.
 */

// --- Neutral surfaces (mirror charcoal-*) ------------------------------------
export const CHART_SURFACE = "#161616"; // charcoal-900 -- chart background
export const CHART_TEXT = "#a8a8a8"; // charcoal-400 -- axis / label text (muted)
export const CHART_TEXT_MUTED = "#8a8a8a"; // charcoal-500 -- secondary labels
export const CHART_GRID = "#2b2b2b"; // charcoal-800 -- gridlines
export const CHART_BORDER = "#353535"; // charcoal-700 -- scale borders
export const CHART_CROSSHAIR = "#484848"; // charcoal-600 -- crosshair

// --- Monochrome chart accent (neutral grays — charts read monochrome) --------
export const ACCENT_CORAL = "#cccccc"; // charcoal-300 -- primary series line
export const ACCENT_CORAL_BRIGHT = "#ededed"; // charcoal-100 -- emphasis / lead
export const ACCENT_CORAL_DEEP = "#767676"; // mid-gray -- deep line

// --- Semantic signal colors (the only saturated colors; never as fills) ------
export const POSITIVE = "#3fbf6f"; // gains -- muted green, luminance-matched
export const POSITIVE_BRIGHT = "#4ade80";
export const NEGATIVE = "#e5544b"; // losses -- muted red, luminance-matched
export const NEGATIVE_BRIGHT = "#f87171";
export const WARNING = "#e0a13a"; // caution -- stale/paper/warning

// --- Neutral data series (distinct grays for overlaid indicators) ------------
export const NEUTRAL = "#a8a8a8"; // charcoal-400 -- comparison / secondary series
export const NEUTRAL_LIGHT = "#8f8f8f"; // distinct mid-gray (historical name)

// --- RGB tuples for alpha fills (canvas wants rgba()) ------------------------
export const ACCENT_CORAL_RGB = "204, 204, 204"; // #cccccc -- three-place lockstep
export const POSITIVE_RGB = "63, 191, 111";
export const NEGATIVE_RGB = "229, 84, 75";

/** `rgba()` fill from the neutral chart accent at the given alpha (0-1). */
export function coralFill(alpha: number): string {
  return `rgba(${ACCENT_CORAL_RGB}, ${alpha})`;
}
/** `rgba()` fill from the positive (gain) color at the given alpha (0-1). */
export function positiveFill(alpha: number): string {
  return `rgba(${POSITIVE_RGB}, ${alpha})`;
}
/** `rgba()` fill from the negative (loss) color at the given alpha (0-1). */
export function negativeFill(alpha: number): string {
  return `rgba(${NEGATIVE_RGB}, ${alpha})`;
}

/**
 * Distinct, MONOCHROME indicator line palette -- five neutral grays at clearly
 * separated lightness so the first few overlaid indicators read apart against
 * the near-black surface without introducing any hue (faithful OpenCode dark).
 */
export const INDICATOR_PALETTE = [
  ACCENT_CORAL_BRIGHT, // #ededed -- brightest lead
  NEUTRAL, // #a8a8a8
  ACCENT_CORAL, // #cccccc
  ACCENT_CORAL_DEEP, // #767676
  NEUTRAL_LIGHT, // #8f8f8f
] as const;

/**
 * Convenience surface theme many panels spread into their chart `layout` /
 * `grid` / `crosshair` options. Mirrors the `CHART_THEME` shape panels already
 * declared locally.
 */
export const CHART_THEME = {
  background: CHART_SURFACE,
  text: CHART_TEXT,
  textMuted: CHART_TEXT_MUTED,
  grid: CHART_GRID,
  border: CHART_BORDER,
  crosshair: CHART_CROSSHAIR,
} as const;
