/**
 * Region / locale (default `IN` since R10 E1).
 *
 * Drives locale-aware number formatting AND, via the `X-Vysted-Region` header
 * sent on every sidecar request, the symbol resolver's market, the exchange
 * calendar that labels a quote live/stale, the macro provider, the news feed
 * and the screener universe (R15-DATA-092 — this is live, not a later-pass
 * seam). This module is PURE (no store import) so it can be read anywhere
 * without a cycle; the ACTIVE region lives in the settings bundle
 * (`store/settings`), read at the format seam (`lib/format`) and threaded
 * onto sidecar requests (`lib/sidecar-client`).
 *
 * Currency display still stays USD until a later pass adds FX conversion,
 * since the underlying market data is USD-denominated.
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

// R10 (E1): India-first default, mirroring the sidecar's `config._DEFAULT_REGION`
// — flip both in the same commit. User Settings still override.
export const DEFAULT_REGION: Region = "IN";

/** Type guard for restoring a persisted region (older/garbled blobs → default). */
export function isRegion(value: unknown): value is Region {
  return typeof value === "string" && REGIONS.some((r) => r.id === value);
}

/** Resolve a region id to its config, falling back to the actual default (India). */
export function regionConfig(region: Region): RegionConfig {
  return (
    REGIONS.find((r) => r.id === region) ??
    REGIONS.find((r) => r.id === DEFAULT_REGION) ??
    REGIONS[0]
  );
}
