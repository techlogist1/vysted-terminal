import { type ClassValue, clsx } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

/**
 * tailwind-merge, taught the R5 custom font-size utilities (`text-micro`,
 * `text-caption`, `text-body`, `text-panel-title`, `text-section`,
 * `text-overview`, `text-hero` — defined as @utility in styles/tokens.css).
 *
 * The stock (unconfigured) `twMerge` does NOT know these are font sizes, so it
 * classifies them as text-*colour* utilities and treats them as conflicting with
 * `text-charcoal-*`/`text-amber-*` — silently DROPPING the size whenever a size
 * and a colour are merged in one `cn(...)` call (e.g. `cn("text-body",
 * "text-charcoal-100")` rendered at the inherited size, not 13px). That quietly
 * defeated the type scale across the ~90 files that merge a size with a colour.
 *
 * Registering the seven utilities in the `font-size` group lets a size and a
 * colour coexist, while two competing SIZES still collapse to the last one.
 * Load-bearing for the whole design system — do not revert to bare `twMerge`.
 */
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        { text: ["micro", "caption", "body", "panel-title", "section", "overview", "hero"] },
      ],
    },
  },
});

/** Merge conditional class names, de-duplicating conflicting Tailwind utilities. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
