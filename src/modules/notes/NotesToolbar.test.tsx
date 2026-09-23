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
