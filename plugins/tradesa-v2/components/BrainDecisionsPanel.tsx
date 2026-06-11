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
import { PanelFetchError } from "./PanelFetchError";
import { formatPercent, formatRelativeIso, formatUsd, useInterval } from "./_utils";

import type { DecisionAction, TradesaCostRollup, TradesaDecision } from "../../../types/tradesa_v2";

// ---------------------------------------------------------------------------
// Decision card
// ---------------------------------------------------------------------------

const ACTION_TONE: Record<DecisionAction, string> = {
  OPEN_LONG: "text-positive bg-positive/15 border-positive/40",
  OPEN_SHORT: "text-negative bg-negative/15 border-negative/40",
  CLOSE: "text-warning bg-warning/15 border-warning/40",
  ADJUST_SL: "text-warning bg-warning/15 border-warning/40",
  HOLD: "bg-charcoal-800 text-charcoal-400 border-charcoal-700",
};

function ActionBadge({ action }: { action: DecisionAction }) {
  const cls = ACTION_TONE[action];
  return (
    <span
      data-testid={`tradesa-action-${action}`}
      className={`text-micro rounded-control inline-flex border px-1 py-0.5 font-semibold tracking-wide uppercase ${cls}`}
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
      ? "bg-positive"
      : clamped >= 0.5
        ? "bg-warning"
        : clamped >= 0.25
          ? "bg-warning"
          : "bg-negative";
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={pct}
      aria-label="Decision confidence"
      className="flex items-center gap-2"
    >
      <div className="bg-charcoal-800 h-1 w-20 overflow-hidden rounded-none">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-charcoal-400 text-micro font-mono">{pct}%</span>
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
      className="border-charcoal-800 bg-charcoal-900/40 hover:bg-charcoal-900/70 rounded-none border p-3 transition-colors"
    >
      <header className="flex flex-wrap items-center gap-2">
        <ActionBadge action={decision.action} />
        <span className="bg-charcoal-800 text-charcoal-300 text-micro rounded-control px-1 py-0.5 font-mono">
          {decision.instrument}
        </span>
        <ConfidenceBar value={decision.confidence} />
        <span className="text-charcoal-500 text-micro ml-auto">
          {formatRelativeIso(decision.timestamp)}
        </span>
      </header>

      {(decision.size_pct !== null || decision.stop_loss_pct !== null) && (
        <div className="text-charcoal-400 text-micro mt-2 flex flex-wrap gap-3">
          {decision.size_pct !== null && (
            <span>
              size{" "}
              <span className="text-charcoal-200 font-mono">
                {formatPercent(decision.size_pct)}
              </span>
            </span>
          )}
          {decision.stop_loss_pct !== null && (
            <span>
              SL{" "}
              <span className="text-charcoal-200 font-mono">
                {formatPercent(decision.stop_loss_pct)}
              </span>
            </span>
          )}
          <span>
            lev <span className="text-charcoal-200 font-mono">{decision.leverage}x</span>
          </span>
        </div>
      )}

      {rationale && (
        <div className="text-charcoal-300 text-caption mt-2 leading-relaxed">
          {expanded ? rationale : truncated}
          {isLong && (
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-charcoal-300 hover:text-charcoal-100 ml-2 hover:underline"
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
        className="text-charcoal-500 text-body flex h-full items-center justify-center p-6"
      >
        No brain decisions yet — Router LLM hasn&apos;t fired the Director.
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
      className="border-charcoal-800 bg-charcoal-925/60 flex w-full flex-col gap-3 border-l p-3 md:w-72"
    >
      <header>
        <h3 className="text-charcoal-500 text-caption font-medium tracking-wide uppercase">
          Today&apos;s LLM cost
        </h3>
        <p className="text-charcoal-100 text-overview mt-1 font-mono">
          {formatUsd(rollup?.total_usd ?? 0)}
        </p>
        {rollup?.date && <p className="text-charcoal-500 text-micro">{rollup.date} UTC</p>}
      </header>

      <div className="flex flex-col gap-2">
        <h4 className="text-charcoal-500 text-micro font-medium tracking-wide uppercase">
          By model
        </h4>
        {entries.length === 0 ? (
          <p className="text-charcoal-500 text-caption">No LLM calls today.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {entries.map((entry) => (
              <li
                key={entry.model}
                data-testid="tradesa-cost-row"
                className="flex flex-col gap-0.5"
              >
                <div className="text-charcoal-300 text-micro flex justify-between">
                  <span className="truncate font-mono">{entry.model}</span>
                  <span className="text-charcoal-400 font-mono">{formatUsd(entry.cost)}</span>
                </div>
                <div className="bg-charcoal-800 h-1 overflow-hidden rounded-none">
                  <div
                    className="bg-charcoal-500 h-full"
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
      <PanelFetchError error={decisionsState.error} onRetry={() => void refreshDecisions()} />
      <div className="flex flex-1 flex-col overflow-hidden md:flex-row">
        <DecisionsColumn decisions={decisions} />
        <CostColumn rollup={costState.data} />
      </div>
    </PanelShell>
  );
}

export default BrainDecisionsPanel;
