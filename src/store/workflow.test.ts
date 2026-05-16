import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { WorkflowRunEvent, WorkflowSpec } from "../../types/workflow";

// Stub the Tauri-coupled ``getSidecarBaseUrl`` so the store resolves a URL
// without a desktop runtime.
vi.mock("@/lib/sidecar-client", () => ({
  getSidecarBaseUrl: () => Promise.resolve("http://127.0.0.1:51763"),
}));

import {
  selectActiveRunLog,
  selectPendingNotifications,
  selectRunLog,
  useWorkflowStore,
} from "@/store/workflow";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _spec(): WorkflowSpec {
  return {
    id: "wf-test",
    name: "Test",
    version: 1,
    nodes: [],
    edges: [],
    updatedAt: 0,
  };
}

function _resetStore(): void {
  useWorkflowStore.setState({
    runs: {},
    activeRun: null,
    pendingNotifications: [],
  });
}

/** Build a fake SSE response from a list of JSON-encodable event payloads. */
function _sseResponse(events: Array<Record<string, unknown>>): Response {
  const body = events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
  return new Response(body, {
    status: 200,
    headers: { "Content-Type": "text/event-stream" },
  });
}

describe("useWorkflowStore — event accumulation", () => {
  beforeEach(_resetStore);

  it("starts with no runs and no active run", () => {
    const state = useWorkflowStore.getState();
    expect(state.runs).toEqual({});
    expect(state.activeRun).toBeNull();
    expect(state.pendingNotifications).toEqual([]);
  });

  it("appendEvent stores events keyed by runId in arrival order", () => {
    const { appendEvent } = useWorkflowStore.getState();
    const evt1: WorkflowRunEvent = {
      kind: "run-start",
      runId: "r1",
      startedAt: 1,
    };
    const evt2: WorkflowRunEvent = {
      kind: "node-start",
      runId: "r1",
      nodeId: "n1",
      nodeType: "data.fetch_quote",
      startedAt: 2,
    };
    appendEvent(evt1);
    appendEvent(evt2);

    const log = useWorkflowStore.getState().runs["r1"];
    expect(log).toEqual([evt1, evt2]);
  });

  it("run-start updates activeRun, run-complete clears it", () => {
    const { appendEvent } = useWorkflowStore.getState();
    appendEvent({ kind: "run-start", runId: "r1", startedAt: 1 });
    expect(useWorkflowStore.getState().activeRun).toBe("r1");

    appendEvent({ kind: "run-complete", runId: "r1", durationMs: 12 });
    expect(useWorkflowStore.getState().activeRun).toBeNull();
  });

  it("run-error also clears activeRun for the matching run id", () => {
    const { appendEvent } = useWorkflowStore.getState();
    appendEvent({ kind: "run-start", runId: "r1", startedAt: 1 });
    appendEvent({
      kind: "run-error",
      runId: "r1",
      message: "boom",
      durationMs: 5,
    });
    expect(useWorkflowStore.getState().activeRun).toBeNull();
  });

  it("captures desktop-notification intents from node-output events", () => {
    const { appendEvent } = useWorkflowStore.getState();
    appendEvent({
      kind: "node-output",
      runId: "r1",
      nodeId: "n5",
      outputs: {
        intent: "desktop-notification",
        notified: true,
        title: "Alert",
        message: "Price hit target",
      },
      durationMs: 2,
    });
    const intents = useWorkflowStore.getState().pendingNotifications;
    expect(intents).toHaveLength(1);
    expect(intents[0]).toMatchObject({
      runId: "r1",
      nodeId: "n5",
      title: "Alert",
      message: "Price hit target",
    });
  });

  it("non-notification node-outputs do not enqueue intents", () => {
    const { appendEvent } = useWorkflowStore.getState();
    appendEvent({
      kind: "node-output",
      runId: "r1",
      nodeId: "n1",
      outputs: { quote: { symbol: "AAPL" } },
      durationMs: 1,
    });
    expect(useWorkflowStore.getState().pendingNotifications).toEqual([]);
  });

  it("drainNotifications returns and clears the queue", () => {
    const { appendEvent, drainNotifications } = useWorkflowStore.getState();
    appendEvent({
      kind: "node-output",
      runId: "r1",
      nodeId: "n5",
      outputs: { intent: "desktop-notification", notified: true, title: "T", message: "M" },
      durationMs: 1,
    });
    const drained = drainNotifications();
    expect(drained).toHaveLength(1);
    expect(useWorkflowStore.getState().pendingNotifications).toEqual([]);
  });

  it("clearRun drops one run's log; clearAll drops all", () => {
    const { appendEvent, clearRun, clearAll } = useWorkflowStore.getState();
    appendEvent({ kind: "run-start", runId: "r1", startedAt: 1 });
    appendEvent({ kind: "run-start", runId: "r2", startedAt: 2 });
    clearRun("r1");
    expect(useWorkflowStore.getState().runs).toHaveProperty("r2");
    expect(useWorkflowStore.getState().runs).not.toHaveProperty("r1");
    clearAll();
    expect(useWorkflowStore.getState().runs).toEqual({});
  });
});

describe("useWorkflowStore — selectors are referentially stable", () => {
  beforeEach(_resetStore);

  it("selectRunLog returns the same frozen empty ref for unknown run ids", () => {
    const a = selectRunLog(useWorkflowStore.getState(), "ghost");
    const b = selectRunLog(useWorkflowStore.getState(), "other-ghost");
    const c = selectRunLog(useWorkflowStore.getState(), null);
    const d = selectRunLog(useWorkflowStore.getState(), undefined);
    expect(a).toBe(b);
    expect(b).toBe(c);
    expect(c).toBe(d);
    expect(a).toHaveLength(0);
  });

  it("selectRunLog returns the same array ref across reads when state did not change", () => {
    const { appendEvent } = useWorkflowStore.getState();
    appendEvent({ kind: "run-start", runId: "r1", startedAt: 1 });
    const a = selectRunLog(useWorkflowStore.getState(), "r1");
    const b = selectRunLog(useWorkflowStore.getState(), "r1");
    expect(a).toBe(b);
  });

  it("selectActiveRunLog mirrors selectRunLog of the active run id", () => {
    const { appendEvent } = useWorkflowStore.getState();
    appendEvent({ kind: "run-start", runId: "r1", startedAt: 1 });
    const active = selectActiveRunLog(useWorkflowStore.getState());
    const direct = selectRunLog(useWorkflowStore.getState(), "r1");
    expect(active).toBe(direct);
  });

  it("selectPendingNotifications returns the same ref across reads when nothing pending changes", () => {
    const a = selectPendingNotifications(useWorkflowStore.getState());
    const b = selectPendingNotifications(useWorkflowStore.getState());
    expect(a).toBe(b);
  });
});

describe("useWorkflowStore.runWorkflow — SSE consumption", () => {
  beforeEach(_resetStore);

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("POSTs to /workflow/run with the spec + inputs and resolves on run-start", async () => {
    const events = [
      { kind: "run-start", runId: "run-abc", startedAt: 100 },
      {
        kind: "node-start",
        runId: "run-abc",
        nodeId: "n1",
        nodeType: "data.fetch_quote",
        startedAt: 101,
      },
      {
        kind: "node-output",
        runId: "run-abc",
        nodeId: "n1",
        outputs: { quote: { symbol: "AAPL" } },
        durationMs: 12,
      },
      { kind: "run-complete", runId: "run-abc", durationMs: 22 },
    ];
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(_sseResponse(events));

    const runId = await useWorkflowStore.getState().runWorkflow(_spec(), { focused: "AAPL" });

    expect(runId).toBe("run-abc");

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(String(url)).toBe("http://127.0.0.1:51763/workflow/run");
    expect(init?.method).toBe("POST");
    const parsedBody = JSON.parse(init?.body as string) as Record<string, unknown>;
    expect(parsedBody).toEqual({ spec: _spec(), inputs: { focused: "AAPL" } });

    // The stream completes synchronously in this test (the mocked Response
    // body is finite); the log should contain every event by the time
    // runWorkflow resolves OR shortly after — wait a microtask to be sure.
    await Promise.resolve();
    await Promise.resolve();
    const log = useWorkflowStore.getState().runs["run-abc"];
    expect(log?.map((e) => e.kind)).toEqual([
      "run-start",
      "node-start",
      "node-output",
      "run-complete",
    ]);
    expect(useWorkflowStore.getState().activeRun).toBeNull();
  });

  it("normalises snake_case wire fields into camelCase events", async () => {
    const events = [
      { kind: "run-start", run_id: "snake-run", started_at: 7 },
      {
        kind: "node-output",
        run_id: "snake-run",
        node_id: "n1",
        outputs: { foo: 1 },
        duration_ms: 4,
      },
      { kind: "run-complete", run_id: "snake-run", duration_ms: 9 },
    ];
    vi.spyOn(globalThis, "fetch").mockResolvedValue(_sseResponse(events));

    const runId = await useWorkflowStore.getState().runWorkflow(_spec());
    expect(runId).toBe("snake-run");

    await Promise.resolve();
    await Promise.resolve();
    const log = useWorkflowStore.getState().runs["snake-run"];
    expect(log?.[0]).toMatchObject({ kind: "run-start", runId: "snake-run", startedAt: 7 });
    expect(log?.[1]).toMatchObject({
      kind: "node-output",
      runId: "snake-run",
      nodeId: "n1",
      durationMs: 4,
    });
  });

  it("rejects when the sidecar returns a non-2xx response", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("Internal Error", { status: 500 }),
    );

    await expect(useWorkflowStore.getState().runWorkflow(_spec())).rejects.toThrow(
      /Internal Error|500/,
    );
  });

  it("rejects when the stream closes without ever seeing run-start", async () => {
    // An empty SSE body — no frames at all.
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("", {
        status: 200,
        headers: { "Content-Type": "text/event-stream" },
      }),
    );
    await expect(useWorkflowStore.getState().runWorkflow(_spec())).rejects.toThrow(/run-start/);
  });
});
