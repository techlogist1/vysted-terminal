/**
 * Tradesa V2 wrapper — shared panel UI utilities.
 *
 * Pure helpers used across every panel: relative-time formatting,
 * currency formatting, percentage formatting, and a small `useInterval`
 * helper that mirrors the canonical mount-then-interval pattern (clear
 * on unmount, no `setInterval` leak).
 *
 * No data-fetching here — all fetching lives in the per-panel components
 * which call `useTradesaStore` refresh actions on the cadence enumerated
 * in `../store.ts::POLL_CADENCE_MS`.
 */

import { useEffect, useRef } from "react";

import type { TradesaConnectionStatus } from "../../../types/tradesa_v2";

// ---------------------------------------------------------------------------
// Time helpers
// ---------------------------------------------------------------------------

/**
 * Format a duration in seconds as a compact relative-time label, e.g.
 * "12s ago", "3m ago", "1h ago", "2d ago". Returns "just now" for
 * sub-second values and falls back to "—" for null/undefined.
 */
export function formatRelativeSeconds(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return "—";
  const s = Math.max(0, Math.round(seconds));
  if (s < 1) return "just now";
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  return `${d}d ago`;
}

/**
 * Format an ISO-8601 timestamp string as a relative-time label using
 * `formatRelativeSeconds`. Returns "—" for null/undefined/unparseable.
 */
export function formatRelativeIso(
  iso: string | null | undefined,
  now: number = Date.now(),
): string {
  if (!iso) return "—";
  const ms = Date.parse(iso);
  if (!Number.isFinite(ms)) return "—";
  return formatRelativeSeconds((now - ms) / 1000);
}

/**
 * Format a positive uptime in seconds as "Nd Nh Nm" (compact).
 * Returns "—" for null/undefined/negative.
 */
export function formatUptime(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds) || seconds < 0) {
    return "—";
  }
  const totalMin = Math.floor(seconds / 60);
  const d = Math.floor(totalMin / (60 * 24));
  const h = Math.floor((totalMin % (60 * 24)) / 60);
  const m = totalMin % 60;
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

/**
 * Format a duration between two ISO timestamps as a compact label, e.g.
 * "2h 13m", "5m 12s", "12s". Returns "—" if either is null/unparseable.
 */
export function formatDuration(
  startIso: string | null | undefined,
  endIso: string | null | undefined,
): string {
  if (!startIso || !endIso) return "—";
  const start = Date.parse(startIso);
  const end = Date.parse(endIso);
  if (!Number.isFinite(start) || !Number.isFinite(end) || end < start) return "—";
  const sec = Math.round((end - start) / 1000);
  if (sec < 60) return `${sec}s`;
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m < 60) return s > 0 ? `${m}m ${s}s` : `${m}m`;
  const h = Math.floor(m / 60);
  const mr = m % 60;
  return mr > 0 ? `${h}h ${mr}m` : `${h}h`;
}

// ---------------------------------------------------------------------------
// Number helpers
// ---------------------------------------------------------------------------

/** Format a USD value with 2 decimal places + thousands separators. */
export function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  return `${sign}$${abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/**
 * Format a number with up to N significant decimals. Strips trailing
 * zeros so a price like 30000.0 renders as "30,000".
 */
export function formatNumber(value: number | null | undefined, decimals = 4): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const fixed = value.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  });
  return fixed;
}

/** Format a [0, 1] ratio as an integer percentage, e.g. "73%". */
export function formatPercent(ratio: number | null | undefined): string {
  if (ratio === null || ratio === undefined || !Number.isFinite(ratio)) return "—";
  return `${Math.round(ratio * 100)}%`;
}

// ---------------------------------------------------------------------------
// Status tone → Tailwind classes
// ---------------------------------------------------------------------------

const TONE_CLASS: Record<"ok" | "warn" | "error" | "muted", string> = {
  ok: "text-emerald-300 bg-emerald-950/40 border-emerald-800/60",
  warn: "text-amber-300 bg-amber-950/40 border-amber-800/60",
  error: "text-red-300 bg-red-950/40 border-red-800/60",
  muted: "text-zinc-400 bg-zinc-900/40 border-zinc-800",
};

export function toneClasses(tone: "ok" | "warn" | "error" | "muted"): string {
  return TONE_CLASS[tone];
}

// ---------------------------------------------------------------------------
// Status guards (every panel uses the same branching)
// ---------------------------------------------------------------------------

/** True when the panel should render its populated body (data trustworthy). */
export function isPopulated(status: TradesaConnectionStatus): boolean {
  return status === "healthy" || status === "partial" || status === "bot-offline";
}

/** True when the panel should render the skeleton-loader UX. */
export function isLoadingState(status: TradesaConnectionStatus): boolean {
  return status === "connecting";
}

// ---------------------------------------------------------------------------
// useInterval — mount + cadence + clear-on-unmount
// ---------------------------------------------------------------------------

/**
 * Run `callback` once on mount, then every `intervalMs` while the
 * component is mounted. Clears the interval on unmount.
 *
 * The callback may be async (return type `unknown`) — return value is
 * discarded; the helper does NOT await between iterations.
 *
 * Pass `null` for `intervalMs` to skip scheduling (still fires once on
 * mount). Pass `false` for `immediate` to suppress the on-mount call.
 */
export function useInterval(
  callback: () => unknown,
  intervalMs: number | null,
  immediate = true,
): void {
  const cbRef = useRef(callback);
  useEffect(() => {
    cbRef.current = callback;
  }, [callback]);

  useEffect(() => {
    if (immediate) {
      try {
        cbRef.current();
      } catch {
        /* swallow — refresh actions are responsible for their own error capture */
      }
    }
    if (intervalMs === null || intervalMs <= 0) return;
    const handle = window.setInterval(() => {
      try {
        cbRef.current();
      } catch {
        /* swallow */
      }
    }, intervalMs);
    return () => window.clearInterval(handle);
  }, [intervalMs, immediate]);
}
