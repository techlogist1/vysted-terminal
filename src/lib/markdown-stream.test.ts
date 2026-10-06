import { describe, expect, it } from "vitest";

import { completeIncomplete, hasIncompleteCodeFence } from "@/lib/markdown-stream";

describe("hasIncompleteCodeFence", () => {
  it("is false for balanced fences", () => {
    expect(hasIncompleteCodeFence("```\ncode\n```")).toBe(false);
    expect(hasIncompleteCodeFence("~~~\ncode\n~~~")).toBe(false);
    expect(hasIncompleteCodeFence("no fences at all")).toBe(false);
    expect(hasIncompleteCodeFence("")).toBe(false);
  });

  it("is true for a dangling open fence", () => {
    expect(hasIncompleteCodeFence("```ts\nconst x = 1")).toBe(true);
    expect(hasIncompleteCodeFence("~~~\nstill going")).toBe(true);
  });

  it("ignores indented (non-fence) backtick runs", () => {
    // A fence cannot be indented 4+ spaces (that's an indented code block).
    expect(hasIncompleteCodeFence("    ```not a fence")).toBe(false);
  });

  it("treats a longer closing fence as a valid close", () => {
    // CommonMark: the closing fence must be at least as long as the opener.
    expect(hasIncompleteCodeFence("```\ncode\n````")).toBe(false);
  });

  it("does not close a ``` opener with a ~~~ line", () => {
    expect(hasIncompleteCodeFence("```\ncode\n~~~")).toBe(true);
  });
});

describe("completeIncomplete", () => {
  it("passes balanced input through unchanged", () => {
    const balanced = "**bold** and *italic* and `code` and a [1] cite.";
    expect(completeIncomplete(balanced)).toBe(balanced);
    const table = "| a | b |\n| --- | --- |\n| 1 | 2 |";
    expect(completeIncomplete(table)).toBe(table);
    const fenced = "```ts\nconst x = 1;\n```";
    expect(completeIncomplete(fenced)).toBe(fenced);
    expect(completeIncomplete("")).toBe("");
  });

  it("closes a dangling bold marker", () => {
    expect(completeIncomplete("a **bold")).toBe("a **bold**");
  });

  it("closes a dangling italic marker", () => {
    expect(completeIncomplete("a *italic")).toBe("a *italic*");
  });

  it("closes a dangling inline-code backtick", () => {
    expect(completeIncomplete("a `code")).toBe("a `code`");
  });

  it("appends a synthetic close fence for an open code block", () => {
    const out = completeIncomplete("```ts\nconst x = 1");
    expect(hasIncompleteCodeFence(out)).toBe(false);
    expect(out.endsWith("\n```")).toBe(true);
  });

  it("completes half of a streaming table (header + separator, no rows yet)", () => {
    // The table is structurally renderable once the separator row arrives; the
    // completer must not corrupt it (it adds no inline markers here).
    const half = "| a | b |\n| --- | --- |";
    expect(completeIncomplete(half)).toBe(half);
  });

  it("does not double-close already-closed emphasis", () => {
    expect(completeIncomplete("**a** **b**")).toBe("**a** **b**");
    expect(completeIncomplete("`a` `b`")).toBe("`a` `b`");
  });

  it("does not mistake bold for a dangling italic", () => {
    // "**x" has an odd count of '*' runs but is a bold opener, not italic.
    expect(completeIncomplete("**x")).toBe("**x**");
  });

  it("leaves a dangling marker inside an open fence alone (fence wins)", () => {
    const out = completeIncomplete("```\n**not bold");
    // Inside a fence emphasis is literal — only the fence is closed.
    expect(out).toBe("```\n**not bold\n```");
  });

  it("ignores a literal `*` / `**` inside a balanced inline-code span", () => {
    // Emphasis parity must skip inline code, or these complete inputs corrupt.
    expect(completeIncomplete("the `**kwargs` argument")).toBe("the `**kwargs` argument");
    expect(completeIncomplete("the `**` operator")).toBe("the `**` operator");
    expect(completeIncomplete("the `*ptr` deref")).toBe("the `*ptr` deref");
    // Double-backtick spans delimit a single code span the same way.
    expect(completeIncomplete("the ``a*b`` macro")).toBe("the ``a*b`` macro");
  });

  it("treats emphasis after a dangling backtick as literal code (not unbalanced)", () => {
    // The open backtick swallows the rest as code, so the stray `**` is literal;
    // only the backtick is closed, no spurious `**` is appended.
    expect(completeIncomplete("`code with **bold inside")).toBe("`code with **bold inside`");
  });

  it("still closes a real dangling bold when a closed code span holds literal emphasis", () => {
    // `*lit*` is inside a balanced span (ignored); the leading `**` truly dangles.
    expect(completeIncomplete("real **bold and `*lit*` code")).toBe(
      "real **bold and `*lit*` code**",
    );
  });
});
