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
      className={`inline-flex rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase ${cls}`}
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
        className="border-charcoal-800 bg-charcoal-925/60 text-charcoal-500 border-b p-4 text-sm"
      >
        No heartbeat recorded yet.
      </div>
    );
  }
  const statusTone =
    STATUS_TONE[latest.status?.toLowerCase()] ??
    "bg-charcoal-800 text-charcoal-300 border-charcoal-700";
  const tile =
    "border-charcoal-800 bg-charcoal-900/40 flex flex-col gap-0.5 rounded-md border px-3 py-2";
  return (
    <div
      data-testid="tradesa-health-card"
      className="border-charcoal-800 bg-charcoal-925/60 grid shrink-0 grid-cols-2 gap-3 border-b p-4 md:grid-cols-4"
    >
      <div className={tile}>
        <div className="text-charcoal-500 text-[10px] tracking-wide uppercase">Status</div>
        <span
          className={`mt-0.5 inline-flex w-fit rounded border px-1.5 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${statusTone}`}
        >
          {latest.status}
        </span>
        {latest.detail && (
          <span className="text-charcoal-500 mt-1 truncate text-[10px]">{latest.detail}</span>
        )}
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-[10px] tracking-wide uppercase">Uptime</div>
        <div className="text-charcoal-100 mt-0.5 font-mono text-sm">
          {formatUptime(latest.uptime_s)}
        </div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-[10px] tracking-wide uppercase">FD count</div>
        <div className="text-charcoal-100 mt-0.5 font-mono text-sm">
          {latest.fd_count !== null ? latest.fd_count.toLocaleString() : "—"}
        </div>
      </div>
      <div className={tile}>
        <div className="text-charcoal-500 text-[10px] tracking-wide uppercase">Threads</div>
        <div className="text-charcoal-100 mt-0.5 font-mono text-sm">
          {latest.thread_count !== null ? latest.thread_count.toLocaleString() : "—"}
        </div>
      </div>
      <div className={`${tile} col-span-2 md:col-span-4`}>
        <div className="text-charcoal-500 text-[10px] tracking-wide uppercase">Last heartbeat</div>
        <div className="text-charcoal-100 mt-0.5 text-sm">
          {formatRelativeIso(latest.recorded_at)}
        </div>
        <div className="text-charcoal-500 text-[10px]">
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
        className="text-charcoal-500 flex flex-1 items-center justify-center p-6 text-sm"
      >
        No kill-switch events recorded.
      </div>
    );
  }
  return (
    <div className="flex flex-1 flex-col overflow-auto p-3">
      <h3 className="text-charcoal-500 mb-2 text-[11px] font-medium tracking-wide uppercase">
        Kill-switch events
      </h3>
      <ul className="flex flex-col gap-2">
        {events.map((event) => (
          <li
            key={event.id}
            data-testid="tradesa-killswitch-row"
            className="border-charcoal-800 bg-charcoal-900/40 rounded-md border p-3"
          >
            <div className="flex flex-wrap items-center gap-2">
              <SourceBadge source={event.source} />
              <span className="text-charcoal-300 text-xs">
                {event.actor ?? <em className="text-charcoal-500">unknown actor</em>}
              </span>
              <span className="text-charcoal-500 ml-auto text-[10px]">
                {formatRelativeIso(event.fired_at)}
              </span>
            </div>
            {event.reason && <p className="text-charcoal-300 mt-1.5 text-xs">{event.reason}</p>}
            <div className="text-charcoal-500 mt-1.5 text-[10px]">
              {event.cleared_at ? (
                <>cleared {formatRelativeIso(event.cleared_at)}</>
              ) : (
                <span className="border-negative/40 bg-negative/15 text-negative inline-flex rounded border px-1.5 py-0.5">
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
