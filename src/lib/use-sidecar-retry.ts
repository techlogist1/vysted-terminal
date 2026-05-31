"use client";

/**
 * `useRetryOnSidecarReady` — cold-boot fetch resilience for fetch-once panels.
 *
 * Fetch-once data panels (Macro, SEC Filings, Earnings, Screener) call their
 * store's load action exactly once on mount. On a cold boot the Python sidecar
 * has a port assigned before it actually binds — the PyInstaller `_MEI` re-exec
 * plus the MCP-supervisor join can take tens of seconds — so a mount-time fetch
 * can fire into a dead socket, exhaust the shared `getSidecarBaseUrl` probe, and
 * latch a permanent error. News / Portfolio already self-heal with a bounded
 * backoff; this hook lifts the same resilience into a reusable shape.
 *
 * Two recovery mechanisms, belt-and-braces:
 *
 *   1. **Bounded backoff** (1s, 2s, 4s, capped 5s, ~12 attempts ≈ 50s) re-runs
 *      the load while the very first call races a sidecar that is *almost* up.
 *      The backoff disarms permanently once a load resolves.
 *   2. **Re-arm on reconnect** — subscribe to `useAppStore.sidecarStatus`; a
 *      fresh `connecting | error -> connected` transition re-runs the load (and
 *      re-arms the backoff) so a panel whose backoff already lapsed before the
 *      sidecar came up still recovers when the app-level health probe succeeds.
 *
 * `loadFn` MUST return a promise that rejects on failure (resolves on success)
 * so the hook can tell a recoverable failure from a settled load. The store
 * actions these panels use swallow their own errors into store state, so each
 * panel passes a thin wrapper that re-throws on the error status — see the call
 * sites. SSR-safe: all timers/subscriptions live inside effects.
 */

import { useEffect, useRef } from "react";

import { useAppStore, type SidecarStatus } from "@/store/app";

const MAX_ATTEMPTS = 12;
const MAX_BACKOFF_MS = 5000;

/**
 * Run `loadFn` on mount and auto-retry it until it succeeds, re-arming on a
 * fresh sidecar reconnect.
 *
 * @param loadFn   Async load to (re)run. Must reject on a recoverable failure.
 * @param deps     When these change the hook re-runs `loadFn` from a clean slate
 *                 (same contract as a `useEffect` dependency array). Pass the
 *                 panel's default-fetch inputs (e.g. the default symbol). Do NOT
 *                 pass user-driven inputs — those keep their own explicit loads.
 */
export function useRetryOnSidecarReady(
  loadFn: () => Promise<void>,
  deps: readonly unknown[],
): void {
  // Keep the latest `loadFn` in a ref so the retry timer and the status
  // subscription call the current closure without re-subscribing every render.
  // Assigned in an effect (never during render) per the rules-of-hooks ref
  // immutability rule — same shape as PortfolioPanel's `loadRef`.
  const loadRef = useRef(loadFn);
  useEffect(() => {
    loadRef.current = loadFn;
  }, [loadFn]);

  // True once a load has resolved for the current `deps` generation — disarms
  // both the backoff and the reconnect re-fire so a healthy panel never loops.
  const succeededRef = useRef(false);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    succeededRef.current = false;

    const attempt = (n: number) => {
      loadRef
        .current()
        .then(() => {
          if (!cancelled) {
            succeededRef.current = true;
          }
        })
        .catch(() => {
          if (cancelled || succeededRef.current) {
            return;
          }
          if (n < MAX_ATTEMPTS) {
            timer = setTimeout(() => attempt(n + 1), Math.min(1000 * 2 ** n, MAX_BACKOFF_MS));
          }
          // After the backoff lapses we stop here and wait for a reconnect
          // transition (below) to re-fire — no permanent error loop.
        });
    };
    attempt(0);

    // Re-arm on a fresh `-> connected` transition. The mount fetch may have
    // exhausted its backoff before the sidecar finished binding; the app-level
    // health probe flipping to "connected" is the signal that a retry will now
    // succeed. We only re-fire on the *edge* into "connected" (not on the
    // initial "connecting" the panel mounts under) and only while this panel
    // has not already loaded successfully.
    let prevStatus: SidecarStatus = useAppStore.getState().sidecarStatus;
    const unsubscribe = useAppStore.subscribe((state) => {
      const next = state.sidecarStatus;
      if (
        next === "connected" &&
        prevStatus !== "connected" &&
        !succeededRef.current &&
        !cancelled
      ) {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
        attempt(0);
      }
      prevStatus = next;
    });

    return () => {
      cancelled = true;
      if (timer) {
        clearTimeout(timer);
        timer = null;
      }
      unsubscribe();
    };
    // `loadFn` is intentionally read through the ref; the caller-supplied `deps`
    // are the real reset trigger.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
