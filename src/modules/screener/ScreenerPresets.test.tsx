/**
 * ScreenerPresets tests.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { useScreenerStore } from "@/store/screener";

import { ScreenerPresets } from "./ScreenerPresets";

vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: vi.fn().mockResolvedValue("http://127.0.0.1:9000"),
  sidecarGet: vi.fn(),
}));

// `__resetForTests` doesn't rebuild actions — stub `runScreener` so applying a
// preset never fires a real network call, and restore it afterward so the
// stub doesn't leak into other test files' shared store instance.
const ORIGINAL_RUN_SCREENER = useScreenerStore.getState().runScreener;

beforeEach(() => {
  useScreenerStore.getState().__resetForTests();
  useScreenerStore.setState({ runScreener: vi.fn(async () => null) });
});

afterEach(() => {
  useScreenerStore.setState({ runScreener: ORIGINAL_RUN_SCREENER });
  vi.restoreAllMocks();
});

describe("ScreenerPresets", () => {
  it("R15-UI-007: a preset resets a nested group + formula, not just criteria", () => {
    // A draft with BOTH a nested group (which supersedes flat criteria) and a
    // formula (AND-combined) — the exact "old group and formula still ride"
    // defect shape.
    useScreenerStore.setState({
      advanced: true,
      group: {
        combinator: "or",
        criteria: [
          {
            combinator: "and",
            criteria: [{ field: "roe", operator: "gt", value: 0.5 }],
          },
        ],
      },
      formula: "pe_ratio < 5",
      combinator: "or",
      universe: "nifty50",
    });

    render(<ScreenerPresets />);
    fireEvent.click(screen.getByRole("button", { name: "Sound value" }));

    const state = useScreenerStore.getState();
    expect(state.group).toBeNull();
    expect(state.advanced).toBe(false);
    expect(state.formula).toBe("");
    expect(state.combinator).toBe("and");
    expect(state.universe).toBe("sp500");
    expect(state.criteria).toEqual([
      { field: "pe_ratio", operator: "gt", value: 0 },
      { field: "pe_ratio", operator: "lt", value: 15 },
      { field: "roe", operator: "gt", value: 0.12 },
      { field: "debt_to_equity", operator: "lt", value: 1.0 },
    ]);
    expect(state.runScreener).toHaveBeenCalledTimes(1);
  });
});
