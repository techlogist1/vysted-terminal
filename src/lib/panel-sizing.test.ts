import { describe, expect, it, vi } from "vitest";

import { collectPanels } from "@/lib/module-registry";
import { PANEL_MIN_SIZE } from "@/lib/panel-sizing";
import { vystedModules } from "@/modules";

// Only component ids matter here; keep the tiptap editor bundle out of the import graph.
vi.mock("@/modules/notes/NotesPanel", () => ({ NotesPanel: () => null }));

describe("PANEL_MIN_SIZE parity (R15-CODE-FRONTEND-025)", () => {
  const components = new Set(collectPanels(vystedModules).map((panel) => panel.component));

  it("every key is a registered panel component", () => {
    expect(Object.keys(PANEL_MIN_SIZE).filter((key) => !components.has(key))).toEqual([]);
  });

  it("every registered panel component has an entry", () => {
    expect([...components].filter((component) => !(component in PANEL_MIN_SIZE))).toEqual([]);
  });
});
