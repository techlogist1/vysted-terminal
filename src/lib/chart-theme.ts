/**
 * Canvas palette — the single source of truth for every `lightweight-charts`
 * surface and drawing primitive.
 *
 * Canvas elements render to a `<canvas>` bitmap and CANNOT read CSS custom
 * properties, so each chart/drawing file used to hard-code its own copy of the
 * palette — which is exactly how values silently drifted off-palette. This
 * module mirrors `styles/tokens.css` (minimal-dark "cold instrument" — neutral
 * zinc + cool-teal accent) once; when a token changes, update both the CSS token
 * AND its constant here — but only here, not in 12 files (FR-030: re-skin the
 * canvas + tokens in lockstep).
 *
 * NOTE: the export NAMES (`ACCENT_CORAL`, `coralFill`, …) are historical and
 * kept so the 12 importing files don't churn — they now carry the COOL-TEAL
 * accent, mirroring the `amber-*` token. Read the role, not the name.
 */

// --- Neutral zinc surfaces (mirror charcoal-*) -----------------------------
export const CHART_SURFACE = "#161619"; // charcoal-900 — chart background
export const CHART_TEXT = "#a1a1aa"; // charcoal-400 — axis / label text (muted)
export const CHART_TEXT_MUTED = "#71717a"; // charcoal-500 — secondary labels
export const CHART_GRID = "#27272a"; // charcoal-800 — gridlines
export const CHART_BORDER = "#34343a"; // charcoal-700 — scale borders
export const CHART_CROSSHAIR = "#3f3f46"; // charcoal-600 — crosshair

// --- Cool-indigo accent (mirror amber-* [indigo]) --------------------------
export const ACCENT_CORAL = "#818cf8"; // amber-400 — brand / default accent (indigo)
export const ACCENT_CORAL_BRIGHT = "#a5b4fc"; // amber-300 — emphasis
export const ACCENT_CORAL_DEEP = "#3730a3"; // amber-600 — deep accent / line

// --- Semantic signal colors (the only saturated colors; kept clear of teal) -
export const POSITIVE = "#22c55e"; // gains — green-500
export const POSITIVE_BRIGHT = "#4ade80";
export const NEGATIVE = "#ef4444"; // losses — red-500 (distinct from teal)
export const NEGATIVE_BRIGHT = "#f87171";
export const WARNING = "#f59e0b"; // caution — amber-500

// --- Neutral data series (mirror sage-* → zinc neutral) --------------------
export const NEUTRAL = "#a1a1aa"; // sage-400 — comparison / secondary series
export const NEUTRAL_LIGHT = "#d4d4d8"; // sage-300

// --- RGB tuples for alpha fills (canvas wants rgba()) ----------------------
export const ACCENT_CORAL_RGB = "129, 140, 248"; // #818cf8 — cool indigo
export const POSITIVE_RGB = "34, 197, 94";
export const NEGATIVE_RGB = "239, 68, 68";

/** `rgba()` fill from the teal accent at the given alpha (0–1). */
export function coralFill(alpha: number): string {
  return `rgba(${ACCENT_CORAL_RGB}, ${alpha})`;
}
/** `rgba()` fill from the positive (gain) color at the given alpha (0–1). */
export function positiveFill(alpha: number): string {
  return `rgba(${POSITIVE_RGB}, ${alpha})`;
}
/** `rgba()` fill from the negative (loss) color at the given alpha (0–1). */
export function negativeFill(alpha: number): string {
  return `rgba(${NEGATIVE_RGB}, ${alpha})`;
}

/**
 * Distinct, on-brand indicator line palette — teal lead, zinc neutrals, and a
 * green. Order is chosen so the first few overlaid indicators read clearly
 * against the neutral zinc surface.
 */
export const INDICATOR_PALETTE = [
  ACCENT_CORAL, // teal
  NEUTRAL, // zinc neutral
  POSITIVE, // green
  ACCENT_CORAL_BRIGHT, // teal-bright
  NEUTRAL_LIGHT, // light zinc
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
