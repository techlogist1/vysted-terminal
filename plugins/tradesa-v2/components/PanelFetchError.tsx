"use client";

/**
 * Per-panel fetch-error banner (Phase 9.5). The PanelShell only surfaces
 * connection-level status (unauthenticated / supabase-error / bot-offline);
 * an individual panel's own `FetchState.error` (e.g. the positions poll failed
 * while the connection is otherwise healthy) was previously never rendered, so
 * the panel silently showed stale/empty data. This thin banner makes that
 * failure visible with a retry affordance. Renders nothing when there is no
 * error, so panels with a healthy fetch (and their tests) are unaffected.
 */
export function PanelFetchError({
  error,
  onRetry,
}: {
  error: string | null;
  onRetry?: () => void;
}) {
  if (!error) return null;
  return (
    <div
      role="alert"
      data-testid="panel-fetch-error"
      className="border-warning/40 bg-warning/10 text-warning text-caption flex items-center justify-between gap-3 border-b px-3 py-1"
    >
      <span className="truncate">Could not refresh this panel: {error}</span>
      {onRetry !== undefined && (
        <button
          type="button"
          onClick={onRetry}
          className="border-warning/50 hover:bg-warning/15 text-micro rounded-control shrink-0 border px-2 py-0.5 font-mono tracking-wide uppercase"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export default PanelFetchError;
