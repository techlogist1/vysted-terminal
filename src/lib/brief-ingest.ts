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
  // R7 surface naming maps onto the brief-contract tiers (normal/deep/ultra →
  // quick/deep/heavy). Without this, a Tier B ULTRA brief (depth="ultra")
  // displayed as the DEEP tier (adversarial-sweep finding, R9).
  if (d === "ultra") {
    return "heavy";
  }
  if (d === "normal" || d === "fast") {
    return "quick";
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
 * The depth TIER a brief reached, read from its explicit `depth` field with a
 * fallback to the mode badge for older briefs that predate the field. Shared by
 * the chat surface's depth control AND the brief panel's read-only mirror so the
 * two never disagree about the current tier (one source of truth, FR-115).
 */
export function briefDepthTier(brief: { depth?: BriefDepth; mode: BriefMode }): BriefDepth {
  if (brief.depth === "quick" || brief.depth === "deep" || brief.depth === "heavy") {
    return brief.depth;
  }
  return brief.mode === "DEEP" ? "deep" : "quick";
}

/** The next tier "Go deeper" escalates to (`quick`→`deep`→`heavy`), or `null` at
 *  the deepest (`heavy`) tier — there is nowhere deeper to go. */
export function nextBriefDepth(depth: BriefDepth): Exclude<BriefDepth, "quick"> | null {
  if (depth === "quick") {
    return "deep";
  }
  if (depth === "deep") {
    return "heavy";
  }
  return null;
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

// ── citation-marker + banner truth (R8) ─────────────────────────────────────

/** Inline `[n]` citation marker — not a markdown link (`[1](url)` is a link). */
const CITE_MARKER_RE = /\[(\d{1,3})\](?!\()/g;

/**
 * Strip every inline `[n]` marker whose index exceeds the cited source count
 * (or any marker at all when there are zero sources). The live failure: a FAST
 * brief whose prose cited "[1] Screener.in" while the rail held 0 sources, and
 * an ULTRA brief citing [47] against 21 sources — a dead chip must never
 * render. Punctuation/space residue from the removal is tidied per line.
 */
export function sanitizeCitationMarkers(markdown: string, sourceCount: number): string {
  let removed = false;
  const cleaned = markdown.replace(CITE_MARKER_RE, (whole, digits: string) => {
    const n = Number(digits);
    if (n >= 1 && n <= sourceCount) {
      return whole;
    }
    removed = true;
    return "";
  });
  if (!removed) {
    return markdown;
  }
  return cleaned
    .split("\n")
    .map((line) =>
      line
        .replace(/[ \t]+([.,;:!?)\]])/g, "$1")
        .replace(/\(\s*\)/g, "")
        .replace(/[ \t]{2,}/g, " ")
        .trimEnd(),
    )
    .join("\n");
}

/** Bare-domain shapes that read as a web citation inside prose. */
const WEB_DOMAIN_RE =
  /https?:\/\/|\b[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.(?:com|net|org|io|co|in|gov|edu)\b/i;

/**
 * Does the brief BODY visibly cite web domains (Screener.in, URLs, …)?
 * Drives the honest banner copy: when the body cites the web but the run
 * captured zero sources, the banner must say "Sources were not captured for
 * this brief" — never the internally-inconsistent "no web sources found".
 */
export function bodyCitesWeb(markdown: string): boolean {
  return WEB_DOMAIN_RE.test(markdown);
}

/**
 * The meta-header token segment, or `null` to OMIT it entirely — zero tokens
 * never render as "0 tok" (R8 Proportion Law §6).
 */
export function formatBriefTokens(tokens: number | undefined): string | null {
  if (typeof tokens !== "number" || !Number.isFinite(tokens) || tokens <= 0) {
    return null;
  }
  if (tokens >= 1000) {
    return `${(tokens / 1000).toFixed(tokens >= 10000 ? 0 : 1)}k tok`;
  }
  return `${tokens} tok`;
}

/**
 * The meta-header spend segment, or `null` to OMIT it. "$0.0000" never renders
 * (R8 Proportion Law §6): zero/absent spend → omit; below $0.005 → "<$0.01".
 */
export function formatBriefSpend(spendUsd: number | undefined): string | null {
  if (typeof spendUsd !== "number" || !Number.isFinite(spendUsd) || spendUsd <= 0) {
    return null;
  }
  if (spendUsd < 0.005) {
    return "<$0.01";
  }
  return `$${spendUsd.toFixed(2)}`;
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

  // Sources appendix — de-duplicated, 1-based to match the `[n]` markers; the
  // body is sanitised against the SAME deduped count so the exported document
  // never carries a marker its own appendix cannot resolve (R8).
  const sources = dedupeSources(brief.sources);

  const body = sanitizeCitationMarkers(brief.markdown, sources.length).trim();
  if (body) {
    lines.push(body);
    lines.push("");
  }
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
