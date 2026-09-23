import { beforeEach, describe, expect, it } from "vitest";

import { usePortfoliosStore, type HoldingInput } from "./portfolios";

/**
 * The portfolios store's holding writes — the ONE write path for the panel and
 * the agent's portfolio host actions alike (the dead addPosition/updatePosition/
 * deletePosition/refresh client was removed, R15-CODE-PLATFORM-022). A rejected
 * input is a no-op, never a fabricated holding.
 */

const RELIANCE: HoldingInput = {
  symbol: "RELIANCE",
  quantity: 5,
  costBasis: 1263,
  assetClass: "equity",
};

function holdings() {
  return usePortfoliosStore.getState().portfolios[0].holdings;
}

beforeEach(() => {
  usePortfoliosStore.setState({
    portfolios: [{ id: "default", name: "Portfolio", holdings: [] }],
    activeId: "default",
  });
});

describe("addHolding", () => {
  it("appends to the portfolio with a fresh holding id", () => {
    usePortfoliosStore.getState().addHolding("default", RELIANCE);
    expect(holdings()).toHaveLength(1);
    expect(holdings()[0]).toMatchObject({ symbol: "RELIANCE", quantity: 5, costBasis: 1263 });
    expect(holdings()[0].id).toMatch(/^h-/);
  });

  it("writes nothing when the symbol is empty/whitespace", () => {
    usePortfoliosStore.getState().addHolding("default", { ...RELIANCE, symbol: "   " });
    expect(holdings()).toHaveLength(0);
  });

  it("uppercases + trims the symbol via the store normalizer", () => {
    usePortfoliosStore.getState().addHolding("default", { ...RELIANCE, symbol: "  infy  " });
    expect(holdings()[0].symbol).toBe("INFY");
  });
});

describe("holding validation (R15-DATA-088)", () => {
  it("a corrupt restored blob drops a negative cost and a garbage quantity instead of zeroing them", () => {
    usePortfoliosStore.getState().setAll([
      {
        id: "default",
        name: "Portfolio",
        holdings: [
          { id: "h-bad-qty", symbol: "RELIANCE", quantity: "abc", costBasis: 100 },
          { id: "h-neg-cost", symbol: "TCS", quantity: 5, costBasis: -100 },
          { id: "h-zero-qty", symbol: "INFY", quantity: 0, costBasis: 1500 },
          { id: "h-ok", symbol: "HDFC", quantity: 2, costBasis: 0 },
        ] as never,
      },
    ]);
    expect(holdings().map((h) => h.id)).toEqual(["h-ok"]);
  });

  it("add and update refuse the same values the form refuses", () => {
    const store = usePortfoliosStore.getState();
    expect(store.addHolding("default", { ...RELIANCE, costBasis: -1 })).toBeNull();
    expect(store.addHolding("default", { ...RELIANCE, quantity: Number.NaN })).toBeNull();
    const id = store.addHolding("default", RELIANCE)!;
    expect(store.updateHolding("default", id, { ...RELIANCE, quantity: -3 })).toBe(false);
    expect(holdings()).toEqual([expect.objectContaining({ id, quantity: 5, costBasis: 1263 })]);
  });
});

describe("updateHolding / removeHolding", () => {
  it("updates an existing holding in place", () => {
    usePortfoliosStore.getState().addHolding("default", RELIANCE);
    const id = holdings()[0].id;
    usePortfoliosStore
      .getState()
      .updateHolding("default", id, { ...RELIANCE, quantity: 10, costBasis: 1300 });
    expect(holdings()[0]).toMatchObject({ id, quantity: 10, costBasis: 1300 });
  });

  it("a rejected update (empty symbol) leaves the original untouched", () => {
    usePortfoliosStore.getState().addHolding("default", RELIANCE);
    const id = holdings()[0].id;
    usePortfoliosStore.getState().updateHolding("default", id, { ...RELIANCE, symbol: "" });
    expect(holdings()[0].symbol).toBe("RELIANCE");
  });

  it("removes by id, and an unknown id is a no-op", () => {
    usePortfoliosStore.getState().addHolding("default", RELIANCE);
    usePortfoliosStore.getState().removeHolding("default", "nope");
    expect(holdings()).toHaveLength(1);
    usePortfoliosStore.getState().removeHolding("default", holdings()[0].id);
    expect(holdings()).toHaveLength(0);
  });
});
