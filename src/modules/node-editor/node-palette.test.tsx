import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { NodeSpec } from "../../../types/plugin";
import { buildRegistry } from "./node-registry";
import { NODE_DRAG_MIME, NodePalette } from "./node-palette";

afterEach(() => {
  cleanup();
});

// Generic plugin fixture — not tied to any bundled plugin.
const pluginNode: NodeSpec = {
  id: "example-plugin.wait-for-signal",
  label: "Wait for Signal",
  category: "trigger",
  inputs: [],
  outputs: [{ id: "signal", label: "Signal", type: "object" }],
  description: "Block until the plugin emits a signal event.",
};

describe("NodePalette", () => {
  it("renders one palette card per built-in node", () => {
    const registry = buildRegistry([]);
    render(<NodePalette registry={registry} />);
    expect(screen.getByTestId("palette-card-data.fetch_quote")).toBeInTheDocument();
    expect(screen.getByTestId("palette-card-flow.sleep")).toBeInTheDocument();
  });

  it("groups cards by their NodeSpec category", () => {
    const registry = buildRegistry([]);
    render(<NodePalette registry={registry} />);
    expect(screen.getByTestId("palette-category-trigger")).toBeInTheDocument();
    expect(screen.getByTestId("palette-category-transform")).toBeInTheDocument();
    expect(screen.getByTestId("palette-category-condition")).toBeInTheDocument();
    expect(screen.getByTestId("palette-category-action")).toBeInTheDocument();
  });

  it("renders plugin-contributed nodes as draggable cards in their category (no redundant flat section)", () => {
    const registry = buildRegistry([pluginNode]);
    render(<NodePalette registry={registry} />);
    // Plugin nodes render exactly once — as a draggable card within their
    // category group — not duplicated in a separate non-draggable label list.
    expect(screen.getByTestId(`palette-card-example-plugin.wait-for-signal`)).toBeInTheDocument();
    expect(screen.queryByTestId("palette-section-plugin")).not.toBeInTheDocument();
  });

  it("stamps the drag MIME type on dragstart so the canvas can identify the drop", () => {
    const registry = buildRegistry([]);
    render(<NodePalette registry={registry} />);
    const card = screen.getByTestId("palette-card-data.fetch_quote");
    const setData = (() => {
      const calls: Array<{ type: string; data: string }> = [];
      return { calls, setData: (type: string, data: string) => calls.push({ type, data }) };
    })();
    const dataTransfer = {
      setData: setData.setData,
      effectAllowed: "",
    } as unknown as DataTransfer;
    fireEvent.dragStart(card, { dataTransfer });
    expect(setData.calls.some((c) => c.type === NODE_DRAG_MIME)).toBe(true);
    expect(setData.calls.find((c) => c.type === NODE_DRAG_MIME)?.data).toBe("data.fetch_quote");
  });
});
