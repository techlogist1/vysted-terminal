"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, Settings2, Trash2, Power } from "lucide-react";

import { Button } from "@/components/ui/button";
import { MARKETPLACE_CATALOG } from "@/lib/marketplace";
import { cn } from "@/lib/utils";
import { useMarketplaceStore } from "@/store/marketplace";
import { usePluginsStore } from "@/store/plugins";

import type { MarketplaceCategory, MarketplaceEntry } from "../../../types/marketplace";

const CATEGORY_ORDER: { id: MarketplaceCategory; label: string; blurb: string }[] = [
  {
    id: "broker",
    label: "Brokers",
    blurb: "Read-only broker connections. None pre-installed — install the one you use.",
  },
  {
    id: "data",
    label: "Data providers",
    blurb: "Market + fundamentals + macro sources. yfinance is the keyless default.",
  },
  { id: "panel", label: "Panels", blurb: "Extra cockpit surfaces contributed by plugins." },
  { id: "agent", label: "Agents", blurb: "Agent packs that add personas/lenses." },
  { id: "analytics", label: "Analytics", blurb: "Analysis extensions." },
];

/**
 * The plugin marketplace (FR-050, US10) — the app's front door for capability.
 * Browse brokers / data / panels / agents and install, enable, configure (BYOK),
 * or remove each through one lifecycle. The Configure form is the generic
 * credentials hub (FR-034): it renders each plugin's declared credential fields,
 * masks secrets, and writes them to the OS keychain. Safety stays host-enforced
 * (FR-055) — installing a broker adds no execution path.
 */
export function MarketplacePanel() {
  const refresh = useMarketplaceStore((s) => s.refresh);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const byCategory = useMemo(() => {
    const map = new Map<MarketplaceCategory, MarketplaceEntry[]>();
    for (const entry of MARKETPLACE_CATALOG) {
      const list = map.get(entry.category) ?? [];
      list.push(entry);
      map.set(entry.category, list);
    }
    return map;
  }, []);

  return (
    <div className="bg-charcoal-950 flex h-full w-full flex-col overflow-y-auto">
      <header className="border-charcoal-700 bg-charcoal-925 sticky top-0 z-10 border-b px-4 py-3">
        <h2 className="text-charcoal-100 font-serif text-sm font-semibold">Marketplace</h2>
        <p className="text-charcoal-400 mt-0.5 font-mono text-[0.65rem]">
          Install, enable, configure, and remove extensions — brokers, data, panels, and agents.
        </p>
      </header>
      <div className="flex flex-col gap-5 px-4 py-4">
        {CATEGORY_ORDER.map(({ id, label, blurb }) => {
          const entries = byCategory.get(id) ?? [];
          if (entries.length === 0) return null;
          return (
            <section key={id} aria-label={label}>
              <div className="mb-2">
                <h3 className="hud-label">{label}</h3>
                <p className="text-charcoal-500 mt-0.5 font-mono text-[0.6rem]">{blurb}</p>
              </div>
              <ul className="flex flex-col gap-2">
                {entries.map((entry) => (
                  <MarketplaceCard key={entry.pluginId} entry={entry} />
                ))}
              </ul>
            </section>
          );
        })}
      </div>
    </div>
  );
}

function MarketplaceCard({ entry }: { entry: MarketplaceEntry }) {
  // Subscribe to the reactive slices so the card re-renders on a transition.
  const flags = useMarketplaceStore((s) => s.flags[entry.pluginId]);
  const configured = useMarketplaceStore((s) => s.configured[entry.pluginId] ?? false);
  const busy = useMarketplaceStore((s) => s.busy[entry.pluginId] ?? false);
  const install = useMarketplaceStore((s) => s.install);
  const enable = useMarketplaceStore((s) => s.enable);
  const disable = useMarketplaceStore((s) => s.disable);
  const remove = useMarketplaceStore((s) => s.remove);
  const record = usePluginsStore((s) => s.plugins.find((p) => p.manifest.id === entry.pluginId));

  const [configuring, setConfiguring] = useState(false);
  const state = {
    installed: flags?.installed ?? entry.preinstalled,
    enabled: flags?.enabled ?? entry.preinstalled,
    configured,
    runtimeState: record?.state,
    errorMessage: record?.errorMessage,
  };
  const hasCreds = (entry.credentialFields?.length ?? 0) > 0;

  return (
    <li className="border-charcoal-700 bg-charcoal-900 rounded-md border px-3 py-2.5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-charcoal-100 font-mono text-xs font-medium">{entry.name}</span>
            <StateBadge state={state} preinstalled={entry.preinstalled} />
          </div>
          <p className="text-charcoal-400 mt-0.5 font-mono text-[0.65rem]">{entry.description}</p>
          {state.errorMessage && (
            <p className="text-negative mt-0.5 font-mono text-[0.6rem]">{state.errorMessage}</p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {!state.installed && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => void install(entry.pluginId)}
            >
              Install
            </Button>
          )}
          {state.installed && !state.enabled && (
            <Button
              size="sm"
              variant="outline"
              disabled={busy}
              onClick={() => void enable(entry.pluginId)}
            >
              <Power className="size-3" /> Enable
            </Button>
          )}
          {state.installed && state.enabled && (
            <Button
              size="sm"
              variant="ghost"
              disabled={busy}
              aria-label={`Disable ${entry.name}`}
              onClick={() => void disable(entry.pluginId)}
            >
              <Power className="size-3" /> Disable
            </Button>
          )}
          {state.installed && hasCreds && (
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label={`Configure ${entry.name}`}
              onClick={() => setConfiguring((v) => !v)}
            >
              <Settings2 className="size-3.5" />
            </Button>
          )}
          {state.installed && !entry.preinstalled && (
            <Button
              size="icon-sm"
              variant="ghost"
              disabled={busy}
              aria-label={`Remove ${entry.name}`}
              onClick={() => void remove(entry.pluginId)}
            >
              <Trash2 className="size-3.5" />
            </Button>
          )}
        </div>
      </div>
      {configuring && hasCreds && (
        <CredentialForm entry={entry} onDone={() => setConfiguring(false)} />
      )}
    </li>
  );
}

function StateBadge({
  state,
  preinstalled,
}: {
  state: { installed: boolean; enabled: boolean; configured: boolean; runtimeState?: string };
  preinstalled: boolean;
}) {
  let label = "Available";
  let tone = "text-charcoal-500 border-charcoal-700";
  if (state.runtimeState === "error") {
    label = "Error";
    tone = "text-negative border-negative/40";
  } else if (state.installed && state.enabled) {
    label = preinstalled ? "Pre-installed" : "Enabled";
    tone = "text-positive border-positive/40";
  } else if (state.installed) {
    label = "Disabled";
    tone = "text-warning border-warning/40";
  }
  return (
    <span className={cn("rounded border px-1.5 py-0.5 font-mono text-[0.55rem] uppercase", tone)}>
      {label}
    </span>
  );
}

function CredentialForm({ entry, onDone }: { entry: MarketplaceEntry; onDone: () => void }) {
  const configure = useMarketplaceStore((s) => s.configure);
  const busy = useMarketplaceStore((s) => s.busy[entry.pluginId] ?? false);
  const [values, setValues] = useState<Record<string, string>>({});
  const fields = entry.credentialFields ?? [];

  return (
    <form
      className="border-charcoal-700 mt-2.5 flex flex-col gap-2 border-t pt-2.5"
      onSubmit={(e) => {
        e.preventDefault();
        void configure(entry.pluginId, values).then(onDone);
      }}
    >
      {entry.instructions && (
        <p className="text-charcoal-400 font-mono text-[0.6rem]">{entry.instructions}</p>
      )}
      {entry.website && (
        <a
          href={entry.website}
          target="_blank"
          rel="noreferrer"
          className="font-mono text-[0.6rem] text-amber-300 hover:underline"
        >
          Where to get credentials →
        </a>
      )}
      {fields.length === 0 && (
        <p className="text-charcoal-500 font-mono text-[0.6rem]">This extension needs no key.</p>
      )}
      {fields.map((field) => (
        <label key={field.key} className="flex flex-col gap-1">
          <span className="text-charcoal-400 font-mono text-[0.6rem]">
            {field.label}
            {field.required && <span className="text-negative"> *</span>}
          </span>
          <input
            type={field.type === "password" ? "password" : "text"}
            value={values[field.key] ?? ""}
            placeholder={field.placeholder}
            autoComplete="off"
            onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
            className="bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 h-7 rounded-md px-2 font-mono text-xs outline-none focus:ring-1 focus:ring-amber-400"
          />
        </label>
      ))}
      <div className="flex items-center justify-end gap-1.5">
        <Button type="button" size="sm" variant="ghost" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" size="sm" variant="outline" disabled={busy}>
          <Check className="size-3" /> Save credentials
        </Button>
      </div>
      <p className="text-charcoal-500 font-mono text-[0.55rem]">
        Stored in your OS keychain — never written to disk or logs. Broker access is read-only;
        order execution stays deferred (paper-default, host §6.5-gated).
      </p>
    </form>
  );
}
