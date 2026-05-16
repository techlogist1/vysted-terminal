/**
 * Tradesa V2 wrapper — Health panel.
 *
 * Top: big "health card" with bot status (running/degraded/stopping),
 * uptime (formatted "Nd Nh Nm"), FD count, thread count, last heartbeat
 * (relative).
 *
 * Bottom: kill-switch event timeline — fired_at (relative), source badge
 * (telegram/cli/sentinel/etc), actor, reason, cleared_at (relative) or
 * "still active" badge.
 *
 * Polls `/tradesa-v2/health` every 15 seconds.
 */

"use client";

import { POLL_CADENCE_MS, useTradesaStore } from "../store";

import { PanelShell } from "./_PanelShell";
import { formatRelativeIso, formatUptime, useInterval } from "./_utils";

import type {
  TradesaKillSwitchEvent,
  KillSwitchSource,
} from "../../../types/tradesa_v2";
import type { TradesaBotHealthLike } from "../connection";

const STATUS_TONE: Record<string, string> = {
  running: "bg-emerald-950/60 text-emerald-300 border-emerald-800",
  starting: "bg-blue-950/60 text-blue-300 border-blue-800",
  degraded: "bg-amber-950/60 text-amber-300 border-amber-800",
  stopping: "bg-zinc-900 text-zinc-400 border-zinc-700",
};

const SOURCE_TONE: Record<KillSwitchSource, string> = {
  operator_telegram: "bg-blue-950/60 text-blue-300 border-blue-800",
  manual_cli: "bg-zinc-900 text-zinc-300 border-zinc-700",
  sentinel: "bg-amber-950/60 text-amber-300 border-amber-800",
  self_tuning: "bg-purple-950/60 text-purple-300 border-purple-800",
  daily_loss: "bg-red-950/60 text-red-300 border-red-800",
};

function SourceBadge({ source }: { source: KillSwitchSource }) {
  const cls = SOURCE_TONE[source] ?? "bg-zinc-900 text-zinc-400 border-zinc-700";
  return (
    <span
      data-testid={`tradesa-source-${source}`}
      className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${cls}`}
    >
      {source.replace(/_/g, " ")}
    </span>
  );
}

function HealthCard({ latest }: { latest: TradesaBotHealthLike | null }) {
  if (!latest) {
    return (
      <div
        data-testid="tradesa-health-card"
        className="border-b border-zinc-800 bg-zinc-950/60 p-4 text-sm text-zinc-500"
      >
        No heartbeat recorded yet.
      </div>
    );
  }
  const statusTone =
    STATUS_TONE[latest.status?.toLowerCase()] ?? "bg-zinc-900 text-zinc-300 border-zinc-700";
  const tile = "flex flex-col gap-0.5 rounded-md border border-zinc-800 bg-zinc-900/40 px-3 py-2";
  return (
    <div
      data-testid="tradesa-health-card"
      className="grid shrink-0 grid-cols-2 gap-3 border-b border-zinc-800 bg-zinc-950/60 p-4 md:grid-cols-4"
    >
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Status</div>
        <span
          className={`mt-0.5 inline-flex w-fit rounded border px-1.5 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${statusTone}`}
        >
          {latest.status}
        </span>
        {latest.detail && (
          <span className="mt-1 truncate text-[10px] text-zinc-500">{latest.detail}</span>
        )}
      </div>
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Uptime</div>
        <div className="mt-0.5 font-mono text-sm text-zinc-100">{formatUptime(latest.uptime_s)}</div>
      </div>
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">FD count</div>
        <div className="mt-0.5 font-mono text-sm text-zinc-100">
          {latest.fd_count !== null ? latest.fd_count.toLocaleString() : "—"}
        </div>
      </div>
      <div className={tile}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Threads</div>
        <div className="mt-0.5 font-mono text-sm text-zinc-100">
          {latest.thread_count !== null ? latest.thread_count.toLocaleString() : "—"}
        </div>
      </div>
      <div className={`${tile} col-span-2 md:col-span-4`}>
        <div className="text-[10px] uppercase tracking-wide text-zinc-500">Last heartbeat</div>
        <div className="mt-0.5 text-sm text-zinc-100">{formatRelativeIso(latest.recorded_at)}</div>
        <div className="text-[10px] text-zinc-600">
          {latest.recorded_at} ({latest.service})
        </div>
      </div>
    </div>
  );
}

function KillSwitchTimeline({ events }: { events: TradesaKillSwitchEvent[] }) {
  if (events.length === 0) {
    return (
      <div
        data-testid="tradesa-killswitch-empty"
        className="flex flex-1 items-center justify-center p-6 text-sm text-zinc-500"
      >
        No kill-switch events recorded.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col overflow-auto p-3">
      <h3 className="mb-2 text-[11px] font-medium uppercase tracking-wide text-zinc-500">
        Kill-switch events
      </h3>
      <ul className="flex flex-col gap-2">
        {events.map((event) => (
          <li
            key={event.id}
            data-testid="tradesa-killswitch-row"
            className="rounded-md border border-zinc-800 bg-zinc-900/40 p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge source={event.source} />
              <span className="text-xs text-zinc-300">
                {event.actor ?? <em className="text-zinc-500">unknown actor</em>}
              </span>
              <span className="ml-auto text-[10px] text-zinc-500">
                {formatRelativeIso(event.fired_at)}
              </span>
            </div>
            {event.reason && (
              <p className="mt-1.5 text-xs text-zinc-300">{event.reason}</p>
            )}
            <div className="mt-1.5 text-[10px] text-zinc-500">
              {event.cleared_at ? (
                <>cleared {formatRelativeIso(event.cleared_at)}</>
              ) : (
                <span className="inline-flex rounded border border-red-800 bg-red-950/40 px-1.5 py-0.5 text-red-300">
                  still active
                </span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function HealthPanel() {
  const healthState = useTradesaStore((s) => s.health);
  const refreshHealth = useTradesaStore((s) => s.refreshHealth);

  useInterval(() => {
    void refreshHealth();
  }, POLL_CADENCE_MS.health);

  const latest = healthState.data?.latest ?? null;
  const events = healthState.data?.recent_kill_switch_events ?? [];

  return (
    <PanelShell title="Health">
      <HealthCard latest={latest} />
      <KillSwitchTimeline events={events} />
    </PanelShell>
  );
}

export default HealthPanel;
