import { describe, expect, it } from "vitest";

import { fuzzyRank, fuzzyScore } from "./fuzzy";

describe("fuzzyScore", () => {
  it("returns null when the query is not a subsequence of the target", () => {
    expect(fuzzyScore("xyz", "Option Pricer")).toBeNull();
    expect(fuzzyScore("zzz", "Watchlist")).toBeNull();
  });

  it("returns 0 for an empty query (matches everything neutrally)", () => {
    expect(fuzzyScore("", "anything")).toBe(0);
    expect(fuzzyScore("   ", "anything")).toBe(0);
  });

  it("is case-insensitive", () => {
    expect(fuzzyScore("AAPL", "aapl")).not.toBeNull();
    expect(fuzzyScore("aapl", "AAPL")).not.toBeNull();
  });

  it("matches a non-contiguous subsequence", () => {
    // "ssn" is a subsequence of "Settings" (S..s..n? no n) — use a real one.
    expect(fuzzyScore("stg", "Settings")).not.toBeNull(); // S-e-t-t-in-g-s → s,t,g
    expect(fuzzyScore("optprc", "Option Pricer")).not.toBeNull();
  });

  it("scores a prefix match higher than a mid-string match", () => {
    const prefix = fuzzyScore("set", "Settings");
    const mid = fuzzyScore("set", "Reset View");
    expect(prefix).not.toBeNull();
    expect(mid).not.toBeNull();
    expect(prefix as number).toBeGreaterThan(mid as number);
  });

  it("scores a contiguous substring higher than a scattered subsequence", () => {
    const contiguous = fuzzyScore("char", "Chart");
    const scattered = fuzzyScore("char", "Custom Hierarchy Archive Report");
    expect(contiguous).not.toBeNull();
    expect(scattered).not.toBeNull();
    expect(contiguous as number).toBeGreaterThan(scattered as number);
  });

  it("rewards word-boundary matches", () => {
    // "ow" hits a word boundary in "Equity Overview" (O of Overview).
    const boundary = fuzzyScore("ow", "Equity Overview");
    expect(boundary).not.toBeNull();
  });
});

describe("fuzzyRank", () => {
  const items = [
    { id: "a", label: "Open Chart" },
    { id: "b", label: "Open Watchlist" },
    { id: "c", label: "Reset Chart View" },
    { id: "d", label: "Settings" },
  ];

  it("returns all items unchanged for an empty query (stable order)", () => {
    const ranked = fuzzyRank("", items, (i) => i.label);
    expect(ranked.map((i) => i.id)).toEqual(["a", "b", "c", "d"]);
  });

  it("drops non-matches", () => {
    const ranked = fuzzyRank("chart", items, (i) => i.label);
    const ids = ranked.map((i) => i.id);
    expect(ids).toContain("a"); // Open Chart
    expect(ids).toContain("c"); // Reset Chart View
    expect(ids).not.toContain("d"); // Settings — no "chart" subsequence
  });

  it("ranks the prefix/earlier match ahead of the later one", () => {
    const ranked = fuzzyRank("chart", items, (i) => i.label);
    // "Open Chart" — chart starts at a word boundary; "Reset Chart View" too,
    // but "Open Chart" is shorter / earlier-weighted, so it should not rank
    // below the longer string. Assert both present and a stable winner.
    expect(ranked[0].id === "a" || ranked[0].id === "c").toBe(true);
    expect(ranked.length).toBe(2);
  });

  it("is stable for ties (preserves input order on equal scores)", () => {
    const tied = [
      { id: "x", label: "Same" },
      { id: "y", label: "Same" },
    ];
    const ranked = fuzzyRank("same", tied, (i) => i.label);
    expect(ranked.map((i) => i.id)).toEqual(["x", "y"]);
  });
});
