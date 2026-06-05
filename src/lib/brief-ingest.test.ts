import { describe, expect, it } from "vitest";

import {
  briefSlug,
  composeBriefMarkdown,
  dedupeSources,
  deriveAssetClass,
  deriveSourceType,
  isAcceptableBriefMode,
  normalizeBriefDepth,
  normalizeBriefMode,
} from "@/lib/brief-ingest";
import type { BriefSource, BriefStructured, ResearchBriefData } from "../../types/brief";

function brief(overrides: Partial<ResearchBriefData> = {}): ResearchBriefData {
  return {
    query: "What is NVIDIA's data-center moat?",
    symbol: "NVDA",
    mode: "DEEP",
    markdown: "NVIDIA leads on CUDA [1] and Blackwell [2].",
    sources: [],
    sourceCount: 0,
    webAvailable: true,
    createdAt: 1_700_000_000_000,
    ...overrides,
  };
}

// ── mode / depth casing normalisation (S-6 / S-7) ───────────────────────────

describe("normalizeBriefMode", () => {
  it("maps the lowercase wire values to the uppercase badge", () => {
    expect(normalizeBriefMode("fast")).toBe("FAST");
    expect(normalizeBriefMode("deep")).toBe("DEEP");
    // "heavy" folds into the DEEP badge.
    expect(normalizeBriefMode("heavy")).toBe("DEEP");
  });

  it("accepts the canonical uppercase too", () => {
    expect(normalizeBriefMode("FAST")).toBe("FAST");
    expect(normalizeBriefMode("DEEP")).toBe("DEEP");
  });

  it("falls back to FAST for anything unrecognised", () => {
    expect(normalizeBriefMode("")).toBe("FAST");
    expect(normalizeBriefMode(undefined)).toBe("FAST");
    expect(normalizeBriefMode("quick")).toBe("FAST");
    expect(normalizeBriefMode(42)).toBe("FAST");
  });
});

describe("normalizeBriefDepth", () => {
  it("prefers an explicit depth token", () => {
    expect(normalizeBriefDepth("quick")).toBe("quick");
    expect(normalizeBriefDepth("deep")).toBe("deep");
    expect(normalizeBriefDepth("heavy")).toBe("heavy");
  });

  it("derives the tier from the mode when depth is absent", () => {
    expect(normalizeBriefDepth("", "heavy")).toBe("heavy");
    expect(normalizeBriefDepth("", "deep")).toBe("deep");
    expect(normalizeBriefDepth("", "fast")).toBe("quick");
    expect(normalizeBriefDepth(undefined, undefined)).toBe("quick");
  });
});

describe("isAcceptableBriefMode (restore validation)", () => {
  it("accepts canonical uppercase and raw lowercase wire modes", () => {
    expect(isAcceptableBriefMode("FAST")).toBe(true);
    expect(isAcceptableBriefMode("DEEP")).toBe(true);
    expect(isAcceptableBriefMode("fast")).toBe(true);
    expect(isAcceptableBriefMode("deep")).toBe(true);
    expect(isAcceptableBriefMode("heavy")).toBe(true);
    expect(isAcceptableBriefMode("quick")).toBe(true);
  });

  it("rejects garbage", () => {
    expect(isAcceptableBriefMode("")).toBe(false);
    expect(isAcceptableBriefMode(undefined)).toBe(false);
    expect(isAcceptableBriefMode("turbo")).toBe(false);
    expect(isAcceptableBriefMode(7)).toBe(false);
  });
});

// ── source dedup ────────────────────────────────────────────────────────────

describe("dedupeSources", () => {
  const make = (url: string, title = url): BriefSource => ({ url, title, excerpt: "" });

  it("keeps the first occurrence and drops later repeats", () => {
    const out = dedupeSources([
      make("https://sec.gov/a", "first"),
      make("https://sec.gov/a", "second"),
      make("https://reuters.com/b"),
    ]);
    expect(out).toHaveLength(2);
    expect(out[0].title).toBe("first");
    expect(out[1].url).toBe("https://reuters.com/b");
  });

  it("collapses trivially-different spellings (scheme / www / trailing slash / fragment)", () => {
    const out = dedupeSources([
      make("https://www.reuters.com/x/"),
      make("http://reuters.com/x"),
      make("https://reuters.com/x#section"),
    ]);
    expect(out).toHaveLength(1);
  });

  it("drops blank URLs and never mutates the input", () => {
    const input = [make("https://a.com"), { url: "", title: "blank", excerpt: "" }];
    const out = dedupeSources(input);
    expect(out).toHaveLength(1);
    expect(input).toHaveLength(2); // input untouched
  });
});

// ── source-type derivation ───────────────────────────────────────────────────

describe("deriveSourceType", () => {
  const at = (url: string, extra: Partial<BriefSource> = {}): BriefSource => ({
    url,
    title: "",
    excerpt: "",
    ...extra,
  });

  it("honours an explicit sourceType over the domain heuristic", () => {
    expect(deriveSourceType(at("https://reuters.com/x", { sourceType: "filing" }))).toBe("filing");
  });

  it("classifies SEC + regulators as filing", () => {
    expect(deriveSourceType(at("https://www.sec.gov/cgi-bin/x"))).toBe("filing");
    expect(deriveSourceType(at("https://nseindia.com/x"))).toBe("filing");
  });

  it("classifies the internal structured-data scheme as research", () => {
    expect(deriveSourceType(at("vysted://price/NVDA"))).toBe("research");
    expect(deriveSourceType(at("https://morningstar.com/x"))).toBe("research");
  });

  it("classifies wires + financial press as news", () => {
    expect(deriveSourceType(at("https://www.reuters.com/x"))).toBe("news");
    expect(deriveSourceType(at("https://bloomberg.com/x"))).toBe("news");
    expect(deriveSourceType(at("https://finance.yahoo.com/x"))).toBe("news");
  });

  it("uses the domain field when present, falling back to URL parse", () => {
    expect(deriveSourceType(at("vysted://x", { domain: "sec.gov" }))).toBe("filing");
  });

  it("defaults an unknown host to web (never a fabricated authority)", () => {
    expect(deriveSourceType(at("https://some-random-blog.example/post"))).toBe("web");
  });
});

// ── asset-class derivation ────────────────────────────────────────────────────

describe("deriveAssetClass", () => {
  const resolved = (assetClass: string): BriefStructured => ({
    resolved: { ok: true, resolved: { symbol: "X", asset_class: assetClass } },
  });

  it("reads asset_class out of the resolve_symbol wire shape", () => {
    expect(deriveAssetClass(resolved("crypto"))).toBe("crypto");
    expect(deriveAssetClass(resolved("etf"))).toBe("etf");
    expect(deriveAssetClass(resolved("fx"))).toBe("fx");
    expect(deriveAssetClass(resolved("equity"))).toBe("equity");
  });

  it("folds provider spelling variants", () => {
    expect(deriveAssetClass(resolved("cryptocurrency"))).toBe("crypto");
    expect(deriveAssetClass(resolved("fund"))).toBe("etf");
    expect(deriveAssetClass(resolved("currency"))).toBe("fx");
  });

  it("defaults to equity when unclassifiable / absent", () => {
    expect(deriveAssetClass(undefined)).toBe("equity");
    expect(deriveAssetClass({})).toBe("equity");
    expect(deriveAssetClass(resolved("widget"))).toBe("equity");
  });
});

// ── slug + markdown composition ───────────────────────────────────────────────

describe("briefSlug", () => {
  it("prefers the symbol, lower-kebab, path-safe", () => {
    expect(briefSlug({ symbol: "BRK.B", query: "anything" })).toBe("brk-b");
    expect(briefSlug({ symbol: "BTC/USDT", query: "x" })).toBe("btc-usdt");
  });

  it("falls back to the query, then to 'brief'", () => {
    expect(briefSlug({ symbol: undefined, query: "Is Apple cheap?" })).toBe("is-apple-cheap");
    expect(briefSlug({ symbol: undefined, query: "   " })).toBe("brief");
  });
});

describe("composeBriefMarkdown", () => {
  it("composes a title, metadata line, body, and a deduped Sources appendix", () => {
    const md = composeBriefMarkdown(
      brief({
        sources: [
          { url: "https://sec.gov/aapl", title: "10-K", excerpt: "Risks" },
          { url: "https://sec.gov/aapl", title: "10-K dup", excerpt: "Risks" }, // dup → dropped
          { url: "https://reuters.com/b", title: "Reuters story", excerpt: "" },
        ],
        sourceCount: 3,
      }),
    );
    expect(md).toContain("# What is NVIDIA's data-center moat?");
    expect(md).toContain("Mode: DEEP");
    expect(md).toContain("Symbol: NVDA");
    expect(md).toContain("NVIDIA leads on CUDA [1]");
    expect(md).toContain("## Sources");
    // De-dup: only two source lines, 1-based, "[n] title — url".
    expect(md).toContain("[1] 10-K — https://sec.gov/aapl");
    expect(md).toContain("[2] Reuters story — https://reuters.com/b");
    expect(md).not.toContain("[3]");
    expect(md).not.toContain("10-K dup");
  });

  it("uses the URL as the source label when the title is blank", () => {
    const md = composeBriefMarkdown(
      brief({ sources: [{ url: "https://x.com/a", title: "", excerpt: "" }], sourceCount: 1 }),
    );
    expect(md).toContain("[1] https://x.com/a — https://x.com/a");
  });

  it("flags a structured-data-only brief and surfaces the note", () => {
    const md = composeBriefMarkdown(
      brief({ webAvailable: false, note: "No web backend configured.", sources: [] }),
    );
    expect(md).toContain("structured-data-only");
    expect(md).toContain("No web backend configured.");
    // No appendix when there are no sources.
    expect(md).not.toContain("## Sources");
  });

  it("omits the symbol line when the brief has no symbol", () => {
    const md = composeBriefMarkdown(brief({ symbol: undefined }));
    expect(md).not.toContain("Symbol:");
  });
});
