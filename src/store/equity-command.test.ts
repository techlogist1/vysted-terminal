import { describe, expect, it, beforeEach } from "vitest";

import { resetEquityCommandStoreForTests, useEquityCommandStore } from "./equity-command";

describe("equity-command store", () => {
  beforeEach(() => {
    resetEquityCommandStoreForTests();
  });

  it("starts with no command", () => {
    expect(useEquityCommandStore.getState().command).toBeNull();
  });

  it("loadSymbol sets the command and bumps seq each issue (so a re-open re-triggers)", () => {
    const { loadSymbol } = useEquityCommandStore.getState();
    loadSymbol("AAPL");
    expect(useEquityCommandStore.getState().command).toEqual({ symbol: "AAPL", seq: 1 });
    // Re-issuing the SAME symbol still bumps seq so the consumer effect re-fires.
    loadSymbol("AAPL");
    expect(useEquityCommandStore.getState().command).toEqual({ symbol: "AAPL", seq: 2 });
    loadSymbol("RELIANCE.NS");
    expect(useEquityCommandStore.getState().command).toEqual({ symbol: "RELIANCE.NS", seq: 3 });
  });
});
