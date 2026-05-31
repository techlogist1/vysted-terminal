"use client";

/**
 * KillSwitchToolbar — BLUEPRINT §6.5 #5 UI surface.
 *
 * The kill switch lives inline in the header as a quiet, always-available
 * control: an octagon-stop icon that is cool-neutral at rest and escalates to
 * red only when it has been FIRED. The app ships read-only with no live order
 * path, so a permanent red "Halt All Trading" billboard would be fear-theater —
 * the control earns prominence when there is something to halt, not before. The
 * §6.5 mechanism behind it is unchanged; it stays one click (or one OS-global
 * Cmd/Ctrl+Shift+K) away, with a clear tooltip and a loud fired-state banner.
 *
 * Two fire paths converge here:
 *   1. **In-window click** — the icon; sends `firedBy=user-toolbar`.
 *   2. **OS-wide shortcut** — the Tauri side (`src-tauri/src/kill_switch.rs`)
 *      emits `kill-switch:requested {firedBy:"user-keyboard"}` on
 *      `Cmd/Ctrl+Shift+K`; this component listens and fires the POST.
 *
 * Both POST `/safety/kill-switch` via `useSafetyStore.fireKillSwitch`. The
 * fire result's per-subscriber ack latency is retained in the result + audit
 * for the §6.5 <2s benchmark, but it is NOT surfaced in the user banner — that
 * is bench telemetry, not user information. The banner states the *consequence*
 * in human terms instead.
 *
 * Degrades gracefully when the Tauri event API is unavailable (Vitest,
 * Storybook): the OS-shortcut listener silently no-ops and the button works.
 */

import { useCallback, useEffect, useState } from "react";
import { OctagonX, RotateCcw } from "lucide-react";

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
  const [fireError, setFireError] = useState<string | null>(null);

  const fire = useCallback(
    async (reason: string, firedBy: KillSwitchFiredBy) => {
      if (busy) {
        return;
      }
      setBusy(true);
      setFireError(null);
      try {
        const result = await fireKillSwitch(reason, firedBy);
        setBanner(result);
      } catch (error) {
        // A kill switch that fails to fire is a safety event the user MUST
        // see — never swallow it silently (hunt-error-surfaces #2).
        setBanner(null);
        setFireError(error instanceof Error ? error.message : "Kill switch failed to fire.");
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
      const off = await api.listen<KillSwitchEventPayload>("kill-switch:requested", (event) => {
        const firedBy = event.payload?.firedBy ?? "user-keyboard";
        void fire(`global-shortcut: ${firedBy}`, firedBy);
      });
      // Re-check after the await: if cleanup ran while listen() was pending,
      // unlisten is still null so cleanup skipped it — tear it down now instead
      // of leaking a listener that keeps firing the kill switch after unmount.
      if (cancelled) {
        off();
        return;
      }
      unlisten = off;
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
    setFireError(null);
    try {
      await resetKillSwitch();
      setBanner(null);
    } catch (error) {
      setFireError(error instanceof Error ? error.message : "Kill switch reset failed.");
    } finally {
      setBusy(false);
    }
  }, [resetKillSwitch]);

  return (
    <>
      {/* The control lives inline in the header flex (no fixed positioning, so
          it can never overlap the neighbouring status / settings controls). */}
      {killSwitchFired ? (
        <button
          type="button"
          onClick={handleReset}
          disabled={busy}
          aria-label="Reset kill switch"
          data-testid="kill-switch-toolbar"
          data-state="fired"
          title="Kill switch fired — trading halted. Click to reset."
          className="border-negative/60 bg-negative/15 text-negative hover:bg-negative/25 flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[11px] leading-none transition-colors disabled:opacity-50"
        >
          <OctagonX className="h-3.5 w-3.5" aria-hidden />
          {busy ? "Resetting…" : "Halt fired — Reset"}
        </button>
      ) : (
        <button
          type="button"
          onClick={handleClick}
          disabled={busy}
          aria-label="Halt all trading (kill switch)"
          data-testid="kill-switch-toolbar"
          data-state="armed"
          title="Kill switch — halt trading & force read-only (⌘⌃⇧K)"
          className={cn(
            "text-charcoal-500 hover:text-negative hover:bg-charcoal-800 flex size-6 items-center justify-center rounded-md transition-colors disabled:opacity-50",
            busy && "text-negative animate-pulse",
          )}
        >
          <OctagonX className="h-4 w-4" aria-hidden />
        </button>
      )}

      {/* Notifications float below the header so they never disturb its layout. */}
      <div className="pointer-events-none fixed top-11 right-3 z-50 flex flex-col items-end gap-1">
        <div className="pointer-events-auto flex flex-col items-end gap-1">
          {fireError !== null && (
            <div
              role="alert"
              data-testid="kill-switch-error"
              className="border-negative bg-negative/20 text-negative w-72 rounded-md border px-3 py-2 font-mono text-[11px] shadow-lg"
            >
              <div className="flex items-baseline justify-between">
                <strong className="tracking-wide uppercase">Kill switch failed to fire</strong>
                <button
                  type="button"
                  aria-label="Dismiss"
                  onClick={() => setFireError(null)}
                  className="hover:text-lume opacity-80"
                >
                  ×
                </button>
              </div>
              <p className="mt-1 leading-snug">
                {fireError} — retry, or halt manually at your broker.
              </p>
            </div>
          )}
          {banner !== null && (
            <KillSwitchBanner
              result={banner}
              onDismiss={() => setBanner(null)}
              onReset={handleReset}
            />
          )}
          {!banner && lastResult !== null && killSwitchFired && (
            <KillSwitchBanner result={lastResult} onDismiss={() => undefined} muted />
          )}
        </div>
      </div>
    </>
  );
}

interface BannerProps {
  result: KillSwitchFireResult;
  onDismiss: () => void;
  onReset?: () => void;
  muted?: boolean;
}

function KillSwitchBanner({ result, onDismiss, onReset, muted = false }: BannerProps) {
  // User-meaningful confirmation: how many connections acknowledged the halt.
  // Latency percentiles (p95/max) stay in the result + audit for the §6.5
  // benchmark but are deliberately NOT shown here — they are bench telemetry.
  const ackCount = Object.keys(result.ackTimesMs).length;
  return (
    <div
      role="status"
      data-testid="kill-switch-banner"
      className={cn(
        "w-72 rounded-md border px-3 py-2.5 font-mono text-[11px] shadow-lg",
        muted
          ? "border-negative/40 bg-negative/10 text-negative/90"
          : "border-negative bg-negative/20 text-negative",
      )}
    >
      <div className="flex items-baseline justify-between gap-2">
        <strong className="flex items-center gap-1.5 tracking-wide uppercase">
          <OctagonX className="h-3.5 w-3.5" aria-hidden />
          Kill switch fired
        </strong>
        <button
          type="button"
          aria-label="Dismiss"
          onClick={onDismiss}
          className="hover:text-lume opacity-80"
        >
          ×
        </button>
      </div>
      <p className="text-foreground/90 mt-1.5 leading-snug">
        Trading halted — new orders blocked and all brokers forced read-only.
      </p>
      <p className="mt-1 opacity-70">
        Acknowledged by {ackCount} connection{ackCount === 1 ? "" : "s"}.
      </p>
      {!muted && onReset && (
        <button
          type="button"
          onClick={onReset}
          className="border-negative/50 hover:bg-negative/25 mt-2 inline-flex items-center gap-1.5 rounded-md border px-2 py-1 leading-none transition-colors"
        >
          <RotateCcw className="h-3 w-3" aria-hidden />
          Reset
        </button>
      )}
    </div>
  );
}
