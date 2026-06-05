/**
 * Brief ingest + presentation helpers — the pure, headless-testable logic
 * behind the research brief panel (export composition, source dedup + type
 * derivation, asset-class metric branching, mode/depth casing normalisation).
 *
 * Kept framework-free (no React, no Tauri) so every transform is unit-tested
 * directly: the panel + the `publish_brief` ingest at the agent boundary import
 * from here rather than re-deriving the same logic inline.
 */

import type {
  BriefMode,
  BriefDepth,
  BriefSource,
  BriefSourceType,
  BriefStructured,
  ResearchBriefData,
} from "../../types/brief";

// ── mode / depth casing normalisation (S-6 / S-7) ───────────────────────────

/**
 * Normalise a raw `mode`/`depth` token (the sidecar wire emits lowercase
 * `fast`/`deep`/`heavy`) to the panel's uppercase {@link BriefMode}. The three
 * depth tiers collapse to the two-state badge: `quick`/`fast` → FAST, and
 * `deep`/`heavy` → DEEP. Anything unrecognised falls back to FAST.
 */
export function normalizeBriefMode(raw: unknown): BriefMode {
  const t = String(raw ?? "")
    .trim()
    .toLowerCase();
  if (t === "deep" || t === "heavy") {
    return "DEEP";
  }
  // "fast" | "quick" | "" | anything else → FAST.
  return "FAST";
}

/**
 * Resolve the true depth TIER (`quick`/`deep`/`heavy`) from an explicit `depth`
 * token, falling back to the `mode` token when depth is absent. `heavy` folds
 * into the DEEP badge but stays a distinct tier so "Go deeper" knows it has
 * reached the deepest run.
 */
export function normalizeBriefDepth(rawDepth: unknown, rawMode?: unknown): BriefDepth {
  const d = String(rawDepth ?? "")
    .trim()
    .toLowerCase();
  if (d === "quick" || d === "deep" || d === "heavy") {
    return d as BriefDepth;
  }
  const m = String(rawMode ?? "")
    .trim()
    .toLowerCase();
  if (m === "heavy") {
    return "heavy";
  }
  if (m === "deep") {
    return "deep";
  }
  return "quick";
}

/**
 * Restore-validation accepts either the canonical uppercase mode OR a raw
 * lowercase wire value (a brief persisted before the casing fix, or one written
 * straight from the wire). Used by the brief store's `isBriefData` guard.
 */
export function isAcceptableBriefMode(value: unknown): boolean {
  if (value === "FAST" || value === "DEEP") {
    return true;
  }
  const t = String(value ?? "")
    .trim()
    .toLowerCase();
  return t === "fast" || t === "deep" || t === "heavy" || t === "quick";
}

// ── source-type derivation + dedup ──────────────────────────────────────────

/** Bare-host classifier inputs for {@link deriveSourceType}. */
function hostOf(source: BriefSource): string {
  if (source.domain) {
    return source.domain.toLowerCase().replace(/^www\./, "");
  }
  try {
    return new URL(source.url).hostname.toLowerCase().replace(/^www\./, "");
  } catch {
    return source.url.toLowerCase();
  }
}

/** Filing hosts — regulators + filing aggregators. */
const FILING_HOSTS = [
  "sec.gov",
  "sec.report",
  "annualreports.com",
  "investor.gov",
  "nseindia.com",
  "bseindia.com",
  "sebi.gov.in",
  "londonstockexchange.com",
  "companieshouse.gov.uk",
];

/** News hosts — wires + mainstream financial press. */
const NEWS_HOSTS = [
  "reuters.com",
  "bloomberg.com",
  "wsj.com",
  "ft.com",
  "cnbc.com",
  "marketwatch.com",
  "barrons.com",
  "forbes.com",
  "businessinsider.com",
  "yahoo.com",
  "finance.yahoo.com",
  "apnews.com",
  "nytimes.com",
  "theguardian.com",
  "investing.com",
  "benzinga.com",
  "seekingalpha.com",
  "fool.com",
  "economictimes.indiatimes.com",
  "moneycontrol.com",
  "livemint.com",
  "business-standard.com",
];

/** Research/provider hosts — vendor data + internal structured pulls. */
const RESEARCH_HOSTS = [
  "morningstar.com",
  "spglobal.com",
  "moodys.com",
  "fitchratings.com",
  "ycharts.com",
  "macrotrends.net",
  "tikr.com",
  "gurufocus.com",
  "simplywall.st",
  "koyfin.com",
];

function hostMatches(host: string, list: string[]): boolean {
  return list.some((h) => host === h || host.endsWith(`.${h}`));
}

/**
 * Derive a source's category from its host (the badge in the sources rail). The
 * pipeline's own `sourceType` always wins; otherwise we classify by domain:
 * regulators/filing aggregators → `filing`; the internal `vysted://` structured
 * scheme + known data vendors → `research`; mainstream press/wires → `news`;
 * everything else → `web`. Conservative: an unknown host reads as plain `web`,
 * never a fabricated authority badge.
 */
export function deriveSourceType(source: BriefSource): BriefSourceType {
  if (
    source.sourceType === "news" ||
    source.sourceType === "research" ||
    source.sourceType === "filing" ||
    source.sourceType === "web"
  ) {
    return source.sourceType;
  }
  // The host classification wins first: a `domain` label (e.g. "sec.gov" on an
  // internal filings pull) is the most specific signal we have.
  const host = hostOf(source);
  if (hostMatches(host, FILING_HOSTS)) {
    return "filing";
  }
  if (hostMatches(host, RESEARCH_HOSTS)) {
    return "research";
  }
  if (hostMatches(host, NEWS_HOSTS)) {
    return "news";
  }
  // An unclassified internal structured-data citation (`vysted://price/AAPL`,
  // no recognised domain) is research-class data, not plain web.
  if (source.url.toLowerCase().startsWith("vysted://")) {
    return "research";
  }
  return "web";
}

/** Normalise a URL for dedup — strip the scheme, `www.`, a trailing slash, and
 *  the fragment, lower-cased, so trivially different spellings collapse. */
function dedupKey(url: string): string {
  let s = url.trim().toLowerCase();
  s = s.replace(/^https?:\/\//, "");
  s = s.replace(/^www\./, "");
  s = s.replace(/#.*$/, "");
  s = s.replace(/\/+$/, "");
  return s;
}

/**
 * Drop duplicate sources by URL, keeping the FIRST occurrence (its `[n]` index
 * order is load-bearing — the markdown's citation markers point at it). A source
 * with a blank URL is dropped. Returns a fresh array, never mutates the input.
 */
export function dedupeSources(sources: readonly BriefSource[]): BriefSource[] {
  const seen = new Set<string>();
  const out: BriefSource[] = [];
  for (const source of sources) {
    const url = (source.url ?? "").trim();
    if (!url) {
      continue;
    }
    const key = dedupKey(url);
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    out.push(source);
  }
  return out;
}

// ── asset-class metric branching ────────────────────────────────────────────

/** The three metric families the brief's metric grid branches on. */
export type BriefAssetClass = "equity" | "crypto" | "etf" | "fx";

/**
 * Resolve the brief's asset class from the structured bundle's resolved
 * instrument (`structured.resolved.resolved.asset_class`, the resolve_symbol
 * wire shape) with a fall-back to the explicit `assetClass` on a leg. Returns
 * `equity` when nothing classifies it — the equity metric set is the default.
 */
export function deriveAssetClass(structured: BriefStructured | undefined): BriefAssetClass {
  if (!structured) {
    return "equity";
  }
  const raw = readResolvedAssetClass(structured.resolved);
  return normalizeAssetClass(raw);
}

/** Pull `asset_class` out of the (untyped) resolve_symbol wire payload. */
function readResolvedAssetClass(resolved: unknown): string | undefined {
  if (typeof resolved !== "object" || resolved === null) {
    return undefined;
  }
  const top = resolved as Record<string, unknown>;
  // The wire shape is `{ ok, resolved: { asset_class } }`; accept a flattened
  // `{ asset_class }` too, in case a future leg carries it directly.
  const inner = top.resolved;
  if (typeof inner === "object" && inner !== null) {
    const ac = (inner as Record<string, unknown>).asset_class;
    if (typeof ac === "string") {
      return ac;
    }
  }
  const flat = top.asset_class;
  return typeof flat === "string" ? flat : undefined;
}

/** Fold the many provider spellings into the four metric families. */
function normalizeAssetClass(raw: string | undefined): BriefAssetClass {
  const k = (raw ?? "").trim().toLowerCase();
  if (k === "crypto" || k === "cryptocurrency") {
    return "crypto";
  }
  if (k === "etf" || k === "fund" || k === "mutualfund") {
    return "etf";
  }
  if (k === "fx" || k === "currency" || k === "forex") {
    return "fx";
  }
  return "equity";
}

// ── markdown export composition ─────────────────────────────────────────────

/**
 * Sanitise a query/symbol into a safe, lower-kebab file slug (for the exported
 * `.md`/`.pdf` filename). Strips path separators + punctuation, collapses
 * whitespace to single dashes, caps length, and falls back to `brief`.
 */
export function briefSlug(brief: Pick<ResearchBriefData, "symbol" | "query">): string {
  const base = (brief.symbol || brief.query || "").trim();
  const slug = base
    .toLowerCase()
    .replace(/[/\\]+/g, "-")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
  return slug || "brief";
}

/**
 * Compose a research brief into a self-contained Markdown document: an H1 title
 * (the query), a quiet metadata line (mode · symbol · source count · "as of"),
 * the synthesis body verbatim, and a `## Sources` appendix listing each cited
 * source as `[n] title — url`. Sources are de-duplicated first so the appendix
 * never repeats a URL. Pure string transform — no IO.
 */
export function composeBriefMarkdown(brief: ResearchBriefData): string {
  const lines: string[] = [];
  const title = brief.query.trim() || brief.symbol || "Research brief";
  lines.push(`# ${title}`);
  lines.push("");

  // Metadata line — mode, symbol, source count, produced-at.
  const meta: string[] = [`Mode: ${brief.mode}`];
  if (brief.symbol) {
    meta.push(`Symbol: ${brief.symbol}`);
  }
  const count = typeof brief.sourceCount === "number" ? brief.sourceCount : brief.sources.length;
  meta.push(`${count} source${count === 1 ? "" : "s"}`);
  if (!brief.webAvailable) {
    meta.push("structured-data-only");
  }
  if (typeof brief.createdAt === "number") {
    meta.push(`as of ${new Date(brief.createdAt).toISOString()}`);
  }
  lines.push(`> ${meta.join(" · ")}`);
  lines.push("");

  // The honest no-web / abort note, when present.
  if (brief.note && brief.note.trim()) {
    lines.push(`_${brief.note.trim()}_`);
    lines.push("");
  }

  const body = brief.markdown.trim();
  if (body) {
    lines.push(body);
    lines.push("");
  }

  // Sources appendix — de-duplicated, 1-based to match the `[n]` markers.
  const sources = dedupeSources(brief.sources);
  if (sources.length > 0) {
    lines.push("## Sources");
    lines.push("");
    sources.forEach((source, i) => {
      const label = source.title?.trim() || source.url;
      lines.push(`[${i + 1}] ${label} — ${source.url}`);
    });
    lines.push("");
  }

  // Single trailing newline.
  return lines.join("\n").replace(/\n+$/, "\n");
}
