"use client";

import { type FunctionComponent, useEffect, useMemo, useState } from "react";
import { Blocks } from "lucide-react";

import { EmptyState } from "@/components/EmptyState";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
        <h2 className="text-charcoal-100 text-section">Plugins</h2>
        <p className="text-charcoal-400 text-caption mt-1">
          {plugins.length > 0
            ? `${enabledCount} active of ${plugins.length} loaded · ${dataSources.length} data sources · ${agents.length} agents · ${nodes.length} nodes`
            : null}
        </p>
      </header>
      {runtime === null ? (
        // Runtime not attached yet — row-shaped skeleton with an honest meta line.
        <div data-testid="plugin-runtime-skeleton">
          <ul className="flex flex-col gap-2">
            {[...Array(3)].map((_, i) => (
              <li
                key={i}
                className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3"
              >
                <div className="bg-charcoal-700 h-3 w-2/3 animate-pulse rounded-none" />
                <div className="bg-charcoal-700 mt-2 h-2 w-1/3 animate-pulse rounded-none" />
              </li>
            ))}
          </ul>
          <p className="text-charcoal-500 text-caption mt-2">Loading plugin runtime…</p>
        </div>
      ) : plugins.length === 0 ? (
        // Runtime attached but no plugins loaded — the composed shared surface.
        <EmptyState
          icon={Blocks}
          headline="No plugins loaded"
          hint="No plugins are loaded. Open the Marketplace to install brokers, data providers, panels, and agent packs."
          cta={{
            label: "Open Marketplace",
            primary: true,
            onClick: () => openPanel("marketplace-panel"),
          }}
        />
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

/**
 * A readable monochrome switch on the 32px ladder (replaces the 8px `size-4`
 * checkbox). The real checkbox stays in the tree (`sr-only`, `role="switch"`)
 * so assistive tech and the existing tests keep their contract; the visible
 * track/thumb are styled spans driven by `peer-checked`. Mirrors the
 * SettingsPanel ToggleSwitch — if a third panel needs it, the lead should
 * lift it into a shared component (noted in INTEGRATION_NOTES_R7_PANELS.md).
 */
function ToggleSwitch({
  checked,
  disabled,
  onChange,
  "aria-label": ariaLabel,
}: {
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
  "aria-label"?: string;
}) {
  return (
    <label
      className={cn(
        "relative inline-flex h-8 w-16 shrink-0 items-center",
        disabled ? "cursor-not-allowed" : "cursor-pointer",
      )}
    >
      <input
        type="checkbox"
        role="switch"
        aria-label={ariaLabel}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="peer sr-only"
      />
      <span
        aria-hidden="true"
        className="bg-charcoal-850 border-charcoal-700 peer-checked:bg-charcoal-600 peer-checked:border-charcoal-500 rounded-control absolute inset-0 border transition-colors peer-disabled:opacity-40"
      />
      <span
        aria-hidden="true"
        className="bg-charcoal-500 peer-checked:bg-charcoal-100 rounded-control absolute left-1 size-6 transition-transform peer-checked:translate-x-8 peer-disabled:opacity-40"
      />
    </label>
  );
}

const STATE_TONE: Record<LoadedPluginState, string> = {
  discovered: "bg-charcoal-700 text-charcoal-200",
  initializing: "bg-charcoal-850 text-warning",
  active: "bg-charcoal-850 text-positive",
  stopping: "bg-charcoal-850 text-warning",
  stopped: "bg-charcoal-700 text-charcoal-300",
  error: "bg-charcoal-850 text-negative",
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
      className="border-charcoal-700 bg-charcoal-850 flex flex-col gap-2 rounded-none border px-4 py-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 flex-col">
          <div className="flex items-center gap-2">
            <span className="text-charcoal-100 text-body truncate font-medium">
              {plugin.manifest.name}
            </span>
            <span
              data-testid={`plugin-state-${plugin.manifest.id}`}
              className={`rounded-control text-micro px-1 py-0.5 uppercase ${STATE_TONE[plugin.state]}`}
            >
              {stateLabel}
            </span>
          </div>
          <span className="text-charcoal-400 text-caption">
            v{plugin.manifest.version}
            {plugin.manifest.author ? ` · ${plugin.manifest.author}` : ""} · id{" "}
            <code className="text-charcoal-300">{plugin.manifest.id}</code>
          </span>
          {plugin.manifest.description ? (
            <p className="text-charcoal-400 text-caption mt-1">{plugin.manifest.description}</p>
          ) : null}
        </div>
        <ToggleSwitch
          checked={isActive}
          disabled={!isToggleable || pending}
          onChange={(next) => void handleToggle(next)}
          aria-label={`${plugin.manifest.name} enabled`}
        />
      </div>

      {plugin.errorMessage ? (
        <div
          data-testid={`plugin-error-${plugin.manifest.id}`}
          className="border-negative/30 bg-negative/10 flex items-start justify-between gap-2 rounded-none border px-2 py-1"
        >
          <p className="text-negative text-caption">{plugin.errorMessage}</p>
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
        <span className="text-charcoal-500 text-micro">
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
    return <span className="text-charcoal-500 text-micro">awaiting first health check</span>;
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
          className={`block h-3 w-1.5 rounded-none ${HEALTH_TONE[sample.status] ?? "bg-charcoal-600"}`}
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
