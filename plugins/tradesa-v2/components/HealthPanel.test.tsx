/**
 * Tradesa V2 wrapper — HealthPanel Vitest suite.
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { HealthPanel } from "./HealthPanel";
import {
  installStubAdapter,
  makeBotHealth,
  makeConnectionState,
  makeKillSwitchEvent,
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

describe("HealthPanel", () => {
  it("renders the skeleton-loader UX while connecting", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<HealthPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders 'no heartbeat' card + empty kill-switch when healthy with no data", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      health: { latest: null, recent_kill_switch_events: [] },
    });
    render(<HealthPanel />);
    await waitFor(() => {
      expect(screen.getByText(/No heartbeat recorded yet/i)).toBeInTheDocument();
    });
    expect(screen.getByTestId("tradesa-killswitch-empty")).toBeInTheDocument();
  });

  it("renders populated health card + kill-switch timeline with cleared + active events", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      health: {
        latest: makeBotHealth({ status: "running", fd_count: 142, thread_count: 23 }),
        recent_kill_switch_events: [
          makeKillSwitchEvent({ id: "k1", source: "operator_telegram", cleared_at: null }),
          makeKillSwitchEvent({ id: "k2", source: "sentinel" }),
        ],
      },
    });
    render(<HealthPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-killswitch-row")).toHaveLength(2);
    });
    expect(screen.getByText("running")).toBeInTheDocument();
    expect(screen.getByText("142")).toBeInTheDocument();
    expect(screen.getByText("23")).toBeInTheDocument();
    expect(screen.getByText(/still active/i)).toBeInTheDocument();
    expect(screen.getByTestId("tradesa-source-operator_telegram")).toBeInTheDocument();
    expect(screen.getByTestId("tradesa-source-sentinel")).toBeInTheDocument();
  });
});
