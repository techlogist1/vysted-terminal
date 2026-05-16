/**
 * Tradesa V2 wrapper — TradeHistoryPanel Vitest suite.
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { TradeHistoryPanel } from "./TradeHistoryPanel";
import {
  installStubAdapter,
  makeConnectionState,
  makeTrade,
  resetStore,
  setConnectionState,
} from "./_test-helpers";

beforeEach(() => {
  invokeMock.mockReset();
  invokeMock.mockResolvedValue(null);
});

afterEach(() => {
  cleanup();
  resetStore();
});

describe("TradeHistoryPanel", () => {
  it("renders the skeleton-loader UX while connecting", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<TradeHistoryPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders empty-state message when bot-offline and no rows", async () => {
    setConnectionState(makeConnectionState("bot-offline"));
    installStubAdapter({ probeState: makeConnectionState("bot-offline"), tradeHistory: [] });
    render(<TradeHistoryPanel />);
    expect(screen.getByTestId("tradesa-bot-offline-banner")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-trade-history-empty")).toBeInTheDocument();
    });
  });

  it("renders the summary card + populated table with realized P&L", async () => {
    const closed = [
      makeTrade({
        id: "c1",
        instrument: "BTCUSDT",
        status: "closed",
        realized_pnl: 12.5,
        exit_price: 65500,
        closed_at: "2026-05-17T11:55:00Z",
      }),
      makeTrade({
        id: "c2",
        instrument: "ETHUSDT",
        status: "closed",
        side: "short",
        realized_pnl: -4.25,
        exit_price: 3200,
        closed_at: "2026-05-17T11:00:00Z",
      }),
    ];
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({ probeState: makeConnectionState("healthy"), tradeHistory: closed });
    render(<TradeHistoryPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-trade-row")).toHaveLength(2);
    });
    expect(screen.getByTestId("tradesa-trade-summary")).toBeInTheDocument();
    // Win-rate: 1 winner, 1 loser → 50%
    expect(screen.getByText("50%")).toBeInTheDocument();
    expect(screen.getByText(/1W \/ 1L/)).toBeInTheDocument();
  });
});
