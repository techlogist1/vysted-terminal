/**
 * Small, reusable data-trust badges (Pass-B polish, B6).
 *
 * Two token-driven, reduced-motion-safe chips that label a value's origin and
 * freshness so a user (or the copilot reading the surface) never mistakes a
 * cached / structured-only / synthetic read for a live one. They are generic
 * so any Pass-B surface can reuse them:
 *
 *  - {@link ProvenanceBadge} — WHERE the data came from (the provider label),
 *    with an optional `synthetic` flag that re-colours it as a caution.
 *  - {@link StalenessBadge} — HOW fresh it is: `live`, `stale`, `age unknown`, or
 *    an end-of-day `EOD as of <date>` readout derived from an epoch-ms timestamp.
 *
 * Both are pure presentational `<span>`s — no animation, no effects, no store
 * reads — so they are safe to drop anywhere and trivially testable. Colours come
 * from the design tokens (`--color-warning` is documented as "stale data"), so a
 * re-skin re-values them without touching this file.
 */

import { providerShortLabel } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Freshness } from "../../types/data";

/** Shared chip shell — keeps the two badges visually consistent. The label
 *  never mid-word clips (R8 §3.1): providers render their designed short form
 *  and the chip itself refuses to shrink below its content. */
const CHIP =
  "inline-flex shrink-0 items-center gap-1 rounded-control px-2 py-1 font-mono text-micro whitespace-nowrap";

/**
 * Provider-origin badge. Reads `<provider>` normally; a `synthetic` value is
 * re-coloured to the caution token and labelled so a placeholder is never
 * mistaken for a real read. `prefix` (e.g. a mode like `EOD`) is shown ahead of
 * the provider when supplied (`MODE · src`).
 */
export function ProvenanceBadge({
  provider,
  prefix,
  synthetic = false,
  className,
}: {
  /** The data source label (e.g. `rss`, `NewsAPI`, `sec.gov`). */
  provider: string;
  /** Optional leading qualifier (e.g. a mode), rendered as `prefix · provider`. */
  prefix?: string;
  /** When true, the value is a placeholder, not a real read — coloured as caution. */
  synthetic?: boolean;
  className?: string;
}) {
  const short = providerShortLabel(provider);
  // "synthetic" is always visible text, never colour alone, with or without a prefix.
  const body = synthetic ? "synthetic" : short;
  const label = prefix ? `${prefix} · ${body}` : body;
  return (
    <span
      data-testid="provenance-badge"
      className={cn(
        CHIP,
        synthetic ? "bg-charcoal-850 text-warning" : "bg-charcoal-800 text-charcoal-300",
        className,
      )}
      title={
        synthetic
          ? `Synthetic / placeholder value from ${provider} — not a live read`
          : `Source: ${provider}`
      }
    >
      {label}
    </span>
  );
}

/** Format an epoch-ms timestamp as a `YYYY-MM-DD` date in the viewer's LOCAL
 *  calendar (en-CA is the ISO shape) — a UTC date reads a day early between
 *  00:00 and 05:29 IST and disagrees with the local timestamps beside it. */
function asOfDate(epochMs: number): string {
  const d = new Date(epochMs);
  if (Number.isNaN(d.getTime())) {
    return "";
  }
  return d.toLocaleDateString("en-CA");
}

/**
 * Freshness badge: `live` (green), `stale` / `unknown` (caution — `unknown`
 * means the label could not be computed, so it never reads as live), or `eod`
 * which renders `EOD as of <date>` from `asOf` (epoch ms). A plain `live`/`stale` may also pass
 * `asOf` to surface the timestamp in the tooltip.
 */
export function StalenessBadge({
  freshness,
  asOf,
  className,
}: {
  freshness: Freshness;
  /** Epoch ms the value is as-of. Every `eod` caller passes it — a bare "EOD"
   *  with no date cannot be told apart from today's close. */
  asOf?: number;
  className?: string;
}) {
  const date = typeof asOf === "number" ? asOfDate(asOf) : "";
  const tone =
    freshness === "live"
      ? "bg-charcoal-850 text-positive"
      : freshness === "stale" || freshness === "unknown"
        ? "bg-charcoal-850 text-warning"
        : "bg-charcoal-800 text-charcoal-300";
  const text =
    freshness === "live"
      ? "live"
      : freshness === "stale"
        ? "stale"
        : freshness === "unknown"
          ? "age unknown"
          : date
            ? `EOD as of ${date}`
            : "EOD";
  return (
    <span
      data-testid="staleness-badge"
      className={cn(CHIP, tone, className)}
      title={date ? `As of ${date}` : text}
    >
      {text}
    </span>
  );
}
