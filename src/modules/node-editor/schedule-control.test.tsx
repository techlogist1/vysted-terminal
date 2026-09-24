import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ScheduleControl } from "./schedule-control";

vi.mock("@/lib/sidecar-client", async () => {
  const actual =
    await vi.importActual<typeof import("@/lib/sidecar-client")>("@/lib/sidecar-client");
  return { ...actual, getSidecarBaseUrl: vi.fn(async () => "http://127.0.0.1:9999") };
});

const fetchMock = vi.fn();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("ScheduleControl (R15-AGENT-023)", () => {
  it("creates an interval schedule for the saved workflow and lists it", async () => {
    const stored: unknown[] = [];
    fetchMock.mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = new URL(input.toString());
      expect(url.pathname).toBe("/workflow/schedules");
      if (init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as Record<string, unknown>;
        stored.push({
          id: "sch-1",
          ...body,
          enabled: true,
          createdAt: 1,
          lastFiredAt: null,
          lastSeen: null,
          lastStatus: null,
          lastDetail: null,
        });
        return new Response(JSON.stringify(stored[0]), { status: 200 });
      }
      return new Response(JSON.stringify(stored), { status: 200 });
    });

    render(<ScheduleControl workflowId="wf-1" />);
    fireEvent.change(screen.getByLabelText("Minutes"), { target: { value: "15" } });
    fireEvent.click(screen.getByRole("button", { name: "Add schedule" }));

    expect(await screen.findByTestId("schedule-row")).toHaveTextContent("Every 15 min");
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      workflowId: "wf-1",
      trigger: { kind: "interval", everyMinutes: 15 },
    });
  });

  it("refuses an interval under the 5-minute floor", async () => {
    fetchMock.mockImplementation(async () => new Response("[]", { status: 200 }));
    render(<ScheduleControl workflowId="wf-1" />);
    fireEvent.change(screen.getByLabelText("Minutes"), { target: { value: "2" } });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Add schedule" })).toBeDisabled(),
    );
  });
});
