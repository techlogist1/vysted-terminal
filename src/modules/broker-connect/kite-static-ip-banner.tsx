"use client";

/**
 * Kite Connect static-IP banner.
 *
 * SEBI/NSE retail-algo compliance (in effect 2026-04-01) requires a static
 * IP registered with Kite for order placement. The sidecar's
 * :func:`services.static_ip_detector.static_ip_status` returns a
 * :class:`StaticIpStatus` snapshot — this component polls it through
 * ``GET /safety/static-ip-status?configured=<configuredIp>`` and surfaces
 * the result visually inside the broker-connect panel.
 *
 * UX flow (per the plan §"Tier-3 — Static-IP UX path"):
 *
 *   1. The user sets the configured static IP through the Kite plugin
 *      settings (the Kite plugin's `set-static-ip` control-plane command
 *      persists it on the sidecar adapter).
 *   2. This banner polls the safety route on a steady interval (default
 *      30 s) and re-renders whenever the comparison flips.
 *   3. When `matches=false` the banner switches to a red destructive
 *      variant with the detector's `message` field as copy.
 *   4. When `matches=true` (or the user is in paper mode) the banner
 *      shows a quiet "all good" state — visible but unobtrusive.
 *
 * Placement is delegated to Teammate S's `BrokerConnectPanel.tsx`; this
 * file owns only the banner sub-component. The panel decides whether to
 * mount it (only when the Kite adapter is in live mode).
 */

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Globe } from "lucide-react";

import { cn } from "@/lib/utils";

/** Wire shape returned by ``GET /safety/static-ip-status``. */
export interface KiteStaticIpStatus {
  detectedIp: string | null;
  configuredIp: string | null;
  matches: boolean;
  message: string;
  detectedAt: number;
}

export interface KiteStaticIpBannerProps {
  /** Sidecar base URL — wired through from `PluginConfig.sidecarBaseUrl`. */
  sidecarBaseUrl: string;
  /**
   * The user's configured static IP, surfaced as the comparison anchor.
   * `null` is allowed — the safety route returns a "no static IP configured"
   * status in that case.
   */
  configuredIp: string | null;
  /** Poll interval in milliseconds. Defaults to 30 s. */
  pollIntervalMs?: number;
  /** Optional callback invoked whenever a new status is fetched. */
  onStatus?: (status: KiteStaticIpStatus) => void;
  /** Test seam — inject a fetcher to bypass `fetch()` in unit tests. */
  fetcher?: (url: string) => Promise<KiteStaticIpStatus>;
  /** Extra Tailwind classes appended to the banner root. */
  className?: string;
}

const DEFAULT_POLL_INTERVAL_MS = 30_000;

async function defaultFetcher(url: string): Promise<KiteStaticIpStatus> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as KiteStaticIpStatus;
}

function buildUrl(baseUrl: string, configuredIp: string | null): string {
  const url = new URL("/safety/static-ip-status", baseUrl);
  if (configuredIp) {
    url.searchParams.set("configured", configuredIp);
  }
  return url.toString();
}

export function KiteStaticIpBanner({
  sidecarBaseUrl,
  configuredIp,
  pollIntervalMs = DEFAULT_POLL_INTERVAL_MS,
  onStatus,
  fetcher = defaultFetcher,
  className,
}: KiteStaticIpBannerProps) {
  const [status, setStatus] = useState<KiteStaticIpStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refresh = useCallback(async () => {
    try {
      const next = await fetcher(buildUrl(sidecarBaseUrl, configuredIp));
      setStatus(next);
      setError(null);
      onStatus?.(next);
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, [fetcher, sidecarBaseUrl, configuredIp, onStatus]);

  useEffect(() => {
    let cancelled = false;

    // Defer the initial fetch via queueMicrotask so the effect body
    // returns to React before any setState lands. The component
    // already renders in the loading state from the `useState(true)`
    // default for the first paint.
    const kick = () => {
      if (cancelled) {
        return;
      }
      refresh().catch(() => {
        /* refresh() already swallows + records the error */
      });
    };

    queueMicrotask(kick);
    const interval = setInterval(kick, pollIntervalMs);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [refresh, pollIntervalMs]);

  if (loading && !status && !error) {
    return (
      <div
        role="status"
        aria-live="polite"
        data-testid="kite-static-ip-banner"
        data-variant="loading"
        className={cn(
          "border-border bg-muted/40 text-muted-foreground text-caption flex items-center gap-2 rounded-none border px-3 py-2",
          className,
        )}
      >
        <Globe className="h-3.5 w-3.5" />
        <span>Checking Kite static-IP status…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div
        role="alert"
        data-testid="kite-static-ip-banner"
        data-variant="error"
        className={cn(
          "border-warning/40 bg-warning/10 text-warning text-caption flex items-start gap-2 rounded-none border px-3 py-2",
          className,
        )}
      >
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <div className="flex-1">
          <div className="font-medium">Static-IP status unavailable</div>
          <div className="text-warning/80">{error}</div>
        </div>
      </div>
    );
  }

  if (!status) {
    return null;
  }

  if (status.matches) {
    return (
      <div
        role="status"
        aria-live="polite"
        data-testid="kite-static-ip-banner"
        data-variant="ok"
        className={cn(
          "border-positive/30 bg-positive/10 text-positive text-caption flex items-start gap-2 rounded-none border px-3 py-2",
          className,
        )}
      >
        <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0" />
        <div className="flex-1">
          <div className="font-medium">Kite static IP matches</div>
          <div className="text-positive/80">
            Detected {status.detectedIp ?? "—"} · Configured {status.configuredIp ?? "—"}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      role="alert"
      data-testid="kite-static-ip-banner"
      data-variant="mismatch"
      className={cn(
        "border-negative/30 bg-negative/10 text-negative text-caption flex items-start gap-2 rounded-none border px-3 py-2",
        className,
      )}
    >
      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <div className="flex-1">
        <div className="font-medium">Kite static IP mismatch — orders may be rejected</div>
        <div className="text-negative/80">{status.message}</div>
        <div className="text-negative/70 mt-1">
          Detected {status.detectedIp ?? "—"} · Configured {status.configuredIp ?? "—"}
        </div>
      </div>
    </div>
  );
}

export default KiteStaticIpBanner;
