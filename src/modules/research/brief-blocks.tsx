"use client";

/**
 * Typed-block brief renderer (Sprint-3 Track 1 + 2 — "show, don't tell").
 *
 * The research brief is rendered as a sequence of TYPED BLOCKS by native React
 * components, never as a wall of raw markdown. The block array is DERIVED
 * deterministically on the frontend from the brief the pipeline already ships
 * (`markdown` + the provenance-tagged `structured` bundle + `sources`) — so the
 * rich view is robust on every model (it never depends on a weak LLM emitting a
 * perfect typed-block JSON) and works on older persisted briefs too.
 *
 * Two producers feed the document body:
 *   - `deriveMetrics(structured)` → a native metric-card grid (price/P-E/market
 *     cap/…), color-coded green/red, sourced ONLY from real numbers — an absent
 *     or failed leg renders nothing, never a fabricated value (Constitution VI).
 *   - `parseBodyBlocks(markdown)` → heading / paragraph / list / TABLE blocks
 *     (the table parse kills the "unreadable wall of pipes" the chat used to dump).
 *
 * Every ticker in the document is a LIVE chip (Track 2): clicking it drives the
 * existing chart panel via `loadSymbolIntoChart` (the always-consumed
 * chart-command channel — fit-aware, never spawns a panel per click). The
 * `[n]` citation markers stay interactive (scroll-to-source).
 *
 * Visual constitution (dark, minimal, Cursor-grade): three contrast tiers via
 * weight/opacity, tabular/mono numerals, 1px hairline borders + elevation steps
 * for hierarchy (NO gradients / shadows / blur / glow), exactly one accent
 * (amber) + the green/red signal reserved for data direction. Entrance stagger
 * is reduced-motion aware.
 */

import { Fragment, useMemo, type ReactNode } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";

import { ProvenanceBadge, StalenessBadge, type Freshness } from "@/components/DataBadges";
import {
  dedupeSources,
  deriveAssetClass,
  sanitizeCitationMarkers,
  type BriefAssetClass,
} from "@/lib/brief-ingest";
import { loadSymbolIntoChart } from "@/lib/host-actions";
import { staggerChild, staggerParent } from "@/lib/motion";
import { useSymbolsStore } from "@/store/symbols";
import type { BriefStructured, ResearchBriefData } from "../../../types/brief";
import type { Fundamentals, Quote } from "../../../types/data";

// --- formatters (mirror EquityOverviewPanel's battle-tested conventions) -----

function formatNumber(value: number | null | undefined, fractionDigits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  });
}

/** Compact large magnitudes (market cap, volume): 4.48T / 182.3B / 9.4M. */
function formatLarge(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  const abs = Math.abs(value);
  if (abs >= 1e12) return `${(value / 1e12).toFixed(2)}T`;
  if (abs >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(value / 1e3).toFixed(1)}K`;
  return formatNumber(value, 0);
}

/** A fraction (yfinance dividend_yield = 0.0044) → "0.44%". */
function formatFractionPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${(value * 100).toFixed(2)}%`;
}

/** An already-percent value (Quote.change_percent = 1.36 → "+1.36%"). */
function formatSignedPct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function formatSigned(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${value >= 0 ? "+" : ""}${formatNumber(value)}`;
}

// --- metric derivation -------------------------------------------------------

interface MetricItem {
  label: string;
  value: string;
}

interface MetricsModel {
  symbol?: string;
  provider?: string;
  freshness?: Freshness;
  price?: number;
  change?: number;
  changePercent?: number;
  currency?: string;
  /** The metric family the card set was branched on (equity / crypto / etf / fx). */
  assetClass: BriefAssetClass;
  items: MetricItem[];
}

function isLeg(
  value: unknown,
): value is { ok?: boolean; provider?: string | null; data?: unknown } {
  return typeof value === "object" && value !== null;
}

/** A `(label,value)` collector that drops any "—" value so an absent field
 *  renders NO card rather than a fabricated one (Constitution VI). */
function makeItems(): { items: MetricItem[]; push: (label: string, value: string) => void } {
  const items: MetricItem[] = [];
  const push = (label: string, value: string) => {
    if (value !== "—") {
      items.push({ label, value });
    }
  };
  return { items, push };
}

/** The 52-week range card, shared across classes (renders only when both ends
 *  are real numbers). */
function pushRange(
  push: (label: string, value: string) => void,
  fund: Fundamentals | undefined,
): void {
  const lo = fund?.fifty_two_week_low;
  const hi = fund?.fifty_two_week_high;
  if (typeof lo === "number" && typeof hi === "number") {
    push("52w range", `${formatNumber(lo, 0)}–${formatNumber(hi, 0)}`);
  }
}

/** Equity / single-name metric set — the full valuation + quality + growth grid. */
function equityItems(fund: Fundamentals | undefined, quote: Quote | undefined): MetricItem[] {
  const { items, push } = makeItems();
  if (fund) {
    push("Market cap", formatLarge(fund.market_cap));
    push("P/E", formatNumber(fund.pe_ratio));
    push("Fwd P/E", formatNumber(fund.forward_pe));
    push("PEG", formatNumber(fund.peg_ratio));
    push("Price/Book", formatNumber(fund.price_to_book));
    // yfinance's dividend_yield unit is historically unreliable (CURRENT_STATE
    // §3.3) — guard the unit-error blow-up (an equity yield ≥ 25% is almost
    // certainly mis-scaled) rather than show a wrong number on a trust surface.
    if (typeof fund.dividend_yield === "number" && fund.dividend_yield * 100 < 25) {
      push("Div yield", formatFractionPct(fund.dividend_yield));
    }
    push("EPS", formatNumber(fund.eps));
    push("Beta", formatNumber(fund.beta));
    push("ROE", formatFractionPct(fund.roe));
    push("Net margin", formatFractionPct(fund.profit_margin));
    push("Debt/Equity", formatNumber(fund.debt_to_equity));
    push("Rev growth", formatFractionPct(fund.revenue_growth));
    push("Revenue", formatLarge(fund.revenue_ttm));
    pushRange(push, fund);
  }
  if (quote && typeof quote.volume === "number") {
    push("Volume", formatLarge(quote.volume));
  }
  return items;
}

/** Crypto metric set — no earnings/valuation ratios (meaningless for a coin);
 *  lead on market cap, 24h volume, range, and beta when present. */
function cryptoItems(fund: Fundamentals | undefined, quote: Quote | undefined): MetricItem[] {
  const { items, push } = makeItems();
  if (fund) {
    push("Market cap", formatLarge(fund.market_cap));
  }
  if (quote && typeof quote.volume === "number") {
    push("24h volume", formatLarge(quote.volume));
  }
  if (fund) {
    pushRange(push, fund);
    push("Beta", formatNumber(fund.beta));
  }
  return items;
}

/** ETF / fund metric set — AUM (market cap), expense proxy via yield, beta,
 *  range, volume; no single-company quality ratios. */
function etfItems(fund: Fundamentals | undefined, quote: Quote | undefined): MetricItem[] {
  const { items, push } = makeItems();
  if (fund) {
    push("Net assets", formatLarge(fund.market_cap));
    if (typeof fund.dividend_yield === "number" && fund.dividend_yield * 100 < 25) {
      push("Yield", formatFractionPct(fund.dividend_yield));
    }
    push("Beta", formatNumber(fund.beta));
    push("P/E", formatNumber(fund.pe_ratio));
    pushRange(push, fund);
  }
  if (quote && typeof quote.volume === "number") {
    push("Volume", formatLarge(quote.volume));
  }
  return items;
}

/** FX metric set — a currency pair has no fundamentals; price action + range. */
function fxItems(fund: Fundamentals | undefined, quote: Quote | undefined): MetricItem[] {
  const { items, push } = makeItems();
  if (fund) {
    pushRange(push, fund);
    push("Beta", formatNumber(fund.beta));
  }
  if (quote && typeof quote.volume === "number") {
    push("Volume", formatLarge(quote.volume));
  }
  return items;
}

/**
 * Build a metric model from the structured bundle. Returns `null` when there is
 * no usable price OR fundamentals leg — the brief then renders prose-only (no
 * empty/fake card). The metric SET branches on the resolved instrument's asset
 * class (equity / crypto / etf / fx) so a coin never shows a meaningless P/E and
 * a pair never shows a non-existent market cap. Reads each numeric field
 * defensively (most are nullable); an absent field renders no card, never a
 * fabricated value (Constitution VI).
 */
export function deriveMetrics(structured: BriefStructured | undefined): MetricsModel | null {
  if (!structured) {
    return null;
  }
  const priceLeg = isLeg(structured.price) && structured.price.ok ? structured.price : null;
  const fundLeg =
    isLeg(structured.fundamentals) && structured.fundamentals.ok ? structured.fundamentals : null;
  const quote = (priceLeg?.data ?? undefined) as Quote | undefined;
  const fund = (fundLeg?.data ?? undefined) as Fundamentals | undefined;
  if (!quote && !fund) {
    return null;
  }

  const assetClass = deriveAssetClass(structured);
  const items =
    assetClass === "crypto"
      ? cryptoItems(fund, quote)
      : assetClass === "etf"
        ? etfItems(fund, quote)
        : assetClass === "fx"
          ? fxItems(fund, quote)
          : equityItems(fund, quote);

  const freshness: Freshness | undefined =
    quote?.freshness === "live" || quote?.freshness === "stale" || quote?.freshness === "eod"
      ? quote.freshness
      : undefined;

  return {
    symbol: quote?.symbol ?? fund?.symbol,
    provider: priceLeg?.provider ?? fundLeg?.provider ?? quote?.provider ?? fund?.provider,
    freshness,
    price: typeof quote?.price === "number" ? quote.price : undefined,
    change: typeof quote?.change === "number" ? quote.change : undefined,
    changePercent: typeof quote?.change_percent === "number" ? quote.change_percent : undefined,
    currency: quote?.currency,
    assetClass,
    items,
  };
}

// --- markdown → typed body blocks --------------------------------------------

type Align = "left" | "right" | "center";

type BodyBlock =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "table"; headers: string[]; aligns: Align[]; rows: string[][] }
  | { kind: "code"; lang: string; text: string };

/** Split a markdown table row "| a | b |" into trimmed cells. */
function splitRow(line: string): string[] {
  let s = line.trim();
  if (s.startsWith("|")) s = s.slice(1);
  if (s.endsWith("|")) s = s.slice(0, -1);
  return s.split("|").map((c) => c.trim());
}

/** A "|---|:--:|--:|" separator row marks the line above as a table header. */
function isTableSeparator(line: string): boolean {
  const t = line.trim();
  if (!t.includes("-") || !t.includes("|")) {
    return false;
  }
  return splitRow(t).every((cell) => /^:?-{1,}:?$/.test(cell.replace(/\s/g, "")));
}

function alignOf(sep: string): Align {
  const s = sep.replace(/\s/g, "");
  const left = s.startsWith(":");
  const right = s.endsWith(":");
  if (left && right) return "center";
  if (right) return "right";
  return "left";
}

/**
 * Parse a markdown body into typed blocks: heading / paragraph / list / table.
 * A superset of the prior inline-markdown renderer (adds GFM pipe tables), so
 * it never loses content — an unrecognised line becomes a paragraph.
 */
export function parseBodyBlocks(source: string): BodyBlock[] {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const out: BodyBlock[] = [];
  let list: { ordered: boolean; items: string[] } | null = null;

  const flushList = () => {
    if (list) {
      out.push({ kind: "list", ordered: list.ordered, items: list.items });
      list = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trimEnd();

    // Fenced code block: a "```"/"~~~" opener buffers raw lines (no inline
    // parse) until the matching close fence; the info string after the opener
    // is the language hint (may be empty). Checked first so a pipe inside code
    // can't be mistaken for a table row.
    const fence = /^ {0,3}(```+|~~~+)(.*)$/.exec(line);
    if (fence) {
      flushList();
      const marker = fence[1];
      const fenceChar = marker[0];
      const lang = fence[2].trim();
      // Close fence: same marker char, >= opener length (CommonMark). Hoisted out
      // of the buffer loop — fenceChar/marker.length are loop-invariant. The {0,3}
      // leading-space tolerance matches markdown-stream's completer so an indented
      // streaming fence doesn't flicker a literal ``` into the live view.
      const close = new RegExp(`^${fenceChar === "`" ? "`" : "~"}{${marker.length},}\\s*$`);
      const buf: string[] = [];
      let j = i + 1;
      for (; j < lines.length; j++) {
        const raw = lines[j];
        if (close.test(raw.trim())) {
          break;
        }
        buf.push(raw);
      }
      out.push({ kind: "code", lang, text: buf.join("\n") });
      i = j; // skip the close fence (or run to EOF on an unterminated block)
      continue;
    }

    // GFM pipe table: a "| … |" header line immediately followed by a separator.
    if (line.includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      flushList();
      const headers = splitRow(line);
      const aligns = splitRow(lines[i + 1]).map(alignOf);
      const rows: string[][] = [];
      let j = i + 2;
      for (; j < lines.length; j++) {
        const r = lines[j].trim();
        if (!r.includes("|") || r === "") {
          break;
        }
        rows.push(splitRow(r));
      }
      out.push({ kind: "table", headers, aligns, rows });
      i = j - 1;
      continue;
    }

    const heading = /^(#{1,4})\s+(.*)$/.exec(line);
    const bullet = /^[-*]\s+(.*)$/.exec(line);
    const ordered = /^\d+\.\s+(.*)$/.exec(line);

    if (heading) {
      flushList();
      out.push({ kind: "heading", level: heading[1].length, text: heading[2] });
      continue;
    }
    if (bullet) {
      if (!list || list.ordered) {
        flushList();
        list = { ordered: false, items: [] };
      }
      list.items.push(bullet[1]);
      continue;
    }
    if (ordered) {
      if (!list || !list.ordered) {
        flushList();
        list = { ordered: true, items: [] };
      }
      list.items.push(ordered[1]);
      continue;
    }
    flushList();
    if (line.trim() !== "") {
      out.push({ kind: "paragraph", text: line });
    }
  }
  flushList();
  return out;
}

// --- inline rendering: emphasis + citation chips + LIVE ticker chips ---------

interface InlineCtx {
  onCite: (n: number) => void;
  /** High-confidence symbols (resolved + watchlist + structured) — always chipped. */
  known: Set<string>;
}

/** Live, clickable ticker chip → loads the symbol into the existing chart. */
function TickerChip({ symbol }: { symbol: string }) {
  return (
    <button
      type="button"
      onClick={() => loadSymbolIntoChart(symbol)}
      title={`Load ${symbol} into the chart`}
      className="rounded-control text-micro bg-charcoal-850 text-charcoal-300 hover:text-charcoal-100 focus-visible:ring-charcoal-500/70 mx-px inline-flex translate-y-[-1px] items-center px-1 align-baseline font-mono font-medium transition-colors focus-visible:ring-1 focus-visible:outline-none"
    >
      {symbol}
    </button>
  );
}

/** Interactive `[n]` citation chip → scrolls its source into view. */
function CiteChip({ n, onCite }: { n: number; onCite: (n: number) => void }) {
  return (
    <button
      type="button"
      onClick={() => onCite(n)}
      aria-label={`Jump to source ${n}`}
      className="rounded-control text-micro bg-charcoal-850 text-charcoal-300 hover:text-charcoal-100 focus-visible:ring-charcoal-500/60 mx-px inline-flex translate-y-[-2px] items-center px-1 align-baseline font-mono leading-tight transition-colors focus-visible:ring-1 focus-visible:outline-none"
    >
      {n}
    </button>
  );
}

/** Split a plain-text run into ticker chips ($CASHTAG or a KNOWN symbol) + text.
 *
 * Precision over recall: a chip only fires on an explicit `$TICKER` cashtag or a
 * symbol in the high-confidence known set (resolved symbol + watchlist +
 * structured). A bare uppercase word (GPU, CUDA, the company NAME) is NEVER
 * chipped — a chip that loads a junk symbol is worse than a missing chip. */
function renderTickers(text: string, known: Set<string>, keyBase: number): ReactNode[] {
  const nodes: ReactNode[] = [];
  // $CASHTAG (explicit) or a bare word-boundary candidate (matched only when known).
  const pattern = /(\$[A-Za-z][A-Za-z0-9.\-]{0,9})|([A-Za-z][A-Za-z0-9.\-]{1,9})/g;
  let last = 0;
  let key = keyBase;
  let m: RegExpExecArray | null;
  while ((m = pattern.exec(text)) !== null) {
    const token = m[0];
    let symbol: string | null = null;
    if (m[1]) {
      // $CASHTAG → always a chip.
      symbol = m[1].slice(1).toUpperCase();
    } else {
      const upper = token.toUpperCase();
      if (known.has(upper)) {
        symbol = upper;
      }
    }
    if (symbol) {
      if (m.index > last) {
        nodes.push(<Fragment key={key++}>{text.slice(last, m.index)}</Fragment>);
      }
      nodes.push(<TickerChip key={key++} symbol={symbol} />);
      last = pattern.lastIndex;
    }
  }
  if (last < text.length) {
    nodes.push(<Fragment key={key++}>{text.slice(last)}</Fragment>);
  }
  return nodes.length ? nodes : [text];
}

/** Render a line of inline markdown: bold / italic / code / `[n]` cite / ticker chip. */
function renderInline(text: string, ctx: InlineCtx): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[(\d+)\])/g;
  let last = 0;
  let key = 0;
  let match: RegExpExecArray | null;
  const emitText = (slice: string) => {
    if (slice) {
      nodes.push(<Fragment key={key++}>{renderTickers(slice, ctx.known, key * 1000)}</Fragment>);
    }
  };
  while ((match = pattern.exec(text)) !== null) {
    if (match.index > last) {
      emitText(text.slice(last, match.index));
    }
    const token = match[0];
    if (match[2] !== undefined) {
      nodes.push(<CiteChip key={key++} n={Number(match[2])} onCite={ctx.onCite} />);
    } else if (token.startsWith("**")) {
      nodes.push(
        <strong key={key++} className="text-lume font-semibold">
          {renderTickers(token.slice(2, -2), ctx.known, key * 1000)}
        </strong>,
      );
    } else if (token.startsWith("*")) {
      nodes.push(
        <em key={key++} className="text-charcoal-200">
          {token.slice(1, -1)}
        </em>,
      );
    } else {
      nodes.push(
        <code
          key={key++}
          className="bg-charcoal-800 rounded-control text-caption text-charcoal-100 px-1 py-px font-mono"
        >
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = pattern.lastIndex;
  }
  emitText(text.slice(last));
  return nodes;
}

// --- block components --------------------------------------------------------

function MetricsBlock({ model }: { model: MetricsModel }) {
  const up = (model.changePercent ?? 0) >= 0;
  const Caret = up ? ChevronUp : ChevronDown;
  const tone = up ? "text-positive" : "text-negative";
  return (
    <section className="border-charcoal-700 bg-charcoal-925 overflow-hidden rounded-none border">
      {/* Price line — symbol chip, the live price, the signed change/percent. */}
      {(model.price !== undefined || model.symbol) && (
        <div className="border-charcoal-800 flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b px-3 py-3">
          {model.symbol ? <TickerChip symbol={model.symbol} /> : null}
          {model.price !== undefined ? (
            <span className="text-lume text-overview font-mono leading-none font-medium whitespace-nowrap tabular-nums">
              {model.currency && model.currency !== "USD" ? `${model.currency} ` : ""}
              {formatNumber(model.price)}
            </span>
          ) : null}
          {model.changePercent !== undefined ? (
            <span
              className={`text-body inline-flex items-center gap-0.5 font-mono whitespace-nowrap tabular-nums ${tone}`}
            >
              <Caret className="size-3" />
              {formatSigned(model.change)} ({formatSignedPct(model.changePercent)})
            </span>
          ) : null}
          <span className="ml-auto flex items-center gap-2">
            {model.provider ? <ProvenanceBadge provider={model.provider} /> : null}
            {model.freshness ? <StalenessBadge freshness={model.freshness} /> : null}
          </span>
        </div>
      )}
      {/* Metric grid — gap-px over the border draws hairline dividers between cells. */}
      {model.items.length > 0 ? (
        // Columns follow the PANEL (container query), never the viewport — a narrow
        // rail drops to 2 columns so numeric values render WHOLE (overflow law: a
        // number that cannot fit drops a column, never ellipsizes into "4.5…").
        // BriefPanel's root declares @container.
        <div className="bg-charcoal-700 grid grid-cols-2 gap-px @[30rem]:grid-cols-3 @[42rem]:grid-cols-4">
          {model.items.map((item) => (
            <div
              key={item.label}
              className={`bg-charcoal-925 flex min-w-0 flex-col gap-0.5 px-3 py-2 ${/range/i.test(item.label) ? "col-span-2" : ""}`}
            >
              <span className="hud-label">{item.label}</span>
              <span
                className="text-charcoal-100 text-body truncate font-mono tabular-nums"
                title={item.value}
              >
                {item.value}
              </span>
            </div>
          ))}
        </div>
      ) : null}
    </section>
  );
}

function HeadingBlock({ level, text, ctx }: { level: number; text: string; ctx: InlineCtx }) {
  const sizes = ["text-overview", "text-section", "text-prose", "text-prose"];
  return (
    <p className={`text-lume mt-1 mb-0.5 font-semibold ${sizes[level - 1] ?? "text-prose"}`}>
      {renderInline(text, ctx)}
    </p>
  );
}

function ParagraphBlock({
  text,
  ctx,
  proseClass,
}: {
  text: string;
  ctx: InlineCtx;
  proseClass: string;
}) {
  return (
    <p className={`text-charcoal-200 ${proseClass} leading-relaxed`}>{renderInline(text, ctx)}</p>
  );
}

function ListBlock({
  ordered,
  items,
  ctx,
  proseClass,
}: {
  ordered: boolean;
  items: string[];
  ctx: InlineCtx;
  proseClass: string;
}) {
  const Tag = ordered ? "ol" : "ul";
  return (
    <Tag
      className={`text-charcoal-200 ${proseClass} ml-4 flex flex-col gap-1 leading-relaxed ${
        ordered ? "list-decimal" : "list-disc"
      }`}
    >
      {items.map((item, i) => (
        <li key={i} className="pl-1">
          {renderInline(item, ctx)}
        </li>
      ))}
    </Tag>
  );
}

function TableBlock({
  headers,
  aligns,
  rows,
  ctx,
}: {
  headers: string[];
  aligns: Align[];
  rows: string[][];
  ctx: InlineCtx;
}) {
  const alignClass = (i: number) =>
    aligns[i] === "right" ? "text-right" : aligns[i] === "center" ? "text-center" : "text-left";
  return (
    <div className="border-charcoal-700 overflow-x-auto rounded-none border">
      <table className="text-caption w-full border-collapse font-mono">
        <thead>
          <tr className="border-charcoal-700 bg-charcoal-925 border-b">
            {headers.map((h, i) => (
              <th
                key={i}
                className={`text-charcoal-300 px-3 py-1 font-medium tracking-wide ${alignClass(i)}`}
              >
                {renderInline(h, ctx)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-charcoal-800 border-b last:border-b-0">
              {row.map((cell, c) => (
                <td key={c} className={`text-charcoal-100 px-3 py-1 tabular-nums ${alignClass(c)}`}>
                  {renderInline(cell, ctx)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Fenced code block — raw monospace, no syntax highlighting (Shiki is deferred).
 *  Reuses the inline-code surface tokens so it sits in the same charcoal family. */
function CodeBlock({ text }: { lang: string; text: string }) {
  return (
    <pre className="bg-charcoal-800 rounded-control text-caption text-charcoal-100 overflow-x-auto px-3 py-2 font-mono leading-relaxed">
      <code className="font-mono">{text}</code>
    </pre>
  );
}

// --- the shared body renderer ------------------------------------------------

/**
 * Render a markdown source as the shared typed-block document body: the same
 * heading / paragraph / list / table / code switch the brief uses, with live
 * ticker chips (`$CASHTAG` + the `known` set) and interactive `[n]` cite chips.
 * Used by both the research brief (below) and the chat assistant reply, so the
 * two surfaces never diverge. No metric grid here — that is brief-only.
 *
 * `known` defaults to empty (chat may have no known set); `onCite` defaults to a
 * no-op (chat has no source rail, so cite chips render inert but un-broken).
 */
export function MarkdownBody({
  source,
  known,
  onCite,
  responsiveProse = false,
}: {
  source: string;
  known?: Set<string>;
  onCite?: (n: number) => void;
  /**
   * Container-aware prose sizing (R8 Proportion Law §1): when true (the brief
   * body, whose panel root declares `@container`), reading prose renders at
   * `text-body` (13px) and steps up to `text-prose` (16px) only at ≥420px of
   * container width — never 16px squeezed into a 200px column. Chat keeps its
   * own sizing (default false; no container ancestor required).
   */
  responsiveProse?: boolean;
}) {
  const reduced = useReducedMotion();
  const blocks = useMemo(() => parseBodyBlocks(source), [source]);
  const ctx = useMemo<InlineCtx>(
    () => ({ onCite: onCite ?? (() => {}), known: known ?? new Set<string>() }),
    [onCite, known],
  );
  const proseClass = responsiveProse ? "text-body @min-[420px]:text-prose" : "text-prose";

  const childProps = reduced ? {} : { variants: staggerChild };

  return (
    <>
      {blocks.map((block, i) => (
        <motion.div key={i} {...childProps}>
          {block.kind === "heading" ? (
            <HeadingBlock level={block.level} text={block.text} ctx={ctx} />
          ) : block.kind === "paragraph" ? (
            <ParagraphBlock text={block.text} ctx={ctx} proseClass={proseClass} />
          ) : block.kind === "list" ? (
            <ListBlock
              ordered={block.ordered}
              items={block.items}
              ctx={ctx}
              proseClass={proseClass}
            />
          ) : block.kind === "code" ? (
            <CodeBlock lang={block.lang} text={block.text} />
          ) : (
            <TableBlock headers={block.headers} aligns={block.aligns} rows={block.rows} ctx={ctx} />
          )}
        </motion.div>
      ))}
    </>
  );
}

// --- the document ------------------------------------------------------------

/** Collect the high-confidence ticker set: resolved symbol + watchlist + structured. */
function knownTickersOf(brief: ResearchBriefData, watchlist: string[]): Set<string> {
  const set = new Set<string>();
  const add = (s: string | undefined | null) => {
    if (s && typeof s === "string") {
      set.add(s.toUpperCase());
    }
  };
  add(brief.symbol);
  watchlist.forEach(add);
  const st = brief.structured;
  if (st) {
    const priceData = isLeg(st.price) ? (st.price.data as Quote | undefined) : undefined;
    const fundData = isLeg(st.fundamentals)
      ? (st.fundamentals.data as Fundamentals | undefined)
      : undefined;
    add(priceData?.symbol);
    add(fundData?.symbol);
  }
  return set;
}

/**
 * The brief BODY as a typed-block document: the metric-card grid (when the
 * structured bundle backs it) followed by the parsed markdown blocks, each with
 * live ticker chips + interactive citation markers. Reduced-motion-aware
 * staggered entrance.
 */
export function BriefBody({
  brief,
  onCite,
}: {
  brief: ResearchBriefData;
  onCite: (n: number) => void;
}) {
  const watchlist = useSymbolsStore((s) => s.entries);
  const reduced = useReducedMotion();

  const metrics = useMemo(() => deriveMetrics(brief.structured), [brief.structured]);
  const known = useMemo(
    () =>
      knownTickersOf(
        brief,
        watchlist.map((e) => e.symbol),
      ),
    [brief, watchlist],
  );
  // R8 marker truth: a `[n]` beyond the deduped source rail (or ANY marker on a
  // zero-source brief) is stripped before parsing — a dead chip never renders.
  // The rail indexes the SAME deduped list, so marker range == rail range.
  const body = useMemo(
    () => sanitizeCitationMarkers(brief.markdown, dedupeSources(brief.sources).length),
    [brief.markdown, brief.sources],
  );

  const parentProps = reduced
    ? {}
    : { variants: staggerParent, initial: "hidden", animate: "show" };
  const childProps = reduced ? {} : { variants: staggerChild };

  return (
    <motion.div className="flex flex-col gap-3 px-3 pt-3 pb-4" {...parentProps}>
      {metrics ? (
        <motion.div {...childProps}>
          <MetricsBlock model={metrics} />
        </motion.div>
      ) : null}
      <MarkdownBody source={body} known={known} onCite={onCite} responsiveProse />
    </motion.div>
  );
}
