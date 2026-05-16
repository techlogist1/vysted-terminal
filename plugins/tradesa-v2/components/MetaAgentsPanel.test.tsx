/**
 * Tradesa V2 wrapper — MetaAgentsPanel Vitest suite.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { MetaAgentsPanel } from "./MetaAgentsPanel";
import {
  installStubAdapter,
  makeConnectionState,
  makeDiscoveryHypothesis,
  makeReflectionNote,
  makeTuningProposal,
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

describe("MetaAgentsPanel", () => {
  it("renders the skeleton-loader UX while connecting", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<MetaAgentsPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders the empty-state message in each tab when no rows", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({ probeState: makeConnectionState("healthy") });
    render(<MetaAgentsPanel />);
    // Tuning is the default tab
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-tuning-empty")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("tradesa-tab-discovery"));
    expect(screen.getByTestId("tradesa-discovery-empty")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("tradesa-tab-reflection"));
    expect(screen.getByTestId("tradesa-reflection-empty")).toBeInTheDocument();
  });

  it("renders populated tuning cards with status + value diff", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      tuning: [
        makeTuningProposal({ id: "tp1", status: "pending", proposed_value: "0.08" }),
        makeTuningProposal({ id: "tp2", status: "approved", target_key: "stop_pct_max" }),
      ],
    });
    render(<MetaAgentsPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-tuning-card")).toHaveLength(2);
    });
  });

  it("switches to the Discovery tab and renders hypothesis cards", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      discovery: [makeDiscoveryHypothesis({ id: "dh1", title: "Asian session breakout" })],
    });
    render(<MetaAgentsPanel />);
    fireEvent.click(screen.getByTestId("tradesa-tab-discovery"));
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-discovery-card")).toBeInTheDocument();
    });
    expect(screen.getByText("Asian session breakout")).toBeInTheDocument();
  });

  it("switches to the Reflection tab and renders note cards with tags", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      reflection: [
        makeReflectionNote({
          id: "rn1",
          tags: ["entry_timing", "stop_placement"],
          summary: "Stop hit just before reversal",
        }),
      ],
    });
    render(<MetaAgentsPanel />);
    fireEvent.click(screen.getByTestId("tradesa-tab-reflection"));
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-reflection-card")).toBeInTheDocument();
    });
    expect(screen.getByText("entry_timing")).toBeInTheDocument();
    expect(screen.getByText("stop_placement")).toBeInTheDocument();
  });
});
