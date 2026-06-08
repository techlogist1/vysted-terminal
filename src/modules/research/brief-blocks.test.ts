import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import { deriveMetrics, MarkdownBody } from "@/modules/research/brief-blocks";
import type { BriefStructured } from "../../../types/brief";
import type { Fundamentals, Quote } from "../../../types/data";

/** Render MarkdownBody to static HTML for content assertions (no DOM needed). */
function renderBody(source: string, known?: Set<string>): string {
  return renderToStaticMarkup(createElement(MarkdownBody, { source, known }));
}

function quote(overrides: Partial<Quote> = {}): Quote {
  return {
    symbol: "X",
    price: 100,
    change: 1,
    change_percent: 1,
    volume: 1_000_000,
    currency: "USD",
    market_state: "REGULAR",
    timestamp: "2024-01-01T00:00:00Z",
    provider: "yfinance",
    freshness: "live",
    ...overrides,
  };
}

function fundamentals(overrides: Partial<Fundamentals> = {}): Fundamentals {
  return {
    symbol: "X",
    name: "X Corp",
    sector: null,
    industry: null,
    currency: "USD",
    market_cap: 2_000_000_000,
    pe_ratio: 25,
    forward_pe: 22,
    peg_ratio: 1.5,
    price_to_book: 8,
    price_to_sales: null,
    ev_to_ebitda: null,
    book_value: null,
    dividend_yield: 0.005,
    dividend_per_share: null,
    eps: 4,
    beta: 1.1,
    fifty_two_week_high: 120,
    fifty_two_week_low: 80,
    fifty_two_week_change: null,
    roe: 0.3,
    roa: null,
    gross_margin: null,
    operating_margin: null,
    profit_margin: 0.25,
    debt_to_equity: 0.4,
    current_ratio: null,
    quick_ratio: null,
    revenue_ttm: 500_000_000,
    net_income_ttm: null,
    free_cash_flow: null,
    shares_outstanding: null,
    revenue_growth: 0.2,
    earnings_growth: null,
    held_percent_insiders: null,
    held_percent_institutions: null,
    provider: "yfinance",
    ...overrides,
  };
}

function structured(
  assetClass: string | undefined,
  extra: Partial<BriefStructured> = {},
): BriefStructured {
  return {
    resolved:
      assetClass === undefined
        ? undefined
        : { ok: true, resolved: { symbol: "X", asset_class: assetClass } },
    price: { ok: true, provider: "yfinance", data: quote() },
    fundamentals: { ok: true, provider: "yfinance", data: fundamentals() },
    ...extra,
  };
}

const labels = (s: BriefStructured) => deriveMetrics(s)?.items.map((i) => i.label) ?? [];

describe("deriveMetrics — asset-class branching", () => {
  it("returns null when there is no usable price or fundamentals leg", () => {
    expect(deriveMetrics(undefined)).toBeNull();
    expect(deriveMetrics({})).toBeNull();
    expect(deriveMetrics({ price: { ok: false }, fundamentals: { ok: false } })).toBeNull();
  });

  it("equity: the full valuation + quality + growth grid", () => {
    const model = deriveMetrics(structured("equity"));
    expect(model?.assetClass).toBe("equity");
    const l = labels(structured("equity"));
    expect(l).toContain("P/E");
    expect(l).toContain("ROE");
    expect(l).toContain("Rev growth");
    expect(l).toContain("Market cap");
  });

  it("crypto: market cap + 24h volume + range, NO equity valuation ratios", () => {
    const model = deriveMetrics(structured("crypto"));
    expect(model?.assetClass).toBe("crypto");
    const l = labels(structured("crypto"));
    expect(l).toContain("Market cap");
    expect(l).toContain("24h volume");
    expect(l).toContain("52w range");
    // A coin must never show a meaningless P/E / PEG / ROE.
    expect(l).not.toContain("P/E");
    expect(l).not.toContain("PEG");
    expect(l).not.toContain("ROE");
  });

  it("etf: net assets + yield + beta, no single-company quality ratios", () => {
    const model = deriveMetrics(structured("etf"));
    expect(model?.assetClass).toBe("etf");
    const l = labels(structured("etf"));
    expect(l).toContain("Net assets");
    expect(l).toContain("Beta");
    expect(l).not.toContain("ROE");
    expect(l).not.toContain("Rev growth");
  });

  it("fx: price action + range only, no fundamentals cards", () => {
    const model = deriveMetrics(structured("fx"));
    expect(model?.assetClass).toBe("fx");
    const l = labels(structured("fx"));
    expect(l).not.toContain("Market cap");
    expect(l).not.toContain("P/E");
    expect(l).toContain("52w range");
  });

  it("defaults to the equity set when the resolved instrument is absent", () => {
    const model = deriveMetrics(structured(undefined));
    expect(model?.assetClass).toBe("equity");
    expect(labels(structured(undefined))).toContain("P/E");
  });

  it("never fabricates a card — an absent field renders no card", () => {
    const s = structured("equity", {
      fundamentals: { ok: true, provider: "yfinance", data: fundamentals({ pe_ratio: null }) },
    });
    expect(labels(s)).not.toContain("P/E");
  });

  it("deriveMetrics(undefined) is null so the chat path renders no metric grid", () => {
    expect(deriveMetrics(undefined)).toBeNull();
  });
});

describe("MarkdownBody — the shared typed-block renderer", () => {
  it("renders headings, paragraphs, and lists", () => {
    const html = renderBody("## Title\n\nA paragraph.\n\n- one\n- two\n\n1. first\n2. second");
    expect(html).toContain("Title");
    expect(html).toContain("A paragraph.");
    expect(html).toContain("<ul");
    expect(html).toContain("<ol");
    expect(html).toContain("one");
    expect(html).toContain("first");
  });

  it("renders a GFM pipe table into a real <table>", () => {
    const html = renderBody("| Sym | Px |\n| --- | --: |\n| AAPL | 100 |\n| MSFT | 200 |");
    expect(html).toContain("<table");
    expect(html).toContain("<thead");
    expect(html).toContain("<tbody");
    expect(html).toContain("AAPL");
    expect(html).toContain("200");
  });

  it("renders a fenced code block into <pre><code> with no inline parse", () => {
    const html = renderBody("```ts\nconst x = **not bold**;\n```");
    expect(html).toContain("<pre");
    expect(html).toContain("<code");
    // Code is literal — the ** must survive, NOT become a <strong>.
    expect(html).toContain("const x = **not bold**;");
    expect(html).not.toContain("<strong");
  });

  it("renders an unterminated fenced block (streaming) without dropping content", () => {
    const html = renderBody("```python\nprint(1)");
    expect(html).toContain("<pre");
    expect(html).toContain("print(1)");
  });

  it("chips a $CASHTAG and a known symbol, never a bare uppercase word", () => {
    const html = renderBody("Buy $AAPL and NVDA but not the GPU.", new Set(["NVDA"]));
    // Both the cashtag and the known symbol become ticker <button> chips…
    const buttons = html.match(/<button/g) ?? [];
    expect(buttons.length).toBe(2);
    // …a bare uppercase word (not in the known set, no $) stays plain text.
    expect(html).toContain("GPU");
    expect(html).toContain("AAPL");
    expect(html).toContain("NVDA");
  });

  it("renders [n] cite chips inert (no onCite) without throwing", () => {
    const html = renderBody("A claim [1] and another [2].");
    expect(html).toContain("Jump to source 1");
    expect(html).toContain("Jump to source 2");
  });
});
