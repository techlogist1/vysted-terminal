import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import type { WorkflowRunEvent } from "../../../types/workflow";
import {
  applyEvent,
  emptyOverlayState,
  WorkflowRunOverlay,
  type RunOverlayState,
} from "./workflow-run-overlay";

afterEach(() => {
  cleanup();
});

describe("workflow-run-overlay: applyEvent", () => {
  it("seeds the runId and 'running' status on run-start", () => {
    const next = applyEvent(emptyOverlayState(), {
      kind: "run-start",
      runId: "run-1",
      startedAt: 1000,
    });
    expect(next.runId).toBe("run-1");
    expect(next.status).toBe("running");
    expect(next.startedAt).toBe(1000);
    expect(next.nodes).toEqual([]);
  });

  it("adds a 'running' node row on node-start", () => {
    const events: WorkflowRunEvent[] = [
      { kind: "run-start", runId: "r1", startedAt: 0 },
      { kind: "node-start", runId: "r1", nodeId: "n1", nodeType: "data.fetch_quote", startedAt: 5 },
    ];
    const state = events.reduce(applyEvent, emptyOverlayState());
    expect(state.nodes).toHaveLength(1);
    expect(state.nodes[0]).toMatchObject({
      nodeId: "n1",
      nodeType: "data.fetch_quote",
      status: "running",
    });
  });

  it("flips a node to 'ok' with timing on node-output", () => {
    const events: WorkflowRunEvent[] = [
      { kind: "run-start", runId: "r1", startedAt: 0 },
      { kind: "node-start", runId: "r1", nodeId: "n1", nodeType: "data.fetch_quote", startedAt: 5 },
      {
        kind: "node-output",
        runId: "r1",
        nodeId: "n1",
        outputs: { quote: { last: 100 } },
        durationMs: 42,
      },
    ];
    const state = events.reduce(applyEvent, emptyOverlayState());
    const row = state.nodes[0];
    expect(row.status).toBe("ok");
    expect(row.durationMs).toBe(42);
    expect(row.outputs).toEqual({ quote: { last: 100 } });
  });

  it("flips a node to 'error' with the error message on node-error", () => {
    const events: WorkflowRunEvent[] = [
      { kind: "run-start", runId: "r1", startedAt: 0 },
      { kind: "node-start", runId: "r1", nodeId: "n1", nodeType: "data.fetch_quote", startedAt: 5 },
      { kind: "node-error", runId: "r1", nodeId: "n1", message: "boom", durationMs: 8 },
    ];
    const state = events.reduce(applyEvent, emptyOverlayState());
    expect(state.nodes[0]).toMatchObject({ status: "error", error: "boom", durationMs: 8 });
  });

  it("creates a pending row if node-output arrives before its node-start", () => {
    const next = applyEvent(emptyOverlayState(), {
      kind: "node-output",
      runId: "r1",
      nodeId: "n9",
      outputs: {},
      durationMs: 1,
    });
    expect(next.nodes[0].nodeId).toBe("n9");
    expect(next.nodes[0].status).toBe("ok");
  });

  it("sets the run-level status on run-complete and run-error", () => {
    const complete = applyEvent(emptyOverlayState(), {
      kind: "run-complete",
      runId: "r1",
      durationMs: 100,
    });
    expect(complete.status).toBe("ok");
    expect(complete.durationMs).toBe(100);

    const errored = applyEvent(emptyOverlayState(), {
      kind: "run-error",
      runId: "r1",
      message: "engine crashed",
      durationMs: 99,
    });
    expect(errored.status).toBe("error");
    expect(errored.message).toBe("engine crashed");
  });
});

describe("workflow-run-overlay: render", () => {
  it("does not render when the run state is idle", () => {
    const onClose = vi.fn();
    const { container } = render(
      <WorkflowRunOverlay state={emptyOverlayState()} onClose={onClose} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders per-node rows with their type + status + timing", () => {
    const state: RunOverlayState = {
      runId: "r1",
      status: "ok",
      startedAt: 0,
      durationMs: 100,
      nodes: [
        {
          nodeId: "n1",
          nodeType: "data.fetch_quote",
          status: "ok",
          durationMs: 42,
        },
        {
          nodeId: "n2",
          nodeType: "compute.indicator",
          status: "ok",
          durationMs: 58,
        },
      ],
    };
    render(<WorkflowRunOverlay state={state} onClose={() => {}} />);
    expect(screen.getByTestId("run-row-n1")).toHaveTextContent("data.fetch_quote");
    expect(screen.getByTestId("run-row-n2")).toHaveTextContent("compute.indicator");
    expect(screen.getByTestId("run-status-ok")).toBeInTheDocument();
  });

  it("shows the Run-again button only when the run has finished", () => {
    const onRerun = vi.fn();
    const running: RunOverlayState = {
      runId: "r1",
      status: "running",
      nodes: [],
    };
    const { rerender } = render(
      <WorkflowRunOverlay state={running} onClose={() => {}} onRerun={onRerun} />,
    );
    expect(screen.queryByRole("button", { name: "Run again" })).toBeNull();
    rerender(
      <WorkflowRunOverlay
        state={{ ...running, status: "ok" }}
        onClose={() => {}}
        onRerun={onRerun}
      />,
    );
    expect(screen.getByRole("button", { name: "Run again" })).toBeInTheDocument();
  });
});
