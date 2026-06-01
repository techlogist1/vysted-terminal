"use client";

import { type FunctionComponent, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Bot,
  Check,
  Download,
  KeyRound,
  Keyboard,
  Layers,
  Network,
  Palette,
  Plug,
  RotateCcw,
  Settings2,
  Sliders,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { INTEGRATIONS } from "@/lib/integrations/registry";
import type { IntegrationSpec } from "@/lib/integrations/types";
import { type Region, REGIONS } from "@/lib/region";
import { cn } from "@/lib/utils";
import { ConnectCard } from "@/modules/integrations/ConnectCard";
import { useBrokersStore } from "@/store/brokers";
import { deleteSecret, KEYCHAIN_NAMESPACES } from "@/lib/keychain";
import { HOST_VERSION } from "@/lib/plugin-bootstrap";
import {
  autosaveLayout,
  deleteWorkspace,
  listWorkspaces,
  loadWorkspace,
  saveWorkspace,
  WorkspaceError,
} from "@/lib/workspace";
import { PLATFORM_MODULE_ID } from "@/modules/platform";
import {
  type AgentSummary,
  selectCustomAgents,
  selectFirstPartyAgents,
  useAgentsStore,
} from "@/store/agents";
import {
  DEFAULT_KEYBINDINGS,
  formatBinding,
  type KeybindingCategory,
  type KeybindingDef,
  useKeybindingsStore,
} from "@/store/keybindings";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { KNOWN_MODELS_BY_PROVIDER, useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useProviderKeysStore } from "@/store/provider-keys";
import { type SettingsBundle, useSettingsStore } from "@/store/settings";
import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";
import type { LLMProviderId } from "../../types/ai";

/**
 * Settings — the discoverable control surface (Cursor-grade preferences,
 * FR-037/FR-038/FR-039, SC-011).
 *
 * Sections:
 *  - AI Providers (BYOK): the "where do I put my key" surface. Every provider
 *    shows its key status from the OS keychain with add / update / remove, plus
 *    a default-provider picker. This is what first-run onboarding points to.
 *  - Preferences: default agent/persona, default provider + provider
 *    *preference order*, default model, command-palette behaviour, the FR-032
 *    starter-cockpit composition, and the dark-only theme knobs.
 *  - Keybindings (FR-039): every bindable action with its current combo, an
 *    inline key recorder, a reset, and a surfaced conflict warning.
 *  - Integrations: read-only broker connections.
 *  - Layouts: save / restore / delete named cockpits + reset to the default.
 *  - Modules: enable / disable registered modules.
 *  - Export / Import (FR-037/FR-038): round-trip every preference between
 *    machines as a JSON bundle — explicitly WITHOUT secrets (FR-036/SC-010).
 *  - About: the open / local-first / BYOK positioning + version.
 *
 * Opened from the toolbar gear, the `platform.open-settings` command, or the
 * onboarding banner. Wired into the platform module as
 * `panelComponents["settings-panel"]`.
 */
export const SettingsPanel: FunctionComponent = () => {
  return (
    // Single scroll container: the root clips at the painted charcoal box
    // (`overflow-hidden`) so over-scroll never reveals the WKWebView backdrop
    // (the "blue void"), and the one inner `overflow-y-auto` is the only
    // scrollbar — fixes the double-scrollbar-into-void (map-settings 3a).
    <div className="bg-charcoal-900 flex h-full w-full flex-col overflow-hidden">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
          <header>
            <h1 className="text-charcoal-100 flex items-center gap-2 font-serif text-2xl">
              <Settings2 className="size-5 text-amber-400" aria-hidden="true" />
              Settings
            </h1>
            <p className="text-charcoal-400 mt-1 font-mono text-xs">
              Local-first &amp; bring-your-own-keys. Nothing leaves this machine except calls you
              make to providers you configure.
            </p>
          </header>
          <ProvidersSection />
          <PreferencesSection />
          <KeybindingsSection />
          <IntegrationsSection />
          <LayoutsSection />
          <ModulesSection />
          <ExportImportSection />
          <AboutSection />
        </div>
      </div>
    </div>
  );
};

SettingsPanel.displayName = "SettingsPanel";

// ---------------------------------------------------------------------------
// AI Providers (BYOK)
// ---------------------------------------------------------------------------

function ProvidersSection() {
  const providers = useLLMProvidersStore((s) => s.providers);
  const defaultProviderId = useLLMProvidersStore((s) => s.defaultProviderId);
  const setDefaultProviderId = useLLMProvidersStore((s) => s.setDefaultProviderId);
  const status = useProviderKeysStore((s) => s.status);
  const refresh = useProviderKeysStore((s) => s.refresh);
  const refreshOne = useProviderKeysStore((s) => s.refreshOne);

  const [dialogProvider, setDialogProvider] = useState<LLMProviderId | null>(null);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleRemove(id: LLMProviderId) {
    await deleteSecret(KEYCHAIN_NAMESPACES.llmProvider(id));
    await refreshOne(id);
  }

  return (
    <section aria-labelledby="settings-providers">
      <SectionHeader
        id="settings-providers"
        icon={<Plug className="size-4 text-amber-400" aria-hidden="true" />}
        title="AI Providers"
        hint="Paste an API key to enable an AI provider. Keys are stored in your OS keychain — never on disk or sent anywhere but the provider you call."
      />
      <ul className="flex flex-col gap-1.5">
        {providers.map((provider) => {
          const keyState = status[provider.id] ?? "missing";
          const configured = keyState === "configured";
          const isDefault = defaultProviderId === provider.id;
          const needsKey = provider.requiresKey;
          return (
            <li
              key={provider.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-md border px-4 py-3"
            >
              <div className="flex min-w-0 flex-col">
                <span className="text-charcoal-100 flex items-center gap-2 font-mono text-sm">
                  {provider.label}
                  {isDefault && (
                    <span className="rounded bg-amber-500/15 px-1.5 py-0.5 font-mono text-[10px] tracking-wide text-amber-400 uppercase">
                      default
                    </span>
                  )}
                </span>
                <span className="mt-0.5 flex items-center gap-1.5 font-mono text-xs">
                  {!needsKey ? (
                    <span className="text-charcoal-400">No key required (local)</span>
                  ) : configured ? (
                    <span className="text-positive flex items-center gap-1">
                      <Check className="size-3" aria-hidden="true" /> Key configured
                    </span>
                  ) : (
                    <span className="text-charcoal-400">No key yet</span>
                  )}
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                {/* Picking a default is a free preference (no key precondition),
                    so it shows on every non-default row — not just the one
                    provider that happens to need no key (regression-95 BUG-3). */}
                {!isDefault && (
                  <button
                    type="button"
                    onClick={() => {
                      setDefaultProviderId(provider.id);
                      // Persist immediately (into the autosave slot) so the
                      // choice survives relaunch even without a layout change.
                      void autosaveLayout();
                    }}
                    className="text-charcoal-400 hover:text-charcoal-100 font-mono text-[11px] uppercase"
                  >
                    Set default
                  </button>
                )}
                {needsKey && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setDialogProvider(provider.id)}
                    >
                      <KeyRound className="size-3" aria-hidden="true" />
                      {configured ? "Update key" : "Add key"}
                    </Button>
                    {configured && (
                      <button
                        type="button"
                        aria-label={`Remove ${provider.label} key`}
                        onClick={() => void handleRemove(provider.id)}
                        className="text-charcoal-400 rounded p-1.5 hover:text-red-400"
                      >
                        <Trash2 className="size-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </>
                )}
              </div>
            </li>
          );
        })}
      </ul>
      <KeyEntryDialog
        open={dialogProvider !== null}
        providerId={dialogProvider}
        onOpenChange={(next) => {
          if (!next) setDialogProvider(null);
        }}
        onSaved={(id) => void refreshOne(id)}
      />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Integrations (brokers + data providers)
// ---------------------------------------------------------------------------

function IntegrationsSection() {
  const brokerStates = useBrokersStore((s) => s.byId) as Record<
    string,
    { status?: string } | undefined
  >;
  const refreshBrokers = useBrokersStore((s) => s.refresh);
  const [connectSpec, setConnectSpec] = useState<IntegrationSpec | null>(null);

  useEffect(() => {
    void refreshBrokers();
  }, [refreshBrokers]);

  const brokers = INTEGRATIONS.filter((i) => i.category === "broker");

  return (
    <section aria-labelledby="settings-integrations">
      <SectionHeader
        id="settings-integrations"
        icon={<Network className="size-4 text-amber-400" aria-hidden="true" />}
        title="Integrations"
        hint="Connect a broker for read-only positions, holdings & P&L the copilot can analyse over your real account. Order execution stays in the broker panel."
      />
      <ul className="flex flex-col gap-1.5">
        {brokers.map((spec) => {
          const connected = brokerStates[spec.id]?.status === "connected";
          return (
            <li
              key={spec.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-md border px-4 py-3"
            >
              <div className="flex min-w-0 flex-col">
                <span className="text-charcoal-100 font-mono text-sm">{spec.label}</span>
                <span className="text-charcoal-400 font-mono text-xs">{spec.blurb}</span>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                <span
                  className={`font-mono text-[10px] tracking-wide uppercase ${
                    connected ? "text-positive" : "text-charcoal-500"
                  }`}
                >
                  {connected ? "connected" : "not connected"}
                </span>
                <Button size="sm" variant="outline" onClick={() => setConnectSpec(spec)}>
                  {connected ? "Manage" : "Connect"}
                </Button>
              </div>
            </li>
          );
        })}
      </ul>
      <ConnectCard
        spec={connectSpec}
        open={connectSpec !== null}
        onOpenChange={(open) => !open && setConnectSpec(null)}
      />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Layouts
// ---------------------------------------------------------------------------

function LayoutsSection() {
  const [names, setNames] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [newName, setNewName] = useState("");
  const activeName = useWorkspaceStore((s) => s.name);
  const resetLayout = useWorkspaceStore((s) => s.resetToDefaultLayout);

  async function reload() {
    try {
      const all = await listWorkspaces();
      setNames(all.filter((n) => !isReservedLayoutName(n)).sort());
      setError(null);
    } catch (caught) {
      setError(caught instanceof WorkspaceError ? caught.message : "Could not list layouts.");
      setNames([]);
    }
  }

  useEffect(() => {
    // `reload` only sets state after the awaited listWorkspaces() resolves —
    // never synchronously within the effect — so the cascading-render concern
    // the rule guards against does not apply (same pattern as PortfolioPanel).
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void reload();
  }, []);

  async function withBusy(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (caught) {
      setError(caught instanceof WorkspaceError ? caught.message : "Layout operation failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="settings-layouts">
      <SectionHeader
        id="settings-layouts"
        icon={<Layers className="size-4 text-amber-400" aria-hidden="true" />}
        title="Layouts"
        hint="Drag tabs to dock, split, or rearrange any panel into your own cockpit, then save it. Your last layout is restored automatically on launch."
      />
      <form
        className="mb-2 flex items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const name = newName.trim();
          if (!name) return;
          void withBusy(async () => {
            await saveWorkspace(name);
            setNewName("");
            await reload();
          });
        }}
      >
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Save current layout as…"
          aria-label="New layout name"
          className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-400 h-8 flex-1 rounded-md border px-3 font-mono text-xs outline-none focus:border-amber-400"
        />
        <Button type="submit" size="sm" variant="outline" disabled={busy || newName.trim() === ""}>
          Save
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => void resetLayout()}>
          Reset to default
        </Button>
      </form>
      {error && <p className="mb-2 font-mono text-xs text-red-400">{error}</p>}
      {names === null ? (
        <p className="text-charcoal-400 font-mono text-xs">Loading layouts…</p>
      ) : names.length === 0 ? (
        <p className="text-charcoal-400 font-mono text-xs">
          No saved layouts yet — arrange your panels and save above.
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {names.map((name) => (
            <li
              key={name}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-md border px-3 py-2"
            >
              <span className="text-charcoal-100 truncate font-mono text-xs">
                {name}
                {name === activeName && (
                  <span className="text-charcoal-500 ml-2 text-[10px] uppercase">active</span>
                )}
              </span>
              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => void withBusy(() => loadWorkspace(name))}
                  className="text-charcoal-300 font-mono text-[11px] uppercase hover:text-amber-400"
                >
                  Load
                </button>
                <button
                  type="button"
                  aria-label={`Delete layout ${name}`}
                  onClick={() =>
                    void withBusy(async () => {
                      await deleteWorkspace(name);
                      await reload();
                    })
                  }
                  className="text-charcoal-400 rounded p-1 hover:text-red-400"
                >
                  <X className="size-3.5" aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="text-charcoal-500 mt-2 font-mono text-[10px]">
        Autosave slot: {AUTOSAVE_LAYOUT_NAME} (hidden; restored on launch)
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Modules
// ---------------------------------------------------------------------------

function ModulesSection() {
  const modules = useModulesStore((state) => state.modules);
  const enabled = useModulesStore((state) => state.enabled);
  const setModuleEnabled = useModulesStore((state) => state.setModuleEnabled);

  return (
    <section aria-labelledby="settings-modules">
      <SectionHeader
        id="settings-modules"
        icon={<Layers className="size-4 text-amber-400" aria-hidden="true" />}
        title="Modules"
        hint="Disabled modules contribute no panels or ⌘K commands."
      />
      <ul className="flex flex-col gap-1.5">
        {modules.map((module) => {
          const isPlatform = module.id === PLATFORM_MODULE_ID;
          const isEnabled = enabled[module.id] !== false;
          return (
            <li
              key={module.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-md border px-4 py-3"
            >
              <div className="flex flex-col">
                <span className="text-charcoal-100 font-mono text-sm">{module.title}</span>
                <span className="text-charcoal-400 font-mono text-xs">
                  {module.panels.length} panel{module.panels.length === 1 ? "" : "s"} ·{" "}
                  {module.commands.length} command{module.commands.length === 1 ? "" : "s"}
                  {isPlatform ? " · always on" : ""}
                </span>
              </div>
              <label className="flex items-center gap-2">
                <span className="sr-only">
                  {isEnabled ? "Disable" : "Enable"} {module.title}
                </span>
                <input
                  type="checkbox"
                  role="switch"
                  aria-label={`${module.title} enabled`}
                  checked={isEnabled}
                  disabled={isPlatform}
                  onChange={(event) => {
                    if (isPlatform) return;
                    setModuleEnabled(module.id, event.target.checked);
                  }}
                  className="size-4 accent-amber-400 disabled:cursor-not-allowed disabled:opacity-40"
                />
              </label>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Preferences
// ---------------------------------------------------------------------------

/** Friendly labels for the panel ids the starter cockpit can compose. */
const STARTER_PANEL_LABELS: Record<string, string> = {
  "chart-panel": "Chart",
  "equity-overview-panel": "Equity Overview",
  "watchlist-panel": "Watchlist",
  "news-panel": "News",
  "portfolio-panel": "Portfolio",
  "screener-panel": "Screener",
  "sec-filings-panel": "SEC Filings",
  "macro-panel": "Macro",
  "earnings-calendar-panel": "Earnings Calendar",
  "analyst-ratings-panel": "Analyst Ratings",
};

function PreferencesSection() {
  const firstParty = useAgentsStore(selectFirstPartyAgents);
  const custom = useAgentsStore(selectCustomAgents);
  const refreshAgents = useAgentsStore((s) => s.refresh);

  const providers = useLLMProvidersStore((s) => s.providers);
  const defaultProviderId = useLLMProvidersStore((s) => s.defaultProviderId);
  const setDefaultProviderId = useLLMProvidersStore((s) => s.setDefaultProviderId);
  const modelFor = useModelSelectionStore((s) => s.modelFor);
  const setModel = useModelSelectionStore((s) => s.setModel);

  const defaultAgentId = useSettingsStore((s) => s.defaultAgentId);
  const setDefaultAgentId = useSettingsStore((s) => s.setDefaultAgentId);
  const providerPreferenceOrder = useSettingsStore((s) => s.providerPreferenceOrder);
  const moveProviderPreference = useSettingsStore((s) => s.moveProviderPreference);
  const paletteRecentsEnabled = useSettingsStore((s) => s.paletteRecentsEnabled);
  const setPaletteRecentsEnabled = useSettingsStore((s) => s.setPaletteRecentsEnabled);
  const paletteScopedToPanel = useSettingsStore((s) => s.paletteScopedToPanel);
  const setPaletteScopedToPanel = useSettingsStore((s) => s.setPaletteScopedToPanel);
  const starterCockpitPanelIds = useSettingsStore((s) => s.starterCockpitPanelIds);
  const toggleStarterCockpitPanel = useSettingsStore((s) => s.toggleStarterCockpitPanel);
  const themeKnobs = useSettingsStore((s) => s.themeKnobs);
  const setThemeKnobs = useSettingsStore((s) => s.setThemeKnobs);
  const region = useSettingsStore((s) => s.region);
  const setRegion = useSettingsStore((s) => s.setRegion);

  useEffect(() => {
    void refreshAgents();
  }, [refreshAgents]);

  const agents: AgentSummary[] = [...firstParty, ...custom];
  const providerLabel = (id: LLMProviderId) => providers.find((p) => p.id === id)?.label ?? id;
  // Union the persisted order with the live providers so a provider added in a
  // later release still appears (appended), and a stale id drops off.
  const liveIds = new Set(providers.map((p) => p.id));
  const orderedProviderIds: LLMProviderId[] = [
    ...providerPreferenceOrder.filter((id) => liveIds.has(id)),
    ...providers.map((p) => p.id).filter((id) => !providerPreferenceOrder.includes(id)),
  ];
  // Prefer the live, config-driven model list; fall back to the static map.
  const defaultProviderInfo = providers.find((p) => p.id === defaultProviderId);
  const defaultModelOptions: readonly string[] =
    defaultProviderInfo?.knownModels && defaultProviderInfo.knownModels.length > 0
      ? defaultProviderInfo.knownModels
      : (KNOWN_MODELS_BY_PROVIDER[defaultProviderId] ?? []);

  return (
    <section aria-labelledby="settings-preferences">
      <SectionHeader
        id="settings-preferences"
        icon={<Sliders className="size-4 text-amber-400" aria-hidden="true" />}
        title="Preferences"
        hint="How the copilot, the command palette, and your first-run cockpit behave. These travel with Export / Import below."
      />
      <div className="flex flex-col gap-4">
        {/* Default agent / persona */}
        <PrefRow
          label="Default agent"
          hint="The persona the copilot starts with each session."
          icon={<Bot className="size-3.5 text-amber-400" aria-hidden="true" />}
        >
          <select
            aria-label="Default agent"
            value={defaultAgentId ?? ""}
            onChange={(e) => setDefaultAgentId(e.target.value === "" ? null : e.target.value)}
            className={selectClass}
          >
            <option value="">No default (raw chat)</option>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.name}
              </option>
            ))}
          </select>
        </PrefRow>

        {/* Default provider */}
        <PrefRow
          label="Default provider"
          hint="The provider the copilot uses when an agent has no preference."
        >
          <select
            aria-label="Default provider"
            value={defaultProviderId}
            onChange={(e) => {
              setDefaultProviderId(e.target.value as LLMProviderId);
              void autosaveLayout();
            }}
            className={selectClass}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
        </PrefRow>

        {/* Default model for the default provider */}
        <PrefRow
          label="Default model"
          hint={`The model used for ${providerLabel(defaultProviderId)}.`}
        >
          <select
            aria-label="Default model"
            value={modelFor(defaultProviderId)}
            onChange={(e) => setModel(defaultProviderId, e.target.value)}
            className={selectClass}
          >
            {defaultModelOptions.map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </PrefRow>

        {/* Region / locale — Pass A item 8 foundation seam (defaults to US) */}
        <PrefRow
          label="Region"
          hint="Locale used for number formatting. Defaults to United States — a foundation for region-first data + feeds in a later release."
        >
          <select
            aria-label="Region"
            value={region}
            onChange={(e) => setRegion(e.target.value as Region)}
            className={selectClass}
          >
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </PrefRow>

        {/* Provider preference order */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-md border px-4 py-3">
          <p className="text-charcoal-200 font-mono text-xs">Provider preference order</p>
          <p className="text-charcoal-400 mt-0.5 mb-2 font-mono text-[11px]">
            The order providers are offered in pickers. Reorder to surface the ones you reach for
            first.
          </p>
          <ul className="flex flex-col gap-1">
            {orderedProviderIds.map((id, idx) => (
              <li
                key={id}
                className="border-charcoal-700 bg-charcoal-900 flex items-center justify-between gap-2 rounded border px-3 py-1.5"
              >
                <span className="text-charcoal-100 flex items-center gap-2 font-mono text-xs">
                  <span className="text-charcoal-500 w-4 text-right tabular-nums">{idx + 1}</span>
                  {providerLabel(id)}
                </span>
                <span className="flex items-center gap-0.5">
                  <button
                    type="button"
                    aria-label={`Move ${providerLabel(id)} up`}
                    disabled={idx === 0}
                    onClick={() => moveProviderPreference(id, "up")}
                    className="text-charcoal-400 rounded p-1 hover:text-amber-400 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ArrowUp className="size-3.5" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    aria-label={`Move ${providerLabel(id)} down`}
                    disabled={idx === orderedProviderIds.length - 1}
                    onClick={() => moveProviderPreference(id, "down")}
                    className="text-charcoal-400 rounded p-1 hover:text-amber-400 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ArrowDown className="size-3.5" aria-hidden="true" />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Command-palette behaviour */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-md border px-4 py-3">
          <p className="text-charcoal-200 mb-2 font-mono text-xs">Command palette</p>
          <ToggleRow
            label="Show recent commands"
            checked={paletteRecentsEnabled}
            onChange={setPaletteRecentsEnabled}
          />
          <ToggleRow
            label="Scope to the focused panel first"
            checked={paletteScopedToPanel}
            onChange={setPaletteScopedToPanel}
          />
        </div>

        {/* Starter-cockpit composition (FR-032) */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-md border px-4 py-3">
          <p className="text-charcoal-200 font-mono text-xs">Starter cockpit</p>
          <p className="text-charcoal-400 mt-0.5 mb-2 font-mono text-[11px]">
            The panels that open on first run, before you save your own layout.
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {Object.entries(STARTER_PANEL_LABELS).map(([panelId, label]) => {
              const checked = starterCockpitPanelIds.includes(panelId);
              return (
                <label
                  key={panelId}
                  className="text-charcoal-200 flex items-center gap-2 font-mono text-xs"
                >
                  <input
                    type="checkbox"
                    aria-label={`Starter cockpit: ${label}`}
                    checked={checked}
                    onChange={(e) => toggleStarterCockpitPanel(panelId, e.target.checked)}
                    className="size-4 accent-amber-400"
                  />
                  {label}
                </label>
              );
            })}
          </div>
        </div>

        {/* Theme knobs (dark-only) */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-md border px-4 py-3">
          <p className="text-charcoal-200 flex items-center gap-2 font-mono text-xs">
            <Palette className="size-3.5 text-amber-400" aria-hidden="true" />
            Appearance
          </p>
          <p className="text-charcoal-400 mt-0.5 mb-2 font-mono text-[11px]">
            Vysted is dark-only by design. These tune the dark language.
          </p>
          <div className="flex flex-col gap-2">
            <PrefRow label="Accent intensity">
              <select
                aria-label="Accent intensity"
                value={themeKnobs.accentIntensity}
                onChange={(e) =>
                  setThemeKnobs({
                    accentIntensity: e.target.value as typeof themeKnobs.accentIntensity,
                  })
                }
                className={selectClass}
              >
                <option value="muted">Muted</option>
                <option value="normal">Normal</option>
                <option value="vivid">Vivid</option>
              </select>
            </PrefRow>
            <PrefRow label="Density">
              <select
                aria-label="Density"
                value={themeKnobs.density}
                onChange={(e) =>
                  setThemeKnobs({ density: e.target.value as typeof themeKnobs.density })
                }
                className={selectClass}
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </select>
            </PrefRow>
          </div>
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Keybindings (FR-039)
// ---------------------------------------------------------------------------

/** Display order + headings for the keybinding categories. */
const CATEGORY_ORDER: { id: KeybindingCategory; label: string }[] = [
  { id: "palette", label: "Command palette" },
  { id: "agent", label: "Agent modes" },
  { id: "changes", label: "Proposed changes" },
  { id: "workspace", label: "Workspace" },
  { id: "panels", label: "Panels" },
  { id: "tools", label: "Tools" },
];

/**
 * Build a binding-grammar combo string from a keydown event. Modifiers first
 * (in the store's canonical order), the key last. `mod` is emitted for the
 * platform-primary modifier so it renders ⌘/Ctrl correctly. A bare modifier
 * press (e.g. just Shift) yields `""` so we keep listening for the real key.
 */
function comboFromEvent(event: React.KeyboardEvent): string {
  const key = event.key.toLowerCase();
  if (["control", "shift", "alt", "meta", "os", "hyper"].includes(key)) {
    return "";
  }
  const parts: string[] = [];
  // `metaKey`→⌘ and `ctrlKey`→Ctrl; collapse the platform-primary one to `mod`
  // so the binding matches the store's grammar regardless of OS.
  if (event.ctrlKey) parts.push("ctrl");
  if (event.altKey) parts.push("alt");
  if (event.shiftKey) parts.push("shift");
  if (event.metaKey) parts.push("meta");
  const normalizedKey = key === " " ? "space" : key === "esc" ? "escape" : key;
  parts.push(normalizedKey);
  return parts.join("+");
}

function KeybindingsSection() {
  const overrides = useKeybindingsStore((s) => s.overrides);
  const setBinding = useKeybindingsStore((s) => s.setBinding);
  const resetBinding = useKeybindingsStore((s) => s.resetBinding);
  const conflicts = useKeybindingsStore((s) => s.conflicts);

  const [recording, setRecording] = useState<string | null>(null);

  // Effective def per action (override beats default), grouped by category.
  const entries: { actionId: string; def: KeybindingDef; combo: string }[] = Object.entries(
    DEFAULT_KEYBINDINGS,
  ).map(([actionId, def]) => {
    const combo = overrides[actionId] ?? def.keys;
    return { actionId, def: { ...def, keys: combo }, combo };
  });

  // Conflicts → a set of action ids that collide, plus per-combo lists for the
  // warning copy.
  const conflictList = conflicts();
  const conflictedActionIds = new Set<string>();
  for (const c of conflictList) {
    for (const id of c.actionIds) conflictedActionIds.add(id);
  }

  function handleRecord(actionId: string, event: React.KeyboardEvent) {
    // Recording must swallow the keystroke so it never dispatches the action
    // (e.g. recording over ⌘K must not also open the palette).
    event.preventDefault();
    event.stopPropagation();
    const combo = comboFromEvent(event);
    if (combo === "") {
      return; // bare modifier — keep listening for the real key
    }
    setBinding(actionId, combo);
    setRecording(null);
  }

  return (
    <section aria-labelledby="settings-keybindings">
      <SectionHeader
        id="settings-keybindings"
        icon={<Keyboard className="size-4 text-amber-400" aria-hidden="true" />}
        title="Keybindings"
        hint="Remap any shortcut. Press Record, then the new combination. Conflicts are flagged below — two actions on one combo both fire."
      />

      {conflictList.length > 0 && (
        <div
          role="alert"
          className="border-warning/40 bg-warning/10 text-warning mb-3 flex items-start gap-2 rounded-md border px-3 py-2 font-mono text-xs"
        >
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Conflicting bindings detected</p>
            {conflictList.map((c) => (
              <p key={c.keys} className="text-warning/90 mt-0.5">
                <span className="font-mono">{formatBinding(c.keys)}</span> is bound to{" "}
                {c.actionIds.map((id) => DEFAULT_KEYBINDINGS[id]?.label ?? id).join(" and ")}.
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {CATEGORY_ORDER.map(({ id: category, label }) => {
          const group = entries.filter((e) => e.def.category === category);
          if (group.length === 0) {
            return null;
          }
          return (
            <div key={category}>
              <h3 className="text-charcoal-400 mb-1.5 font-mono text-[10px] tracking-wider uppercase">
                {label}
              </h3>
              <ul className="flex flex-col gap-1">
                {group.map(({ actionId, def, combo }) => {
                  const isRecording = recording === actionId;
                  const isOverridden = actionId in overrides;
                  const conflicted = conflictedActionIds.has(actionId);
                  return (
                    <li
                      key={actionId}
                      className={cn(
                        "border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-md border px-4 py-2.5",
                        conflicted && "border-warning/50",
                      )}
                    >
                      <div className="flex min-w-0 flex-col">
                        <span className="text-charcoal-100 font-mono text-xs">{def.label}</span>
                        <span className="text-charcoal-400 truncate font-mono text-[11px]">
                          {def.description}
                        </span>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <kbd
                          aria-label={`${def.label} binding`}
                          className={cn(
                            "border-charcoal-700 bg-charcoal-900 rounded border px-2 py-0.5 font-mono text-xs",
                            conflicted ? "text-warning" : "text-charcoal-100",
                          )}
                        >
                          {isRecording ? "Press keys…" : formatBinding(combo)}
                        </kbd>
                        <button
                          type="button"
                          aria-label={`Record binding for ${def.label}`}
                          onClick={() => setRecording(isRecording ? null : actionId)}
                          onKeyDown={isRecording ? (e) => handleRecord(actionId, e) : undefined}
                          className={cn(
                            "rounded px-2 py-1 font-mono text-[11px] uppercase",
                            isRecording
                              ? "bg-amber-500/20 text-amber-400"
                              : "text-charcoal-400 hover:text-charcoal-100",
                          )}
                        >
                          {isRecording ? "Recording" : "Record"}
                        </button>
                        <button
                          type="button"
                          aria-label={`Reset binding for ${def.label}`}
                          disabled={!isOverridden}
                          onClick={() => resetBinding(actionId)}
                          className="text-charcoal-400 rounded p-1 hover:text-amber-400 disabled:cursor-not-allowed disabled:opacity-30"
                        >
                          <RotateCcw className="size-3.5" aria-hidden="true" />
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Export / Import (FR-037 / FR-038)
// ---------------------------------------------------------------------------

/** The exported settings bundle shape. NEVER includes secrets (FR-036/SC-010). */
export interface SettingsExport {
  /** A small version tag so a future import can migrate older bundles. */
  version: 1;
  /** Remappable-keybinding overrides, keyed by action id. */
  keybindingOverrides: Record<string, string>;
  /** The local preferences bundle. */
  settings: SettingsBundle;
}

/** Build the export bundle from the live stores. Pure of secrets by construction. */
export function buildSettingsExport(): SettingsExport {
  return {
    version: 1,
    keybindingOverrides: { ...useKeybindingsStore.getState().overrides },
    settings: useSettingsStore.getState().toBundle(),
  };
}

function ExportImportSection() {
  const setOverrides = useKeybindingsStore((s) => s.setOverrides);
  const setAll = useSettingsStore((s) => s.setAll);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [status, setStatus] = useState<{ kind: "ok" | "error"; message: string } | null>(null);

  function handleExport() {
    if (typeof window === "undefined") {
      return;
    }
    const bundle = buildSettingsExport();
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "vysted-settings.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    setStatus({ kind: "ok", message: "Exported vysted-settings.json (no secrets included)." });
  }

  async function handleImportFile(file: File) {
    try {
      const text = await file.text();
      const parsed = JSON.parse(text) as Partial<SettingsExport>;
      if (parsed.keybindingOverrides && typeof parsed.keybindingOverrides === "object") {
        setOverrides(parsed.keybindingOverrides);
      }
      if (parsed.settings && typeof parsed.settings === "object") {
        setAll(parsed.settings);
      }
      setStatus({ kind: "ok", message: "Imported settings. Secrets re-enter via the keychain." });
    } catch {
      setStatus({ kind: "error", message: "Could not read that file — expected a Vysted export." });
    }
  }

  return (
    <section aria-labelledby="settings-export">
      <SectionHeader
        id="settings-export"
        icon={<Download className="size-4 text-amber-400" aria-hidden="true" />}
        title="Export / Import"
        hint="Carry your keybindings and preferences to another machine. Secrets are NEVER exported — re-enter your API keys via the keychain on the new machine."
      />
      <div className="border-charcoal-700 bg-charcoal-850 flex flex-col gap-3 rounded-md border px-4 py-3">
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={handleExport}>
            <Download className="size-3.5" aria-hidden="true" />
            Export settings
          </Button>
          <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>
            <Upload className="size-3.5" aria-hidden="true" />
            Import settings
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/json,.json"
            aria-label="Import settings file"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) {
                void handleImportFile(file);
              }
              e.target.value = ""; // allow re-importing the same file
            }}
          />
        </div>
        <p className="text-charcoal-500 font-mono text-[11px]">
          The export bundles your keybinding remaps and preferences (default agent, provider order,
          palette behaviour, starter cockpit, theme). API keys and broker credentials stay in your
          OS keychain and are never written to the file.
        </p>
        {status && (
          <p
            className={cn(
              "font-mono text-[11px]",
              status.kind === "ok" ? "text-positive" : "text-negative",
            )}
          >
            {status.message}
          </p>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// About
// ---------------------------------------------------------------------------

function AboutSection() {
  return (
    <section aria-labelledby="settings-about" className="pb-4">
      <SectionHeader
        id="settings-about"
        icon={<Settings2 className="size-4 text-amber-400" aria-hidden="true" />}
        title="About"
      />
      <div className="border-charcoal-700 bg-charcoal-850 text-charcoal-300 flex flex-col gap-1.5 rounded-md border px-4 py-3 font-mono text-xs">
        <p>
          Vysted Terminal <span className="text-charcoal-500">v{HOST_VERSION}</span> — an
          open-source, AI-native finance terminal.
        </p>
        <p className="text-charcoal-400">
          Plugin architecture · local-first · bring-your-own-keys. Your data, your keys, your
          machine — extend it like an IDE.
        </p>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Shared
// ---------------------------------------------------------------------------

function SectionHeader({
  id,
  icon,
  title,
  hint,
}: {
  id: string;
  icon: React.ReactNode;
  title: string;
  hint?: string;
}) {
  return (
    <header className="mb-3">
      <h2 id={id} className="text-charcoal-100 flex items-center gap-2 font-serif text-lg">
        {icon}
        {title}
      </h2>
      {hint && <p className="text-charcoal-400 mt-1 font-mono text-xs">{hint}</p>}
    </header>
  );
}

/** Shared `<select>` styling for the preferences controls. */
const selectClass =
  "border-charcoal-700 bg-charcoal-900 text-charcoal-100 h-8 min-w-[12rem] rounded-md border px-2 font-mono text-xs outline-none focus:border-amber-400";

/** A labelled preference row: label + hint on the left, a control on the right. */
function PrefRow({
  label,
  hint,
  icon,
  children,
}: {
  label: string;
  hint?: string;
  icon?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-md border px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-charcoal-100 flex items-center gap-2 font-mono text-xs">
          {icon}
          {label}
        </span>
        {hint && <span className="text-charcoal-400 mt-0.5 font-mono text-[11px]">{hint}</span>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

/** A compact labelled checkbox row used inside grouped preference cards. */
function ToggleRow({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label className="text-charcoal-200 flex items-center justify-between gap-3 py-1 font-mono text-xs">
      {label}
      <input
        type="checkbox"
        role="switch"
        aria-label={label}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="size-4 accent-amber-400"
      />
    </label>
  );
}
