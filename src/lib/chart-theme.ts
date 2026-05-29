/**
 * Canvas palette — the single source of truth for every `lightweight-charts`
 * surface and drawing primitive.
 *
 * Canvas elements render to a `<canvas>` bitmap and CANNOT read CSS custom
 * properties, so each chart/drawing file used to hard-code its own copy of the
 * palette — which is exactly how three values silently drifted off-palette
 * (`#e8b441`, `#c39a3e`, and a forbidden cold cyan `#4ec9a3`). This module
 * mirrors `styles/tokens.css` ("Claude after dark") once; when a token changes,
 * update both the CSS token AND its constant here — but only here, not in 12
 * files. Hex values intentionally match the `tokens.css` espresso/coral palette.
 */

// --- Espresso surfaces (mirror charcoal-*) ---------------------------------
export const CHART_SURFACE = "#241d19"; // charcoal-900 — chart background
export const CHART_TEXT = "#d6c8bb"; // charcoal-200 — axis / label text
export const CHART_TEXT_MUTED = "#998778"; // charcoal-400 — secondary labels
export const CHART_GRID = "#352a25"; // charcoal-800 — gridlines
export const CHART_BORDER = "#473a33"; // charcoal-700 — scale borders
export const CHART_CROSSHAIR = "#5c4d44"; // charcoal-600 — crosshair

// --- Coral accent (mirror amber-* [coral]) ---------------------------------
export const ACCENT_CORAL = "#d97757"; // amber-400 — brand / default accent
export const ACCENT_CORAL_BRIGHT = "#e69e84"; // amber-300 — emphasis
export const ACCENT_CORAL_DEEP = "#a44a30"; // amber-600 — deep accent / line

// --- Semantic signal colors ------------------------------------------------
export const POSITIVE = "#7fa96a"; // gains — warm moss green
export const POSITIVE_BRIGHT = "#9fc97f";
export const NEGATIVE = "#cf5b48"; // losses — brick red (distinct from coral)
export const NEGATIVE_BRIGHT = "#e3705a";
export const WARNING = "#e0a458"; // caution — amber-gold

// --- Neutral data series (mirror sage-* → muted clay) ----------------------
export const NEUTRAL = "#a8917f"; // sage-400 — comparison / secondary series
export const NEUTRAL_LIGHT = "#c9b9ad"; // sage-300

// --- RGB tuples for alpha fills (canvas wants rgba()) ----------------------
export const ACCENT_CORAL_RGB = "217, 119, 87";
export const POSITIVE_RGB = "127, 169, 106";
export const NEGATIVE_RGB = "207, 91, 72";

/** `rgba()` fill from the coral accent at the given alpha (0–1). */
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
 * Distinct, on-brand indicator line palette — coral lead, warm neutrals, and a
 * moss green. No cold hues (the retired cyan drift is gone). Order is chosen so
 * the first few overlaid indicators read clearly against the espresso surface.
 */
export const INDICATOR_PALETTE = [
  ACCENT_CORAL, // coral
  NEUTRAL, // muted clay
  POSITIVE, // moss green
  ACCENT_CORAL_BRIGHT, // coral-bright
  NEUTRAL_LIGHT, // light neutral
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
