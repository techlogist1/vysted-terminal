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
});
