/**
 * Canvas palette — the single source of truth for every `lightweight-charts`
 * surface and drawing primitive.
 *
 * Canvas elements render to a `<canvas>` bitmap and CANNOT read CSS custom
 * properties, so each chart/drawing file used to hard-code its own copy of the
 * palette — which is exactly how values silently drifted off-palette. This
 * module mirrors `styles/tokens.css` ("cold instrument" minimal-dark) once;
 * when a token changes, update both the CSS token AND its constant here — but
 * only here, not in 12 files (FR-030: re-skin the canvas + tokens in lockstep).
 *
 * NOTE: the export NAMES (`ACCENT_CORAL`, `coralFill`, …) are historical and
 * kept so the 12 importing files don't churn — they now carry the ION-BLUE
 * accent, mirroring the `amber-*` token rename. Read the role, not the name.
 */

// --- Graphite-ink surfaces (mirror charcoal-*) -----------------------------
export const CHART_SURFACE = "#121419"; // charcoal-900 — chart background
export const CHART_TEXT = "#cbd1dd"; // charcoal-200 — axis / label text
export const CHART_TEXT_MUTED = "#868d9c"; // charcoal-400 — secondary labels
export const CHART_GRID = "#21242c"; // charcoal-800 — gridlines
export const CHART_BORDER = "#2b2f39"; // charcoal-700 — scale borders
export const CHART_CROSSHAIR = "#3d424f"; // charcoal-600 — crosshair

// --- Ion-blue accent (mirror amber-* [ion blue]) ---------------------------
export const ACCENT_CORAL = "#4f86f7"; // amber-400 — brand / default accent
export const ACCENT_CORAL_BRIGHT = "#93b2fa"; // amber-300 — emphasis
export const ACCENT_CORAL_DEEP = "#2b53b0"; // amber-600 — deep accent / line

// --- Semantic signal colors (kept clear of the blue accent) ----------------
export const POSITIVE = "#38b25f"; // gains — cool green
export const POSITIVE_BRIGHT = "#56cc7c";
export const NEGATIVE = "#ef5369"; // losses — clear red (distinct from blue)
export const NEGATIVE_BRIGHT = "#ff6b80";
export const WARNING = "#e0a23c"; // caution — amber-gold

// --- Neutral data series (mirror sage-* → cool steel) ----------------------
export const NEUTRAL = "#8b94a3"; // sage-400 — comparison / secondary series
export const NEUTRAL_LIGHT = "#b6bdc8"; // sage-300

// --- RGB tuples for alpha fills (canvas wants rgba()) ----------------------
export const ACCENT_CORAL_RGB = "79, 134, 247";
export const POSITIVE_RGB = "56, 178, 95";
export const NEGATIVE_RGB = "239, 83, 105";

/** `rgba()` fill from the ion-blue accent at the given alpha (0–1). */
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
 * Distinct, on-brand indicator line palette — ion-blue lead, cool steel
 * neutrals, and a green. Order is chosen so the first few overlaid indicators
 * read clearly against the cold graphite surface.
 */
export const INDICATOR_PALETTE = [
  ACCENT_CORAL, // ion blue
  NEUTRAL, // cool steel
  POSITIVE, // green
  ACCENT_CORAL_BRIGHT, // ion-bright
  NEUTRAL_LIGHT, // light steel
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
