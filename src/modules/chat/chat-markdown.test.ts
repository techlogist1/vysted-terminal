import { describe, expect, it } from "vitest";

import { normalizePipeTables, stripTableRows } from "./chat-markdown";

describe("normalizePipeTables", () => {
  it("synthesizes a separator under a separator-less pipe table (the wall-of-pipes fix)", () => {
    const src = ["Intro line.", "| Metric | Value |", "| P/E | 31.2 |", "| EPS | 6.42 |"].join(
      "\n",
    );
    const out = normalizePipeTables(src);
    expect(out.split("\n")).toEqual([
      "Intro line.",
      "| Metric | Value |",
      "| --- | --- |",
      "| P/E | 31.2 |",
      "| EPS | 6.42 |",
    ]);
  });

  it("sizes the synthesized separator to the header's column count", () => {
    const src = "| A | B | C |\n| 1 | 2 | 3 |";
    expect(normalizePipeTables(src).split("\n")[1]).toBe("| --- | --- | --- |");
  });

  it("leaves a well-formed GFM table byte-identical", () => {
    const src = "| A | B |\n| --- | --- |\n| 1 | 2 |";
    expect(normalizePipeTables(src)).toBe(src);
  });

  it("is idempotent", () => {
    const src = "| Metric | Value |\n| P/E | 31.2 |";
    const once = normalizePipeTables(src);
    expect(normalizePipeTables(once)).toBe(once);
  });

  it("never touches pipes inside fenced code", () => {
    const src = ["```", "| not | a | table |", "| still | not | one |", "```"].join("\n");
    expect(normalizePipeTables(src)).toBe(src);
  });

  it("leaves a lone pipe row alone (a still-streaming table header)", () => {
    const src = "Some prose.\n| Metric | Value |";
    expect(normalizePipeTables(src)).toBe(src);
  });

  it("handles two separate separator-less tables in one message", () => {
    const src = ["| A | B |", "| 1 | 2 |", "", "prose", "", "| C | D |", "| 3 | 4 |"].join("\n");
    const out = normalizePipeTables(src).split("\n");
    expect(out[1]).toBe("| --- | --- |");
    expect(out[7]).toBe("| --- | --- |");
  });

  it("returns pipe-free text unchanged (fast path)", () => {
    const src = "plain prose, no tables at all";
    expect(normalizePipeTables(src)).toBe(src);
  });
});

describe("stripTableRows", () => {
  it("drops table rows and separators, keeping the prose", () => {
    const src = ["NVDA looks rich.", "| Metric | Value |", "| --- | --- |", "More prose."].join(
      "\n",
    );
    expect(stripTableRows(src)).toBe("NVDA looks rich.\nMore prose.");
  });

  it("leaves pipe-free text unchanged", () => {
    expect(stripTableRows("nothing tabular here")).toBe("nothing tabular here");
  });
});
