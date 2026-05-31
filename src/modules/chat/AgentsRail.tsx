"use client";

import { useMemo } from "react";
import { X } from "lucide-react";

import { useAgentRunsStore } from "@/store/agent-runs";

import { agentModeMeta } from "../../../types/agent-modes";

/**
 * The agents rail (FR-027, US3 AS3) — running agent tasks with live status,
 * cost-so-far, and a cancel control. In P1 a run is a foreground invocation
 * (Delegate included); P3 deepens this into durable, budget-guarded background
 * runs with checkpoint/resume + bring-to-foreground. Hidden when nothing runs.
 */
export function AgentsRail() {
  const runs = useAgentRunsStore((state) => state.runs);
  const cancelRun = useAgentRunsStore((state) => state.cancelRun);

  const active = useMemo(
    () => runs.filter((r) => r.status === "running" || r.status === "paused"),
    [runs],
  );
  if (active.length === 0) {
    return null;
  }

  return (
    <section
      aria-label="Running agents"
      className="border-charcoal-700 bg-charcoal-925 border-b px-3 py-1"
    >
      <ul className="flex flex-col gap-1">
        {active.map((run) => (
          <li
            key={run.id}
            className="flex items-center justify-between gap-2 font-mono text-[0.6rem]"
          >
            <span className="flex min-w-0 items-center gap-1.5">
              <span
                className={
                  run.status === "paused" ? "text-warning" : "animate-pulse text-amber-400"
                }
                aria-hidden
              >
                ●
              </span>
              <span className="text-charcoal-200 truncate">{run.agentName}</span>
              <span className="text-charcoal-500">{agentModeMeta(run.mode).label}</span>
              {typeof run.tokens === "number" && run.tokens > 0 && (
                <span className="text-charcoal-500">{run.tokens.toLocaleString()} tok</span>
              )}
              {run.status === "paused" && run.detail && (
                <span className="text-warning truncate">{run.detail}</span>
              )}
            </span>
            <button
              type="button"
              aria-label={`Cancel ${run.agentName}`}
              onClick={() => cancelRun(run.id)}
              className="text-charcoal-500 hover:text-negative shrink-0"
            >
              <X size={11} aria-hidden />
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
