/**
 * Tradesa V2 wrapper — shared panel shell.
 *
 * Every Tradesa V2 panel renders this shell at the top level, which:
 *
 *   1. Always mounts `<TradesaBotStatusStrip />` as the panel header.
 *   2. Branches on the current `TradesaConnectionStatus` and renders
 *      one of five dedicated state-UX surfaces (skeleton / unauth /
 *      bot-offline / supabase-error / partial-warning + body). The
 *      `healthy` and `partial` branches render the panel-specific
 *      body via the `children` render prop; the others render a
 *      panel-agnostic state UX.
 *
 * The component centralises every status-branch decision so individual
 * panels stay focused on rendering their tabular / list bodies. The
 * `<TradesaSettingsDialog />` is opened directly from the `unauthenticated`
 * branch's "Open Settings" CTA.
 *
 * The shell never fetches data — its only side effect is opening the
 * settings dialog (controlled by the panel via component-local state).
 */

import { useState, type ReactNode } from "react";
import { RefreshCw } from "lucide-react";

import { useTradesaConnectionState } from "../useTradesaConnectionState";

import { TradesaBotStatusStrip } from "./TradesaBotStatusStrip";
import { TradesaSettingsDialog } from "./TradesaSettingsDialog";

interface PanelShellProps {
  /** Display label for the panel ("Live Positions" etc.) — used in empty-state copy. */
  title: string;
  /** Render-prop for the populated body — only invoked in healthy / partial / bot-offline states. */
  children: ReactNode;
  /**
   * Optional dim-style toggle: when the connection is `bot-offline` the
   * panel renders the body but visually muted (last-known data is
   * stale). Default: true.
   */
  muteOnBotOffline?: boolean;
}

/**
 * Skeleton-loader rows for the `connecting` state.
 */
function SkeletonBody() {
  return (
    <div
      role="status"
      aria-label="Loading"
      data-testid="tradesa-skeleton"
      className="flex flex-1 flex-col gap-2 p-4"
    >
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="h-8 animate-pulse rounded bg-zinc-800/60"
          style={{ width: `${85 - i * 8}%` }}
        />
      ))}
    </div>
  );
}

function UnauthenticatedBody({ title, onOpenSettings }: { title: string; onOpenSettings: () => void }) {
  return (
    <div
      data-testid="tradesa-unauthenticated"
      className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center"
    >
      <h3 className="text-base font-semibold text-zinc-200">Tradesa V2 — {title}</h3>
      <p className="max-w-md text-sm text-zinc-400">
        Connect Vysted Terminal to your Tradesa V2 Supabase project to read live
        bot state. Vysted is observation-only — it never writes to your bot.
      </p>
      <button
        type="button"
        onClick={onOpenSettings}
        className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400"
      >
        Open Settings
      </button>
    </div>
  );
}

function SupabaseErrorBody({
  message,
  onRetry,
}: {
  message: string | null | undefined;
  onRetry: () => void;
}) {
  return (
    <div
      role="alert"
      data-testid="tradesa-supabase-error"
      className="flex flex-1 flex-col items-center justify-center gap-4 p-6 text-center"
    >
      <h3 className="text-base font-semibold text-red-300">Supabase unreachable</h3>
      <p className="max-w-md text-sm text-zinc-400">
        {message || "Tradesa V2's Supabase project returned an error or is unreachable."}
      </p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center gap-2 rounded-md border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-sm font-medium text-zinc-200 transition-colors hover:bg-zinc-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
      >
        <RefreshCw className="size-3.5" />
        Retry
      </button>
    </div>
  );
}

function BotOfflineBanner({ ageSeconds }: { ageSeconds: number | null | undefined }) {
  const minutes = ageSeconds !== null && ageSeconds !== undefined ? Math.floor(ageSeconds / 60) : null;
  const ageLabel = minutes !== null ? `${minutes} minute${minutes === 1 ? "" : "s"}` : "an unknown duration";
  return (
    <div
      role="alert"
      data-testid="tradesa-bot-offline-banner"
      className="border-b border-red-900/60 bg-red-950/40 px-3 py-2 text-xs text-red-200"
    >
      Tradesa V2 bot is offline (no heartbeat in {ageLabel}). Showing last-known data — values may be stale.
    </div>
  );
}

function PartialBanner({ message }: { message: string | null | undefined }) {
  return (
    <div
      role="alert"
      data-testid="tradesa-partial-banner"
      className="border-b border-amber-900/60 bg-amber-950/40 px-3 py-2 text-xs text-amber-200"
    >
      {message || "Some Tradesa V2 endpoints are unreachable — showing partial data."}
    </div>
  );
}

export function PanelShell({ title, children, muteOnBotOffline = true }: PanelShellProps) {
  const { status, state, refresh } = useTradesaConnectionState();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const openSettings = () => setSettingsOpen(true);
  const handleSettingsClose = () => setSettingsOpen(false);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <TradesaBotStatusStrip />

      {status === "connecting" && <SkeletonBody />}

      {status === "unauthenticated" && (
        <UnauthenticatedBody title={title} onOpenSettings={openSettings} />
      )}

      {status === "supabase-error" && (
        <SupabaseErrorBody message={state?.message} onRetry={() => void refresh()} />
      )}

      {status === "partial" && <PartialBanner message={state?.message} />}

      {status === "bot-offline" && (
        <BotOfflineBanner ageSeconds={state?.heartbeat_age_s} />
      )}

      {(status === "healthy" || status === "partial" || status === "bot-offline") && (
        <div
          data-testid="tradesa-panel-body"
          data-status={status}
          className={
            status === "bot-offline" && muteOnBotOffline
              ? "flex flex-1 flex-col overflow-hidden opacity-60 saturate-50"
              : "flex flex-1 flex-col overflow-hidden"
          }
        >
          {children}
        </div>
      )}

      <TradesaSettingsDialog open={settingsOpen} onClose={handleSettingsClose} />
    </div>
  );
}

export default PanelShell;
