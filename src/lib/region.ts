/**
 * Region / locale — the minimal foundation seam (Pass A item 8).
 *
 * A single region setting (default `US`) drives locale-aware formatting today and
 * is the registration point a later pass uses to make data + feeds region-first
 * (e.g. India-first quotes/news, INR + FX). This module is PURE (no store import)
 * so it can be read anywhere without a cycle; the ACTIVE region lives in the
 * settings bundle (`store/settings`), read at the format seam (`lib/format`).
 *
 * Pass B extends this WITHOUT a refactor: add a region row here, and read
 * `region` where a data-provider/feed adapter is chosen (see EXTENSION_SEAMS.md).
 * Deliberately small now — selecting a non-US region only changes number LOCALE
 * (grouping); currency stays USD until a later pass adds FX conversion, since the
 * underlying market data is USD-denominated.
 */

/** The supported regions. `IN` is present as the Pass-B target; `GLOBAL` is a
 *  neutral default for users who don't want a national locale. */
export type Region = "US" | "IN" | "GLOBAL";

export interface RegionConfig {
  id: Region;
  label: string;
  /** BCP-47 locale used by the shared formatters for number grouping. */
  locale: string;
  /** ISO-4217 display currency. NOT applied to USD-denominated values until a
   *  later pass adds FX conversion — carried here so the seam is complete. */
  currency: string;
}

export const REGIONS: readonly RegionConfig[] = [
  { id: "US", label: "United States", locale: "en-US", currency: "USD" },
  { id: "IN", label: "India", locale: "en-IN", currency: "INR" },
  { id: "GLOBAL", label: "Global", locale: "en-US", currency: "USD" },
];

export const DEFAULT_REGION: Region = "US";

/** Type guard for restoring a persisted region (older/garbled blobs → default). */
export function isRegion(value: unknown): value is Region {
  return typeof value === "string" && REGIONS.some((r) => r.id === value);
}

/** Resolve a region id to its config, falling back to the default (US). */
export function regionConfig(region: Region): RegionConfig {
  return REGIONS.find((r) => r.id === region) ?? REGIONS[0];
}
