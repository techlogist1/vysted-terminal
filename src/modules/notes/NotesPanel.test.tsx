import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { applyHostAction } from "@/lib/host-actions";
import { useNotesStore } from "@/store/notes";
import { useWorkspaceStore } from "@/store/workspace";

import { NotesPanel } from "./NotesPanel";

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
});
