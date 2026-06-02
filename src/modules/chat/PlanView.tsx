/**
 * PlanView — the visible "plan-then-execute" surface (Track 6 #2).
 *
 * When a compound request runs on a capable model, the sidecar decomposes it into
 * an ordered plan (`services.planner.decompose`) and streams it as an `agent_plan`
 * event BEFORE the tool loop. This renders that plan up front — "here's what I'm
 * about to do" — so the work feels deliberate rather than opaque. It is ADVISORY:
 * the loop still drives execution and stages each host-action through the existing
 * diff/accept gate; the pills below just mark which steps will route there
 * (`review`) versus run inline (`research` / `answer`). Never auto-applies anything.
 */

"use client";

import { motion, useReducedMotion } from "framer-motion";
import { ListChecks } from "lucide-react";

import { staggerChild, staggerParent } from "@/lib/motion";
import type { AgentPlanView } from "@/store/chat-history";

/** A short, human label + pill tone for a plan step's action. */
function stepBadge(action: string, staged: boolean): { label: string; tone: string } {
  if (staged) {
    return { label: "review", tone: "text-amber-300/90 border-amber-500/40" };
  }
  if (action === "research" || action === "deep_research") {
    return { label: "research", tone: "text-sky-300/90 border-sky-500/40" };
  }
  return { label: "answer", tone: "text-charcoal-400 border-charcoal-600" };
}

/** Turn a planner action verb into a terse human phrase for the step line. */
function stepText(action: string, args: Record<string, unknown>, rationale: string): string {
  if (rationale.trim()) {
    return rationale.trim();
  }
  const symbol = typeof args.symbol === "string" ? args.symbol : undefined;
  const query = typeof args.query === "string" ? args.query : undefined;
  switch (action) {
    case "set_chart_symbol":
      return symbol ? `Chart ${symbol}` : "Set the chart symbol";
    case "add_to_watchlist":
      return symbol ? `Add ${symbol} to the watchlist` : "Add to the watchlist";
    case "open_panel":
      return typeof args.panel === "string" ? `Open the ${args.panel} panel` : "Open a panel";
    case "arrange_layout":
      return typeof args.pattern === "string" ? `Arrange: ${args.pattern}` : "Arrange the layout";
    case "research":
    case "deep_research":
      return query ? `Research ${query}` : "Research";
    default:
      return action.replace(/_/g, " ");
  }
}

export function PlanView({ plan, active }: { plan: AgentPlanView; active: boolean }) {
  const reduce = useReducedMotion();
  if (!plan.steps.length) {
    return null;
  }
  return (
    <div className="border-charcoal-700 bg-charcoal-800/40 mb-1.5 rounded-md border px-2.5 py-2">
      <div className="text-charcoal-300 mb-1.5 flex items-center gap-1.5 text-[0.6rem] tracking-wide uppercase">
        <ListChecks className={`size-3 text-amber-400 ${active ? "animate-pulse" : ""}`} />
        <span>Plan</span>
        <span className="text-charcoal-500">· {plan.steps.length} steps</span>
      </div>
      <motion.ol
        className="flex flex-col gap-1"
        variants={reduce ? undefined : staggerParent}
        initial={reduce ? undefined : "hidden"}
        animate={reduce ? undefined : "show"}
      >
        {plan.steps.map((step, index) => {
          const badge = stepBadge(step.action, step.staged);
          return (
            <motion.li
              key={`${index}-${step.action}`}
              variants={reduce ? undefined : staggerChild}
              className="flex items-start gap-2 text-[0.68rem] leading-snug"
            >
              <span className="text-charcoal-500 mt-px tabular-nums">{index + 1}.</span>
              <span className="text-charcoal-200 flex-1">
                {stepText(step.action, step.args, step.rationale)}
              </span>
              <span className={`shrink-0 rounded border px-1 py-px text-[0.55rem] ${badge.tone}`}>
                {badge.label}
              </span>
            </motion.li>
          );
        })}
      </motion.ol>
      {plan.note && (
        <div className="text-charcoal-500 mt-1.5 text-[0.6rem] italic">{plan.note}</div>
      )}
    </div>
  );
}
