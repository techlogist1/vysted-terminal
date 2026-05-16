/**
 * Tradesa V2 wrapper — SettingsPanel Vitest suite.
 */

import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const invokeMock = vi.hoisted(() => vi.fn());
vi.mock("@tauri-apps/api/core", () => ({ invoke: invokeMock }));

import { SettingsPanel } from "./SettingsPanel";
import {
  installStubAdapter,
  makeBotSetting,
  makeConnectionState,
  makeSettingsDrift,
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

describe("SettingsPanel", () => {
  it("renders the skeleton-loader UX while connecting", () => {
    setConnectionState(makeConnectionState("connecting"));
    installStubAdapter({ probeState: makeConnectionState("connecting") });
    render(<SettingsPanel />);
    expect(screen.getByTestId("tradesa-skeleton")).toBeInTheDocument();
  });

  it("renders populated settings table with searchable rows", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      settings: [
        makeBotSetting({ key: "size_pct_max", value: "0.10" }),
        makeBotSetting({ key: "stop_pct_max", value: "0.05" }),
        makeBotSetting({ key: "leverage_cap", value: "4" }),
      ],
    });
    render(<SettingsPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-settings-row")).toHaveLength(3);
    });

    // Filter to size_*
    fireEvent.change(screen.getByTestId("tradesa-settings-search"), {
      target: { value: "size" },
    });
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-settings-row")).toHaveLength(1);
    });
  });

  it("renders drift cards when switched to the Drift tab", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      settings: [makeBotSetting()],
      drift: [
        makeSettingsDrift({ key: "stop_pct_max", previous_value: "0.04", current_value: "0.05" }),
      ],
    });
    render(<SettingsPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-settings-row")).toHaveLength(1);
    });
    fireEvent.click(screen.getByTestId("tradesa-tab-drift"));
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-drift-row")).toBeInTheDocument();
    });
    expect(screen.getByText("0.04")).toBeInTheDocument();
    expect(screen.getByText("0.05")).toBeInTheDocument();
  });

  it("renders 'No drift detected' message when drift list is empty", async () => {
    setConnectionState(makeConnectionState("healthy"));
    installStubAdapter({
      probeState: makeConnectionState("healthy"),
      settings: [makeBotSetting()],
      drift: [],
    });
    render(<SettingsPanel />);
    await waitFor(() => {
      expect(screen.getAllByTestId("tradesa-settings-row")).toHaveLength(1);
    });
    fireEvent.click(screen.getByTestId("tradesa-tab-drift"));
    await waitFor(() => {
      expect(screen.getByTestId("tradesa-drift-empty")).toBeInTheDocument();
    });
  });
});
