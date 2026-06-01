import { afterEach, describe, expect, it } from "vitest";

import { usePanelContextBus } from "@/store/panel-context";
import type { PanelContextEvent } from "../../../types/panel-context";

import { captureTerminalState } from "./context-provider";

/** Publish a portfolio snapshot event onto the live bus. */
function publishPortfolio(payload: unknown): void {
  const event: PanelContextEvent = {
    source: "portfolio",
    kind: "snapshot",
    payload,
    emittedAt: Date.now(),
  };
  usePanelContextBus.getState().publish(event);
}

describe("captureTerminalState — portfolio holdings (FR-110/111, SC-024)", () => {
  afterEach(() => {
    // Reset the bus so each test reads a clean snapshot.
    usePanelContextBus.setState({
      lastEventBySource: {},
      focusedSource: null,
      updatedAt: 0,
    });
  });

  it("extracts the full holdings array + active id/name from a multi-portfolio payload", () => {
    publishPortfolio({
      positionCount: 2,
      totalValue: 31_250,
      activePortfolioId: "pf-growth",
      activePortfolioName: "Growth",
      holdings: [
        {
          symbol: "AAPL",
          quantity: 100,
          costBasis: 150,
          assetClass: "equity",
          marketValue: 19_000,
          pnl: 4_000,
        },
        {
          symbol: "BTC/USDT",
          quantity: 0.25,
          costBasis: 49_000,
          assetClass: "crypto",
          marketValue: 12_250,
          pnl: 0,
        },
      ],
    });

    const { portfolio } = captureTerminalState();

    expect(portfolio).not.toBeNull();
    expect(portfolio?.positionCount).toBe(2);
    expect(portfolio?.totalValue).toBe(31_250);
    expect(portfolio?.activePortfolioId).toBe("pf-growth");
    expect(portfolio?.activePortfolioName).toBe("Growth");
    // Zero divergence from the published store: full holdings carried through.
    expect(portfolio?.holdings).toEqual([
      {
        symbol: "AAPL",
        quantity: 100,
        costBasis: 150,
        assetClass: "equity",
        marketValue: 19_000,
        pnl: 4_000,
      },
      {
        symbol: "BTC/USDT",
        quantity: 0.25,
        costBasis: 49_000,
        assetClass: "crypto",
        marketValue: 12_250,
        pnl: 0,
      },
    ]);
  });

  it("carries marketValue/pnl as null when a holding has no resolved quote", () => {
    publishPortfolio({
      positionCount: 1,
      totalValue: 0,
      activePortfolioId: "pf-1",
      activePortfolioName: "Main",
      holdings: [
        {
          symbol: "XYZ",
          quantity: 10,
          costBasis: 5,
          assetClass: "equity",
          marketValue: null,
          pnl: null,
        },
      ],
    });

    const { portfolio } = captureTerminalState();

    expect(portfolio?.holdings).toEqual([
      {
        symbol: "XYZ",
        quantity: 10,
        costBasis: 5,
        assetClass: "equity",
        marketValue: null,
        pnl: null,
      },
    ]);
  });

  it("yields holdings:[] for an older payload that predates multi-portfolio truth", () => {
    // The pre-B6 shape carried only positionCount + totalValue.
    publishPortfolio({ positionCount: 3, totalValue: 9_999 });

    const { portfolio } = captureTerminalState();

    expect(portfolio).not.toBeNull();
    expect(portfolio?.positionCount).toBe(3);
    expect(portfolio?.totalValue).toBe(9_999);
    expect(portfolio?.holdings).toEqual([]);
    expect(portfolio?.activePortfolioId).toBeUndefined();
    expect(portfolio?.activePortfolioName).toBeUndefined();
  });

  it("returns portfolio:null when no portfolio panel has published", () => {
    // Bus has a non-portfolio event so the snapshot is non-empty but carries
    // no portfolio source.
    usePanelContextBus.getState().publish({
      source: "watchlist",
      kind: "snapshot",
      payload: { symbols: ["SPY"], selectedSymbol: "SPY" },
      emittedAt: Date.now(),
    });

    expect(captureTerminalState().portfolio).toBeNull();
  });

  it("drops malformed holding rows (missing symbol) defensively", () => {
    publishPortfolio({
      positionCount: 1,
      totalValue: 100,
      holdings: [
        { quantity: 1, costBasis: 1, assetClass: "equity" }, // no symbol -> dropped
        { symbol: "MSFT", quantity: 2, costBasis: 300, assetClass: "equity" },
      ],
    });

    const { portfolio } = captureTerminalState();

    expect(portfolio?.holdings).toEqual([
      {
        symbol: "MSFT",
        quantity: 2,
        costBasis: 300,
        assetClass: "equity",
        marketValue: null,
        pnl: null,
      },
    ]);
  });
});
