import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { SIDECAR_REQUEST_TIMEOUT_MS, SidecarError } from "@/lib/sidecar-client";

import { ScheduleControl } from "./schedule-control";

// The schedule CRUD rides the shared sidecar verb (R15-CODE-FRONTEND-027);
// mock it at the module boundary, keep SidecarError and the constants real.
const requestMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, sidecarRequest: requestMock };
});

beforeEach(() => {
  requestMock.mockReset();
});

afterEach(() => {
  cleanup();
});

function schedule(overrides: Record<string, unknown> = {}) {
  return {
    id: "sch-1",
    workflowId: "wf-1",
    trigger: { kind: "interval", everyMinutes: 15 },
    enabled: true,
    createdAt: 1,
    lastFiredAt: null,
    lastSeen: null,
    lastStatus: null,
    lastDetail: null,
    ...overrides,
  };
}

describe("ScheduleControl (R15-AGENT-023)", () => {
  it("creates an interval schedule for the saved workflow and lists it", async () => {
    const stored: unknown[] = [];
    requestMock.mockImplementation(
      async (method: string, path: string, opts?: { body?: Record<string, unknown> }) => {
        expect(path).toBe("/workflow/schedules");
        if (method === "POST") {
          stored.push(schedule(opts?.body));
          return stored[0];
        }
        return stored;
      },
    );

    render(<ScheduleControl workflowId="wf-1" />);
    fireEvent.change(screen.getByLabelText("Minutes"), { target: { value: "15" } });
    fireEvent.click(screen.getByRole("button", { name: "Add schedule" }));

    expect(await screen.findByTestId("schedule-row")).toHaveTextContent("Every 15 min");
    expect(requestMock).toHaveBeenCalledWith("POST", "/workflow/schedules", {
      body: { workflowId: "wf-1", trigger: { kind: "interval", everyMinutes: 15 } },
      timeoutMs: SIDECAR_REQUEST_TIMEOUT_MS,
    });
  });

  it("refuses an interval under the 5-minute floor", async () => {
    requestMock.mockResolvedValue([]);
    render(<ScheduleControl workflowId="wf-1" />);
    fireEvent.change(screen.getByLabelText("Minutes"), { target: { value: "2" } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Add schedule" })).toBeDisabled(),
    );
  });

  it("R15-CODE-FRONTEND-027: toggling PATCHes through the shared verb; a failure shows its sentence", async () => {
    requestMock.mockImplementation(async (method: string) => {
      if (method === "PATCH") {
        throw new SidecarError(404, "schedule not found");
      }
      return [schedule()];
    });

    render(<ScheduleControl workflowId="wf-1" />);
    fireEvent.click(await screen.findByLabelText("Enabled: Every 15 min"));

    expect(await screen.findByRole("alert")).toHaveTextContent("schedule not found");
    expect(requestMock).toHaveBeenCalledWith("PATCH", "/workflow/schedules/sch-1", {
      body: { enabled: false },
      timeoutMs: SIDECAR_REQUEST_TIMEOUT_MS,
    });
  });
});
