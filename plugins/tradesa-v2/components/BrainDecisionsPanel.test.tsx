/**
 * Tradesa V2 wrapper — BrainDecisionsPanel Vitest suite.
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { BrainDecisionsPanel } from "./BrainDecisionsPanel";
import {
  installStubAdapter,
  makeConnectionState,
  makeCostRollup,
  makeDecision,
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

describe("BrainDecisionsPanel", () => {
  it("renders the skeleton-loader UX while connecting", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<BrainDecisionsPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders empty-decisions message + zero-cost rollup when healthy with no data", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      decisions: [],
      cost: makeCostRollup({ by_model: {}, total_usd: 0 }),
    });
    render(<BrainDecisionsPanel />);
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-decisions-empty")).toBeInTheDocument();
    });
    expect(screen.getByTestId("tradesa-cost-rollup")).toBeInTheDocument();
    expect(screen.getByText(/No LLM calls today/i)).toBeInTheDocument();
  });

  it("renders populated decision cards + per-model cost rows when healthy", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      decisions: [
        makeDecision({ id: "d1", action: "OPEN_LONG", confidence: 0.8 }),
        makeDecision({ id: "d2", action: "CLOSE", confidence: 0.5 }),
      ],
      cost: makeCostRollup(),
    });
    render(<BrainDecisionsPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-decision-card")).toHaveLength(2);
    });
    expect(screen.getByTestId("tradesa-action-OPEN_LONG")).toBeInTheDocument();
    expect(screen.getByTestId("tradesa-action-CLOSE")).toBeInTheDocument();
    expect(screen.getAllByTestId("tradesa-cost-row").length).toBeGreaterThanOrEqual(2);
  });
});
