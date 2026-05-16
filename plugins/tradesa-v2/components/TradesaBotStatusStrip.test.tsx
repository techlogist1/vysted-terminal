/**
 * Tradesa V2 wrapper — TradesaBotStatusStrip Vitest suite.
 *
 * The strip is mounted at the top of every panel via PanelShell. Tests
 * render it standalone with the connection slice pre-set so we can
 * verify each status tone + mode badge + reload behaviour without
 * waiting on the 30s poll.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { TradesaBotStatusStrip } from "./TradesaBotStatusStrip";
import {
  installStubAdapter,
  makeConnectionState,
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

describe("TradesaBotStatusStrip", () => {
  it("renders 'Connecting…' label by default (no prior probe)", () => {
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<TradesaBotStatusStrip />);
    expect(screen.getByText("Connecting…")).toBeInTheDocument();
  });

  it("renders 'Bot online' label with paper-mode badge in healthy state", () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({ probeState: makeConnectionState("healthy") });
    render(<TradesaBotStatusStrip />);
    expect(screen.getByText("Bot online")).toBeInTheDocument();
    expect(screen.getByLabelText("Mode: paper")).toHaveTextContent("paper");
  });

  it("formats heartbeat age as relative time (12s ago, not raw seconds)", () => {
    setConnectionState(makeConnectionState("healthy", { heartbeat_age_s: 12 }));
    installStubAdapter({ probeState: makeConnectionState("healthy") });
    render(<TradesaBotStatusStrip />);
    expect(screen.getByText(/heartbeat 12s ago/)).toBeInTheDocument();
  });

  it("renders the kill-switch chip when engaged", () => {
    setConnectionState(makeConnectionState("healthy", { kill_switch_engaged: true }));
    installStubAdapter({ probeState: makeConnectionState("healthy") });
    render(<TradesaBotStatusStrip />);
    expect(screen.getByText("Kill Switch")).toBeInTheDocument();
  });

  it("renders red-tone live badge when bot_mode is 'live'", () => {
    setConnectionState(makeConnectionState("healthy", { bot_mode: "live" }));
    installStubAdapter({ probeState: makeConnectionState("healthy") });
    render(<TradesaBotStatusStrip />);
    const liveBadge = screen.getByLabelText("Mode: live");
    expect(liveBadge).toHaveTextContent("live");
    expect(liveBadge.className).toContain("text-red-200");
  });

  it("reload button calls refreshConnection adapter", async () => {
    const adapter = installStubAdapter({ probeState: makeConnectionState("healthy") });
    render(<TradesaBotStatusStrip />);
    await waitFor(() => {
      expect(adapter.probeStatus).toHaveBeenCalled();
    });
    const initialCalls = (adapter.probeStatus as ReturnType<typeof vi.fn>).mock.calls.length;
    const button = screen.getByLabelText("Reload bot status");
    fireEvent.click(button);
    await waitFor(() => {
      expect((adapter.probeStatus as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
        initialCalls,
      );
    });
  });
});
