import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import { describe, expect, it } from "vitest";

import { BriefBody, deriveMetrics, MarkdownBody } from "@/modules/research/brief-blocks";
import type { BriefDerivedMetrics, BriefStructured, ResearchBriefData } from "../../../types/brief";
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

// ── derived semantics leg (R10 E8) ───────────────────────────────────────────

function derivedLeg(data: BriefDerivedMetrics): BriefStructured["derived"] {
  return { ok: true, provider: "derived", data };
}

describe("deriveMetrics — the derived semantics leg leads the grid (E8)", () => {
  it("renders drawdown and 52w-change as SEPARATE leading cards", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          drawdown_from_high: {
            value: 0.216,
            label: "Below 52-week high",
            basis: "vs 52w high",
            formula: "(52w high − price) / 52w high",
            unit: "percent",
          },
          fifty_two_week_change: {
            value: 0.34,
            label: "52-week change",
            unit: "percent",
          },
        }),
      }),
    );
    const items = model?.items ?? [];
    expect(items[0].label).toBe("Below 52-week high");
    // Drawdown reads as a NEGATIVE magnitude — never 52w-change's upward look.
    expect(items[0].value).toContain("-21.60%");
    expect(items[0].title).toContain("(52w high − price)");
    expect(items[1].label).toBe("52-week change");
    expect(items[1].value).toBe("+34.00%");
  });

  it("dividend + growth carry their basis suffix; nulls render nothing", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          dividend_yield: {
            value: 0.0055,
            label: "Dividend yield",
            basis: "of price",
            unit: "percent",
          },
          dividend_per_share: {
            value: 1,
            label: "Dividend / share",
            basis: "INR",
            unit: "currency",
          },
          revenue_growth: {
            value: 0.124,
            label: "Revenue growth",
            basis: "FY/FY",
            unit: "percent",
          },
          earnings_growth: { value: null, label: "Earnings growth", unit: "percent" },
        }),
      }),
    );
    const byLabel = Object.fromEntries((model?.items ?? []).map((i) => [i.label, i.value]));
    expect(byLabel["Dividend yield"]).toBe("0.55% · of price");
    expect(byLabel["Dividend / share"]).toBe("1.00 · INR");
    expect(byLabel["Revenue growth"]).toBe("+12.40% · FY/FY");
    expect(byLabel["Earnings growth"]).toBeUndefined(); // null → no card, never fabricated
    // The derived dividend/growth cards SHADOW the raw basis-less duplicates.
    expect(byLabel["Div yield"]).toBeUndefined();
    expect(byLabel["Rev growth"]).toBeUndefined();
  });

  it("renders the full 'quarterly YoY (MRQ)' basis without truncation (D55)", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          revenue_growth: {
            value: 0.124,
            label: "Revenue growth",
            basis: "quarterly YoY (MRQ)",
            unit: "percent",
          },
          earnings_growth: {
            value: -0.031,
            label: "Earnings growth",
            basis: "quarterly YoY (MRQ)",
            unit: "percent",
          },
        }),
      }),
    );
    const byLabel = Object.fromEntries((model?.items ?? []).map((i) => [i.label, i.value]));
    // The longer D55 basis string rides the suffix whole — never clipped or
    // assumed away by the formatter.
    expect(byLabel["Revenue growth"]).toBe("+12.40% · quarterly YoY (MRQ)");
    expect(byLabel["Earnings growth"]).toBe("-3.10% · quarterly YoY (MRQ)");
  });

  it("currency-sized cards carry the instrument's code like the price line (D55)", () => {
    const inr = structured("equity", {
      price: { ok: true, provider: "yfinance", data: quote({ currency: "INR" }) },
      derived: derivedLeg({
        dividend_per_share: {
          value: 47.5,
          label: "Dividend / share",
          unit: "currency",
        },
      }),
    });
    const byLabel = Object.fromEntries(
      (deriveMetrics(inr)?.items ?? []).map((i) => [i.label, i.value]),
    );
    // Market cap / Revenue (formatLarge cards) + the currency-unit derived card
    // all wear the ISO code — "4.48T" on an NSE stock is otherwise ambiguous.
    expect(byLabel["Market cap"]).toBe("INR 2.00B");
    expect(byLabel["Revenue"]).toBe("INR 500.00M");
    expect(byLabel["Dividend / share"]).toBe("INR 47.50");

    // USD stays byte-identical to before — the code only appears when != USD,
    // matching the price line's convention.
    const usd = structured("equity", {});
    const usdByLabel = Object.fromEntries(
      (deriveMetrics(usd)?.items ?? []).map((i) => [i.label, i.value]),
    );
    expect(usdByLabel["Market cap"]).toBe("2.00B");
    expect(usdByLabel["Revenue"]).toBe("500.00M");
  });

  it("a currency basis never duplicates an already-coded value (D55)", () => {
    const model = deriveMetrics(
      structured("equity", {
        price: { ok: true, provider: "yfinance", data: quote({ currency: "INR" }) },
        derived: derivedLeg({
          dividend_per_share: {
            value: 1,
            label: "Dividend / share",
            basis: "INR",
            unit: "currency",
          },
        }),
      }),
    );
    const byLabel = Object.fromEntries((model?.items ?? []).map((i) => [i.label, i.value]));
    // The value already reads "INR 1.00" — appending "· INR" again would stutter.
    expect(byLabel["Dividend / share"]).toBe("INR 1.00");
  });

  it("conflicts render as flag lines and never silently reconcile (absent conflict_kind = data_conflict)", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          conflicts: [
            {
              field: "dividend_yield",
              sources: [
                { provider: "yield", value: "0.55%" },
                { provider: "per-share", value: "₹1/share" },
              ],
              note: "not reconciled",
            },
          ],
        }),
      }),
    );
    expect(model?.conflicts).toEqual([
      {
        text: "Sources disagree on dividend yield: 0.55% (yield) vs ₹1/share (per-share) — not reconciled",
        kind: "data_conflict",
      },
    ]);
  });

  it("a derived-only bundle (raw legs failed) still yields a model", () => {
    const model = deriveMetrics({
      price: { ok: false },
      fundamentals: { ok: false },
      derived: derivedLeg({
        drawdown_from_high: { value: 0.1, label: "Below 52-week high", unit: "percent" },
      }),
    });
    expect(model).not.toBeNull();
    expect(model?.items[0].label).toBe("Below 52-week high");
  });
});

// ── conflict presentation tiers (R13 / D69) ──────────────────────────────────

describe("deriveMetrics — conflict_kind presentation tiers (R13)", () => {
  it("an explicit data_conflict keeps the 'Sources disagree' warning framing", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          conflicts: [
            {
              field: "held_percent_institutions",
              conflict_kind: "data_conflict",
              sources: [
                { provider: "yfinance (heldPercentInstitutions)", value: 12.5 },
                { provider: "NSE shareholding filing", value: 40.1 },
              ],
              note: "the provider scalar is unreliable for this listing; both are shown, neither replaced.",
            },
          ],
        }),
      }),
    );
    expect(model?.conflicts).toEqual([
      {
        text:
          "Sources disagree on held percent institutions: 12.5 (yfinance (heldPercentInstitutions)) " +
          "vs 40.1 (NSE shareholding filing) — the provider scalar is unreliable for this listing; " +
          "both are shown, neither replaced.",
        kind: "data_conflict",
      },
    ]);
  });

  it("a definitional_expected conflict reads as an expected-difference note, not a warning", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          conflicts: [
            {
              field: "held_percent_insiders",
              conflict_kind: "definitional_expected",
              sources: [
                { provider: "yfinance (heldPercentInsiders)", value: 74.5, basis: "insiders" },
                {
                  provider: "NSE shareholding filing",
                  value: 73.29,
                  basis: "promoter group, 2026-06-30",
                },
              ],
              note: "Insiders and promoter-group are different by definition; both figures are shown, neither replaced.",
            },
          ],
        }),
      }),
    );
    const conflicts = model?.conflicts ?? [];
    expect(conflicts).toHaveLength(1);
    expect(conflicts[0].kind).toBe("definitional_expected");
    // The lead-in reads as an EXPECTED difference, never "Sources disagree".
    expect(conflicts[0].text).toContain("expected definitional difference");
    expect(conflicts[0].text).not.toContain("Sources disagree");
    expect(conflicts[0].text).toContain("Insiders and promoter-group are different by definition");
  });

  it("MetricsBlock renders the two tiers with distinct chips and never conflates them", () => {
    // Render the full brief body (metrics + markdown) via BriefBody so the
    // MetricsBlock's chip markup is exercised end-to-end.
    const brief: ResearchBriefData = {
      query: "ICICIBANK",
      symbol: "ICICIBANK",
      mode: "FAST",
      markdown: "",
      sources: [],
      sourceCount: 0,
      webAvailable: true,
      createdAt: Date.now(),
      structured: structured("equity", {
        derived: derivedLeg({
          conflicts: [
            {
              field: "held_percent_insiders",
              conflict_kind: "definitional_expected",
              sources: [{ provider: "yfinance", value: 74.5 }],
              note: "different by definition",
            },
            {
              field: "market_cap",
              conflict_kind: "data_conflict",
              sources: [{ provider: "yfinance", value: 100 }],
              note: "diverges from price x shares",
            },
          ],
        }),
      }),
    };
    const body = renderToStaticMarkup(createElement(BriefBody, { brief, onCite: () => {} }));
    expect(body).toContain("DEFINITIONAL");
    expect(body).toContain("CONFLICT");
    expect(body).toContain("different by definition");
    expect(body).toContain("diverges from price x shares");
  });
});

// ── the derived leg surfaces facts it doesn't statically name (R13) ─────────

describe("deriveMetrics — derived-leg facts flow through generically (R13)", () => {
  it("renders the R13 ownership cross-check facts (promoter/institutions) with no per-field code", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          drawdown_from_high: { value: 0.1, label: "Below 52-week high", unit: "percent" },
          // These two keys are NOT named in the BriefDerivedMetrics interface —
          // they arrive on the wire exactly like this (sidecar/services/research/
          // semantics.py _ownership_leg) and must still render, labels intact.
          ...({
            promoter_percent_exchange: {
              value: 0.7329,
              label: "Promoter group (exchange filing)",
              basis: "NSE shareholding filing, 2026-06-30",
              unit: "percent",
            },
            institutions_percent_exchange: {
              value: 0.401,
              label: "Institutional holding (exchange filing)",
              basis: "NSE shareholding filing, 2026-06-30",
              unit: "percent",
            },
          } as Partial<BriefDerivedMetrics>),
        }),
      }),
    );
    const byLabel = Object.fromEntries((model?.items ?? []).map((i) => [i.label, i.value]));
    expect(byLabel["Promoter group (exchange filing)"]).toBe(
      "73.29% · NSE shareholding filing, 2026-06-30",
    );
    expect(byLabel["Institutional holding (exchange filing)"]).toBe(
      "40.10% · NSE shareholding filing, 2026-06-30",
    );
    // Unsigned — a holding percentage is a level, not a directional change.
    expect(byLabel["Promoter group (exchange filing)"]).not.toContain("+");
  });

  it("renders the D56/D57 declared-dividend facts the same generic way", () => {
    const model = deriveMetrics(
      structured("equity", {
        derived: derivedLeg({
          ...({
            dividend_per_share_ttm: {
              value: 1.5,
              label: "Dividend/share (trailing 12m PAID)",
              basis: "corporate-action history",
              unit: "currency",
            },
            dividend_declared: {
              value: 2.0,
              label: "Declared, not yet paid (record date 2026-07-15)",
              basis: "NSE corporate action",
              unit: "currency",
            },
          } as Partial<BriefDerivedMetrics>),
        }),
      }),
    );
    const byLabel = Object.fromEntries((model?.items ?? []).map((i) => [i.label, i.value]));
    expect(byLabel["Dividend/share (trailing 12m PAID)"]).toBe("1.50 · corporate-action history");
    expect(byLabel["Declared, not yet paid (record date 2026-07-15)"]).toBe(
      "2.00 · NSE corporate action",
    );
  });
});

// R12: a zero-filled 52w range is provider ABSENCE — the card must not render
// a fabricated-looking "0–0" (seen live on a BSE-only scrip's archived brief).
describe("52w range zero-guard (R12)", () => {
  it("renders no range card when the provider zero-fills the bounds", () => {
    const zeroed = structured("equity", {
      fundamentals: {
        ok: true,
        provider: "bse",
        data: { ...fundamentals(), fifty_two_week_low: 0, fifty_two_week_high: 0 },
      },
    });
    expect(labels(zeroed)).not.toContain("52w range");
  });
});
