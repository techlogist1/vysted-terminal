"use client";

/**
 * KillSwitchToolbar — BLUEPRINT §6.5 #5 UI surface.
 *
 * Always-visible red button. Two fire paths converge here:
 *
 *   1. **In-window click** — the button itself; sends `firedBy=user-toolbar`.
 *   2. **OS-wide shortcut** — the Tauri side
 *      (`src-tauri/src/kill_switch.rs`) emits `kill-switch:requested` with
 *      `{firedBy: "user-keyboard"}` when `Cmd/Ctrl+Shift+K` is pressed; this
 *      component listens and fires the POST.
 *
 * Both paths POST `/safety/kill-switch` through `useSafetyStore.fireKillSwitch`,
 * then surface the per-subscriber ack times in a transient banner so the user
 * sees the kill switch propagated to every broker in <2s (BLUEPRINT §6.5 #5).
 *
 * The component degrades gracefully when the Tauri event API is unavailable
 * (Vitest, Storybook): the OS-shortcut listener silently no-ops and the
 * button still works.
 */

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useSafetyStore } from "@/store/safety";

import type { KillSwitchFireResult, KillSwitchFiredBy } from "../../../types/safety";

interface KillSwitchEventPayload {
  firedBy: KillSwitchFiredBy;
}

interface TauriEventApi {
  listen: <T>(event: string, handler: (event: { payload: T }) => void) => Promise<() => void>;
}

async function getTauriEventApi(): Promise<TauriEventApi | null> {
  try {
    const mod = (await import("@tauri-apps/api/event")) as TauriEventApi;
    return mod;
  } catch {
    return null;
  }
}

export function KillSwitchToolbar() {
  const fireKillSwitch = useSafetyStore((s) => s.fireKillSwitch);
  const resetKillSwitch = useSafetyStore((s) => s.resetKillSwitch);
  const refreshKillSwitchStatus = useSafetyStore((s) => s.refreshKillSwitchStatus);
  const killSwitchFired = useSafetyStore((s) => s.killSwitchFired);
  const lastResult = useSafetyStore((s) => s.lastKillSwitchResult);

  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<KillSwitchFireResult | null>(null);

  const fire = useCallback(
    async (reason: string, firedBy: KillSwitchFiredBy) => {
      if (busy) {
        return;
      }
      setBusy(true);
      try {
        const result = await fireKillSwitch(reason, firedBy);
        setBanner(result);
      } catch {
        setBanner(null);
      } finally {
        setBusy(false);
      }
    },
    [busy, fireKillSwitch],
  );

  useEffect(() => {
    void refreshKillSwitchStatus();
  }, [refreshKillSwitchStatus]);

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;
    (async () => {
      const api = await getTauriEventApi();
      if (api === null || cancelled) {
        return;
      }
      unlisten = await api.listen<KillSwitchEventPayload>("kill-switch:requested", (event) => {
        const firedBy = event.payload?.firedBy ?? "user-keyboard";
        void fire(`global-shortcut: ${firedBy}`, firedBy);
      });
    })();
    return () => {
      cancelled = true;
      if (unlisten !== null) {
        unlisten();
      }
    };
  }, [fire]);

  const handleClick = useCallback(() => {
    void fire("toolbar-click", "user-toolbar");
  }, [fire]);

  const handleReset = useCallback(async () => {
    setBusy(true);
    try {
      await resetKillSwitch();
      setBanner(null);
    } finally {
      setBusy(false);
    }
  }, [resetKillSwitch]);

  return (
    <div
      data-testid="kill-switch-toolbar"
      className="pointer-events-auto fixed top-2 right-2 z-50 flex flex-col items-end gap-1"
    >
      {killSwitchFired ? (
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleReset}
          disabled={busy}
          aria-label="Reset kill switch"
          data-state="fired"
          className="border-red-500 bg-red-950/40 text-red-300 hover:bg-red-900/40"
        >
          Kill switch fired — Reset
        </Button>
      ) : (
        <Button
          type="button"
          size="sm"
          variant="destructive"
          onClick={handleClick}
          disabled={busy}
          aria-label="Halt all trading (kill switch)"
          data-state="armed"
          title="Halt all trading (Cmd/Ctrl+Shift+K)"
        >
          {busy ? "Firing…" : "Halt All Trading"}
        </Button>
      )}

      {banner !== null && <KillSwitchBanner result={banner} onDismiss={() => setBanner(null)} />}
      {!banner && lastResult !== null && killSwitchFired && (
        <KillSwitchBanner result={lastResult} onDismiss={() => undefined} muted />
      )}
    </div>
  );
}

interface BannerProps {
  result: KillSwitchFireResult;
  onDismiss: () => void;
  muted?: boolean;
}

function KillSwitchBanner({ result, onDismiss, muted = false }: BannerProps) {
  const subscriberCount = Object.keys(result.ackTimesMs).length;
  return (
    <div
      role="status"
      data-testid="kill-switch-banner"
      className={cn(
        "w-72 rounded-md border px-3 py-2 font-mono text-[10px] shadow-lg",
        muted
          ? "border-red-900 bg-red-950/40 text-red-300"
          : "border-red-500 bg-red-900/50 text-red-100",
      )}
    >
      <div className="flex items-baseline justify-between">
        <strong className="tracking-wide uppercase">Kill switch fired</strong>
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onDismiss}
          className="text-red-200/80 hover:text-red-100"
        >
          ×
        </button>
      </div>
      <p className="mt-1 leading-snug">{result.event.reason}</p>
      <dl className="mt-2 grid grid-cols-3 gap-1">
        <div>
          <dt className="text-red-200/70">subs</dt>
          <dd>{subscriberCount}</dd>
        </div>
        <div>
          <dt className="text-red-200/70">p95</dt>
          <dd>{result.p95AckMs.toFixed(1)}ms</dd>
        </div>
        <div>
          <dt className="text-red-200/70">max</dt>
          <dd>{result.maxAckMs.toFixed(1)}ms</dd>
        </div>
      </dl>
    </div>
  );
}
