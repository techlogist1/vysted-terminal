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

/** The active region's ISO-4217 display currency (US → `USD`, byte-identical to
 *  before). Read at call time so a region change reflects immediately. */
function activeCurrency(): string {
  return regionConfig(useSettingsStore.getState().region).currency;
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

/** Active-currency value with full cents precision. Non-finite -> "—".
 *  (US → USD, byte-identical to before.) */
export function formatMoney(value: number): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString(activeLocale(), {
    style: "currency",
    currency: activeCurrency(),
    maximumFractionDigits: 2,
  });
}

/**
 * The active currency's symbol (e.g. `$`, `₹`), derived from Intl so the compact
 * path never hardcodes `$`. Extracts the part either side of the magnitude in a
 * formatted sample; falls back to the ISO code if the locale renders no symbol.
 */
function currencyAffix(): { prefix: string; suffix: string } {
  const formatted = (1).toLocaleString(activeLocale(), {
    style: "currency",
    currency: activeCurrency(),
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  const digitAt = formatted.search(/\d/);
  if (digitAt === -1) {
    return { prefix: `${activeCurrency()} `, suffix: "" };
  }
  const lastDigitAt =
    formatted.length - 1 - [...formatted].reverse().findIndex((c) => /\d/.test(c));
  return {
    prefix: formatted.slice(0, digitAt).trimEnd(),
    suffix: formatted.slice(lastDigitAt + 1).trimStart(),
  };
}

/** Active currency, abbreviated at >= 1M (₹621.7Q etc.); full cents below that.
 *  Non-finite -> "—". US output is byte-identical (`$`-prefixed). */
export function formatCompactMoney(value: number): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const abbr = abbreviate(abs);
  if (abbr !== null) {
    const { prefix, suffix } = currencyAffix();
    return `${value < 0 ? "-" : ""}${prefix}${abbr}${suffix}`;
  }
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

/**
 * A bare price / ratio readout (no currency symbol). Sub-unit magnitudes keep
 * significant digits so a micro-cap crypto at 0.000021 doesn't collapse to
 * "0.00"; values >= 1 render at `dp` decimals (default 2). Non-finite -> "—".
 * This is the single price formatter — the watchlist's old local `formatPrice`
 * (sig-digit small / 2dp large) folds into it byte-identically.
 */
export function formatPrice(value: number, dp = 2): string {
  if (!Number.isFinite(value)) return "—";
  if (value !== 0 && Math.abs(value) < 1) {
    return value.toLocaleString(activeLocale(), { maximumSignificantDigits: 6 });
  }
  return value.toLocaleString(activeLocale(), {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  });
}

/** Unit tiers for {@link formatUnit} — extends {@link MONEY_UNITS} down to the K
 *  tier so counts / volumes always carry a suffix. */
const UNIT_TIERS: readonly { value: number; suffix: string }[] = [
  { value: 1e15, suffix: "Q" },
  { value: 1e12, suffix: "T" },
  { value: 1e9, suffix: "B" },
  { value: 1e6, suffix: "M" },
  { value: 1e3, suffix: "K" },
];

/**
 * A magnitude with a K/M/B/T/Q suffix and NO currency symbol — the single
 * formatter for share counts, volumes, and any large unsuffixed count that must
 * never render as a bare overflow ("Shares out. 14.698" → "14.70B"). Abbreviates
 * at >= 1e3 (K) and up; below 1K it locale-groups at `dp` decimals. `dp` controls
 * the abbreviated-mantissa precision (default 2), dropping to 0 once the mantissa
 * reads >= 100 so a unit never shows four significant figures. Non-finite -> "—".
 *
 * Differs from {@link formatCompactNumber} only by abbreviating the K tier too,
 * so the share-count / volume class always reads with a unit.
 */
export function formatUnit(value: number, dp = 2): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";
  for (const { value: threshold, suffix } of UNIT_TIERS) {
    if (abs >= threshold) {
      const m = abs / threshold;
      const digits = m >= 100 ? 0 : dp;
      return `${sign}${m.toFixed(digits)}${suffix}`;
    }
  }
  return `${sign}${abs.toLocaleString(activeLocale(), { maximumFractionDigits: dp })}`;
}
