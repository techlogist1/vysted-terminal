/**
 * ScreenerFormulaLeaf tests (R7 Pillar 3) — the formula editor surface:
 * caret-position inline errors, the field-name prefix dropdown (keyboard +
 * mouse), and the one-click example chips.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { compileScreenerExpr } from "@/lib/screener-expr";
import { useScreenerStore } from "@/store/screener";

import { ScreenerFormulaLeaf } from "./ScreenerFormulaLeaf";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** Type into the input, placing the caret at the end (jsdom default). */
function type(value: string) {
  const input = screen.getByTestId("screener-formula-input") as HTMLInputElement;
  fireEvent.change(input, { target: { value } });
  return input;
}

describe("ScreenerFormulaLeaf", () => {
  it("renders without an error for a blank formula", () => {
    render(<ScreenerFormulaLeaf />);
    expect(screen.queryByTestId("screener-formula-error")).not.toBeInTheDocument();
  });

  it("shows a caret-position error line for an invalid formula", () => {
    render(<ScreenerFormulaLeaf />);
    const src = "pe < 15 and bogus > 1";
    type(src);
    const error = screen.getByTestId("screener-formula-error");
    const [exprLine, caretLine] = error.textContent!.split("\n");
    expect(exprLine).toBe(src);
    // The ^ sits exactly under the offending identifier.
    expect(caretLine!.indexOf("^")).toBe(src.indexOf("bogus"));
    expect(caretLine).toContain("unknown field 'bogus'");
  });

  it("lists the referenced canonical fields for a valid formula", () => {
    render(<ScreenerFormulaLeaf />);
    type("pe < 15 and roe > 0.2");
    expect(screen.getByText(/Fields: pe_ratio, roe/)).toBeInTheDocument();
  });

  describe("autocomplete", () => {
    it("opens a prefix dropdown while typing an identifier", () => {
      render(<ScreenerFormulaLeaf />);
      type("mar");
      const list = screen.getByTestId("screener-formula-suggestions");
      expect(list).toBeInTheDocument();
      expect(screen.getByTestId("screener-formula-suggestion-market_cap")).toBeInTheDocument();
    });

    it("does not open after a complete expression (caret on whitespace)", () => {
      render(<ScreenerFormulaLeaf />);
      type("pe < 15 ");
      expect(screen.queryByTestId("screener-formula-suggestions")).not.toBeInTheDocument();
    });

    it("Enter accepts the highlighted suggestion and completes the field", () => {
      render(<ScreenerFormulaLeaf />);
      const input = type("divid");
      fireEvent.keyDown(input, { key: "Enter" });
      expect(useScreenerStore.getState().formula).toBe("dividend_yield");
    });

    it("ArrowDown moves the highlight before accepting", () => {
      render(<ScreenerFormulaLeaf />);
      const input = type("pe");
      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(1);
      fireEvent.keyDown(input, { key: "ArrowDown" });
      fireEvent.keyDown(input, { key: "Enter" });
      expect(useScreenerStore.getState().formula).toBe(
        options[1]!.querySelector("span")!.textContent,
      );
    });

    it("Escape dismisses the dropdown", () => {
      render(<ScreenerFormulaLeaf />);
      const input = type("mar");
      fireEvent.keyDown(input, { key: "Escape" });
      expect(screen.queryByTestId("screener-formula-suggestions")).not.toBeInTheDocument();
    });

    it("mouse pick inserts the suggestion", () => {
      render(<ScreenerFormulaLeaf />);
      type("debt");
      fireEvent.mouseDown(screen.getByTestId("screener-formula-suggestion-debt_to_equity"));
      expect(useScreenerStore.getState().formula).toBe("debt_to_equity");
    });
  });

  describe("example chips", () => {
    it("renders three one-click examples that all parse", () => {
      render(<ScreenerFormulaLeaf />);
      for (const i of [0, 1, 2]) {
        const chip = screen.getByTestId(`screener-formula-example-${i}`);
        const formula = chip.getAttribute("title")!;
        expect(compileScreenerExpr(formula).ok).toBe(true);
      }
    });

    it("clicking a chip writes its formula into the store", () => {
      render(<ScreenerFormulaLeaf />);
      const chip = screen.getByTestId("screener-formula-example-0");
      fireEvent.click(chip);
      expect(useScreenerStore.getState().formula).toBe(chip.getAttribute("title"));
      // And it renders valid (no error block).
      expect(screen.queryByTestId("screener-formula-error")).not.toBeInTheDocument();
    });
  });
});
