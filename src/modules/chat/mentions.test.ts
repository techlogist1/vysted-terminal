import { afterEach, describe, expect, it, vi } from "vitest";

const sidecarGet = vi.fn();

vi.mock("@/lib/sidecar-client", () => ({
  sidecarGet: (...args: unknown[]) => sidecarGet(...args),
}));

import {
  applyMentionPrefixes,
  insertMentionToken,
  matchMention,
  resolveMention,
  STATIC_MENTIONS,
} from "./mentions";

afterEach(() => {
  sidecarGet.mockReset();
});

describe("matchMention", () => {
  it("opens with an empty query right after an `@`", () => {
    const input = "explain @";
    expect(matchMention(input, input.length)).toEqual({ open: true, query: "" });
  });

  it("opens with the partial token under the caret", () => {
    const input = "look at @char";
    expect(matchMention(input, input.length)).toEqual({ open: true, query: "char" });
  });

  it("matches against the token boundary at the caret, not the line end", () => {
    const input = "@chart and more text";
    // caret right after `@chart`
    expect(matchMention(input, 6)).toEqual({ open: true, query: "chart" });
  });

  it("is closed when the token under the caret does not start with `@`", () => {
    const input = "plain words here";
    expect(matchMention(input, input.length)).toEqual({ open: false, query: "" });
  });

  it("closes once a space ends the mention token", () => {
    const input = "@chart ";
    expect(matchMention(input, input.length)).toEqual({ open: false, query: "" });
  });

  it("does not trigger on an email-style `@` in the middle of a word", () => {
    const input = "mail me at user@host";
    expect(matchMention(input, input.length)).toEqual({ open: false, query: "" });
  });

  it("clamps an out-of-range caret", () => {
    const input = "@news";
    expect(matchMention(input, 999)).toEqual({ open: true, query: "news" });
  });
});

describe("STATIC_MENTIONS", () => {
  it("declares the four surfaces, two scopes, and two agents", () => {
    const tokens = STATIC_MENTIONS.map((m) => m.token);
    expect(tokens).toEqual(
      expect.arrayContaining([
        "@chart",
        "@news",
        "@filings",
        "@terminal",
        "@watchlist",
        "@portfolio",
        "@analyst",
        "@quant",
      ]),
    );
    expect(STATIC_MENTIONS.filter((m) => m.kind === "surface")).toHaveLength(4);
    expect(STATIC_MENTIONS.filter((m) => m.kind === "scope")).toHaveLength(2);
    expect(STATIC_MENTIONS.filter((m) => m.kind === "agent")).toHaveLength(2);
  });

  it("carries a promptPrefix on the agent mentions only", () => {
    const analyst = STATIC_MENTIONS.find((m) => m.token === "@analyst");
    const quant = STATIC_MENTIONS.find((m) => m.token === "@quant");
    expect(analyst?.promptPrefix).toContain("fundamental analyst");
    expect(quant?.promptPrefix).toContain("quantitative analyst");
    for (const m of STATIC_MENTIONS.filter((m) => m.kind !== "agent")) {
      expect(m.promptPrefix).toBeUndefined();
    }
  });
});

describe("insertMentionToken", () => {
  it("replaces an in-progress `@token` ending at the caret (picker accept)", () => {
    const input = "look at @char";
    expect(insertMentionToken(input, input.length, "@chart")).toEqual({
      value: "look at @chart ",
      caret: "look at @chart ".length,
    });
  });

  it("inserts at the caret into an empty composer", () => {
    expect(insertMentionToken("", 0, "@watchlist")).toEqual({
      value: "@watchlist ",
      caret: 11,
    });
  });

  it("space-separates when the caret sits flush against a word (typing parity)", () => {
    const input = "compare apple";
    expect(insertMentionToken(input, input.length, "@chart")).toEqual({
      value: "compare apple @chart ",
      caret: "compare apple @chart ".length,
    });
  });

  it("does not double a space the user already typed", () => {
    const input = "compare ";
    expect(insertMentionToken(input, input.length, "@portfolio")).toEqual({
      value: "compare @portfolio ",
      caret: "compare @portfolio ".length,
    });
  });

  it("inserts mid-text, preserving the tail after the caret", () => {
    const input = "summarize  please";
    // caret between the doubled spaces
    const out = insertMentionToken(input, 10, "@news");
    expect(out.value).toBe("summarize @news  please");
    expect(out.caret).toBe("summarize @news ".length);
  });

  it("clamps an out-of-range caret to the end", () => {
    expect(insertMentionToken("abc", 999, "@quant").value).toBe("abc @quant ");
  });
});

describe("resolveMention", () => {
  it("returns only static matches for a too-short query (no resolve call)", async () => {
    const out = await resolveMention("c", "US");
    expect(sidecarGet).not.toHaveBeenCalled();
    expect(out.every((m) => m.kind !== "instrument")).toBe(true);
    // `@chart` (prefix) is present.
    expect(out.some((m) => m.token === "@chart")).toBe(true);
  });

  it("appends live instrument matches for a ticker/name query", async () => {
    sidecarGet.mockResolvedValue({
      ok: true,
      query: "GOLD",
      region: "IN",
      resolved: {
        symbol: "GOLDBEES",
        name: "Nippon India ETF Gold BeES",
        exchange: "NSE",
        region: "IN",
        asset_class: "etf",
        yahoo_symbol: "GOLDBEES.NS",
        confidence: 1,
      },
      needs_disambiguation: false,
      candidates: [
        {
          symbol: "GOLDBEES",
          name: "Nippon India ETF Gold BeES",
          exchange: "NSE",
          region: "IN",
          asset_class: "etf",
          yahoo_symbol: "GOLDBEES.NS",
          confidence: 1,
        },
      ],
    });

    const out = await resolveMention("GOLD", "IN");

    expect(sidecarGet).toHaveBeenCalledWith("/resolve", { q: "GOLD", region: "IN" });
    const instrument = out.find((m) => m.kind === "instrument");
    expect(instrument).toBeDefined();
    expect(instrument?.token).toBe("@GOLDBEES");
    expect(instrument?.label).toBe("GOLDBEES · NSE");
    expect(instrument?.description).toBe("Nippon India ETF Gold BeES");
    // The resolved best + its candidate are de-duplicated by symbol.
    expect(out.filter((m) => m.kind === "instrument")).toHaveLength(1);
  });

  it("omits instruments when resolve reports no match", async () => {
    sidecarGet.mockResolvedValue({
      ok: false,
      query: "zzzz",
      region: "US",
      message: "No instrument matched 'zzzz'.",
      resolved: null,
      needs_disambiguation: false,
      candidates: [],
    });

    const out = await resolveMention("zzzz", "US");
    expect(out.every((m) => m.kind !== "instrument")).toBe(true);
  });

  it("keeps the matching static mention when resolve reports no match", async () => {
    sidecarGet.mockResolvedValue({
      ok: false,
      query: "char",
      region: "US",
      message: "No instrument matched 'char'.",
      resolved: null,
      needs_disambiguation: false,
      candidates: [],
    });

    // `char` prefix-matches `@chart` (a static surface) so the picker is never
    // empty even though the resolve missed.
    const out = await resolveMention("char", "US");
    expect(out.some((m) => m.token === "@chart")).toBe(true);
    expect(out.every((m) => m.kind !== "instrument")).toBe(true);
  });

  it("degrades to static matches when the resolve call throws", async () => {
    sidecarGet.mockRejectedValue(new Error("network down"));
    // `port` prefix-matches `@portfolio`; the thrown resolve never empties it.
    const out = await resolveMention("port", "US");
    expect(out.some((m) => m.token === "@portfolio")).toBe(true);
    expect(out.every((m) => m.kind !== "instrument")).toBe(true);
  });
});

describe("applyMentionPrefixes", () => {
  it("returns the message untouched when there's no agent mention", () => {
    expect(applyMentionPrefixes("what's NVDA's moat?")).toBe("what's NVDA's moat?");
  });

  it("strips @analyst and prepends the fundamental-analyst prefix", () => {
    expect(applyMentionPrefixes("@analyst is NVDA overvalued?")).toBe(
      "[Act as a fundamental analyst] is NVDA overvalued?",
    );
  });

  it("strips @quant and prepends the quantitative-analyst prefix", () => {
    expect(applyMentionPrefixes("size a position @quant")).toBe(
      "[Act as a quantitative analyst] size a position",
    );
  });

  it("stacks both prefixes in catalog order when both mentions appear", () => {
    const out = applyMentionPrefixes("@quant @analyst compare these");
    expect(out).toBe(
      "[Act as a fundamental analyst] [Act as a quantitative analyst] compare these",
    );
  });

  it("leaves surface/scope/instrument mentions in place", () => {
    // Only the agent layer rewrites the prompt; @chart / @AAPL stay for the
    // context layer to consume.
    expect(applyMentionPrefixes("@analyst look at @chart for @AAPL")).toBe(
      "[Act as a fundamental analyst] look at @chart for @AAPL",
    );
  });

  it("only matches a whole-word token (not @analysts)", () => {
    expect(applyMentionPrefixes("the @analysts disagree")).toBe("the @analysts disagree");
  });

  it("is case-insensitive on the token", () => {
    expect(applyMentionPrefixes("@Analyst thoughts?")).toBe(
      "[Act as a fundamental analyst] thoughts?",
    );
  });
});
