"use client";

import { type FunctionComponent, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { usePluginsStore } from "@/store/plugins";
import { useWorkspaceStore } from "@/store/workspace";
import type { LoadedPlugin, LoadedPluginState } from "../../types/plugin-runtime";

/**
 * Plugin Manager panel — lists every loaded plugin with its lifecycle state,
 * recent health history, metadata, and an enable/disable toggle.
 *
 * The data flows from `usePluginsStore`, which the page-level bootstrap
 * subscribes to a `PluginRuntime` instance via `attachRuntime()`. Toggling a
 * plugin calls `runtime.loadPlugin` / `runtime.unloadPlugin` directly so the
 * store re-syncs on the runtime's emitted events; persistence is handled by
 * the runtime's adapter (sidecar `/plugins/{id}/config`), not here.
 *
 * Wired into the plugin-manager module as `panelComponents["plugin-manager-panel"]`.
 */
export const PluginManagerPanel: FunctionComponent = () => {
  const plugins = usePluginsStore((state) => state.plugins);
  const runtime = usePluginsStore((state) => state.runtime);
  const dataSources = usePluginsStore((state) => state.dataSources);
  const agents = usePluginsStore((state) => state.agents);
  const nodes = usePluginsStore((state) => state.nodes);
  const openPanel = useWorkspaceStore((state) => state.openPanel);

  // Pin the latest health-history sample's status next to the plugin name.
  const enabledCount = plugins.filter((plugin) => plugin.state === "active").length;

  return (
    <div className="bg-charcoal-900 h-full w-full overflow-y-auto p-6">
      <header className="mb-4">
        <h2 className="text-charcoal-100 font-serif text-xl">Plugins</h2>
        <p className="text-charcoal-400 mt-1 font-mono text-xs">
          {plugins.length > 0
            ? `${enabledCount} active of ${plugins.length} loaded · ${dataSources.length} data sources · ${agents.length} agents · ${nodes.length} nodes`
            : null}
        </p>
      </header>
      {runtime === null ? (
        // Runtime not attached yet — show skeleton rows
        <ul className="flex flex-col gap-2">
          {[...Array(3)].map((_, i) => (
            <li key={i} className="border-charcoal-700 bg-charcoal-850 rounded-md border px-4 py-3">
              <div className="bg-charcoal-700 h-3 w-2/3 animate-pulse rounded" />
              <div className="bg-charcoal-700 mt-2 h-2 w-1/3 animate-pulse rounded" />
            </li>
          ))}
          <p className="text-charcoal-500 mt-2 font-mono text-xs">Loading plugin runtime…</p>
        </ul>
      ) : plugins.length === 0 ? (
        // Runtime attached but no plugins loaded
        <div className="flex flex-col items-center justify-center gap-3 py-12 text-center">
          <h3 className="text-charcoal-200 font-serif text-base">Plugin Manager</h3>
          <p className="text-charcoal-400 max-w-xs font-mono text-xs">
            No plugins are loaded. Open Marketplace to install extensions.
          </p>
          <Button size="sm" variant="outline" onClick={() => openPanel("marketplace-panel")}>
            Open Marketplace
          </Button>
        </div>
      ) : (
        <ul className="flex flex-col gap-2">
          {plugins.map((plugin) => (
            <PluginRow key={plugin.manifest.id} plugin={plugin} runtimeReady={runtime !== null} />
          ))}
        </ul>
      )}
    </div>
  );
};

PluginManagerPanel.displayName = "PluginManagerPanel";

const STATE_TONE: Record<LoadedPluginState, string> = {
  discovered: "bg-charcoal-700 text-charcoal-200",
  initializing: "bg-warning/15 text-warning",
  active: "bg-positive/15 text-positive",
  stopping: "bg-warning/15 text-warning",
  stopped: "bg-charcoal-700 text-charcoal-300",
  error: "bg-negative/15 text-negative",
};

interface PluginRowProps {
  plugin: LoadedPlugin;
  runtimeReady: boolean;
}

function PluginRow({ plugin, runtimeReady }: PluginRowProps) {
  const runtime = usePluginsStore((state) => state.runtime);
  const [pending, setPending] = useState(false);

  const isActive = plugin.state === "active";
  const isToggleable = runtimeReady && plugin.instance !== undefined;
  const latestHealth = plugin.healthHistory.at(-1);

  // Re-render every 5s so the relative timestamp stays fresh while the panel is
  // open. Only arm the interval once there's a health sample to age — a row with
  // no samples has no timestamp to refresh, so an empty tick is pure waste.
  // Cheap regardless because dockview unmounts panels that aren't in view.
  const [, forceTick] = useState(0);
  useEffect(() => {
    if (latestHealth === undefined) {
      return;
    }
    const interval = setInterval(() => forceTick((tick) => tick + 1), 5000);
    return () => clearInterval(interval);
  }, [latestHealth]);

  const stateLabel = useMemo(() => plugin.state.replace(/-/g, " "), [plugin.state]);

  async function handleToggle(nextEnabled: boolean) {
    if (!runtime || !plugin.instance || pending) {
      return;
    }
    setPending(true);
    try {
      if (nextEnabled) {
        await runtime.loadPlugin({ manifest: plugin.manifest, instance: plugin.instance });
      } else {
        await runtime.unloadPlugin(plugin.manifest.id);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <li
      data-testid={`plugin-row-${plugin.manifest.id}`}
      className="border-charcoal-700 bg-charcoal-850 flex flex-col gap-2 rounded-md border px-4 py-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col">
          <div className="flex items-center gap-2">
            <span className="text-charcoal-100 truncate font-mono text-sm font-medium">
              {plugin.manifest.name}
            </span>
            <span
              data-testid={`plugin-state-${plugin.manifest.id}`}
              className={`rounded px-1.5 py-0.5 font-mono text-[10px] tracking-wide uppercase ${STATE_TONE[plugin.state]}`}
            >
              {stateLabel}
            </span>
          </div>
          <span className="text-charcoal-400 font-mono text-xs">
            v{plugin.manifest.version}
            {plugin.manifest.author ? ` · ${plugin.manifest.author}` : ""} · id{" "}
            <code className="text-charcoal-300">{plugin.manifest.id}</code>
          </span>
          {plugin.manifest.description ? (
            <p className="text-charcoal-400 mt-1 font-mono text-xs">
              {plugin.manifest.description}
            </p>
          ) : null}
        </div>
        <label className="flex shrink-0 items-center gap-2">
          <span className="sr-only">
            {isActive ? "Disable" : "Enable"} {plugin.manifest.name}
          </span>
          <input
            type="checkbox"
            role="switch"
            aria-label={`${plugin.manifest.name} enabled`}
            checked={isActive}
            disabled={!isToggleable || pending}
            onChange={(event) => {
              void handleToggle(event.target.checked);
            }}
            className="size-4 accent-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
          />
        </label>
      </div>

      {plugin.errorMessage ? (
        <div
          data-testid={`plugin-error-${plugin.manifest.id}`}
          className="border-negative/30 bg-negative/10 flex items-start justify-between gap-2 rounded-sm border px-2 py-1"
        >
          <p className="text-negative font-mono text-xs">{plugin.errorMessage}</p>
          <Button
            size="xs"
            variant="outline"
            disabled={pending}
            onClick={() => void handleToggle(true)}
            className="text-negative border-negative/40 shrink-0"
          >
            Retry
          </Button>
        </div>
      ) : null}

      <div className="flex items-center justify-between gap-3">
        <HealthHistory history={plugin.healthHistory} />
        <span className="text-charcoal-500 font-mono text-[10px]">
          {latestHealth ? formatRelativeTime(latestHealth.recordedAt) : "no health samples yet"}
        </span>
      </div>
    </li>
  );
}

interface HealthHistoryProps {
  history: LoadedPlugin["healthHistory"];
}

const HEALTH_TONE: Record<string, string> = {
  healthy: "bg-positive",
  degraded: "bg-warning",
  unavailable: "bg-negative",
};

function HealthHistory({ history }: HealthHistoryProps) {
  if (history.length === 0) {
    return (
      <span className="text-charcoal-500 font-mono text-[10px]">awaiting first health check</span>
    );
  }
  return (
    <div
      data-testid="plugin-health-history"
      className="flex items-center gap-0.5"
      title={`${history.length} health sample${history.length === 1 ? "" : "s"}`}
    >
      {history.map((sample, index) => (
        <span
          key={`${sample.recordedAt}-${index}`}
          className={`block h-3 w-1.5 rounded-sm ${HEALTH_TONE[sample.status] ?? "bg-charcoal-600"}`}
          title={`${sample.status}${sample.message ? ` — ${sample.message}` : ""}`}
        />
      ))}
    </div>
  );
}

function formatRelativeTime(epochMs: number): string {
  const deltaSeconds = Math.max(0, Math.round((Date.now() - epochMs) / 1000));
  if (deltaSeconds < 5) return "just now";
  if (deltaSeconds < 60) return `${deltaSeconds}s ago`;
  const minutes = Math.round(deltaSeconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  return `${hours}h ago`;
}
