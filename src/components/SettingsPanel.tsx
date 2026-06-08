"use client";

import { type FunctionComponent, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  ArrowDown,
  ArrowUp,
  Bot,
  Check,
  ChevronDown,
  Cpu,
  Download,
  FlaskConical,
  Info,
  KeyRound,
  Keyboard,
  Network,
  Package,
  Palette,
  Plug,
  RotateCcw,
  Search,
  Sliders,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { type Region, REGIONS } from "@/lib/region";
import { cn } from "@/lib/utils";
import { deleteSecret, getSecret, KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { EXA_KEYCHAIN_ACCOUNT } from "@/lib/search-headers";
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
import { buildModelGroups, modelOptionLabel } from "@/lib/model-options";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelCatalog } from "@/store/model-catalog";
import { KNOWN_MODELS_BY_PROVIDER, useModelSelectionStore } from "@/store/model-selection";
import { useModulesStore } from "@/store/modules";
import { useProviderKeysStore } from "@/store/provider-keys";
import {
  fetchHardwareReport,
  type HardwareReport,
  type ScoredModel,
  verdictMeta,
} from "@/lib/hardware-fit";
import { useSearchSettingsStore } from "@/store/search-settings";
import { type SettingsBundle, useSettingsStore } from "@/store/settings";
import { SEARCH_TIER_LABELS, SEARCH_TIERS, type SearchTier } from "../../types/search";
import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";
import type { LLMModelOption, LLMProviderId } from "../../types/ai";

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
            <h1 className="text-charcoal-100 text-overview flex items-center gap-2">
              <Sliders className="text-charcoal-300 size-5" aria-hidden="true" />
              Settings
            </h1>
            <p className="text-charcoal-400 text-caption mt-1 font-mono">
              Local-first &amp; bring-your-own-keys. Nothing leaves this machine except calls you
              make to providers you configure.
            </p>
          </header>
          <ProvidersSection />
          <WebSearchSection />
          <HardwareSection />
          <DeepResearchSection />
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
        icon={<Plug className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="AI Providers"
        hint="Paste an API key to enable an AI provider. Keys are stored in your OS keychain — never on disk or sent anywhere but the provider you call."
      />
      <ul className="flex flex-col gap-2">
        {providers.map((provider) => {
          const keyState = status[provider.id] ?? "missing";
          const configured = keyState === "configured";
          const isDefault = defaultProviderId === provider.id;
          const needsKey = provider.requiresKey;
          return (
            <li
              key={provider.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-none border px-4 py-3"
            >
              <div className="flex min-w-0 flex-col">
                <span className="text-charcoal-100 text-body flex min-w-0 items-center gap-2 font-mono">
                  <span className="truncate">{provider.label}</span>
                  {isDefault && (
                    <span className="text-micro rounded-control bg-charcoal-700/15 shrink-0 px-2 py-1">
                      default
                    </span>
                  )}
                </span>
                <span className="text-charcoal-400 text-caption mt-1 flex min-w-0 items-center gap-2 font-mono">
                  {!needsKey ? (
                    <span className="truncate">No key required (local)</span>
                  ) : configured ? (
                    <span className="text-positive flex min-w-0 items-center gap-1">
                      <Check className="size-3 shrink-0" aria-hidden="true" />
                      <span className="truncate">Key configured</span>
                    </span>
                  ) : (
                    <span className="truncate">No key yet</span>
                  )}
                </span>
              </div>
              <div className="flex shrink-0 items-center gap-2">
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
                    className="text-micro text-charcoal-400 hover:text-charcoal-100 font-mono"
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
                        className="text-charcoal-400 hover:text-negative rounded-control p-2"
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
// Web search (three tiers — FR-080/083/084)
// ---------------------------------------------------------------------------

/** Providers whose native web search is a PROVIDER-level guarantee (every routable
 *  model rides the provider's own search). Mirrors
 *  `native_search.PROVIDER_LEVEL_NATIVE_SEARCH` on the sidecar. OpenRouter is
 *  deliberately absent — it is gated per-MODEL on the catalog `webSearch` flag. */
const PROVIDER_LEVEL_NATIVE_SEARCH: ReadonlySet<LLMProviderId> = new Set([
  "anthropic",
  "openai",
  "gemini",
  "groq",
  "xai",
]);

/** OpenRouter's documented per-search web-plugin price.
 *
 *  DOCUMENTED ESTIMATE — sourced from OpenRouter's web-search docs
 *  (https://openrouter.ai/docs/features/web-search), NOT from any code or live
 *  pricing feed, so it CAN DRIFT. Docs quote ~$0.005 for a search returning up to
 *  10 results, plus ~$0.001 per extra result. We surface only the typical
 *  (<=10-result) figure, always prefixed with "~" and labelled an estimate — it
 *  is NEVER presented as an authoritative charge. */
const OPENROUTER_WEB_SEARCH_EST_USD = 0.005;

/** Honest, model/provider-aware native-tier status copy (WS5). The OpenRouter
 *  plugin price is a DOCUMENTED ESTIMATE that may drift (OPENROUTER_WEB_SEARCH_
 *  EST_USD) — rendered as an estimate, never an authoritative quote. Exported so
 *  the honesty guarantee across the provider/model matrix is locked by tests. */
export function nativeSearchStatus(
  provider: LLMProviderId,
  modelWebSearch: LLMModelOption["webSearch"],
): string {
  if (PROVIDER_LEVEL_NATIVE_SEARCH.has(provider)) {
    return "Searches run on your active model's own web search — billed to your provider key, no extra key needed.";
  }
  if (provider === "openrouter") {
    if (modelWebSearch === "native") {
      // OpenRouter routes the search to the model's own native search — billed by
      // the upstream, not the priced plugin; no separate per-search estimate.
      return "Searches run on this OpenRouter model's own native web search — billed through your OpenRouter credits.";
    }
    if (modelWebSearch === "plugin") {
      return `This OpenRouter model has no native web search, so searches fall back to the app's search tool. (OpenRouter can run a billed web plugin — est. ~$${OPENROUTER_WEB_SEARCH_EST_USD.toFixed(3)} per search, a documented price that may drift — but the terminal doesn't auto-enable it.)`;
    }
    return "This OpenRouter model has no native web search, so searches use the app's own search tool (Exa/SearXNG/keyless floor).";
  }
  // DeepSeek / Ollama and anything else: no native search rung — the app's tool runs.
  return "This model has no native web search, so searches use the app's own search tool (Exa/SearXNG/keyless floor).";
}

/**
 * Web search — the three-tier search control (FR-080/083/084).
 *
 *  - Tier picker: native (model's own web search on your provider key) /
 *    BYOK Exa / local SearXNG.
 *  - Exa API key (BYOK): stored in the OS keychain, sent as `X-Vysted-Exa-Key`.
 *    Read/written here directly (the search-source plugin's secret namespace).
 *  - SearXNG URL: the local-tier base URL (`X-Vysted-Searxng-Url`); blank =
 *    autodetect `localhost:8080`.
 */
function WebSearchSection() {
  const tier = useSearchSettingsStore((s) => s.tier);
  const setTier = useSearchSettingsStore((s) => s.setTier);
  const searxngUrl = useSearchSettingsStore((s) => s.searxngUrl);
  const setSearxngUrl = useSearchSettingsStore((s) => s.setSearxngUrl);

  // The active provider + model decide whether the NATIVE tier actually fires on
  // THIS model (WS5). The five provider-level native providers always do; an
  // OpenRouter model only fires native search when its catalog flag is "native"
  // (else searches fall back to the app's own search tool). Read the resolved
  // model's capability from the live catalog so the copy is honest per model.
  const activeProvider = useLLMProvidersStore((s) => s.defaultProviderId);
  const activeModel = useModelSelectionStore((s) => s.modelFor(activeProvider));
  const { entry: activeCatalog } = useModelCatalog(activeProvider);
  const activeModelOption = activeCatalog?.models.find((m) => m.id === activeModel);
  const nativeStatus = nativeSearchStatus(activeProvider, activeModelOption?.webSearch ?? null);

  // Exa key status is read straight from the keychain (BYOK; never in a store).
  const [exaConfigured, setExaConfigured] = useState<boolean | null>(null);
  const [exaInput, setExaInput] = useState("");
  const [exaBusy, setExaBusy] = useState(false);
  const [exaError, setExaError] = useState<string | null>(null);

  async function refreshExa() {
    try {
      const value = await getSecret(EXA_KEYCHAIN_ACCOUNT);
      setExaConfigured(Boolean(value));
    } catch {
      setExaConfigured(false);
    }
  }

  useEffect(() => {
    // Only sets state after the awaited keychain read resolves (never
    // synchronously) — same no-cascade pattern as the Layouts section.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshExa();
  }, []);

  async function handleSaveExa() {
    const value = exaInput.trim();
    if (!value) {
      return;
    }
    setExaBusy(true);
    setExaError(null);
    try {
      await setSecret(EXA_KEYCHAIN_ACCOUNT, value);
      setExaInput("");
      await refreshExa();
    } catch (err) {
      // A keychain write can fail (locked keychain, denied access). Surface it —
      // otherwise refreshExa() shows "not configured" and the user thinks it saved.
      setExaError(err instanceof Error ? err.message : "Couldn't save the key to the keychain.");
    } finally {
      setExaBusy(false);
    }
  }

  async function handleRemoveExa() {
    setExaBusy(true);
    setExaError(null);
    try {
      await deleteSecret(EXA_KEYCHAIN_ACCOUNT);
      await refreshExa();
    } catch (err) {
      setExaError(
        err instanceof Error ? err.message : "Couldn't remove the key from the keychain.",
      );
    } finally {
      setExaBusy(false);
    }
  }

  return (
    <section aria-labelledby="settings-search">
      <SectionHeader
        id="settings-search"
        icon={<Search className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Web search"
        hint="Pick how the copilot searches the web. Native rides your model's own search when the active model supports it (else it falls back to the app's search tool); BYOK adds an Exa key for finance-grade retrieval; local routes through a private SearXNG so nothing leaves your machine."
      />
      <div className="flex flex-col gap-4">
        {/* Tier picker */}
        <PrefRow
          label="Search tier"
          hint="Native (model's web search), BYOK Exa, or local SearXNG."
        >
          <Select
            aria-label="Search tier"
            value={tier}
            onChange={(e) => setTier(e.target.value as SearchTier)}
          >
            {SEARCH_TIERS.map((t) => (
              <option key={t} value={t}>
                {SEARCH_TIER_LABELS[t]}
              </option>
            ))}
          </Select>
        </PrefRow>

        {/* Active-tier status: a one-line confirmation of where searches route,
            so the selected tier's effect is never ambiguous. */}
        <p className="text-charcoal-400 text-caption -mt-2 font-mono">
          {tier === "native"
            ? nativeStatus
            : tier === "byok-exa"
              ? exaConfigured
                ? "Searches route through Exa using your stored key."
                : "Add an Exa key below to activate this tier."
              : "Searches route through your local SearXNG instance — nothing leaves your machine."}
        </p>

        {/* Exa API key (BYOK, keychain) */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3">
          <p className="text-charcoal-200 text-caption flex items-center gap-2 font-mono">
            <KeyRound className="text-charcoal-300 size-3.5" aria-hidden="true" />
            Exa API key (BYOK)
          </p>
          <p className="text-charcoal-400 text-caption mt-1 mb-2 font-mono">
            Optional. Stored in your OS keychain — never on disk or sent anywhere but Exa. Powers
            the BYOK search tier.
          </p>
          {exaConfigured === null ? (
            // Keychain read in flight — show a quiet checking state instead of
            // briefly flashing the "needs a key" form (which is misleading if a
            // key IS stored).
            <span className="text-charcoal-400 text-caption font-mono">Checking…</span>
          ) : exaConfigured ? (
            <div className="flex items-center justify-between gap-2">
              <span className="text-positive text-caption flex items-center gap-1 font-mono">
                <Check className="size-3" aria-hidden="true" /> Key configured
              </span>
              <Button
                size="sm"
                variant="outline"
                disabled={exaBusy}
                onClick={() => void handleRemoveExa()}
              >
                <Trash2 className="size-3" aria-hidden="true" />
                Remove
              </Button>
            </div>
          ) : (
            <>
              {/* When the BYOK tier is selected but no key is stored, the tier
                  can't actually run — say so plainly rather than silently falling
                  back. */}
              {tier === "byok-exa" ? (
                <p className="text-warning text-caption mb-2 font-mono">
                  The BYOK search tier is selected but needs an Exa key to work — add one below.
                </p>
              ) : null}
              <form
                className="flex items-center gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void handleSaveExa();
                }}
              >
                <input
                  type="password"
                  value={exaInput}
                  onChange={(e) => setExaInput(e.target.value)}
                  placeholder="exa_..."
                  aria-label="Exa API key"
                  className="border-charcoal-700 bg-charcoal-900 text-charcoal-100 placeholder:text-charcoal-400 rounded-control text-caption focus:border-charcoal-500 h-8 flex-1 border px-3 font-mono outline-none"
                />
                <Button
                  type="submit"
                  size="sm"
                  variant="outline"
                  disabled={exaBusy || exaInput.trim() === ""}
                >
                  Save key
                </Button>
              </form>
              {exaError && (
                <p className="text-negative text-caption mt-2 font-mono" role="alert">
                  {exaError}
                </p>
              )}
            </>
          )}
        </div>

        {/* SearXNG URL (local tier) */}
        <PrefRow
          label="SearXNG URL"
          hint="Local-tier base URL. Leave blank to autodetect localhost:8888 then :8080."
        >
          <input
            type="url"
            value={searxngUrl}
            onChange={(e) => setSearxngUrl(e.target.value)}
            placeholder="http://localhost:8080"
            aria-label="SearXNG URL"
            className="border-charcoal-700 bg-charcoal-900 text-charcoal-100 placeholder:text-charcoal-400 rounded-control text-caption focus:border-charcoal-500 h-8 min-w-[12rem] border px-3 font-mono outline-none"
          />
        </PrefRow>
        {/* Run-a-local-instance hint — keyless private search in one command.
            JSON output is OFF by default in SearXNG, so the setup must enable it. */}
        {tier === "local-searxng" && (
          <div className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3">
            <p className="text-charcoal-200 text-caption font-mono">
              No instance yet? Run one locally (keyless, ~200 MB):
            </p>
            <pre className="text-charcoal-300 bg-charcoal-900 text-caption mt-2 overflow-x-auto rounded-none p-2 font-mono leading-relaxed">
              {
                "docker run -d -p 8080:8080 \\\n  -e SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml \\\n  searxng/searxng"
              }
            </pre>
            <p className="text-charcoal-400 text-caption mt-2 font-mono">
              Then enable JSON output: add <code className="text-charcoal-300">json</code> to{" "}
              <code className="text-charcoal-300">search.formats</code> and set{" "}
              <code className="text-charcoal-300">server.limiter: false</code> in settings.yml. The
              terminal autodetects it on the next research run.
            </p>
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Integrations (brokers + data providers)
// ---------------------------------------------------------------------------

function IntegrationsSection() {
  const openPanel = useWorkspaceStore((s) => s.openPanel);

  return (
    <section aria-labelledby="settings-integrations">
      <SectionHeader
        id="settings-integrations"
        icon={<Network className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Integrations"
        hint="Connect a broker for read-only positions, holdings & P&L the copilot can analyse over your real account."
      />
      <div className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-none border px-4 py-3">
        <span className="text-charcoal-400 text-caption font-mono">
          Broker connections are managed in the Marketplace.
        </span>
        <Button size="sm" variant="outline" onClick={() => openPanel("marketplace-panel")}>
          Open Marketplace
        </Button>
      </div>
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
        icon={<Package className="text-charcoal-300 size-4" aria-hidden="true" />}
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
          className="border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-400 rounded-control text-caption focus:border-charcoal-500 h-8 flex-1 border px-3 font-mono outline-none"
        />
        <Button type="submit" size="sm" variant="outline" disabled={busy || newName.trim() === ""}>
          Save
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => void resetLayout()}>
          Reset to default
        </Button>
      </form>
      {error && <p className="text-negative text-caption mb-2 font-mono">{error}</p>}
      {names === null ? (
        <p className="text-charcoal-400 text-caption font-mono">Loading layouts…</p>
      ) : names.length === 0 ? (
        <p className="text-charcoal-400 text-caption font-mono">
          No saved layouts yet — arrange your panels and save above.
        </p>
      ) : (
        <ul className="flex flex-col gap-1">
          {names.map((name) => (
            <li
              key={name}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-none border px-3 py-2"
            >
              <span className="text-charcoal-100 text-caption truncate font-mono">
                {name}
                {name === activeName && (
                  <span className="text-micro text-charcoal-500 ml-2">active</span>
                )}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void withBusy(() => loadWorkspace(name))}
                  className="text-micro text-charcoal-300 hover:text-charcoal-100 font-mono"
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
                  className="text-charcoal-400 hover:text-negative rounded-control p-1"
                >
                  <X className="size-3.5" aria-hidden="true" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="text-charcoal-500 text-caption mt-2 font-mono">
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
        icon={<Package className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Modules"
        hint="Disabled modules contribute no panels or ⌘K commands."
      />
      <ul className="flex flex-col gap-2">
        {modules.map((module) => {
          const isPlatform = module.id === PLATFORM_MODULE_ID;
          const isEnabled = enabled[module.id] !== false;
          return (
            <li
              key={module.id}
              className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between rounded-none border px-4 py-3"
            >
              <div className="flex flex-col">
                <span className="text-charcoal-100 text-body font-mono">{module.title}</span>
                <span className="text-charcoal-400 text-caption font-mono">
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
                  className="accent-charcoal-300 size-4 disabled:cursor-not-allowed disabled:opacity-40"
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

// ---------------------------------------------------------------------------
// Hardware capability (Track D — local-model fit gate)
// ---------------------------------------------------------------------------

/** One scored model row — a verdict chip + the reason. */
function FitRow({ model }: { model: ScoredModel }) {
  const meta = verdictMeta(model.verdict);
  return (
    <li className="flex items-baseline justify-between gap-3 py-1">
      <div className="min-w-0">
        <div className="text-charcoal-200 text-caption truncate font-mono">{model.name}</div>
        <div className="text-charcoal-500 text-caption truncate font-mono">{model.reason}</div>
      </div>
      <span className={cn("text-caption shrink-0 font-mono font-semibold", meta.className)}>
        {meta.label}
      </span>
    </li>
  );
}

/**
 * Hardware capability — detects the device and shows which local models it can
 * run, gating the heavy local paths (FINDINGS §2.5). On a 16 GB M1, local
 * deep-research is honestly marked "remote" and the app uses the keyless-remote
 * path; on a 32 GB+ box the same models flip to "runs locally" with no change.
 */
function HardwareSection() {
  const [report, setReport] = useState<HardwareReport | null | "loading">("loading");

  useEffect(() => {
    let alive = true;
    void fetchHardwareReport().then((r) => {
      if (alive) {
        setReport(r);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <section aria-labelledby="settings-hardware">
      <SectionHeader
        id="settings-hardware"
        icon={<Cpu className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Hardware & local models"
        hint="What this machine can run on-device. Heavy local paths (local deep-research, large local LLMs) enable only where the hardware earns it; everything else uses the keyless-remote path."
      />
      {report === "loading" && (
        <p className="text-charcoal-500 text-caption font-mono">Detecting device…</p>
      )}
      {report === null && (
        <p className="text-charcoal-500 text-caption font-mono">
          Hardware detection unavailable (sidecar not connected).
        </p>
      )}
      {report && report !== "loading" && (
        <div className="flex flex-col gap-3">
          <div className="border-charcoal-700 bg-charcoal-900 rounded-none border p-3">
            <div className="text-charcoal-100 text-caption font-mono">{report.device.chip}</div>
            <div className="text-charcoal-400 text-caption mt-1 font-mono">
              {report.device.ramGib} GiB RAM · {report.device.gpuBudgetGib} GiB GPU budget ·{" "}
              {report.device.perfCores}P/{report.device.totalCores} cores · {report.device.osName}{" "}
              {report.device.osVersion}
            </div>
          </div>
          {report.ollama.models.length > 0 && (
            <div>
              <div className="text-charcoal-400 text-caption mb-1 font-mono uppercase">
                Installed local models (Ollama)
              </div>
              <ul className="divide-charcoal-800 divide-y">
                {report.ollama.models.map((m) => (
                  <FitRow key={m.name} model={m} />
                ))}
              </ul>
            </div>
          )}
          <div>
            <div className="text-charcoal-400 text-caption mb-1 font-mono uppercase">
              Frontier deep-research models
            </div>
            <ul className="divide-charcoal-800 divide-y">
              {report.referenceCandidates.map((m) => (
                <FitRow key={m.name} model={m} />
              ))}
            </ul>
          </div>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Deep-research engine (Track 5)
// ---------------------------------------------------------------------------

/**
 * Deep-research note (Track 5) — deep research runs Vysted's own native
 * IterResearch loop on the user's configured model. There is no engine selector:
 * native is the only user-facing engine (the opt-in paid Perplexity backend is
 * agent-selected with its own key, never surfaced here), so this is a static
 * explanation, not a radio group + routing probe.
 */
function DeepResearchSection() {
  return (
    <section aria-labelledby="settings-deepresearch">
      <SectionHeader
        id="settings-deepresearch"
        icon={<FlaskConical className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Deep research"
        hint="How /deep and 'go deeper' work."
      />
      <p className="text-charcoal-400 text-caption px-2 font-mono leading-relaxed">
        Deep research runs Vysted&rsquo;s own bounded{" "}
        <span className="text-charcoal-200">IterResearch</span> loop on your configured model — a
        multi-round search → read → reflect → synthesize pass that returns a cited brief. Always
        available, no extra key, no extra cost.
      </p>
    </section>
  );
}

function PreferencesSection() {
  const firstParty = useAgentsStore(selectFirstPartyAgents);
  const custom = useAgentsStore(selectCustomAgents);
  const agentsLoading = useAgentsStore((s) => s.loading);
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
  // Prefer the LIVE provider catalog (queried from the provider's own models
  // API); fall back to the config-driven known list, then the static map.
  const defaultProviderInfo = providers.find((p) => p.id === defaultProviderId);
  const { entry: defaultModelCatalog } = useModelCatalog(defaultProviderId);
  const fallbackModelIds: readonly string[] =
    defaultProviderInfo?.knownModels && defaultProviderInfo.knownModels.length > 0
      ? defaultProviderInfo.knownModels
      : (KNOWN_MODELS_BY_PROVIDER[defaultProviderId] ?? []);
  const defaultModelOptions: LLMModelOption[] =
    defaultModelCatalog?.models && defaultModelCatalog.models.length > 0
      ? defaultModelCatalog.models
      : fallbackModelIds.map((id) => ({ id, label: id }));
  const { groups: defaultModelGroups } = buildModelGroups(
    defaultModelOptions,
    modelFor(defaultProviderId),
  );

  return (
    <section aria-labelledby="settings-preferences">
      <SectionHeader
        id="settings-preferences"
        icon={<Sliders className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Preferences"
        hint="How the copilot, the command palette, and your first-run cockpit behave. These travel with Export / Import below."
      />
      <div className="flex flex-col gap-4">
        {/* Default agent / persona */}
        <PrefRow
          label="Default agent"
          hint="The persona the copilot starts with each session."
          icon={<Bot className="text-charcoal-300 size-3.5" aria-hidden="true" />}
        >
          <Select
            aria-label="Default agent"
            value={agentsLoading && agents.length === 0 ? "__loading__" : (defaultAgentId ?? "")}
            disabled={agentsLoading && agents.length === 0}
            onChange={(e) => setDefaultAgentId(e.target.value === "" ? null : e.target.value)}
          >
            {agentsLoading && agents.length === 0 ? (
              <option value="__loading__" disabled>
                Loading agents…
              </option>
            ) : (
              <>
                <option value="">No default (raw chat)</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </>
            )}
          </Select>
        </PrefRow>

        {/* Default provider */}
        <PrefRow
          label="Default provider"
          hint="The provider the copilot uses when an agent has no preference."
        >
          <Select
            aria-label="Default provider"
            value={defaultProviderId}
            onChange={(e) => {
              setDefaultProviderId(e.target.value as LLMProviderId);
              void autosaveLayout();
            }}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </Select>
        </PrefRow>

        {/* Default model for the default provider */}
        <PrefRow
          label="Default model"
          hint={
            defaultModelCatalog?.note
              ? `${providerLabel(defaultProviderId)} — ${defaultModelCatalog.note}`
              : `The model used for ${providerLabel(defaultProviderId)}.`
          }
        >
          <Select
            aria-label="Default model"
            value={modelFor(defaultProviderId)}
            onChange={(e) => setModel(defaultProviderId, e.target.value)}
          >
            {defaultModelGroups.map((group, index) =>
              group.label ? (
                <optgroup key={group.label} label={group.label}>
                  {group.options.map((option) => (
                    <option key={option.id} value={option.id}>
                      {modelOptionLabel(option)}
                    </option>
                  ))}
                </optgroup>
              ) : (
                group.options.map((option) => (
                  <option key={`${index}-${option.id}`} value={option.id}>
                    {modelOptionLabel(option)}
                  </option>
                ))
              ),
            )}
          </Select>
        </PrefRow>

        {/* Region / locale — Pass A item 8 foundation seam (defaults to US) */}
        <PrefRow
          label="Region"
          hint="Locale used for number formatting. Defaults to United States — a foundation for region-first data + feeds in a later release."
        >
          <Select
            aria-label="Region"
            value={region}
            onChange={(e) => setRegion(e.target.value as Region)}
          >
            {REGIONS.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </Select>
        </PrefRow>

        {/* Provider preference order */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3">
          <p className="text-charcoal-200 text-caption font-mono">Provider preference order</p>
          <p className="text-charcoal-400 text-caption mt-1 mb-2 font-mono">
            The order providers are offered in pickers. Reorder to surface the ones you reach for
            first.
          </p>
          <ul className="flex flex-col gap-1">
            {orderedProviderIds.map((id, idx) => (
              <li
                key={id}
                className="border-charcoal-700 bg-charcoal-900 flex items-center justify-between gap-2 rounded-none border px-3 py-2"
              >
                <span className="text-charcoal-100 text-caption flex items-center gap-2 font-mono">
                  <span className="text-charcoal-500 w-4 text-right tabular-nums">{idx + 1}</span>
                  {providerLabel(id)}
                </span>
                <span className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label={`Move ${providerLabel(id)} up`}
                    disabled={idx === 0}
                    onClick={() => moveProviderPreference(id, "up")}
                    className="text-charcoal-400 rounded-control hover:text-charcoal-100 p-1 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ArrowUp className="size-3.5" aria-hidden="true" />
                  </button>
                  <button
                    type="button"
                    aria-label={`Move ${providerLabel(id)} down`}
                    disabled={idx === orderedProviderIds.length - 1}
                    onClick={() => moveProviderPreference(id, "down")}
                    className="text-charcoal-400 rounded-control hover:text-charcoal-100 p-1 disabled:cursor-not-allowed disabled:opacity-30"
                  >
                    <ArrowDown className="size-3.5" aria-hidden="true" />
                  </button>
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Command-palette behaviour */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3">
          <p className="text-charcoal-200 text-caption mb-2 font-mono">Command palette</p>
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
        <div className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3">
          <p className="text-charcoal-200 text-caption font-mono">Starter cockpit</p>
          <p className="text-charcoal-400 text-caption mt-1 mb-2 font-mono">
            The panels that open on first run, before you save your own layout.
          </p>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1">
            {Object.entries(STARTER_PANEL_LABELS).map(([panelId, label]) => {
              const checked = starterCockpitPanelIds.includes(panelId);
              return (
                <label
                  key={panelId}
                  title={label}
                  className="text-charcoal-200 text-caption flex min-w-0 items-center gap-2 font-mono"
                >
                  <input
                    type="checkbox"
                    aria-label={`Starter cockpit: ${label}`}
                    checked={checked}
                    onChange={(e) => toggleStarterCockpitPanel(panelId, e.target.checked)}
                    className="accent-charcoal-300 size-4 shrink-0"
                  />
                  <span className="truncate">{label}</span>
                </label>
              );
            })}
          </div>
        </div>

        {/* Theme knobs (dark-only) */}
        <div className="border-charcoal-700 bg-charcoal-850 rounded-none border px-4 py-3">
          <p className="text-charcoal-200 text-caption flex items-center gap-2 font-mono">
            <Palette className="text-charcoal-300 size-3.5" aria-hidden="true" />
            Appearance
          </p>
          <p className="text-charcoal-400 text-caption mt-1 mb-2 font-mono">
            Vysted is dark-only by design. These tune the dark language.
          </p>
          <div className="flex flex-col gap-2">
            <PrefRow label="Accent intensity">
              <Select
                aria-label="Accent intensity"
                value={themeKnobs.accentIntensity}
                onChange={(e) =>
                  setThemeKnobs({
                    accentIntensity: e.target.value as typeof themeKnobs.accentIntensity,
                  })
                }
              >
                <option value="muted">Muted</option>
                <option value="normal">Normal</option>
                <option value="vivid">Vivid</option>
              </Select>
            </PrefRow>
            <PrefRow label="Density">
              <Select
                aria-label="Density"
                value={themeKnobs.density}
                onChange={(e) =>
                  setThemeKnobs({ density: e.target.value as typeof themeKnobs.density })
                }
              >
                <option value="comfortable">Comfortable</option>
                <option value="compact">Compact</option>
              </Select>
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
    // Escape cancels recording instead of being bound — caught BEFORE the
    // combo is read so it can never be captured as a binding.
    if (event.key === "Escape") {
      event.preventDefault();
      event.stopPropagation();
      setRecording(null);
      return;
    }
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
        icon={<Keyboard className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Keybindings"
        hint="Remap any shortcut. Press Record, then the new combination. Conflicts are flagged below — two actions on one combo both fire."
      />

      {conflictList.length > 0 && (
        <div
          role="alert"
          className="border-warning/40 bg-warning/10 text-warning text-caption mb-3 flex items-start gap-2 rounded-none border px-3 py-2 font-mono"
        >
          <AlertTriangle className="mt-1 size-3.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Conflicting bindings detected</p>
            {conflictList.map((c) => (
              <p key={c.keys} className="text-warning/90 mt-1">
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
              <h3 className="text-micro text-charcoal-400 mb-2 font-mono">{label}</h3>
              <ul className="flex flex-col gap-1">
                {group.map(({ actionId, def, combo }) => {
                  const isRecording = recording === actionId;
                  const isOverridden = actionId in overrides;
                  const conflicted = conflictedActionIds.has(actionId);
                  return (
                    <li
                      key={actionId}
                      className={cn(
                        "border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-none border px-4 py-3",
                        conflicted && "border-warning/50",
                      )}
                    >
                      <div className="flex min-w-0 flex-col">
                        <span className="text-charcoal-100 text-caption font-mono">
                          {def.label}
                        </span>
                        <span className="text-charcoal-400 text-caption truncate font-mono">
                          {def.description}
                        </span>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <kbd
                          aria-label={`${def.label} binding`}
                          className={cn(
                            "border-charcoal-700 bg-charcoal-900 rounded-control text-caption border px-2 py-1 font-mono",
                            conflicted ? "text-warning" : "text-charcoal-100",
                          )}
                        >
                          {isRecording ? "Press keys… (Esc to cancel)" : formatBinding(combo)}
                        </kbd>
                        <button
                          type="button"
                          aria-label={`Record binding for ${def.label}`}
                          onClick={() => setRecording(isRecording ? null : actionId)}
                          onKeyDown={isRecording ? (e) => handleRecord(actionId, e) : undefined}
                          onBlur={() => {
                            // Cancel recording when focus leaves the button so
                            // the control can't get stranded in recording state.
                            if (isRecording) setRecording(null);
                          }}
                          className={cn(
                            "text-micro rounded-control px-2 py-1 font-mono",
                            isRecording
                              ? "bg-charcoal-700/20 text-charcoal-300"
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
                          className="text-charcoal-400 rounded-control hover:text-charcoal-100 p-1 disabled:cursor-not-allowed disabled:opacity-30"
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
        icon={<Download className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Export / Import"
        hint="Carry your keybindings and preferences to another machine. Secrets are NEVER exported — re-enter your API keys via the keychain on the new machine."
      />
      <div className="border-charcoal-700 bg-charcoal-850 flex flex-col gap-3 rounded-none border px-4 py-3">
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
        <p className="text-charcoal-500 text-caption font-mono">
          The export bundles your keybinding remaps and preferences (default agent, provider order,
          palette behaviour, starter cockpit, theme). API keys and broker credentials stay in your
          OS keychain and are never written to the file.
        </p>
        {status && (
          <p
            className={cn(
              "text-caption font-mono",
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
        icon={<Info className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="About"
      />
      <div className="border-charcoal-700 bg-charcoal-850 text-charcoal-300 text-caption flex flex-col gap-2 rounded-none border px-4 py-3 font-mono">
        <p>
          Vysted <span className="text-charcoal-500">v{HOST_VERSION}</span> — an open-source,
          AI-native finance terminal.
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
      <h2 id={id} className="text-charcoal-100 text-section flex items-center gap-2">
        {icon}
        {title}
      </h2>
      {hint && <p className="text-charcoal-400 text-caption mt-1 font-mono">{hint}</p>}
    </header>
  );
}

/**
 * Shared `<select>` styling for the preferences controls. `appearance-none`
 * strips the cold WKWebView OS-default chrome (so the warm chevron below shows
 * through); `pr-6` reserves room for that chevron.
 */
const selectClass =
  "border-charcoal-700 bg-charcoal-900 text-charcoal-100 h-8 min-w-[12rem] appearance-none rounded-control border pr-6 pl-2 font-mono text-caption outline-none focus:border-charcoal-500";

/**
 * A `<select>` wrapped in a `relative` container with a warm chevron overlay —
 * the chevron replaces the suppressed native control glyph (`appearance-none`).
 */
function Select({ className, children, ...props }: React.ComponentProps<"select">) {
  return (
    <div className="relative inline-block">
      <select className={cn(selectClass, className)} {...props}>
        {children}
      </select>
      <ChevronDown
        className="text-charcoal-400 pointer-events-none absolute top-1/2 right-2 size-3.5 -translate-y-1/2"
        aria-hidden="true"
      />
    </div>
  );
}

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
    <div className="border-charcoal-700 bg-charcoal-850 flex items-center justify-between gap-3 rounded-none border px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-charcoal-100 text-caption flex items-center gap-2 font-mono">
          {icon}
          {label}
        </span>
        {hint && <span className="text-charcoal-400 text-caption mt-1 font-mono">{hint}</span>}
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
    <label className="text-charcoal-200 text-caption flex items-center justify-between gap-3 py-1 font-mono">
      {label}
      <input
        type="checkbox"
        role="switch"
        aria-label={label}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="accent-charcoal-300 size-4"
      />
    </label>
  );
}
