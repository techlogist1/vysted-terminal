/**
 * useTickFlash — the live-data "it moved" signal (Track 5).
 *
 * A finance terminal should flash when a number ticks. This hook tracks the
 * previous value and, on a change, returns a transient `"up"` / `"down"`
 * direction the caller paints as a brief green/red wash that fades. It is
 * reduced-motion aware: when the user prefers reduced motion it returns `null`
 * (no flash) — the sign COLOR on the value still carries the signal, only the
 * motion is suppressed.
 *
 * The flash auto-clears after {@link FLASH_MS}; the caller pairs it with a CSS
 * `transition-colors` so the wash fades out rather than snapping off.
 */

import { useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

import { FLASH_MS } from "@/lib/motion";

export type FlashDirection = "up" | "down" | null;

export function useTickFlash(value: number | null | undefined): FlashDirection {
  const reduce = useReducedMotion();
  const prev = useRef<number | null | undefined>(value);
  const [flash, setFlash] = useState<FlashDirection>(null);

  useEffect(() => {
    const before = prev.current;
    prev.current = value;
    if (value == null || before == null || value === before) {
      return;
    }
    if (reduce) {
      return; // sign colour still encodes the value; suppress the motion only
    }
    setFlash(value > before ? "up" : "down");
    const id = setTimeout(() => setFlash(null), FLASH_MS);
    return () => clearTimeout(id);
  }, [value, reduce]);

  return flash;
}
