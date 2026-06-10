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

/**
 * Resolve the display currency for a money formatter call (R8 §6 — "currency
 * formats by the INSTRUMENT's currency, never the locale default"). A caller
 * holding the instrument's quoted currency (Quote.currency / Fundamentals
 * .currency) passes it through; absent/blank input falls back to the region
 * default so legacy call sites are byte-identical.
 */
function resolveCurrency(currency?: string | null): string {
  const trimmed = currency?.trim().toUpperCase();
  return trimmed && /^[A-Z]{3}$/.test(trimmed) ? trimmed : activeCurrency();
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

/** Currency value with full cents precision. Non-finite -> "—". `currency` is
 *  the INSTRUMENT's ISO-4217 code (R8 §6 — no ₹ on AAPL); omitted → the region
 *  default (byte-identical to before for legacy call sites). */
export function formatMoney(value: number, currency?: string | null): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString(activeLocale(), {
    style: "currency",
    currency: resolveCurrency(currency),
    maximumFractionDigits: 2,
  });
}

/**
 * The active currency's symbol (e.g. `$`, `₹`), derived from Intl so the compact
 * path never hardcodes `$`. Extracts the part either side of the magnitude in a
 * formatted sample; falls back to the ISO code if the locale renders no symbol.
 */
function currencyAffix(currency?: string | null): { prefix: string; suffix: string } {
  const code = resolveCurrency(currency);
  const formatted = (1).toLocaleString(activeLocale(), {
    style: "currency",
    currency: code,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  });
  const digitAt = formatted.search(/\d/);
  if (digitAt === -1) {
    return { prefix: `${code} `, suffix: "" };
  }
  const lastDigitAt =
    formatted.length - 1 - [...formatted].reverse().findIndex((c) => /\d/.test(c));
  return {
    prefix: formatted.slice(0, digitAt).trimEnd(),
    suffix: formatted.slice(lastDigitAt + 1).trimStart(),
  };
}

/** Compact currency, abbreviated at >= 1M ($4.20T etc.); full cents below that.
 *  `currency` is the INSTRUMENT's ISO-4217 code (R8 §6); omitted → region
 *  default. Non-finite -> "—". US output is byte-identical (`$`-prefixed). */
export function formatCompactMoney(value: number, currency?: string | null): string {
  if (!Number.isFinite(value)) return "—";
  const abs = Math.abs(value);
  const abbr = abbreviate(abs);
  if (abbr !== null) {
    const { prefix, suffix } = currencyAffix(currency);
    return `${value < 0 ? "-" : ""}${prefix}${abbr}${suffix}`;
  }
  return formatMoney(value, currency);
}

/** Like {@link formatCompactMoney} but with an explicit leading "+" for positives. */
export function formatSignedMoney(
  value: number,
  compact = false,
  currency?: string | null,
): string {
  if (!Number.isFinite(value)) return "—";
  const formatted = compact ? formatCompactMoney(value, currency) : formatMoney(value, currency);
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

/**
 * Group the digits of an ARBITRARY-PRECISION numeric STRING with thousands
 * separators WITHOUT parsing to a (lossy) JS number — XBRL / SEC share counts and
 * dollar values overflow `Number.MAX_SAFE_INTEGER`, so they ride the wire as
 * strings and must never round-trip through `Number`. A non-numeric string passes
 * through unchanged; an empty string degrades to "—". This is the single
 * precision-safe string grouper (formerly the SEC table's local `formatBigInt`).
 */
export function groupDigits(raw: string | null | undefined): string {
  if (raw === null || raw === undefined) return "—";
  const trimmed = raw.trim();
  if (trimmed === "") return "—";
  if (!/^-?\d+(\.\d+)?$/.test(trimmed)) return trimmed;
  const negative = trimmed.startsWith("-");
  const unsigned = negative ? trimmed.slice(1) : trimmed;
  const [intPart, frac] = unsigned.split(".");
  const withCommas = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const grouped = frac ? `${withCommas}.${frac}` : withCommas;
  return negative ? `-${grouped}` : grouped;
}

/**
 * Designed short forms for data-provider labels (R8 overflow law §3.1 — a
 * meaningful label never mid-word truncates; it gets a designed short form AT
 * THE FORMATTER, not via CSS). The watchlist provenance chip used to clip
 * "yfinance" to "YFINAN" at narrow panel widths; these forms fit the micro
 * chip at every supported width. An unknown provider passes through unchanged
 * (the chip's tooltip always carries the full label).
 */
const PROVIDER_SHORT_LABELS: Record<string, string> = {
  yfinance: "YF",
  newsapi: "NewsAPI",
  alphavantage: "AV",
  alpha_vantage: "AV",
  coingecko: "CoinGecko",
  binance: "Binance",
  ccxt: "CCXT",
  "sec.gov": "SEC",
  sec_edgar: "SEC",
  econdb: "EconDB",
  fred: "FRED",
  nse: "NSE",
  bse: "BSE",
  kite: "Kite",
  upstox: "Upstox",
  dhan: "Dhan",
  rss: "RSS",
};

/** The designed short form for a provider id (case-insensitive); unknown ids
 *  pass through so a new provider is never silently mislabelled. Compound ids
 *  ("ccxt:binance") short-form each segment ("CCXT·Binance") so a raw internal
 *  id never reaches a chip. */
export function providerShortLabel(provider: string): string {
  const key = provider.trim().toLowerCase();
  const direct = PROVIDER_SHORT_LABELS[key];
  if (direct) {
    return direct;
  }
  if (key.includes(":")) {
    return key
      .split(":")
      .filter(Boolean)
      .map((part) => PROVIDER_SHORT_LABELS[part] ?? part)
      .join("·");
  }
  return provider;
}
