/**
 * Shared numeric / currency / percent formatters for the terminal.
 *
 * Finance-terminal conventions: abbreviate large magnitudes (M/B/T/Q), keep
 * full precision for small values, and degrade non-finite inputs (NaN /
 * ±Infinity, which division-by-near-zero can produce) to an em-dash instead of
 * rendering "NaN" / "$Infinity" or overflowing a table row. Phase 9.5 F-GUI-1
 * surfaced an aggregate that rendered "$621,700,012,207,018,900.00" and
 * "+2855345159126.89%"; compact formatting prevents that class of overflow.
 */

import { regionConfig } from "@/lib/region";
import { useSettingsStore } from "@/store/settings";

const MONEY_UNITS: readonly { value: number; suffix: string }[] = [
  { value: 1e15, suffix: "Q" },
  { value: 1e12, suffix: "T" },
  { value: 1e9, suffix: "B" },
  { value: 1e6, suffix: "M" },
];

/**
 * Region/locale read seam (Pass A item 8). The active region's BCP-47 locale
 * drives number grouping; default `US` → `en-US` (identical to before). A later
 * pass extends region into currency/FX + region-first data — this is where the
 * locale is consumed. Read at call time so a region change reflects immediately.
 */
function activeLocale(): string {
  return regionConfig(useSettingsStore.getState().region).locale;
}

/** Abbreviate a magnitude >= 1e6 to a ~3-significant-digit unit string, else null. */
function abbreviate(abs: number): string | null {
  for (const { value, suffix } of MONEY_UNITS) {
    if (abs >= value) {
      const m = abs / value;
      const mantissa = m >= 100 ? m.toFixed(0) : m >= 10 ? m.toFixed(1) : m.toFixed(2);
      return `${mantissa}${suffix}`;
    }
  }
  return null;
}

/** USD with full cents precision. Non-finite -> "—". */
export function formatMoney(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString(activeLocale(), {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

/** USD, abbreviated at >= $1M ($621.7Q etc.); full cents below that. Non-finite -> "—". */
export function formatCompactMoney(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const abbr = abbreviate(abs);
  if (abbr !== null) return `${value < 0 ? "-" : ""}$${abbr}`;
  return formatMoney(value);
}

/** Like {@link formatCompactMoney} but with an explicit leading "+" for positives. */
export function formatSignedMoney(value: number, compact = false): string {
  if (!Number.isFinite(value)) return "—";
  const formatted = compact ? formatCompactMoney(value) : formatMoney(value);
  return value > 0 ? `+${formatted}` : formatted;
}

/**
 * Signed percentage with a leading "+" for positives. Absurd magnitudes
 * (|v| >= 1e5 %) fall back to exponential notation so a degenerate ratio cannot
 * overflow a row (e.g. "+2.86e12%" instead of "+2855345159126.89%"). "—" for
 * non-finite. The input is already a percentage (33.33 means 33.33%).
 */
export function formatPercent(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  if (Math.abs(value) >= 1e5) return `${sign}${value.toExponential(2)}%`;
  return `${sign}${value.toFixed(2)}%`;
}

/** Plain number, abbreviated at >= 1e6 (1.2M etc.); locale-grouped below. Non-finite -> "—". */
export function formatCompactNumber(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const abbr = abbreviate(abs);
  if (abbr !== null) return `${value < 0 ? "-" : ""}${abbr}`;
  return value.toLocaleString(activeLocale(), { maximumFractionDigits: 2 });
}
