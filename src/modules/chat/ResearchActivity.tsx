/**
 * ResearchActivity — the live "thinking / working" surface (Track A).
 *
 * Renders the research-pipeline steps that stream into a chat message while a
 * long research tool runs (`deep_research` / `research`). Before this, a research
 * round fired and then went silent for many seconds — the agent felt dead. Now
 * each step (plan → gather → search → distill → reflect → synthesize) animates in
 * as it happens, with a live elapsed timer and a "brewing" scanline, so the work
 * is visibly underway. Cosmetic only — it surfaces real cognition the sidecar
 * already emits, never fabricated progress.
 *
 * While the message is still streaming (`active`) the latest step pulses and a
 * scanline sweeps; once the run finishes it collapses to a compact, legible
 * trace ("Researched in 6.4s · 5 steps") the user can still read.
 */

"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Check,
  Compass,
  Cpu,
  FileSearch,
  Layers,
  Lightbulb,
  Loader2,
  PenLine,
  Radar,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { useEffect, useState } from "react";

import { tween } from "@/lib/motion";
import { cn } from "@/lib/utils";
import type { ResearchStepView } from "@/store/chat-history";

/** Per-step-kind icon + verb. Unknown kinds fall back to the generic tool look. */
const STEP_META: Record<string, { icon: LucideIcon; label: string }> = {
  engine: { icon: Cpu, label: "Engine" },
  plan: { icon: Compass, label: "Planning" },
  tool: { icon: Wrench, label: "Gathering data" },
  search: { icon: FileSearch, label: "Searching the web" },
  compress: { icon: Layers, label: "Distilling findings" },
  distill: { icon: Layers, label: "Distilling into the report" },
  reflect: { icon: Lightbulb, label: "Assessing coverage" },
  synthesize: { icon: PenLine, label: "Writing the brief" },
};

function metaFor(kind: string): { icon: LucideIcon; label: string } {
  return STEP_META[kind] ?? { icon: Wrench, label: kind };
}

function formatElapsed(ms: number): string {
  const secs = ms / 1000;
  return secs < 10 ? `${secs.toFixed(1)}s` : `${Math.round(secs)}s`;
}

/** Live ticking elapsed-time readout (only mounts while a run is active). */
function ElapsedTimer({ startedAt }: { startedAt: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(id);
  }, []);
  return <span className="tabular-nums">{formatElapsed(Math.max(0, now - startedAt))}</span>;
}

export interface ResearchActivityProps {
  steps: ResearchStepView[];
  /** ``true`` while the owning message is still streaming. */
  active: boolean;
  /** Epoch ms the first step arrived (for the elapsed readout). */
  startedAt?: number;
}

export function ResearchActivity({ steps, active, startedAt }: ResearchActivityProps) {
  if (steps.length === 0) {
    return null;
  }
  const lastIndex = steps.length - 1;
  const totalLatency = steps.reduce((sum, s) => sum + (s.latencyMs ?? 0), 0);

  return (
    <div
      className={cn(
        "mb-2 overflow-hidden rounded-none border",
        active
          ? "border-amber-500/40 bg-amber-500/[0.07]"
          : "border-charcoal-700 bg-charcoal-800/40",
      )}
      aria-label="Research activity"
      aria-live="polite"
    >
      <div className="flex items-center gap-2 px-2 py-2">
        {active ? (
          <motion.span
            animate={{ rotate: 360 }}
            transition={{ repeat: Infinity, ease: "linear", duration: 2.4 }}
            className="text-amber-400"
            aria-hidden
          >
            <Radar size={12} />
          </motion.span>
        ) : (
          <Check size={12} className="text-positive" aria-hidden />
        )}
        <span className="text-micro text-charcoal-200">
          {active ? "Researching" : "Researched"}
        </span>
        <span className="text-micro text-charcoal-500 ml-auto tabular-nums">
          {active && startedAt ? (
            <ElapsedTimer startedAt={startedAt} />
          ) : (
            <>
              {totalLatency > 0 ? `${formatElapsed(totalLatency)} · ` : ""}
              {steps.length} step{steps.length === 1 ? "" : "s"}
            </>
          )}
        </span>
      </div>

      <ul className="flex flex-col gap-1 px-2 pb-2">
        <AnimatePresence initial={false}>
          {steps.map((step, i) => {
            const { icon: Icon, label } = metaFor(step.stepKind);
            const isCurrent = active && i === lastIndex;
            const errored = step.status === "error";
            const skipped = step.status === "skipped";
            // The engine line carries the honest backend/fallback reason — show it
            // in full (wrapped) rather than truncated, so it stays legible.
            const isEngine = step.stepKind === "engine";
            return (
              <motion.li
                key={`${step.index}-${step.stepKind}`}
                layout
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 1, x: 0 }}
                transition={tween(0.16)}
                className={cn("text-caption flex gap-2", isEngine ? "items-start" : "items-center")}
              >
                <span
                  className={cn(
                    "flex h-4 w-4 shrink-0 items-center justify-center",
                    errored ? "text-negative" : isCurrent ? "text-amber-400" : "text-charcoal-400",
                  )}
                  aria-hidden
                >
                  {isCurrent ? <Loader2 size={11} className="animate-spin" /> : <Icon size={11} />}
                </span>
                <span
                  className={cn(
                    "shrink-0 font-medium",
                    isCurrent ? "text-amber-300" : "text-charcoal-300",
                  )}
                >
                  {label}
                </span>
                <span
                  className={cn(
                    isEngine ? "min-w-0 flex-1" : "truncate",
                    errored
                      ? "text-negative/80"
                      : skipped
                        ? "text-charcoal-500"
                        : "text-charcoal-400",
                  )}
                  title={step.detail}
                >
                  {step.detail}
                </span>
                {typeof step.latencyMs === "number" && !isCurrent && (
                  <span className="text-charcoal-600 ml-auto shrink-0 tabular-nums">
                    {step.latencyMs}ms
                  </span>
                )}
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ul>

      {active && (
        <div className="relative h-0.5 w-full overflow-hidden bg-amber-500/10" aria-hidden>
          <motion.div
            className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-amber-400/70 to-transparent"
            animate={{ x: ["-100%", "300%"] }}
            transition={{ repeat: Infinity, ease: "easeInOut", duration: 1.6 }}
          />
        </div>
      )}
    </div>
  );
}
