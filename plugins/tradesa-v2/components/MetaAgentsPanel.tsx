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
import { formatRelativeIso, useInterval } from "./_utils";

import type {
  TradesaDiscoveryHypothesis,
  TradesaReflectionNote,
  TradesaTuningProposal,
  TuningProposalStatus,
} from "../../../types/tradesa_v2";

type TabKey = "tuning" | "discovery" | "reflection";

const STATUS_TONE: Record<TuningProposalStatus, string> = {
  pending: "bg-blue-950/60 text-blue-300 border-blue-800",
  approved: "bg-emerald-950/60 text-emerald-300 border-emerald-800",
  rejected: "bg-red-950/60 text-red-300 border-red-800",
  applied: "bg-purple-950/60 text-purple-300 border-purple-800",
  expired: "bg-zinc-900 text-zinc-400 border-zinc-700",
};

const HYPOTHESIS_TONE: Record<TradesaDiscoveryHypothesis["status"], string> = {
  open: "bg-blue-950/60 text-blue-300 border-blue-800",
  approved: "bg-emerald-950/60 text-emerald-300 border-emerald-800",
  rejected: "bg-red-950/60 text-red-300 border-red-800",
  tested: "bg-purple-950/60 text-purple-300 border-purple-800",
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
  const tone = clamped >= 0.75 ? "bg-emerald-500" : clamped >= 0.5 ? "bg-blue-500" : "bg-amber-500";
  return (
    <div className="flex items-center gap-2" aria-label="Confidence">
      <div className="h-1.5 w-24 overflow-hidden rounded-full bg-zinc-800">
        <div className={`h-full ${tone}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="font-mono text-[10px] text-zinc-400">{pct}%</span>
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
          ? "border-blue-500 text-zinc-100"
          : "border-transparent text-zinc-400 hover:text-zinc-200"
      }`}
    >
      {children}
      <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-300">
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
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
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
          className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <StatusBadge status={p.status} tone={STATUS_TONE[p.status]} />
            <span className="font-mono text-[11px] text-zinc-300">{p.target_key}</span>
            <span className="ml-auto text-[10px] text-zinc-500">
              {formatRelativeIso(p.proposed_at)}
            </span>
          </header>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            <span className="rounded bg-zinc-950 px-2 py-1 font-mono text-zinc-500 line-through">
              {p.current_value}
            </span>
            <span className="rounded bg-zinc-950 px-2 py-1 font-mono text-emerald-300">
              {p.proposed_value}
            </span>
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] tracking-wide text-zinc-300 uppercase">
              {p.queue_reason}
            </span>
          </div>
          {p.rationale && (
            <p className="mt-2 text-xs leading-relaxed text-zinc-300">{p.rationale}</p>
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
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
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
          className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <StatusBadge status={h.status} tone={HYPOTHESIS_TONE[h.status]} />
            <h4 className="text-sm font-semibold text-zinc-100">{h.title}</h4>
            <span className="ml-auto text-[10px] text-zinc-500">
              {formatRelativeIso(h.proposed_at)}
            </span>
          </header>
          <div className="mt-2">
            <ConfidenceBar value={h.confidence} />
          </div>
          {h.body && <p className="mt-2 text-xs leading-relaxed text-zinc-300">{h.body}</p>}
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
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
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
          className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3"
        >
          <header className="flex flex-wrap items-center gap-2">
            <span className="rounded bg-zinc-800 px-1.5 py-0.5 font-mono text-[10px] text-zinc-300">
              trade {note.trade_id.slice(0, 8)}
            </span>
            <span className="ml-auto text-[10px] text-zinc-500">
              {formatRelativeIso(note.created_at)}
            </span>
          </header>
          <p className="mt-2 text-xs font-medium text-zinc-100">{note.summary}</p>
          {note.tags.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {note.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded bg-blue-950/40 px-1.5 py-0.5 font-mono text-[10px] text-blue-300"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
          {note.body && <p className="mt-2 text-xs leading-relaxed text-zinc-300">{note.body}</p>}
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

  return (
    <PanelShell title="Meta-Agents">
      <nav
        role="tablist"
        aria-label="Meta-agent tabs"
        className="flex shrink-0 border-b border-zinc-800 bg-zinc-950/60 px-2"
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
