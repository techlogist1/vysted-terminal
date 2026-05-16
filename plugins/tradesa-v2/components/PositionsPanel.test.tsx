/**
 * Tradesa V2 wrapper — PositionsPanel Vitest suite.
 *
 * Covers the four canonical states every panel renders: skeleton
 * (connecting), unauthenticated (Open Settings CTA), bot-offline
 * (banner + stale-data body), healthy with populated rows (table +
 * side badges).
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { PositionsPanel } from "./PositionsPanel";
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

describe("PositionsPanel", () => {
  it("renders the skeleton-loader UX while status === 'connecting'", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<PositionsPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders 'Open Settings' CTA in the unauthenticated state", () => {
    setConnectionState(makeConnectionState("unauthenticated"));
    installStubAdapter({ probeState: makeConnectionState("unauthenticated") });
    render(<PositionsPanel />);
    expect(screen.getByTestId("tradesa-unauthenticated")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open settings/i })).toBeInTheDocument();
  });

  it("renders the bot-offline banner with stale-minutes copy", () => {
    setConnectionState(
      makeConnectionState("bot-offline", { heartbeat_age_s: 600, bot_mode: "paper" }),
    );
    installStubAdapter({ probeState: makeConnectionState("bot-offline") });
    render(<PositionsPanel />);
    expect(screen.getByTestId("tradesa-bot-offline-banner")).toHaveTextContent(/10 minutes/);
  });

  it("renders populated table rows when healthy with positions", async () => {
    const positions = [
      makeTrade({ id: "p1", instrument: "BTCUSDT", side: "long", qty: 0.5 }),
      makeTrade({ id: "p2", instrument: "ETHUSDT", side: "short", qty: 2 }),
    ];
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({ probeState: makeConnectionState("healthy"), positions });
    render(<PositionsPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-position-row")).toHaveLength(2);
    });
    expect(screen.getByTestId("tradesa-side-long")).toBeInTheDocument();
    expect(screen.getByTestId("tradesa-side-short")).toBeInTheDocument();
    expect(screen.getByText("BTCUSDT")).toBeInTheDocument();
    expect(screen.getByText("ETHUSDT")).toBeInTheDocument();
  });

  it("renders empty-state copy when healthy with no positions", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({ probeState: makeConnectionState("healthy"), positions: [] });
    render(<PositionsPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-positions-empty")).toBeInTheDocument();
    });
    expect(screen.getByText(/no open positions/i)).toBeInTheDocument();
  });
});
