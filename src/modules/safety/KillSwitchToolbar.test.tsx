import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { resetSafetyStoreForTests, useSafetyStore } from "@/store/safety";

import { KillSwitchToolbar } from "./KillSwitchToolbar";

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return {
    ...actual,
    getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999"),
    sidecarGet: vi.fn(async () => ({ fired: false, lastResult: null })),
  };
});

vi.mock("@tauri-apps/api/event", () => ({
  listen: vi.fn(async () => () => undefined),
}));

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
  resetSafetyStoreForTests();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("KillSwitchToolbar", () => {
  it("renders the armed button by default", async () => {
    render(<KillSwitchToolbar />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /halt all trading/i })).toBeInTheDocument();
    });
    const button = screen.getByRole("button", { name: /halt all trading/i });
    expect(button.getAttribute("data-state")).toBe("armed");
  });

  it("fires kill switch on click and displays the banner with ack times", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      statusText: "OK",
      json: async () => ({
        event: { firedAt: 1, reason: "toolbar-click", firedBy: "user-toolbar" },
        ackTimesMs: { alpaca: 1.1, kite: 0.7 },
        p50AckMs: 0.9,
        p95AckMs: 1.1,
        maxAckMs: 1.1,
      }),
    } as Response);

    render(<KillSwitchToolbar />);
    const button = await screen.findByRole("button", { name: /halt all trading/i });
    await act(async () => {
      fireEvent.click(button);
    });
    await waitFor(() => {
      expect(screen.getByTestId("kill-switch-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("kill-switch-banner").textContent).toContain("Kill switch fired");
  });

  it("renders a reset button when the kill switch is already fired", async () => {
    useSafetyStore.setState({
      killSwitchFired: true,
      lastKillSwitchResult: {
        event: { firedAt: 1, reason: "panic", firedBy: "user-toolbar" },
        ackTimesMs: { alpaca: 0.5 },
        p50AckMs: 0.5,
        p95AckMs: 0.5,
        maxAckMs: 0.5,
      },
    });
    render(<KillSwitchToolbar />);
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /reset kill switch/i })).toBeInTheDocument();
    });
  });

  it("listens to the Tauri kill-switch:requested event", async () => {
    const eventMod = await import("@tauri-apps/api/event");
    const listenSpy = vi.mocked(eventMod.listen);
    render(<KillSwitchToolbar />);
    await waitFor(() => {
      expect(listenSpy).toHaveBeenCalledWith("kill-switch:requested", expect.any(Function));
    });
  });
});
