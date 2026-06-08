"use client";

import type { AgentRunBudget } from "@/store/agent-runs";

/** Sensible default ceiling for a Delegate run (FR-026) — bounded tokens, spend,
 *  wall-clock, and steps so an autonomous run can never overrun unbounded. */
export const DEFAULT_DELEGATE_BUDGET: AgentRunBudget = {
  maxTokens: 120_000,
  maxSpendUsd: 1.0,
  maxWallSeconds: 600,
  maxSteps: 12,
};

/**
 * The Delegate budget editor (FR-026) — shown when the agent is in Delegate mode
 * so the user sets the hard ceiling BEFORE launching an autonomous background
 * run. The first breach of any ceiling aborts the run (enforced server-side by
 * the BudgetGuard); this is the trust gate for autonomous spend.
 */
export function BudgetConfig({
  budget,
  onChange,
}: {
  budget: AgentRunBudget;
  onChange: (budget: AgentRunBudget) => void;
}) {
  const field = (
    label: string,
    key: keyof AgentRunBudget,
    step: number,
    value: number | undefined,
  ) => (
    <label className="flex items-center gap-1.5">
      <span className="text-charcoal-500">{label}</span>
      <input
        type="number"
        min={0}
        step={step}
        value={value ?? ""}
        aria-label={`Delegate budget — ${label}`}
        onChange={(e) => {
          const n = e.target.value === "" ? undefined : Number(e.target.value);
          onChange({ ...budget, [key]: Number.isFinite(n) ? n : undefined });
        }}
        className="bg-charcoal-850 text-charcoal-100 text-caption rounded-control focus:ring-charcoal-500 h-8 w-16 px-1.5 text-right outline-none focus:ring-1"
      />
    </label>
  );
  return (
    <div
      aria-label="Delegate budget"
      className="border-charcoal-700 text-charcoal-400 text-caption flex flex-wrap items-center gap-x-3 gap-y-1.5 border-b px-3 py-1.5"
    >
      <span className="tracking-wide uppercase">Budget</span>
      {field("tokens", "maxTokens", 10_000, budget.maxTokens)}
      {field("$", "maxSpendUsd", 0.25, budget.maxSpendUsd)}
      {field("sec", "maxWallSeconds", 60, budget.maxWallSeconds)}
      {field("steps", "maxSteps", 1, budget.maxSteps)}
      <span className="text-charcoal-500">— first breach aborts the run</span>
    </div>
  );
}
