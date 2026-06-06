/**
 * Canvas palette -- the single source of truth for every `lightweight-charts`
 * surface and drawing primitive.
 *
 * Canvas elements render to a `<canvas>` bitmap and CANNOT read CSS custom
 * properties, so each chart/drawing file used to hard-code its own copy of the
 * palette -- which is exactly how values silently drifted off-palette. This
 * module mirrors `styles/tokens.css` (R4 "Warm Graphite" -- warm-graphite
 * neutral + muted amber accent) once; when a token changes, update both the CSS
 * token AND its constant here -- but only here, not in 12 files (FR-030: re-skin
 * the canvas + tokens in lockstep).
 *
 * NOTE: the export NAMES (`ACCENT_CORAL`, `coralFill`, ...) are historical and
 * kept so the 12 importing files don't churn -- they now carry the muted AMBER
 * accent, mirroring the `amber-*` token. Read the role, not the name.
 */

// --- Warm-graphite surfaces (mirror charcoal-*) ------------------------------
export const CHART_SURFACE = "#1e1a15"; // charcoal-900 -- chart background
export const CHART_TEXT = "#ada294"; // charcoal-400 -- axis / label text (muted)
export const CHART_TEXT_MUTED = "#968c7d"; // charcoal-500 -- secondary labels (lightened for WCAG AA)
export const CHART_GRID = "#352f26"; // charcoal-800 -- gridlines
export const CHART_BORDER = "#3e372d"; // charcoal-700 -- scale borders
export const CHART_CROSSHAIR = "#4d463b"; // charcoal-600 -- crosshair

// --- Muted amber accent (mirror amber-*) -------------------------------------
export const ACCENT_CORAL = "#d89a4e"; // amber-400 -- brand / default accent
export const ACCENT_CORAL_BRIGHT = "#e9bd80"; // amber-300 -- emphasis
export const ACCENT_CORAL_DEEP = "#875720"; // amber-600 -- deep accent / line

// --- Semantic signal colors (the only saturated colors; never as fills) ------
export const POSITIVE = "#3fbf6f"; // gains -- muted green, luminance-matched
export const POSITIVE_BRIGHT = "#4ade80";
export const NEGATIVE = "#e5544b"; // losses -- muted red, luminance-matched
export const NEGATIVE_BRIGHT = "#f87171";
export const WARNING = "#e0a13a"; // caution -- stale/paper/warning

// --- Neutral data series (mirror charcoal-400/-300) --------------------------
export const NEUTRAL = "#ada294"; // charcoal-400 -- comparison / secondary series
export const NEUTRAL_LIGHT = "#d6d0c4"; // charcoal-300

// --- RGB tuples for alpha fills (canvas wants rgba()) ------------------------
export const ACCENT_CORAL_RGB = "216, 154, 78"; // #d89a4e -- three-place lockstep
export const POSITIVE_RGB = "63, 191, 111";
export const NEGATIVE_RGB = "229, 84, 75";

/** `rgba()` fill from the indigo accent at the given alpha (0-1). */
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
 * Distinct, on-brand indicator line palette -- amber lead, warm neutrals, and
 * a muted green. Order is chosen so the first few overlaid indicators read
 * clearly against the warm-graphite surface.
 */
export const INDICATOR_PALETTE = [
  ACCENT_CORAL, // amber
  NEUTRAL, // warm neutral
  POSITIVE, // muted green
  ACCENT_CORAL_BRIGHT, // amber-bright
  NEUTRAL_LIGHT, // light warm neutral
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
