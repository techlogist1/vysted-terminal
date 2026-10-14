import { describe, expect, it, vi } from "vitest";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
  sidecarGet: vi.fn(),
}));

import { applyHostAction, applyIntentAsync, describeIntent, parseHostAction } from "@/lib/host-actions";
import { useNotesStore } from "@/store/notes";
import { useWorkspaceStore } from "@/store/workspace";

describe("vshard0 R15-CODE-FRONTEND-003", () => {
  it("literal: mode-less write_note appends", () => {
    useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
    useNotesStore.setState({ general: "", bySymbol: { NVDA: "my long thesis" }, focusSymbol: "" });
    const r = applyHostAction("write_note", { scope: "NVDA", text: "new line" });
    console.log("literal ack:", r, "note:", JSON.stringify(useNotesStore.getState().bySymbol.NVDA));
    expect(useNotesStore.getState().bySymbol.NVDA).toBe("my long thesis\n\nnew line");
  });
  for (const mode of [null, "", "Replace", "APPEND", "overwrite", 1]) {
    it(`fresh: mode=${JSON.stringify(mode)} via parse->describe->applyIntentAsync`, async () => {
      useWorkspaceStore.setState({ openPanel: vi.fn() } as never);
      useNotesStore.setState({ general: "", bySymbol: { INFY: "two-page note" }, focusSymbol: "" });
      const intent = parseHostAction("write_note", { scope: "INFY", text: "x", mode });
      const d = describeIntent(intent);
      const res = await applyIntentAsync(intent);
      console.log(`mode=${JSON.stringify(mode)} title=${d.title} after=${d.after} res=${JSON.stringify(res)} note=${JSON.stringify(useNotesStore.getState().bySymbol.INFY)}`);
      expect(useNotesStore.getState().bySymbol.INFY).toBe("two-page note\n\nx");
    });
  }
});
