"use client";

import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Maximize2, Send, X } from "lucide-react";

import { tween } from "@/lib/motion";
import { cn } from "@/lib/utils";
import { answerDelegateRun } from "@/lib/delegate-runs";
import { useAgentRunsStore, type AgentRun } from "@/store/agent-runs";

import { agentModeMeta } from "../../../types/agent-modes";

/**
 * The agents rail (FR-027, US9) — running agent tasks with live status,
 * cost-so-far vs budget, cancel, bring-to-foreground, and a human-in-the-loop
 * answer box for a paused run. Delegate runs are durable (sidecar-tracked); the
 * cost/status here is synced by the `/runs` poller. Hidden when nothing runs.
 */
export function AgentsRail({
  onForeground,
}: {
  /** Bring a run to the foreground (the parent surfaces its transcript). */
  onForeground?: (run: AgentRun) => void;
}) {
  const runs = useAgentRunsStore((state) => state.runs);
  const cancelRun = useAgentRunsStore((state) => state.cancelRun);

  const active = useMemo(
    () => runs.filter((r) => r.status === "running" || r.status === "paused"),
    [runs],
  );

  return (
    <AnimatePresence initial={false}>
      {active.length > 0 && (
        <motion.section
          aria-label="Running agents"
          className="border-charcoal-700 bg-charcoal-925 flex flex-col gap-1.5 border-b px-3 py-1.5"
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          style={{ overflow: "hidden" }}
          transition={tween(0.2)}
        >
          <AnimatePresence initial={false}>
            {active.map((run) => (
              <RunRow
                key={run.id}
                run={run}
                onCancel={() => cancelRun(run.id)}
                onForeground={onForeground}
              />
            ))}
          </AnimatePresence>
        </motion.section>
      )}
    </AnimatePresence>
  );
}

function RunRow({
  run,
  onCancel,
  onForeground,
}: {
  run: AgentRun;
  onCancel: () => void;
  onForeground?: (run: AgentRun) => void;
}) {
  const [answer, setAnswer] = useState("");
  const cost = run.cost;
  const budget = run.budget;
  // Budget usage fraction (tokens-based, the most common ceiling) for the bar.
  const frac =
    budget?.maxTokens && cost
      ? Math.min(1, cost.tokens / budget.maxTokens)
      : run.status === "running"
        ? null
        : 1;

  return (
    <motion.div
      layout
      className="flex flex-col gap-1 font-mono text-[0.6rem]"
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={tween(0.2)}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-1.5">
          <span
            className={run.status === "paused" ? "text-warning" : "animate-pulse text-amber-400"}
            aria-hidden
          >
            ●
          </span>
          <span className="text-charcoal-200 truncate">{run.agentName}</span>
          <span className="text-charcoal-500">{agentModeMeta(run.mode).label}</span>
          {cost && cost.tokens > 0 && (
            <span className="text-charcoal-500">
              {cost.tokens.toLocaleString()} tok
              {cost.spendUsd > 0 ? ` · $${cost.spendUsd.toFixed(4)}` : ""}
            </span>
          )}
        </span>
        <span className="flex shrink-0 items-center gap-1">
          {onForeground && run.sidecarRunId && (
            <button
              type="button"
              aria-label={`Bring ${run.agentName} to the foreground`}
              onClick={() => onForeground(run)}
              className="text-charcoal-500 hover:text-amber-300"
            >
              <Maximize2 size={11} aria-hidden />
            </button>
          )}
          <button
            type="button"
            aria-label={`Cancel ${run.agentName}`}
            onClick={onCancel}
            className="text-charcoal-500 hover:text-negative"
          >
            <X size={11} aria-hidden />
          </button>
        </span>
      </div>
      {frac !== null && (
        <div className="bg-charcoal-800 h-0.5 w-full overflow-hidden rounded-full" aria-hidden>
          <div
            className={cn("h-full rounded-full", frac >= 1 ? "bg-warning" : "bg-amber-500")}
            style={{ width: `${Math.round(frac * 100)}%` }}
          />
        </div>
      )}
      {run.status === "paused" && run.question && run.sidecarRunId && (
        <form
          className="mt-0.5 flex items-center gap-1"
          onSubmit={(e) => {
            e.preventDefault();
            if (answer.trim()) {
              void answerDelegateRun(run.sidecarRunId!, answer.trim());
              setAnswer("");
            }
          }}
        >
          {/* min-w-0 ensures the question truncates before the input is pushed off */}
          <span className="text-warning min-w-0 truncate" title={run.question}>
            {run.question}
          </span>
          <input
            aria-label="Answer the agent's question"
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            className="bg-charcoal-800 text-charcoal-100 h-5 flex-1 rounded px-1.5 text-[0.6rem] outline-none focus:ring-1 focus:ring-amber-400"
          />
          <button
            type="submit"
            aria-label="Submit answer"
            disabled={!answer.trim()}
            className="text-charcoal-500 hover:text-amber-300 disabled:opacity-30"
          >
            <Send size={10} aria-hidden />
          </button>
        </form>
      )}
    </motion.div>
  );
}
