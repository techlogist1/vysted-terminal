/**
 * Tradesa V2 wrapper — Meta-Agents panel.
 *
 * Three tabs over the bot's meta-agent outputs:
 *   "Tuning Proposals"     — tuning_proposals rows (operator approval queue)
 *   "Discovery Hypotheses" — discovery_hypotheses rows (re-enabled at closed_trades ≥ 100)
 *   "Reflection Notes"     — reflection_notes rows (one per closed trade)
 *
 * Each tab refreshes its surface via `refreshMetaAgentSurface(kind)` on
 * mount + tab switch. Cadence: 120 seconds.
 *
 * Read-only display per v0.6.5 contract — Vysted never approves or
 * rejects proposals (operator does that via Telegram inline keyboard).
 */

"use client";

import { useEffect, useState } from "react";

import { POLL_CADENCE_MS, arrayOrEmpty, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import { PanelFetchError } from "./PanelFetchError";
import { formatRelativeIso, useInterval } from "./_utils";

import type {
  TradesaDiscoveryHypothesis,
  TradesaReflectionNote,
  TradesaTuningProposal,
  TuningProposalStatus,
} from "../../../types/tradesa_v2";

type TabKey = "tuning" | "discovery" | "reflection";

const STATUS_TONE: Record<TuningProposalStatus, string> = {
  pending: "text-warning bg-warning/15 border-warning/40",
  approved: "text-positive bg-positive/15 border-positive/40",
  rejected: "text-negative bg-negative/15 border-negative/40",
  applied: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  expired: "bg-charcoal-800 text-charcoal-400 border-charcoal-700",
};

const HYPOTHESIS_TONE: Record<TradesaDiscoveryHypothesis["status"], string> = {
  open: "text-warning bg-warning/15 border-warning/40",
  approved: "text-positive bg-positive/15 border-positive/40",
  rejected: "text-negative bg-negative/15 border-negative/40",
  tested: "text-positive bg-positive/15 border-positive/40",
};

function StatusBadge({ status, tone }: { status: string; tone: string }) {
  return (
    <span
      className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${tone}`}
    >
      {status}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(1, value));
  const pct = Math.round(clamped * 100);
  const tone = clamped >= 0.75 ? "bg-positive" : clamped >= 0.5 ? "bg-warning" : "bg-negative";
  return (
    <div className="flex items-center gap-2" aria-label="Confidence">
      <div className="bg-charcoal-800 h-1.5 w-24 overflow-hidden rounded-full">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-charcoal-400 font-mono text-[10px]">{pct}%</span>
    </div>
  );
}

function TabButton({
  active,
  count,
  onClick,
  children,
  testId,
}: {
  active: boolean;
  count: number;
  onClick: () => void;
  children: React.ReactNode;
  testId: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      data-testid={testId}
      aria-pressed={active}
      className={`-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm transition-colors ${
        active
          ? "text-charcoal-100 border-amber-400"
          : "text-charcoal-400 hover:text-charcoal-200 border-transparent"
      }`}
    >
      {children}
      <span className="bg-charcoal-800 text-charcoal-300 rounded px-1.5 py-0.5 font-mono text-[10px]">
        {count}
      </span>
    </button>
  );
}

function TuningTab({ rows }: { rows: readonly TradesaTuningProposal[] }) {
  if (rows.length === 0) {
    return (
      <div
        data-testid="tradesa-tuning-empty"
        className="text-charcoal-500 flex flex-1 items-center justify-center p-6 text-sm"
      >
        No tuning proposals yet — the self-tuning agent hasn&apos;t queued one.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col gap-2 overflow-auto p-3">
      {rows.map((p) => (
        <article
          key={p.id}
          data-testid="tradesa-tuning-card"
          className="border-charcoal-800 bg-charcoal-900/40 rounded-md border p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <StatusBadge status={p.status} tone={STATUS_TONE[p.status]} />
            <span className="text-charcoal-300 font-mono text-[11px]">{p.target_key}</span>
            <span className="text-charcoal-500 ml-auto text-[10px]">
              {formatRelativeIso(p.proposed_at)}
            </span>
          </header>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="bg-charcoal-950 text-charcoal-500 rounded px-2 py-1 font-mono line-through">
              {p.current_value}
            </span>
            <span className="bg-charcoal-950 text-positive rounded px-2 py-1 font-mono">
              {p.proposed_value}
            </span>
            <span className="bg-charcoal-800 text-charcoal-300 rounded px-1.5 py-0.5 text-[10px] tracking-wide uppercase">
              {p.queue_reason}
            </span>
          </div>
          {p.rationale && (
            <p className="text-charcoal-300 mt-2 text-xs leading-relaxed">{p.rationale}</p>
          )}
        </article>
      ))}
    </div>
  );
}

function DiscoveryTab({ rows }: { rows: readonly TradesaDiscoveryHypothesis[] }) {
  if (rows.length === 0) {
    return (
      <div
        data-testid="tradesa-discovery-empty"
        className="text-charcoal-500 flex flex-1 items-center justify-center p-6 text-sm"
      >
        No discovery hypotheses yet. (Re-enabled at closed_trades ≥ 100.)
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col gap-2 overflow-auto p-3">
      {rows.map((h) => (
        <article
          key={h.id}
          data-testid="tradesa-discovery-card"
          className="border-charcoal-800 bg-charcoal-900/40 rounded-md border p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <StatusBadge status={h.status} tone={HYPOTHESIS_TONE[h.status]} />
            <h4 className="text-charcoal-100 text-sm font-semibold">{h.title}</h4>
            <span className="text-charcoal-500 ml-auto text-[10px]">
              {formatRelativeIso(h.proposed_at)}
            </span>
          </header>
          <div className="mt-2">
            <ConfidenceBar value={h.confidence} />
          </div>
          {h.body && <p className="text-charcoal-300 mt-2 text-xs leading-relaxed">{h.body}</p>}
        </article>
      ))}
    </div>
  );
}

function ReflectionTab({ rows }: { rows: readonly TradesaReflectionNote[] }) {
  if (rows.length === 0) {
    return (
      <div
        data-testid="tradesa-reflection-empty"
        className="text-charcoal-500 flex flex-1 items-center justify-center p-6 text-sm"
      >
        No reflection notes yet.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col gap-2 overflow-auto p-3">
      {rows.map((note) => (
        <article
          key={note.id}
          data-testid="tradesa-reflection-card"
          className="border-charcoal-800 bg-charcoal-900/40 rounded-md border p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <span className="bg-charcoal-800 text-charcoal-300 rounded px-1.5 py-0.5 font-mono text-[10px]">
              trade {note.trade_id.slice(0, 8)}
            </span>
            <span className="text-charcoal-500 ml-auto text-[10px]">
              {formatRelativeIso(note.created_at)}
            </span>
          </header>
          <p className="text-charcoal-100 mt-2 text-xs font-medium">{note.summary}</p>
          {note.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {note.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] text-amber-300"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          {note.body && (
            <p className="text-charcoal-300 mt-2 text-xs leading-relaxed">{note.body}</p>
          )}
        </article>
      ))}
    </div>
  );
}

export function MetaAgentsPanel() {
  const [tab, setTab] = useState<TabKey>("tuning");
  const tuningState = useTradesaStore((s) => s.tuningProposals);
  const discoveryState = useTradesaStore((s) => s.discoveryHypotheses);
  const reflectionState = useTradesaStore((s) => s.reflectionNotes);
  const refreshMetaAgentSurface = useTradesaStore((s) => s.refreshMetaAgentSurface);

  // Initial fetch for all three surfaces so tab switch is instant.
  useEffect(() => {
    void refreshMetaAgentSurface("tuning");
    void refreshMetaAgentSurface("discovery");
    void refreshMetaAgentSurface("reflection");
  }, [refreshMetaAgentSurface]);

  // On every cadence + on tab switch, re-fetch the active tab's data.
  useInterval(() => {
    void refreshMetaAgentSurface(tab);
  }, POLL_CADENCE_MS.metaAgents);

  const tuning = arrayOrEmpty(tuningState.data);
  const discovery = arrayOrEmpty(discoveryState.data);
  const reflection = arrayOrEmpty(reflectionState.data);

  // Surface the active tab's fetch error (Phase 9.5) — each surface fetches
  // independently, so show the one the user is currently viewing.
  const activeState =
    tab === "tuning" ? tuningState : tab === "discovery" ? discoveryState : reflectionState;

  return (
    <PanelShell title="Meta-Agents">
      <PanelFetchError
        error={activeState.error}
        onRetry={() => void refreshMetaAgentSurface(tab)}
      />
      <nav
        role="tablist"
        aria-label="Meta-agent tabs"
        className="border-charcoal-800 bg-charcoal-925/60 flex shrink-0 border-b px-2"
      >
        <TabButton
          active={tab === "tuning"}
          onClick={() => setTab("tuning")}
          count={tuning.length}
          testId="tradesa-tab-tuning"
        >
          Tuning
        </TabButton>
        <TabButton
          active={tab === "discovery"}
          onClick={() => setTab("discovery")}
          count={discovery.length}
          testId="tradesa-tab-discovery"
        >
          Discovery
        </TabButton>
        <TabButton
          active={tab === "reflection"}
          onClick={() => setTab("reflection")}
          count={reflection.length}
          testId="tradesa-tab-reflection"
        >
          Reflection
        </TabButton>
      </nav>
      {tab === "tuning" && <TuningTab rows={tuning} />}
      {tab === "discovery" && <DiscoveryTab rows={discovery} />}
      {tab === "reflection" && <ReflectionTab rows={reflection} />}
    </PanelShell>
  );
}

export default MetaAgentsPanel;
