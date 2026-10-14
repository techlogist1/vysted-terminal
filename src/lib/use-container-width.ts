"use client";

/**
 * useContainerWidth — the R8 overflow-law measurement seam (§3.2/§3.4).
 *
 * Dense rows (watchlist, portfolio, chart toolbar) declare their collapse order
 * as width-based steps; this hook supplies the measured width those steps key
 * off. A `ResizeObserver` on the attached element reports its border-box width;
 * `null` until the first measurement (callers treat null as "wide" so SSR /
 * first paint renders the full layout and collapses on the next frame, never
 * the reverse flash).
 */

import { useCallback, useEffect, useRef, useState } from "react";

export function useContainerWidth<T extends HTMLElement>(): {
  ref: (node: T | null) => void;
  width: number | null;
} {
  const [width, setWidth] = useState<number | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);

  const ref = useCallback((node: T | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;
    if (node === null) {
      return;
    }
    if (typeof ResizeObserver === "undefined") {
      // Older webview / jsdom without RO: report once from the layout box.
      setWidth(node.getBoundingClientRect().width || null);
      return;
    }
    const observer = new ResizeObserver((entries) => {
      const entry = entries[entries.length - 1];
      if (!entry) {
        return;
      }
      const next = entry.borderBoxSize?.[0]?.inlineSize ?? entry.contentRect.width;
      // Integer-snap so sub-pixel resize chatter never re-renders the table.
      setWidth((prev) => {
        const snapped = Math.round(next);
        return prev === snapped ? prev : snapped;
      });
    });
    observer.observe(node);
    observerRef.current = observer;
  }, []);

  useEffect(() => {
    return () => {
      observerRef.current?.disconnect();
      observerRef.current = null;
    };
  }, []);

  return { ref, width };
}
