/**
 * Shared motion tokens for the framer-motion animation layer. Mirrors the CSS
 * easing tokens in `styles/tokens.css` (`--ease-instrument`, `--ease-detent`)
 * so the JS motion system and the CSS transitions share one house feel — calm,
 * confident, no mechanical overshoot. Keep in lockstep with tokens.css.
 */
import type { Transition, Variants } from "framer-motion";

/** Calm confident ease (mirrors --ease-instrument). */
export const EASE_INSTRUMENT: [number, number, number, number] = [0.2, 0.8, 0.2, 1];
/** Detent ease for snappy settles (mirrors --ease-detent). */
export const EASE_DETENT: [number, number, number, number] = [0.32, 0.9, 0.5, 1];

/** Durations (seconds) — fast for micro-states, base for most, slow for reveals. */
export const DUR = { fast: 0.16, base: 0.22, slow: 0.28 } as const;

/** A house tween at the instrument easing. */
export const tween = (duration: number = DUR.base): Transition => ({
  duration,
  ease: EASE_INSTRUMENT,
});

/** A crisp spring for sliding indicators (the mode pill, highlights). */
export const SPRING_PILL: Transition = { type: "spring", stiffness: 520, damping: 40 };

/** Staggered-list reveal: a parent that cascades its children in, and the child
 *  variant (a small upward fade). Used for plan steps, data load-in, roster rows
 *  — anything that should resolve as an ordered cascade rather than a hard cut.
 *  Callers gate both on `useReducedMotion()` so the cascade collapses to an
 *  instant render when the user prefers reduced motion. */
export const staggerParent: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.04 } },
};

export const staggerChild: Variants = {
  hidden: { opacity: 0, y: 3 },
  show: { opacity: 1, y: 0, transition: { duration: DUR.fast, ease: EASE_INSTRUMENT } },
};
