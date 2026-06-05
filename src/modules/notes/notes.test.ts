/**
 * Notes store + markdown round-trip tests.
 *
 * Tests:
 * 1. NotesStore CRUD: setGeneral / setSymbolNote / setFocusSymbol / noteFor /
 *    symbolsWithNotes / toBundle / fromBundle.
 * 2. Markdown round-trip: markdown → Tiptap editor → getMarkdown() is stable
 *    for headings, lists, tables, and links.
 *
 * The editor tests import Tiptap headlessly (no DOM render) — Tiptap v3 supports
 * headless `Editor` construction via `@tiptap/core` with `element: undefined`.
 */

import { describe, it, expect, beforeEach } from "vitest";

import { useNotesStore, type NotesBundle } from "@/store/notes";

// ── NotesStore unit tests ─────────────────────────────────────────────────────

describe("useNotesStore", () => {
  beforeEach(() => {
    // Reset store to initial state before each test.
    useNotesStore.setState({
      general: "",
      bySymbol: {},
      focusSymbol: undefined,
    });
  });

  it("setGeneral stores markdown in general", () => {
    useNotesStore.getState().setGeneral("# Hello\n\nWorld");
    expect(useNotesStore.getState().general).toBe("# Hello\n\nWorld");
  });

  it("setSymbolNote stores per-symbol note, upper-cased", () => {
    useNotesStore.getState().setSymbolNote("aapl", "Apple note");
    expect(useNotesStore.getState().bySymbol["AAPL"]).toBe("Apple note");
  });

  it("setFocusSymbol upper-cases symbol", () => {
    useNotesStore.getState().setFocusSymbol("nvda");
    expect(useNotesStore.getState().focusSymbol).toBe("NVDA");
  });

  it('setFocusSymbol("") clears focus to general', () => {
    useNotesStore.getState().setFocusSymbol("AAPL");
    useNotesStore.getState().setFocusSymbol("");
    expect(useNotesStore.getState().focusSymbol).toBe("");
  });

  it('noteFor returns general when scope is ""', () => {
    useNotesStore.getState().setGeneral("General note");
    expect(useNotesStore.getState().noteFor("")).toBe("General note");
  });

  it("noteFor returns symbol note (case-insensitive)", () => {
    useNotesStore.getState().setSymbolNote("MSFT", "MSFT note");
    expect(useNotesStore.getState().noteFor("msft")).toBe("MSFT note");
  });

  it("noteFor returns empty string for unknown symbol", () => {
    expect(useNotesStore.getState().noteFor("UNKNOWN")).toBe("");
  });

  it("symbolsWithNotes returns only symbols with non-empty notes", () => {
    useNotesStore.getState().setSymbolNote("AAPL", "Apple note");
    useNotesStore.getState().setSymbolNote("MSFT", "");
    useNotesStore.getState().setSymbolNote("NVDA", "  "); // whitespace-only
    const syms = useNotesStore.getState().symbolsWithNotes();
    expect(syms).toContain("AAPL");
    expect(syms).not.toContain("MSFT");
    expect(syms).not.toContain("NVDA");
  });

  it("toBundle / fromBundle round-trips the state", () => {
    useNotesStore.getState().setGeneral("# General");
    useNotesStore.getState().setSymbolNote("SPY", "SPY note");
    useNotesStore.getState().setFocusSymbol("SPY");

    const bundle = useNotesStore.getState().toBundle();
    expect(bundle.general).toBe("# General");
    expect(bundle.bySymbol["SPY"]).toBe("SPY note");
    expect(bundle.focusSymbol).toBe("SPY");

    // Reset and restore.
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: undefined });
    useNotesStore.getState().fromBundle(bundle);
    expect(useNotesStore.getState().general).toBe("# General");
    expect(useNotesStore.getState().noteFor("SPY")).toBe("SPY note");
    expect(useNotesStore.getState().focusSymbol).toBe("SPY");
  });

  it("fromBundle handles missing fields gracefully (older blobs)", () => {
    const partial: NotesBundle = { general: "hi", bySymbol: {} };
    useNotesStore.getState().fromBundle(partial);
    expect(useNotesStore.getState().general).toBe("hi");
    expect(useNotesStore.getState().focusSymbol).toBe("");
  });
});

// ── Markdown round-trip tests ─────────────────────────────────────────────────
// Build a headless Tiptap editor, set content from markdown, then getMarkdown()
// and compare. Using @tiptap/core + @tiptap/markdown without React or DOM render.

describe("Tiptap markdown round-trip", () => {
  // We use dynamic import to defer Tiptap until the test runtime is ready.
  // This avoids SSR/window issues in the jsdom environment.

  async function makeEditor() {
    const { Editor } = await import("@tiptap/core");
    const { StarterKit } = await import("@tiptap/starter-kit");
    const { Table } = await import("@tiptap/extension-table");
    const { TableRow } = await import("@tiptap/extension-table-row");
    const { TableCell } = await import("@tiptap/extension-table-cell");
    const { TableHeader } = await import("@tiptap/extension-table-header");
    const { Markdown } = await import("@tiptap/markdown");

    const editor = new Editor({
      extensions: [
        StarterKit,
        Table.configure({ resizable: false }),
        TableRow,
        TableCell,
        TableHeader,
        Markdown,
      ],
      content: "",
    });

    return editor;
  }

  function getMarkdown(editor: Awaited<ReturnType<typeof makeEditor>>): string {
    return (editor as unknown as { getMarkdown: () => string }).getMarkdown();
  }

  // Helper: set markdown content using the Markdown extension's contentType option.
  function setMd(editor: Awaited<ReturnType<typeof makeEditor>>, markdown: string): boolean {
    return editor.commands.setContent(markdown, { contentType: "markdown" });
  }

  it("heading round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "# Heading 1\n\n## Heading 2\n\n### Heading 3\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    // Re-run to confirm idempotence.
    setMd(editor, output);
    const output2 = getMarkdown(editor);
    expect(output2).toBe(output);
    editor.destroy();
  });

  it("unordered list round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "- Item A\n- Item B\n- Item C\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    setMd(editor, output);
    expect(getMarkdown(editor)).toBe(output);
    editor.destroy();
  });

  it("ordered list round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "1. First\n2. Second\n3. Third\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    setMd(editor, output);
    expect(getMarkdown(editor)).toBe(output);
    editor.destroy();
  });

  it("bold + italic inline round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "This is **bold** and _italic_ text.\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    setMd(editor, output);
    expect(getMarkdown(editor)).toBe(output);
    editor.destroy();
  });

  it("inline code and code block round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "Use `const x = 1` inline.\n\n```\nconst y = 2;\n```\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    setMd(editor, output);
    expect(getMarkdown(editor)).toBe(output);
    editor.destroy();
  });

  it("link round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "See [Vysted](https://vysted.com) for more.\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    setMd(editor, output);
    expect(getMarkdown(editor)).toBe(output);
    editor.destroy();
  });

  it("blockquote round-trip is stable", async () => {
    const editor = await makeEditor();
    const input = "> This is a quote.\n";
    setMd(editor, input);
    const output = getMarkdown(editor);
    setMd(editor, output);
    expect(getMarkdown(editor)).toBe(output);
    editor.destroy();
  });

  it("table round-trip is stable", async () => {
    const editor = await makeEditor();
    // Start from a programmatic table insertion to avoid markdown-parser-input
    // variance (table headers need whitespace that differs by parser).
    editor.chain().insertTable({ rows: 2, cols: 2, withHeaderRow: true }).run();
    const first = getMarkdown(editor);
    // First→second pass must be idempotent (key SC-032 requirement).
    setMd(editor, first);
    const second = getMarkdown(editor);
    expect(second).toBe(first);
    editor.destroy();
  });

  it("empty string round-trip returns empty string", async () => {
    const editor = await makeEditor();
    setMd(editor, "");
    const output = getMarkdown(editor);
    // Empty doc returns empty string or minimal whitespace — either is fine.
    expect(output.trim()).toBe("");
    editor.destroy();
  });
});

// ── Editor mounts with the FULL NotesPanel extension set ───────────────────────
// Regression guard: the slash-command and wikilink extensions both use
// @tiptap/suggestion. Two Suggestion plugins without distinct pluginKeys collide
// on the shared default key and throw during ProseMirror state creation, crashing
// the editor mount (the round-trip tests above use only the core extensions and
// missed this). This test constructs the editor with the exact NotesPanel set.
describe("NotesPanel editor construction (suggestion-plugin keys)", () => {
  it("constructs with StarterKit + tables + markdown + slash + wikilink without throwing", async () => {
    const { Editor } = await import("@tiptap/core");
    const { StarterKit } = await import("@tiptap/starter-kit");
    const { Table } = await import("@tiptap/extension-table");
    const { TableRow } = await import("@tiptap/extension-table-row");
    const { TableCell } = await import("@tiptap/extension-table-cell");
    const { TableHeader } = await import("@tiptap/extension-table-header");
    const { Markdown } = await import("@tiptap/markdown");
    const { SlashCommandExtension } = await import("./SlashCommandExtension");
    const { WikiLinkExtension } = await import("./WikiLinkExtension");

    let editor: InstanceType<typeof Editor> | null = null;
    expect(() => {
      editor = new Editor({
        extensions: [
          StarterKit,
          Table.configure({ resizable: false }),
          TableRow,
          TableCell,
          TableHeader,
          Markdown,
          SlashCommandExtension,
          WikiLinkExtension.configure({ getSymbols: () => [] }),
        ],
        content: "",
      });
    }).not.toThrow();
    expect(editor).not.toBeNull();
    editor!.destroy();
  });
});
