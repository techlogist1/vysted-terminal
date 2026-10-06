import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { Editor } from "@tiptap/core";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useNotesStore } from "@/store/notes";
import { useWorkspaceStore } from "@/store/workspace";

import { NotesPanel } from "./NotesPanel";

/**
 * R15-UI-025: the toolbar's Link button used `window.prompt`, which the Tauri
 * WKWebView does not implement (it returns null — silently treated as a
 * cancel). It now opens an inline popover instead. Exercised through the real
 * `NotesPanel` (as `NotesPanel.test.tsx` does) so the toolbar runs against a
 * real Tiptap editor rather than a hand-rolled mock.
 */

function editorOf(): Editor {
  return (document.querySelector(".ProseMirror") as unknown as { editor: Editor }).editor;
}

async function renderPanel(): Promise<void> {
  render(<NotesPanel />);
  await waitFor(() => expect(document.querySelector(".ProseMirror")).not.toBeNull());
}

describe("NotesToolbar — Link", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
  });

  afterEach(() => {
    cleanup();
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
  });

  it("opens an inline popover and applies the link mark, never window.prompt", async () => {
    const promptSpy = vi.spyOn(window, "prompt");
    await renderPanel();

    act(() => {
      editorOf().commands.insertContent("Example");
      editorOf().commands.setTextSelection({ from: 1, to: 8 });
    });

    fireEvent.click(screen.getByRole("button", { name: "Link" }));
    const input = await screen.findByLabelText("Link URL");
    fireEvent.change(input, { target: { value: "https://vysted.dev" } });
    fireEvent.click(screen.getByRole("button", { name: "Apply" }));

    expect(editorOf().isActive("link")).toBe(true);
    expect(editorOf().getAttributes("link").href).toBe("https://vysted.dev");
    expect(screen.queryByLabelText("Link URL")).not.toBeInTheDocument();
    expect(promptSpy).not.toHaveBeenCalled();
  });

  it("Remove clears an existing link mark", async () => {
    await renderPanel();
    act(() => {
      editorOf().commands.insertContent("Example");
      editorOf().commands.setTextSelection({ from: 1, to: 8 });
      editorOf().chain().focus().setLink({ href: "https://old.example" }).run();
    });

    fireEvent.click(screen.getByRole("button", { name: "Link" }));
    fireEvent.click(await screen.findByRole("button", { name: "Remove" }));

    expect(editorOf().isActive("link")).toBe(false);
  });
});

describe("NotesToolbar — R15-UI-024", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
  });

  afterEach(() => {
    cleanup();
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
  });

  it("the Task list button toggles a task list (extension is registered)", async () => {
    await renderPanel();
    act(() => {
      editorOf().commands.insertContent("Buy milk");
    });

    fireEvent.click(screen.getByRole("button", { name: "Task list" }));

    expect(editorOf().isActive("taskList")).toBe(true);
  });

  it("Insert [[wikilink]] WRAPS a selection instead of deleting it (repro e)", async () => {
    await renderPanel();
    act(() => {
      editorOf().commands.insertContent("alpha beta gamma");
      editorOf().commands.setTextSelection({ from: 1, to: 6 }); // "alpha"
    });

    fireEvent.click(screen.getByRole("button", { name: "Insert [[wikilink]]" }));

    const md = (editorOf() as unknown as { getMarkdown: () => string }).getMarkdown();
    expect(md).toContain("[[ALPHA]]");
    expect(md).toContain("beta gamma");
  });

  it("Insert [[wikilink]] with no selection still opens the picker (falls back to '[[')", async () => {
    await renderPanel();
    fireEvent.click(screen.getByRole("button", { name: "Insert [[wikilink]]" }));

    expect(editorOf().getText()).toBe("[[");
  });
});

describe("NotesToolbar — R15-DOCS-010", () => {
  beforeEach(() => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
  });

  afterEach(() => {
    cleanup();
    useNotesStore.setState({ general: "", bySymbol: {}, focusSymbol: "" });
  });

  it("the active toolbar button carries the fill class", async () => {
    await renderPanel();
    const boldButton = screen.getByRole("button", { name: "Bold" });
    // classList token checks: the inactive string carries hover:bg-charcoal-800,
    // so a className substring match cannot tell active from inactive.
    expect(boldButton.classList.contains("bg-charcoal-800")).toBe(false);
    expect(boldButton.getAttribute("aria-pressed")).toBe("false");

    fireEvent.click(boldButton);

    await waitFor(() => {
      expect(boldButton.classList.contains("bg-charcoal-800")).toBe(true);
      expect(boldButton.getAttribute("aria-pressed")).toBe("true");
    });
  });
});
