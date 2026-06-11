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
import { PanelFetchError } from "./PanelFetchError";
import { formatRelativeIso, formatUptime, useInterval } from "./_utils";

import type { TradesaKillSwitchEvent, KillSwitchSource } from "../../../types/tradesa_v2";
import type { TradesaBotHealthLike } from "../connection";

const STATUS_TONE: Record<string, string> = {
  running: "text-positive bg-positive/15 border-positive/40",
  starting: "text-warning bg-warning/15 border-warning/40",
  degraded: "text-warning bg-warning/15 border-warning/40",
  stopping: "bg-charcoal-800 text-charcoal-400 border-charcoal-700",
};

const SOURCE_TONE: Record<KillSwitchSource, string> = {
  operator_telegram: "bg-charcoal-800 text-charcoal-300 border-charcoal-700",
  manual_cli: "bg-charcoal-800 text-charcoal-300 border-charcoal-700",
  sentinel: "text-warning bg-warning/15 border-warning/40",
  self_tuning: "bg-amber-500/15 text-amber-300 border-amber-500/40",
  daily_loss: "text-negative bg-negative/15 border-negative/40",
};

function SourceBadge({ source }: { source: KillSwitchSource }) {
  const cls = SOURCE_TONE[source] ?? "bg-charcoal-800 text-charcoal-400 border-charcoal-700";
  return (
    <span
      data-testid={`tradesa-source-${source}`}
      className={`text-micro rounded-control inline-flex border px-1 py-0.5 font-semibold tracking-wide uppercase ${cls}`}
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
        className="border-charcoal-800 bg-charcoal-925/60 text-charcoal-500 text-body border-b p-4"
      >
        No heartbeat recorded yet.
      </div>
    );
  }
  const statusTone =
    STATUS_TONE[latest.status?.toLowerCase()] ??
    "bg-charcoal-800 text-charcoal-300 border-charcoal-700";
  const tile =
    "border-charcoal-800 bg-charcoal-900/40 flex flex-col gap-0.5 rounded-none border px-3 py-2";
  return (
    <div
      data-testid="tradesa-health-card"
      className="border-charcoal-800 bg-charcoal-925/60 grid shrink-0 grid-cols-2 gap-3 border-b p-4 md:grid-cols-4"
    >
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Status</div>
        <span
          className={`rounded-control text-micro mt-0.5 inline-flex w-fit border px-1 py-0.5 font-semibold tracking-wide uppercase ${statusTone}`}
        >
          {latest.status}
        </span>
        {latest.detail && (
          <span className="text-charcoal-500 text-micro mt-1 truncate">{latest.detail}</span>
        )}
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Uptime</div>
        <div className="text-charcoal-100 text-body mt-0.5 font-mono">
          {formatUptime(latest.uptime_s)}
        </div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">FD count</div>
        <div className="text-charcoal-100 text-body mt-0.5 font-mono">
          {latest.fd_count !== null ? latest.fd_count.toLocaleString() : "—"}
        </div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Threads</div>
        <div className="text-charcoal-100 text-body mt-0.5 font-mono">
          {latest.thread_count !== null ? latest.thread_count.toLocaleString() : "—"}
        </div>
      </div>
      <div className={`${tile} col-span-2 md:col-span-4`}>
        <div className="text-charcoal-500 text-micro tracking-wide uppercase">Last heartbeat</div>
        <div className="text-charcoal-100 text-body mt-0.5">
          {formatRelativeIso(latest.recorded_at)}
        </div>
        <div className="text-charcoal-500 text-micro">
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
        className="text-charcoal-500 text-body flex flex-1 items-center justify-center p-6"
      >
        No kill-switch events recorded.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col overflow-auto p-3">
      <h3 className="text-charcoal-500 text-micro mb-2 font-medium tracking-wide uppercase">
        Kill-switch events
      </h3>
      <ul className="flex flex-col gap-2">
        {events.map((event) => (
          <li
            key={event.id}
            data-testid="tradesa-killswitch-row"
            className="border-charcoal-800 bg-charcoal-900/40 rounded-none border p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge source={event.source} />
              <span className="text-charcoal-300 text-caption">
                {event.actor ?? <em className="text-charcoal-500">unknown actor</em>}
              </span>
              <span className="text-charcoal-500 text-micro ml-auto">
                {formatRelativeIso(event.fired_at)}
              </span>
            </div>
            {event.reason && <p className="text-charcoal-300 text-caption mt-2">{event.reason}</p>}
            <div className="text-charcoal-500 text-micro mt-2">
              {event.cleared_at ? (
                <>cleared {formatRelativeIso(event.cleared_at)}</>
              ) : (
                <span className="border-negative/40 bg-negative/15 text-negative rounded-control inline-flex border px-1 py-0.5">
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
      <PanelFetchError error={healthState.error} onRetry={() => void refreshHealth()} />
      <HealthCard latest={latest} />
      <KillSwitchTimeline events={events} />
    </PanelShell>
  );
}

export default HealthPanel;
