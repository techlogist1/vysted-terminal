import { act, cleanup, render, waitFor } from "@testing-library/react";
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
});
