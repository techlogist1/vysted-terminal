"use client";

/**
 * Workflow run overlay — per-node observability surface.
 *
 * Subscribes to a stream of `WorkflowRunEvent`s coming from
 * `POST /workflow/run` (Teammate W's SSE route) and renders the live
 * timing / output / error state for every node in the running workflow.
 *
 * The overlay UI is intentionally simple: a vertically-stacked list of
 * node rows where each row shows status + duration once the node has
 * completed. This is the "populated screenshot" target from the plan —
 * "Run overlay showing per-node timing post-run".
 *
 * The parent panel owns the run lifecycle (the fetch + EventSource
 * subscription) and feeds the reduced state in via props; the overlay
 * is a pure render component so it can be unit-tested without touching
 * the network.
 */

import { useMemo } from "react";

import type { WorkflowRunEvent } from "../../../types/workflow";
import { cn } from "@/lib/utils";

/** Per-node aggregate state derived from the SSE event stream. */
export interface NodeRunState {
  nodeId: string;
  nodeType: string;
  status: "pending" | "running" | "ok" | "error";
  startedAt?: number;
  durationMs?: number;
  outputs?: Record<string, unknown>;
  error?: string;
}

/** Overall-run state derived from the SSE event stream. */
export interface RunOverlayState {
  runId: string | null;
  status: "idle" | "running" | "ok" | "error";
  startedAt?: number;
  durationMs?: number;
  message?: string;
  nodes: NodeRunState[];
}

/** Build the initial state shown before any events have arrived. */
export function emptyOverlayState(): RunOverlayState {
  return { runId: null, status: "idle", nodes: [] };
}

/**
 * Reduce one SSE event into the overlay state. Pure function for tests.
 * The reducer is forgiving on unknown ids — if a `node-output` arrives
 * before its `node-start` (re-ordered network frames) it creates a
 * pending row instead of crashing.
 */
export function applyEvent(state: RunOverlayState, event: WorkflowRunEvent): RunOverlayState {
  switch (event.kind) {
    case "run-start":
      return {
        runId: event.runId,
        status: "running",
        startedAt: event.startedAt,
        nodes: [],
      };
    case "node-start": {
      const next = upsertNode(state.nodes, event.nodeId, (row) => ({
        ...row,
        nodeType: event.nodeType,
        status: "running",
        startedAt: event.startedAt,
      }));
      return { ...state, nodes: next };
    }
    case "node-output": {
      const next = upsertNode(state.nodes, event.nodeId, (row) => ({
        ...row,
        status: "ok",
        outputs: event.outputs,
        durationMs: event.durationMs,
      }));
      return { ...state, nodes: next };
    }
    case "node-error": {
      const next = upsertNode(state.nodes, event.nodeId, (row) => ({
        ...row,
        status: "error",
        error: event.message,
        durationMs: event.durationMs,
      }));
      return { ...state, nodes: next };
    }
    case "run-complete":
      return {
        ...state,
        status: "ok",
        durationMs: event.durationMs,
      };
    case "run-error":
      return {
        ...state,
        status: "error",
        durationMs: event.durationMs,
        message: event.message,
      };
    default: {
      const exhaustive: never = event;
      return exhaustive;
    }
  }
}

function upsertNode(
  nodes: readonly NodeRunState[],
  nodeId: string,
  update: (row: NodeRunState) => NodeRunState,
): NodeRunState[] {
  const idx = nodes.findIndex((row) => row.nodeId === nodeId);
  if (idx === -1) {
    return [
      ...nodes,
      update({
        nodeId,
        nodeType: "?",
        status: "pending",
      }),
    ];
  }
  const next = nodes.slice();
  next[idx] = update(nodes[idx]);
  return next;
}

interface WorkflowRunOverlayProps {
  state: RunOverlayState;
  onClose: () => void;
  onRerun?: () => void;
}

export function WorkflowRunOverlay({ state, onClose, onRerun }: WorkflowRunOverlayProps) {
  // Track the total summary across nodes so the header can show
  // "n/N complete" while the run is still in flight.
  const summary = useMemo(() => {
    const total = state.nodes.length;
    const finished = state.nodes.filter((n) => n.status === "ok" || n.status === "error").length;
    return { total, finished };
  }, [state.nodes]);

  if (state.status === "idle") {
    return null;
  }

  return (
    <aside
      data-testid="workflow-run-overlay"
      className="border-charcoal-700 bg-charcoal-900 flex h-full w-72 flex-col border-l"
    >
      <header className="border-charcoal-700 flex items-baseline justify-between border-b px-3 py-2">
        <div className="flex flex-col">
          <span className="text-charcoal-200 font-mono text-xs uppercase">Run</span>
          <span className="text-charcoal-500 truncate font-mono text-[10px]">
            {state.runId ?? "—"}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close run overlay"
          className="text-charcoal-400 font-mono text-sm hover:text-amber-400"
        >
          ×
        </button>
      </header>

      <div className="border-charcoal-800 flex items-center justify-between border-b px-3 py-2">
        <RunStatusBadge status={state.status} />
        <span className="text-charcoal-400 font-mono text-[10px]">
          {summary.finished}/{summary.total}
          {state.durationMs !== undefined ? ` · ${state.durationMs.toFixed(0)}ms` : ""}
        </span>
      </div>

      <ul className="flex-1 overflow-y-auto">
        {state.nodes.map((node) => (
          <li
            key={node.nodeId}
            data-testid={`run-row-${node.nodeId}`}
            className="border-charcoal-800 flex flex-col gap-1 border-b px-3 py-2"
          >
            <div className="flex items-baseline justify-between">
              <span className="text-charcoal-100 font-mono text-xs">{node.nodeId}</span>
              <NodeStatusBadge status={node.status} />
            </div>
            <span className="text-charcoal-500 font-mono text-[10px]">{node.nodeType}</span>
            {node.durationMs !== undefined && (
              <span className="text-charcoal-400 font-mono text-[10px]">
                {node.durationMs.toFixed(0)}ms
              </span>
            )}
            {node.error !== undefined && (
              <span className="text-negative font-mono text-[10px]">{node.error}</span>
            )}
            {node.outputs !== undefined && Object.keys(node.outputs).length > 0 && (
              <pre className="bg-charcoal-850 text-charcoal-300 max-h-32 overflow-auto rounded p-1 font-mono text-[10px] leading-snug whitespace-pre-wrap">
                {formatOutputs(node.outputs)}
              </pre>
            )}
          </li>
        ))}
      </ul>

      {state.status !== "running" && onRerun !== undefined && (
        <footer className="border-charcoal-700 border-t px-3 py-2">
          <button
            type="button"
            onClick={onRerun}
            className="bg-charcoal-800 hover:bg-charcoal-700 text-charcoal-100 w-full rounded-md py-1.5 font-mono text-xs"
          >
            Run again
          </button>
        </footer>
      )}
    </aside>
  );
}

function RunStatusBadge({ status }: { status: RunOverlayState["status"] }) {
  return (
    <span
      data-testid={`run-status-${status}`}
      className={cn(
        "rounded-control border px-1.5 py-0.5 font-mono text-[10px] uppercase",
        status === "running" && "border-amber-500 bg-amber-500/10 text-amber-300",
        status === "ok" && "border-positive bg-positive/10 text-positive",
        status === "error" && "border-negative bg-negative/10 text-negative",
        status === "idle" && "border-charcoal-700 text-charcoal-400",
      )}
    >
      {status}
    </span>
  );
}

function NodeStatusBadge({ status }: { status: NodeRunState["status"] }) {
  return (
    <span
      data-testid={`node-status-${status}`}
      className={cn(
        "rounded-control border px-1.5 py-0.5 font-mono text-[9px] uppercase",
        status === "running" && "border-amber-500 bg-amber-500/10 text-amber-300",
        status === "ok" && "border-positive bg-positive/10 text-positive",
        status === "error" && "border-negative bg-negative/10 text-negative",
        status === "pending" && "border-charcoal-700 text-charcoal-400",
      )}
    >
      {status}
    </span>
  );
}

function formatOutputs(outputs: Record<string, unknown>): string {
  try {
    return JSON.stringify(outputs, null, 2);
  } catch {
    return String(outputs);
  }
}
