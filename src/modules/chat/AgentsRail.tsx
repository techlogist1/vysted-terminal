"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Maximize2, Play, RotateCcw, Send, X } from "lucide-react";

import { tween } from "@/lib/motion";
import { cn } from "@/lib/utils";
import {
  adoptSidecarRuns,
  answerDelegateRun,
  cancelDelegateRun,
  resumeDelegateRun,
  startDelegateRun,
} from "@/lib/delegate-runs";
import { isLiveRun, useAgentRunsStore, type AgentRun } from "@/store/agent-runs";

import { agentModeMeta } from "../../../types/agent-modes";

/**
 * The agents rail (FR-027, US9) — running agent tasks with live status,
 * cost-so-far vs budget, cancel, bring-to-foreground, and a human-in-the-loop
 * answer box for a paused run. Delegate runs are durable (sidecar-tracked); the
 * cost/status here is synced by the `/runs` poller. A compound Delegate task
 * shows its plan with Start / Discard before it runs, and every run lists its
 * latest tool steps (R15-AGENT-039). A Delegate run that ended in error stays
 * with a Resume control until dismissed (R15-AGENT-035). Hidden when nothing is
 * listed.
 */
export function AgentsRail({
  onForeground,
}: {
  /** Bring a run to the foreground (the parent surfaces its transcript). */
  onForeground?: (run: AgentRun) => void;
}) {
  const runs = useAgentRunsStore((state) => state.runs);
  const cancelRun = useAgentRunsStore((state) => state.cancelRun);
  const removeRun = useAgentRunsStore((state) => state.removeRun);

  // The sidecar decides which Delegate runs exist: adopt the live ones a
  // webview reload dropped from the store (R15-UI-040).
  useEffect(() => {
    void adoptSidecarRuns();
  }, []);

  const active = useMemo(
    () => runs.filter((r) => isLiveRun(r.status) || (r.status === "error" && r.sidecarRunId)),
    [runs],
  );

  return (
    <AnimatePresence initial={false}>
      {active.length > 0 && (
        <motion.section
          aria-label="Running agents"
          className="border-charcoal-700 bg-charcoal-925 flex flex-col gap-2 border-b px-3 py-2"
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
                onCancel={() => (run.status === "error" ? removeRun(run.id) : cancelRun(run.id))}
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
  const [answerBusy, setAnswerBusy] = useState(false);
  const [answerError, setAnswerError] = useState<string | null>(null);
  const [resumeBusy, setResumeBusy] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [startBusy, setStartBusy] = useState(false);
  const failed = run.status === "error";
  const planned = run.status === "planned";
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
      className="text-micro flex flex-col gap-1"
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, height: 0 }}
      transition={tween(0.2)}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="flex min-w-0 items-center gap-2">
          <span
            className={
              failed
                ? "text-negative"
                : run.status === "paused" || planned
                  ? "text-warning"
                  : "animate-pulse text-amber-400"
            }
            aria-hidden
          >
            ●
          </span>
          <span className="text-charcoal-200 truncate">{run.agentName}</span>
          <span className="text-charcoal-500">{agentModeMeta(run.mode).label}</span>
          {cost && cost.tokens > 0 && (
            <span className="text-charcoal-500">
              {cost.tokens.toLocaleString()} tok · ${cost.spendUsd.toFixed(4)}
            </span>
          )}
        </span>
        <span className="flex shrink-0 items-center gap-1">
          {planned && (
            <button
              type="button"
              aria-label={`Start ${run.agentName}`}
              title="Start the run on this plan"
              disabled={startBusy}
              onClick={() => {
                setStartBusy(true);
                setControlError(null);
                void startDelegateRun(run).then((r) => {
                  setStartBusy(false);
                  if (!r.ok) setControlError(r.error ?? "Couldn't start the run — retry.");
                });
              }}
              className="text-charcoal-500 hover:text-charcoal-100 disabled:opacity-30"
            >
              <Play size={11} aria-hidden />
            </button>
          )}
          {failed && run.sidecarRunId && (
            <button
              type="button"
              aria-label={`Resume ${run.agentName}`}
              title="Resume from its checkpoint"
              disabled={resumeBusy}
              onClick={() => {
                setResumeBusy(true);
                setResumeError(null);
                void resumeDelegateRun(run).then((r) => {
                  setResumeBusy(false);
                  if (!r.ok) setResumeError(r.error ?? "Couldn't resume the run — retry.");
                });
              }}
              className="text-charcoal-500 hover:text-charcoal-100 disabled:opacity-30"
            >
              <RotateCcw size={11} aria-hidden />
            </button>
          )}
          {onForeground && run.sidecarRunId && (
            <button
              type="button"
              aria-label={`Bring ${run.agentName} to the foreground`}
              onClick={() => onForeground(run)}
              className="text-charcoal-500 hover:text-charcoal-100"
            >
              <Maximize2 size={11} aria-hidden />
            </button>
          )}
          <button
            type="button"
            aria-label={`${failed ? "Dismiss" : planned ? "Discard" : "Cancel"} ${run.agentName}`}
            onClick={() => {
              if (failed || !run.sidecarRunId) {
                onCancel();
                return;
              }
              setControlError(null);
              void cancelDelegateRun(run.sidecarRunId).then((r) => {
                if (!r.ok) setControlError(r.error ?? "Cancel failed — retry.");
              });
            }}
            className="text-charcoal-500 hover:text-negative"
          >
            <X size={11} aria-hidden />
          </button>
        </span>
      </div>
      {controlError && isLiveRun(run.status) && (
        <span className="text-negative text-micro" role="alert">
          {controlError}
        </span>
      )}
      {failed && (run.detail || resumeError) && (
        <span className="text-negative text-micro truncate" role="alert" title={run.detail}>
          {resumeError ?? run.detail}
        </span>
      )}
      {planned && run.plan && (
        <div aria-label={`Plan for ${run.agentName}`} className="text-charcoal-300">
          <span className="text-charcoal-200">{run.plan.goal}</span>
          <ol className="text-charcoal-400 ml-4 list-decimal">
            {run.plan.steps.map((step, i) => (
              <li key={i}>{step.rationale || step.action}</li>
            ))}
          </ol>
        </div>
      )}
      {run.activity && run.activity.length > 0 && (
        <ul aria-label={`Recent steps of ${run.agentName}`} className="text-charcoal-500">
          {run.activity.slice(-3).map((step, i) => (
            <li key={i} className="truncate" title={step.summary}>
              <span className={step.status === "error" ? "text-negative" : "text-charcoal-400"}>
                {step.status === "error" ? "✕" : "✓"} {step.tool}
              </span>{" "}
              {step.summary}
            </li>
          ))}
        </ul>
      )}
      {frac !== null && (
        <div className="bg-charcoal-800 h-0.5 w-full overflow-hidden" aria-hidden>
          <div
            className={cn("h-full", frac >= 1 ? "bg-warning" : "bg-amber-500")}
            style={{ width: `${Math.round(frac * 100)}%` }}
          />
        </div>
      )}
      {run.status === "paused" && run.question && run.sidecarRunId && (
        <>
          <form
            className="mt-0.5 flex items-center gap-1"
            onSubmit={(e) => {
              e.preventDefault();
              const text = answer.trim();
              if (!text) return;
              setAnswerBusy(true);
              setAnswerError(null);
              void answerDelegateRun(run.sidecarRunId!, text, run.provider).then((r) => {
                setAnswerBusy(false);
                if (r.ok) {
                  setAnswer(""); // keep the text on failure so it isn't lost
                } else {
                  setAnswerError(r.error ?? "Couldn't send your answer — retry.");
                }
              });
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
              disabled={answerBusy}
              className="bg-charcoal-850 text-charcoal-100 text-micro rounded-control focus:ring-charcoal-500 h-6 flex-1 px-2 outline-none focus:ring-1 disabled:opacity-50"
            />
            <button
              type="submit"
              aria-label="Submit answer"
              disabled={!answer.trim() || answerBusy}
              className="text-charcoal-500 hover:text-charcoal-100 disabled:opacity-30"
            >
              <Send size={10} aria-hidden />
            </button>
          </form>
          {answerError && (
            <span className="text-negative text-micro mt-0.5 block" role="alert">
              {answerError}
            </span>
          )}
        </>
      )}
    </motion.div>
  );
}
