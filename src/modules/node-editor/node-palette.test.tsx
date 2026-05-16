import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { NodeSpec } from "../../../types/plugin";
import { buildRegistry } from "./node-registry";
import { NODE_DRAG_MIME, NodePalette } from "./node-palette";

afterEach(() => {
  cleanup();
});

const pluginNode: NodeSpec = {
  id: "tradesa.wait-for-decision",
  label: "Wait for Decision",
  category: "trigger",
  inputs: [],
  outputs: [{ id: "decision", label: "Decision", type: "object" }],
  description: "Block until Tradesa emits a decision event.",
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

  it("renders plugin-contributed nodes alongside built-ins and surfaces the plugin badge", () => {
    const registry = buildRegistry([pluginNode]);
    render(<NodePalette registry={registry} />);
    expect(screen.getByTestId(`palette-card-${pluginNode.id}`)).toBeInTheDocument();
    // The plugin section also renders separately so the user can spot
    // plugin-contributed nodes at a glance.
    expect(screen.getByTestId("palette-section-plugin")).toBeInTheDocument();
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
