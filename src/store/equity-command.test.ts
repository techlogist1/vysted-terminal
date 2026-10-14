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

  it("RETAINS the last command for a late subscriber (mount-time race contract)", () => {
    // The open_panel/open_company_overview host action issues the command and
    // THEN the panel mounts. The store must retain the command so the panel's
    // mount-time read (what React's useStore selector does at subscribe time)
    // still sees it — a consume-and-clear store would lose the race.
    useEquityCommandStore.getState().loadSymbol("SAKSOFT.NS", "pe_ratio");
    // No subscriber existed when the command fired. A late subscriber's initial
    // selector read resolves the retained command…
    const lateRead = useEquityCommandStore.getState().command;
    expect(lateRead).toEqual({ symbol: "SAKSOFT.NS", seq: 1, highlightMetric: "pe_ratio" });
    // …and zustand's subscribe sees no further change events (nothing clears
    // the command behind the subscriber's back).
    const seen: string[] = [];
    const unsub = useEquityCommandStore.subscribe((s) => {
      if (s.command) {
        seen.push(s.command.symbol);
      }
    });
    expect(seen).toEqual([]); // retained state, no spurious replay event
    expect(useEquityCommandStore.getState().command?.symbol).toBe("SAKSOFT.NS");
    unsub();
  });

  it("carries highlightMetric through and drops it on the next plain issue", () => {
    const { loadSymbol } = useEquityCommandStore.getState();
    loadSymbol("TATASTEEL.NS", "pe_ratio");
    expect(useEquityCommandStore.getState().command?.highlightMetric).toBe("pe_ratio");
    loadSymbol("TATASTEEL.NS");
    expect(useEquityCommandStore.getState().command?.highlightMetric).toBeUndefined();
  });
});
