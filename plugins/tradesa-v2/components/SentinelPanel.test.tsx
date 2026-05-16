/**
 * Tradesa V2 wrapper — SentinelPanel Vitest suite.
 */

import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { SentinelPanel } from "./SentinelPanel";
import {
  installStubAdapter,
  makeConnectionState,
  makeSentinelBlock,
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

describe("SentinelPanel", () => {
  it("renders the skeleton-loader UX while connecting", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<SentinelPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders supabase-error CTA when probe fails", () => {
    setConnectionState(makeConnectionState("supabase-error"));
    installStubAdapter({ probeState: makeConnectionState("supabase-error") });
    render(<SentinelPanel />);
    expect(screen.getByTestId("tradesa-supabase-error")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument();
  });

  it("renders gate rows sorted by today_count desc with fail-mode badges", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      sentinel: [
        makeSentinelBlock({ gate_id: "gate_A", today_count: 1, fail_closed: false }),
        makeSentinelBlock({ gate_id: "gate_B", today_count: 9, fail_closed: true }),
        makeSentinelBlock({ gate_id: "gate_C", today_count: 4, fail_closed: true }),
      ],
    });
    render(<SentinelPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-sentinel-row")).toHaveLength(3);
    });
    const rows = screen.getAllByTestId("tradesa-sentinel-row");
    expect(rows[0]).toHaveTextContent("gate_B");
    expect(rows[1]).toHaveTextContent("gate_C");
    expect(rows[2]).toHaveTextContent("gate_A");
    expect(screen.getAllByTestId("tradesa-fail-closed")).toHaveLength(2);
    expect(screen.getAllByTestId("tradesa-fail-open")).toHaveLength(1);
  });
});
