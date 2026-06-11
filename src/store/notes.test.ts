import { beforeEach, describe, expect, it } from "vitest";

import { useNotesStore } from "./notes";

describe("notes store", () => {
  beforeEach(() => useNotesStore.getState().fromBundle(null));

  it("scopes notes per symbol (case-insensitive) and a general bucket", () => {
    useNotesStore.getState().setGeneral("watch the Fed");
    useNotesStore.getState().setSymbolNote("aapl", "services margin story");
    expect(useNotesStore.getState().noteFor("")).toBe("watch the Fed");
    expect(useNotesStore.getState().noteFor("AAPL")).toBe("services margin story");
    expect(useNotesStore.getState().noteFor("aapl")).toBe("services margin story");
    expect(useNotesStore.getState().symbolsWithNotes()).toEqual(["AAPL"]);
  });

  it("round-trips through a workspace bundle", () => {
    useNotesStore.getState().setSymbolNote("MSFT", "azure growth");
    const bundle = useNotesStore.getState().toBundle();
    useNotesStore.getState().fromBundle(null);
    expect(useNotesStore.getState().noteFor("MSFT")).toBe("");
    useNotesStore.getState().fromBundle(bundle);
    expect(useNotesStore.getState().noteFor("MSFT")).toBe("azure growth");
  });

  describe("appendGeneral (R10 write_note seam)", () => {
    it("appends to an empty note without leading blank lines", () => {
      useNotesStore.getState().appendGeneral("first paragraph");
      expect(useNotesStore.getState().general).toBe("first paragraph");
    });

    it("appends with a double-newline separator when body exists", () => {
      useNotesStore.getState().setGeneral("existing content");
      useNotesStore.getState().appendGeneral("new paragraph");
      expect(useNotesStore.getState().general).toBe("existing content\n\nnew paragraph");
    });

    it("appending empty text is a no-op (existing body unchanged)", () => {
      useNotesStore.getState().setGeneral("body");
      useNotesStore.getState().appendGeneral("   ");
      expect(useNotesStore.getState().general).toBe("body");
    });

    it("does NOT trim leading indentation or trailing newlines from the existing body", () => {
      // An agent write_note append must never destroy the user's formatting.
      useNotesStore.getState().setGeneral("  indented note\n");
      useNotesStore.getState().appendGeneral("appended");
      expect(useNotesStore.getState().general).toBe("  indented note\n\n\nappended");
    });
  });

  describe("appendSymbolNote (R10 write_note seam)", () => {
    it("appends to a fresh symbol note", () => {
      useNotesStore.getState().appendSymbolNote("NVDA", "gpu dominance");
      expect(useNotesStore.getState().noteFor("NVDA")).toBe("gpu dominance");
    });

    it("appends with a separator to an existing symbol note", () => {
      useNotesStore.getState().setSymbolNote("NVDA", "first note");
      useNotesStore.getState().appendSymbolNote("nvda", "second note");
      expect(useNotesStore.getState().noteFor("NVDA")).toBe("first note\n\nsecond note");
    });

    it("empty symbol falls back to the general bucket", () => {
      useNotesStore.getState().appendSymbolNote("", "general content");
      expect(useNotesStore.getState().general).toBe("general content");
    });
  });
});
