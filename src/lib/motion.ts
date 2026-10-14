/**
 * Shared motion tokens for the framer-motion animation layer. R4 "Cold
 * Instrument" unified motion vocabulary -- mirrors the CSS duration/easing
 * tokens in `styles/tokens.css` so the JS motion system and the CSS
 * transitions share one house feel. Keep in lockstep with tokens.css.
 *
 * Duration tiers (doc sec5):
 *   120ms micro    -- hover, toggle, button press, color flip, value-flash
 *   180ms default  -- dropdown, popover, tab switch, selection, palette open
 *   240ms entrance -- panel mount, modal/sheet, sidebar slide
 *   160ms exit     -- exits ~30% faster than entrances
 */
import type { Transition, Variants } from "framer-motion";

/** Enter easing -- decelerate, settle (mirrors --ease-enter / --ease-instrument). */
export const EASE_INSTRUMENT: [number, number, number, number] = [0.2, 0, 0, 1];
/** Shared easing -- elements that start and end on screen (mirrors --ease-shared). */
export const EASE_DETENT: [number, number, number, number] = [0.4, 0, 0.2, 1];
/** Exit easing -- accelerate away (mirrors --ease-exit). */
export const EASE_EXIT: [number, number, number, number] = [0.4, 0, 1, 1];

/**
 * Duration tiers in seconds -- unified with CSS --duration-* tokens.
 * fast  = micro (120ms) -- hover flips, color transitions, active flash
 * base  = default (180ms) -- dropdown, tab switch, selection
 * slow  = entrance (240ms) -- panel mount, modal/sheet, sidebar slide
 */
export const DUR = { fast: 0.12, base: 0.18, slow: 0.24 } as const;

/** Exit duration (~30% faster than entrance): 0.24 * 0.67 ~= 0.16 */
export const DUR_EXIT = 0.16;

/**
 * How long a price tick-flash stays lit before fading (ms). The fade itself
 * rides a CSS `transition-colors` of the same duration. 120ms = micro tier.
 */
export const FLASH_MS = 120;

/** Per-item delay (seconds) for a staggered list reveal (data landing).
 *  30-50ms/item, capped at 8 items (doc sec5). */
export const STAGGER = 0.04;

/** A house tween at the instrument (enter) easing. */
export const tween = (duration: number = DUR.base): Transition => ({
  duration,
  ease: EASE_INSTRUMENT,
});

/** A house tween for exit animations -- faster with exit easing. */
export const tweenExit = (duration: number = DUR_EXIT): Transition => ({
  duration,
  ease: EASE_EXIT,
});

/** A crisp spring for sliding indicators (the mode pill, highlights). */
export const SPRING_PILL: Transition = { type: "spring", stiffness: 520, damping: 40 };

/**
 * Staggered-list reveal: a parent that cascades its children in, and the child
 * variant (a small upward fade). Used for plan steps, data load-in, roster rows
 * -- anything that should resolve as an ordered cascade rather than a hard cut.
 * Callers gate both on `useReducedMotion()` so the cascade collapses to an
 * instant render when the user prefers reduced motion.
 * Stagger capped at 8 items (doc sec5).
 */
export const staggerParent: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: STAGGER } },
};

export const staggerChild: Variants = {
  hidden: { opacity: 0, y: 3 },
  show: { opacity: 1, y: 0, transition: { duration: DUR.fast, ease: EASE_INSTRUMENT } },
};
