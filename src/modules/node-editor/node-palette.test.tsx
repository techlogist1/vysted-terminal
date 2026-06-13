import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import type { NodeSpec } from "../../../types/plugin";
import { buildRegistry } from "./node-registry";
import { NODE_DRAG_MIME, NodePalette } from "./node-palette";

afterEach(() => {
  cleanup();
});

const pluginNode: NodeSpec = {
  id: "example.wait-for-decision",
  label: "Wait for Decision",
  category: "trigger",
  inputs: [],
  outputs: [{ id: "decision", label: "Decision", type: "object" }],
  description: "Block until an external source emits a decision event.",
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
    expect(screen.getByTestId(`palette-card-${pluginNode.id}`)).toBeInTheDocument();
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

  it("offers every first-party kind — code node and v0.6.0 sidecar kinds included", () => {
    render(<NodePalette registry={buildRegistry([])} />);
    expect(screen.getByTestId("palette-card-transform.code")).toBeInTheDocument();
    expect(screen.getByTestId("palette-card-data.fetch_macro_series")).toBeInTheDocument();
    expect(screen.getByTestId("palette-card-quant.price_option")).toBeInTheDocument();
    expect(screen.getByTestId("palette-card-analysis.screener_query")).toBeInTheDocument();
    expect(screen.getByTestId("node-palette-count")).toHaveTextContent("23");
  });

  it("shows the search input once the registry exceeds 12 kinds", () => {
    render(<NodePalette registry={buildRegistry([])} />);
    expect(screen.getByTestId("node-palette-search")).toBeInTheDocument();
  });

  it("hides the search input for a small registry", () => {
    const registry = buildRegistry([]).slice(0, 5);
    render(<NodePalette registry={registry} />);
    expect(screen.queryByTestId("node-palette-search")).not.toBeInTheDocument();
  });

  it("filters cards by label / id / description and shows the filtered count", () => {
    render(<NodePalette registry={buildRegistry([])} />);
    fireEvent.change(screen.getByTestId("node-palette-search"), {
      target: { value: "earnings" },
    });
    expect(screen.getByTestId("palette-card-data.fetch_earnings_calendar")).toBeInTheDocument();
    expect(screen.getByTestId("palette-card-data.fetch_earnings_history")).toBeInTheDocument();
    expect(screen.queryByTestId("palette-card-data.fetch_quote")).not.toBeInTheDocument();
    expect(screen.getByTestId("node-palette-count")).toHaveTextContent("2/23");
  });

  it("matches the code node by description keywords", () => {
    render(<NodePalette registry={buildRegistry([])} />);
    fireEvent.change(screen.getByTestId("node-palette-search"), {
      target: { value: "expression" },
    });
    expect(screen.getByTestId("palette-card-transform.code")).toBeInTheDocument();
  });

  it("renders an honest empty state when nothing matches", () => {
    render(<NodePalette registry={buildRegistry([])} />);
    fireEvent.change(screen.getByTestId("node-palette-search"), {
      target: { value: "zzz-no-such-node" },
    });
    expect(screen.getByTestId("node-palette-empty")).toBeInTheDocument();
    expect(screen.queryByTestId("palette-category-trigger")).not.toBeInTheDocument();
  });
});
