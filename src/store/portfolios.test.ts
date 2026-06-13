import { beforeEach, describe, expect, it } from "vitest";

import {
  addPosition,
  deletePosition,
  refresh,
  updatePosition,
  usePortfoliosStore,
  type HoldingInput,
} from "./portfolios";

/**
 * The typed portfolio write client (R10, E6) the host-action apply path drives
 * for agent portfolio writes. These tests pin the HONEST-FAILURE contract: a
 * rejected input returns null/false so the apply path narrates a real failure
 * instead of a write that never landed (the E3/E6 defect class this seam exists
 * to kill). Holdings are LOCAL state (workspace blob) — no sidecar round-trip.
 */

const RELIANCE: HoldingInput = {
  symbol: "RELIANCE",
  quantity: 5,
  costBasis: 1263,
  assetClass: "equity",
};

beforeEach(() => {
  // Reset to a single empty default portfolio.
  usePortfoliosStore.setState({
    portfolios: [{ id: "default", name: "Portfolio", holdings: [] }],
    activeId: "default",
  });
});

describe("addPosition", () => {
  it("appends to the active portfolio and returns the genuine holding id", () => {
    const id = addPosition(RELIANCE);
    expect(typeof id).toBe("string");
    const holdings = usePortfoliosStore.getState().portfolios[0].holdings;
    expect(holdings).toHaveLength(1);
    expect(holdings[0]).toMatchObject({ symbol: "RELIANCE", quantity: 5, costBasis: 1263 });
    expect(holdings[0].id).toBe(id);
  });

  it("returns null (no fabricated success) when the symbol is empty/whitespace", () => {
    expect(addPosition({ ...RELIANCE, symbol: "   " })).toBeNull();
    expect(usePortfoliosStore.getState().portfolios[0].holdings).toHaveLength(0);
  });

  it("uppercases + trims the symbol via the store normalizer", () => {
    const id = addPosition({ ...RELIANCE, symbol: "  infy  " });
    expect(id).not.toBeNull();
    expect(usePortfoliosStore.getState().portfolios[0].holdings[0].symbol).toBe("INFY");
  });
});

describe("updatePosition", () => {
  it("updates an existing holding and returns true", () => {
    const id = addPosition(RELIANCE)!;
    const ok = updatePosition(id, { ...RELIANCE, quantity: 10, costBasis: 1300 });
    expect(ok).toBe(true);
    const holding = usePortfoliosStore.getState().portfolios[0].holdings.find((h) => h.id === id);
    expect(holding).toMatchObject({ quantity: 10, costBasis: 1300 });
  });

  it("returns false when the holding id does not exist (no fabricated success)", () => {
    expect(updatePosition("nonexistent", RELIANCE)).toBe(false);
  });

  it("returns false when normalizeHolding rejects the input (empty symbol)", () => {
    const id = addPosition(RELIANCE)!;
    expect(updatePosition(id, { ...RELIANCE, symbol: "" })).toBe(false);
    // The original holding is untouched.
    const holding = usePortfoliosStore.getState().portfolios[0].holdings.find((h) => h.id === id);
    expect(holding?.symbol).toBe("RELIANCE");
  });
});

describe("deletePosition", () => {
  it("removes the holding from the active portfolio", () => {
    const id = addPosition(RELIANCE)!;
    expect(usePortfoliosStore.getState().portfolios[0].holdings).toHaveLength(1);
    deletePosition(id);
    expect(usePortfoliosStore.getState().portfolios[0].holdings).toHaveLength(0);
  });

  it("is a no-op for an unknown id (never throws)", () => {
    addPosition(RELIANCE);
    expect(() => deletePosition("nope")).not.toThrow();
    expect(usePortfoliosStore.getState().portfolios[0].holdings).toHaveLength(1);
  });
});

describe("refresh", () => {
  it("is a no-op for local-state portfolios (no throw)", () => {
    expect(() => refresh()).not.toThrow();
  });
});
