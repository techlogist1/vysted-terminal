/**
 * Tradesa V2 wrapper — Brain Decisions panel.
 *
 * Two-column layout:
 *   Left: scrollable list of recent DirectorDecision cards.
 *   Right: today's LLM cost rollup (total + per-model div-bar chart).
 *
 * Polls `/tradesa-v2/decisions` every 30s (Router LLM fires on watcher
 * events only, so 30s captures every brain-tick within one cadence) and
 * `/tradesa-v2/cost-today` every 60s.
 */

"use client";

import { useMemo, useState } from "react";

import { POLL_CADENCE_MS, arrayOrEmpty, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import {
  formatPercent,
  formatRelativeIso,
  formatUsd,
  useInterval,
} from "./_utils";

import type {
  DecisionAction,
  TradesaCostRollup,
  TradesaDecision,
} from "../../../types/tradesa_v2";

// ---------------------------------------------------------------------------
// Decision card
// ---------------------------------------------------------------------------

const ACTION_TONE: Record<DecisionAction, string> = {
  OPEN_LONG: "bg-emerald-950/60 text-emerald-300 border-emerald-800",
  OPEN_SHORT: "bg-red-950/60 text-red-300 border-red-800",
  CLOSE: "bg-amber-950/60 text-amber-300 border-amber-800",
  ADJUST_SL: "bg-amber-950/60 text-amber-300 border-amber-800",
  HOLD: "bg-zinc-900 text-zinc-400 border-zinc-700",
};

function ActionBadge({ action }: { action: DecisionAction }) {
  const cls = ACTION_TONE[action];
  return (
    <span
      data-testid={`tradesa-action-${action}`}
      className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}
    >
      {action.replace("_", " ")}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(1, value));
  const pct = Math.round(clamped * 100);
  const tone =
    clamped >= 0.75
      ? "bg-emerald-500"
      : clamped >= 0.5
        ? "bg-blue-500"
        : clamped >= 0.25
          ? "bg-amber-500"
          : "bg-red-500";
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label="Decision confidence"
      className="flex items-center gap-2"
    >
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-zinc-400">{pct}%</span>
    </div>
  );
}

function DecisionCard({ decision }: { decision: TradesaDecision }) {
  const [expanded, setExpanded] = useState(false);
  const rationale = decision.rationale ?? "";
  const truncated = rationale.length > 200 ? rationale.slice(0, 200) + "…" : rationale;
  const isLong = rationale.length > 200;

  return (
    <article
      data-testid="tradesa-decision-card"
      className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3 transition-colors hover:bg-zinc-900/70"
    >
      <header className="flex flex-wrap items-center gap-2">
        <ActionBadge action={decision.action} />
        <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-300">
          {decision.instrument}
        </span>
        <ConfidenceBar value={decision.confidence} />
        <span className="ml-auto text-[10px] text-zinc-500">
          {formatRelativeIso(decision.timestamp)}
        </span>
      </header>

      {(decision.size_pct !== null || decision.stop_loss_pct !== null) && (
        <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-zinc-400">
          {decision.size_pct !== null && (
            <span>
              size <span className="font-mono text-zinc-200">{formatPercent(decision.size_pct)}</span>
            </span>
          )}
          {decision.stop_loss_pct !== null && (
            <span>
              SL <span className="font-mono text-zinc-200">{formatPercent(decision.stop_loss_pct)}</span>
            </span>
          )}
          <span>
            lev <span className="font-mono text-zinc-200">{decision.leverage}x</span>
          </span>
        </div>
      )}

      {rationale && (
        <div className="mt-2 text-xs leading-relaxed text-zinc-300">
          {expanded ? rationale : truncated}
          {isLong && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="ml-2 text-blue-400 hover:text-blue-300 hover:underline"
            >
              {expanded ? "show less" : "show more"}
            </button>
          )}
        </div>
      )}
    </article>
  );
}

function DecisionsColumn({ decisions }: { decisions: readonly TradesaDecision[] }) {
  if (decisions.length === 0) {
    return (
      <div
        data-testid="tradesa-decisions-empty"
        className="flex h-full items-center justify-center p-6 text-sm text-zinc-500"
      >
        No brain decisions yet — Router LLM hasn't fired the Director.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col gap-2 overflow-auto p-3">
      {decisions.map((d) => (
        <DecisionCard key={d.id} decision={d} />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Cost rollup column
// ---------------------------------------------------------------------------

function CostColumn({ rollup }: { rollup: TradesaCostRollup | undefined }) {
  const entries = useMemo(() => {
    if (!rollup) return [] as { model: string; cost: number; pct: number }[];
    const sorted = Object.entries(rollup.by_model)
      .map(([model, cost]) => ({ model, cost }))
      .sort((a, b) => b.cost - a.cost);
    const max = sorted.length > 0 ? sorted[0].cost : 0;
    return sorted.map((e) => ({ ...e, pct: max > 0 ? e.cost / max : 0 }));
  }, [rollup]);

  return (
    <aside
      data-testid="tradesa-cost-rollup"
      className="flex w-full flex-col gap-3 border-l border-zinc-800 bg-zinc-950/60 p-3 md:w-72"
    >
      <header>
        <h3 className="text-xs font-medium uppercase tracking-wide text-zinc-500">
          Today's LLM cost
        </h3>
        <p className="mt-1 font-mono text-2xl text-zinc-100">
          {formatUsd(rollup?.total_usd ?? 0)}
        </p>
        {rollup?.date && (
          <p className="text-[10px] text-zinc-600">{rollup.date} UTC</p>
        )}
      </header>

      <div className="flex flex-col gap-2">
        <h4 className="text-[10px] font-medium uppercase tracking-wide text-zinc-500">
          By model
        </h4>
        {entries.length === 0 ? (
          <p className="text-xs text-zinc-500">No LLM calls today.</p>
        ) : (
          <ul className="flex flex-col gap-1.5">
            {entries.map((entry) => (
              <li key={entry.model} data-testid="tradesa-cost-row" className="flex flex-col gap-0.5">
                <div className="flex justify-between text-[11px] text-zinc-300">
                  <span className="truncate font-mono">{entry.model}</span>
                  <span className="font-mono text-zinc-400">{formatUsd(entry.cost)}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-zinc-800">
                  <div
                    className="h-full bg-blue-500"
                    style={{ width: `${Math.round(entry.pct * 100)}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}

export function BrainDecisionsPanel() {
  const decisionsState = useTradesaStore((s) => s.decisions);
  const costState = useTradesaStore((s) => s.costToday);
  const refreshDecisions = useTradesaStore((s) => s.refreshDecisions);
  const refreshCostToday = useTradesaStore((s) => s.refreshCostToday);

  useInterval(() => {
    void refreshDecisions();
  }, POLL_CADENCE_MS.decisions);

  useInterval(() => {
    void refreshCostToday();
  }, POLL_CADENCE_MS.cost);

  const decisions = arrayOrEmpty(decisionsState.data);

  return (
    <PanelShell title="Brain Decisions">
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        <DecisionsColumn decisions={decisions} />
        <CostColumn rollup={costState.data} />
      </div>
    </PanelShell>
  );
}

export default BrainDecisionsPanel;
