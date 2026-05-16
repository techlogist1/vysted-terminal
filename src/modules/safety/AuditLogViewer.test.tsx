import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import * as sidecarClient from "@/lib/sidecar-client";
import { resetSafetyStoreForTests } from "@/store/safety";

import { AuditLogViewer } from "./AuditLogViewer";

import type { AuditLogEntry } from "../../../types/safety";

function makeEntry(partial: Partial<AuditLogEntry>): AuditLogEntry {
  return {
    id: 1,
    timestampMs: 1_700_000_000_000,
    broker: "alpaca",
    accountId: "acc-1",
    action: "order-proposed",
    payload: { proposalId: "p-1" },
    source: "manual",
    outcome: "ok",
    ...partial,
  };
}

beforeEach(() => {
  vi.spyOn(sidecarClient, "getSidecarBaseUrl").mockResolvedValue("http://127.0.0.1:9999");
  vi.spyOn(sidecarClient, "sidecarGet").mockResolvedValue({
    entries: [
      makeEntry({ id: 3, broker: "alpaca", action: "order-placed" }),
      makeEntry({ id: 2, broker: "kite", action: "order-confirmed" }),
      makeEntry({ id: 1, broker: "alpaca", action: "order-proposed" }),
    ],
  });
  resetSafetyStoreForTests();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.useRealTimers();
});

describe("AuditLogViewer", () => {
  it("fetches the audit log on mount and renders rows", async () => {
    render(<AuditLogViewer />);
    await waitFor(() => {
      expect(screen.getByTestId("audit-log-viewer")).toBeInTheDocument();
    });
    await waitFor(() => {
      expect(screen.getByTestId("audit-row-1")).toBeInTheDocument();
      expect(screen.getByTestId("audit-row-2")).toBeInTheDocument();
      expect(screen.getByTestId("audit-row-3")).toBeInTheDocument();
    });
  });

  it("filters by broker", async () => {
    render(<AuditLogViewer />);
    await waitFor(() => {
      expect(screen.getByTestId("audit-row-1")).toBeInTheDocument();
    });
    const select = screen.getByTestId("audit-filter-broker") as HTMLSelectElement;
    await act(async () => {
      fireEvent.change(select, { target: { value: "kite" } });
    });
    await waitFor(() => {
      expect(screen.queryByTestId("audit-row-1")).toBeNull();
      expect(screen.queryByTestId("audit-row-3")).toBeNull();
      expect(screen.getByTestId("audit-row-2")).toBeInTheDocument();
    });
  });

  it("filters by action", async () => {
    render(<AuditLogViewer />);
    await waitFor(() => {
      expect(screen.getByTestId("audit-row-3")).toBeInTheDocument();
    });
    const select = screen.getByTestId("audit-filter-action") as HTMLSelectElement;
    await act(async () => {
      fireEvent.change(select, { target: { value: "order-placed" } });
    });
    await waitFor(() => {
      expect(screen.queryByTestId("audit-row-1")).toBeNull();
      expect(screen.queryByTestId("audit-row-2")).toBeNull();
      expect(screen.getByTestId("audit-row-3")).toBeInTheDocument();
    });
  });

  it("export CSV invokes fetch against the export endpoint", async () => {
    const fetchSpy = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      blob: async () => new Blob(["id,timestamp_ms\n"], { type: "text/csv" }),
    } as unknown as Response);
    vi.stubGlobal("fetch", fetchSpy);
    const objectUrlSpy = vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:fake");
    vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => undefined);
    render(<AuditLogViewer />);
    const button = await screen.findByTestId("audit-export-csv");
    await act(async () => {
      fireEvent.click(button);
    });
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalled();
    });
    expect(objectUrlSpy).toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("polls the audit log on a timer", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const spy = sidecarClient.sidecarGet as ReturnType<typeof vi.fn>;
    render(<AuditLogViewer />);
    await waitFor(() => {
      expect(spy.mock.calls.length).toBeGreaterThanOrEqual(1);
    });
    const baseline = spy.mock.calls.length;
    await act(async () => {
      await vi.advanceTimersByTimeAsync(4_500);
    });
    expect(spy.mock.calls.length).toBeGreaterThan(baseline);
  });
});
