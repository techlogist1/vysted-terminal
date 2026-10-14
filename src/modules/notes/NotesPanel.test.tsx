import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { applyHostAction } from "@/lib/host-actions";
import { useNotesStore } from "@/store/notes";
import { defaultSymbolsForRegion, useSymbolsStore } from "@/store/symbols";
import { useWorkspaceStore } from "@/store/workspace";

import { NotesPanel } from "./NotesPanel";

// The fixtures below are written against the US watchlist; the app default is
// IN (R15-UI-076), so seed the US list explicitly.
const US_SYMBOLS = defaultSymbolsForRegion("US");

/** The Tiptap editor behind the rendered ProseMirror view. */
function editorOf(): Editor {
  return (document.querySelector(".ProseMirror") as unknown as { editor: Editor }).editor;
}

function markdown(): string {
  return (editorOf() as unknown as { getMarkdown: () => string }).getMarkdown();
}

async function renderPanel(): Promise<void> {
  render(<NotesPanel />);
  await waitFor(() => expect(document.querySelector(".ProseMirror")).not.toBeNull());
  vi.useFakeTimers();
}

/** A user keystroke: a content change that emits an editor update. */
function type(text: string): void {
  act(() => {
    editorOf().commands.insertContent(text);
  });
}

describe("NotesPanel — the notes store is authoritative", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    useSymbolsStore.setState({ entries: [...US_SYMBOLS] });
  });

  it("shows an agent write_note into the open note, and the next keystroke keeps it", async () => {
    useNotesStore.setState({ general: "My thesis.", bySymbol: {}, focusSymbol: "" });
    await renderPanel();
    expect(markdown()).toContain("My thesis.");

    act(() => {
      applyHostAction("write_note", { scope: "global", text: "Agent takeaway." });
    });
    expect(markdown()).toContain("Agent takeaway.");

    type("Mine ");
    act(() => {
      vi.advanceTimersByTime(600);
    });
    const saved = useNotesStore.getState().general;
    expect(saved).toContain("My thesis.");
    expect(saved).toContain("Agent takeaway.");
    expect(saved).toContain("Mine");
  });

  it("a scope switch inside the debounce window saves each scope's own text", async () => {
    useNotesStore.setState({
      general: "",
      bySymbol: { AAPL: "a", MSFT: "m" },
      focusSymbol: "AAPL",
    });
    await renderPanel();

    type("X");
    act(() => {
      useNotesStore.getState().setFocusSymbol("MSFT");
    });
    expect(useNotesStore.getState().bySymbol.AAPL).toContain("X");
    expect(useNotesStore.getState().bySymbol.MSFT).toBe("m");
    expect(markdown()).toBe("m");

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(useNotesStore.getState().bySymbol.MSFT).toBe("m");
  });

  it("R15-UI-050: a slash-menu row never carries a fixed h-8 (two-line rows clip)", async () => {
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    await renderPanel();

    act(() => {
      document.dispatchEvent(
        new CustomEvent("notes:slash-menu", {
          detail: {
            items: [{ title: "Heading 1", description: "Large section heading", action: vi.fn() }],
            rect: { bottom: 10, left: 10, top: 0, right: 0, width: 0, height: 0 } as DOMRect,
            query: "",
            command: vi.fn(),
          },
        }),
      );
    });

    const row = screen.getByText("Heading 1").closest("button");
    expect(row).not.toBeNull();
    const classes = row!.className.split(/\s+/);
    expect(classes).not.toContain("h-8");
    expect(classes).toContain("min-h-8");
  });

  // R15-UI-024 repro d: getWikiSymbols used to close over the render-time
  // `symbolEntries` prop, captured once when `useEditor`'s extensions array
  // was built at mount — a symbol added to the watchlist afterwards never
  // appeared in the "[[" picker. It now reads `useSymbolsStore.getState()`
  // live on every open.
  it("R15-UI-024: the [[ picker offers a symbol added to the watchlist AFTER mount", async () => {
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
    useSymbolsStore.setState({ entries: [...US_SYMBOLS] });
    await renderPanel();

    act(() => {
      useSymbolsStore.getState().addSymbol("TCS.NS", "equity");
    });

    act(() => {
      editorOf().commands.insertContent("[[");
    });
    // @tiptap/suggestion's plugin view `update()` hook is async (it awaits
    // `items()`), so the popup-opening `onStart` callback lands on a
    // microtask after this transaction, not inside it.
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(screen.getByText("TCS.NS")).toBeInTheDocument();
  });
});
