/**
 * @vitest-environment jsdom
 */
import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { useDesktopNotificationBridge } from "./desktop-notification";
import { useWorkflowStore } from "@/store/workflow";

// Mock the Tauri notification plugin — the bridge dynamic-imports it.
const sendNotificationMock = vi.fn<(args: { title: string; body: string }) => void>();
const isPermissionGrantedMock = vi.fn<() => Promise<boolean>>();
const requestPermissionMock = vi.fn<() => Promise<"granted" | "denied">>();

vi.mock("@tauri-apps/plugin-notification", () => ({
  sendNotification: (...args: Parameters<typeof sendNotificationMock>) =>
    sendNotificationMock(...args),
  isPermissionGranted: () => isPermissionGrantedMock(),
  requestPermission: () => requestPermissionMock(),
}));

function _setTauri(active: boolean): void {
  if (active) {
    Object.defineProperty(window, "__TAURI_INTERNALS__", { value: {}, configurable: true });
  } else {
    delete (window as unknown as Record<string, unknown>).__TAURI_INTERNALS__;
  }
}

describe("useDesktopNotificationBridge", () => {
  beforeEach(() => {
    sendNotificationMock.mockReset();
    isPermissionGrantedMock.mockReset();
    requestPermissionMock.mockReset();
    useWorkflowStore.getState().clearAll();
  });

  afterEach(() => {
    _setTauri(false);
  });

  it("flushes pending intents through the Tauri notification API when permission granted", async () => {
    _setTauri(true);
    isPermissionGrantedMock.mockResolvedValue(true);

    renderHook(() => useDesktopNotificationBridge());

    useWorkflowStore.getState().appendEvent({
      kind: "node-output",
      runId: "run-1",
      nodeId: "node-notify",
      outputs: {
        intent: "desktop-notification",
        notified: true,
        title: "Earnings beat",
        message: "AAPL EPS surprise +12%",
      },
      durationMs: 4,
    });

    // The bridge's flush is async (dynamic import + await chain).
    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(sendNotificationMock).toHaveBeenCalledWith({
      title: "Earnings beat",
      body: "AAPL EPS surprise +12%",
    });
    expect(useWorkflowStore.getState().pendingNotifications).toEqual([]);
  });

  it("requests permission when not yet granted, then sends", async () => {
    _setTauri(true);
    isPermissionGrantedMock.mockResolvedValue(false);
    requestPermissionMock.mockResolvedValue("granted");

    renderHook(() => useDesktopNotificationBridge());

    useWorkflowStore.getState().appendEvent({
      kind: "node-output",
      runId: "run-2",
      nodeId: "node-notify",
      outputs: {
        intent: "desktop-notification",
        notified: true,
        title: "T",
        message: "M",
      },
      durationMs: 2,
    });

    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(requestPermissionMock).toHaveBeenCalled();
    expect(sendNotificationMock).toHaveBeenCalledTimes(1);
  });

  it("does not send when permission denied", async () => {
    _setTauri(true);
    isPermissionGrantedMock.mockResolvedValue(false);
    requestPermissionMock.mockResolvedValue("denied");

    renderHook(() => useDesktopNotificationBridge());

    useWorkflowStore.getState().appendEvent({
      kind: "node-output",
      runId: "run-3",
      nodeId: "node-notify",
      outputs: {
        intent: "desktop-notification",
        notified: true,
        title: "T",
        message: "M",
      },
      durationMs: 1,
    });

    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(sendNotificationMock).not.toHaveBeenCalled();
    // Even denied, the bridge drains so a re-mount doesn't re-attempt.
    expect(useWorkflowStore.getState().pendingNotifications).toEqual([]);
  });

  it("is a safe no-op outside the Tauri webview", async () => {
    _setTauri(false);

    renderHook(() => useDesktopNotificationBridge());

    useWorkflowStore.getState().appendEvent({
      kind: "node-output",
      runId: "run-4",
      nodeId: "node-notify",
      outputs: {
        intent: "desktop-notification",
        notified: true,
        title: "T",
        message: "M",
      },
      durationMs: 1,
    });

    await new Promise((resolve) => setTimeout(resolve, 20));

    expect(sendNotificationMock).not.toHaveBeenCalled();
    expect(isPermissionGrantedMock).not.toHaveBeenCalled();
    expect(useWorkflowStore.getState().pendingNotifications).toEqual([]);
  });
});
