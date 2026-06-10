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
  Globe,
  Info,
  KeyRound,
  Keyboard,
  LayoutPanelLeft,
  Network,
  Package,
  Plug,
  RotateCcw,
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
import { getSidecarBaseUrl } from "@/lib/sidecar-client";
import {
  type HostedSearchEngine,
  type ResearchTier,
  useSearchSettingsStore,
} from "@/store/search-settings";
import { type SettingsBundle, useSettingsStore } from "@/store/settings";
import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";
import type { LLMModelOption, LLMProviderId } from "../../types/ai";

/**
 * Settings — the discoverable control surface (Cursor-grade preferences,
 * FR-037/FR-038/FR-039, SC-011).
 *
 * R8 layout — a sectioned hierarchy instead of a wall; ONE search surface
 * (the R7 research tiers — the legacy "Web search" section is gone, its
 * Exa key and custom SearXNG URL folded into the tier details):
 *
 *   Settings
 *   [jump nav: AI Providers · Research · Region & locale ·
 *              Interface · Keybindings · Advanced]
 *   ── AI Providers ──────────────────────────────────────────────
 *      key rows (fixed-slot right cluster, so status text and buttons
 *      align row to row) · defaults (agent/provider/model) · order
 *   ── Research ──────────────────────────────────────────────────
 *      search tiers (t1 keyless · t2 SearXNG + custom URL ·
 *      t3 BYOK: OpenRouter hosted or Exa direct) · deep research ·
 *      hardware & local models
 *   ── Region & locale ───────────────────────────────────────────
 *   ── Interface ─────────────────────────────────────────────────
 *      command palette · starter cockpit · appearance
 *   ── Keybindings ───────────────────────────────────────────────
 *   ── Advanced ──────────────────────────────────────────────────
 *      integrations · layouts · modules · export/import · about
 *
 * Rows share ONE primitive (32px-control SettingRow inside a single bordered
 * card with hairline dividers — never a card per row); toggles are readable
 * switches, never 8px checkboxes. Every pre-R7 setting stays reachable and
 * its store wiring is untouched. Opened from the toolbar gear, the
 * `platform.open-settings` command, or the onboarding banner. Wired into the
 * platform module as `panelComponents["settings-panel"]`.
 */
export const SettingsPanel: FunctionComponent = () => {
  return (
    // Single scroll container: the root clips at the painted charcoal box
    // (`overflow-hidden`) so over-scroll never reveals the WKWebView backdrop
    // (the "blue void"), and the one inner `overflow-y-auto` is the only
    // scrollbar — fixes the double-scrollbar-into-void (map-settings 3a).
    <div className="bg-charcoal-900 flex h-full w-full flex-col overflow-hidden">
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto flex max-w-2xl flex-col gap-12 p-6 pb-12">
          <header className="flex flex-col gap-3">
            <div>
              <h1 className="text-charcoal-100 text-overview flex items-center gap-2">
                <Sliders className="text-charcoal-300 size-5" aria-hidden="true" />
                Settings
              </h1>
              <p className="text-charcoal-400 text-caption mt-1">
                Local-first &amp; bring-your-own-keys. Nothing leaves this machine except calls you
                make to providers you configure.
              </p>
            </div>
            <SectionNav />
          </header>
          <ProvidersSection />
          <ResearchSection />
          <RegionSection />
          <InterfaceSection />
          <KeybindingsSection />
          <AdvancedSection />
        </div>
      </div>
    </div>
  );
};

SettingsPanel.displayName = "SettingsPanel";

// ---------------------------------------------------------------------------
// Section scaffolding
// ---------------------------------------------------------------------------

const SECTION_NAV: { id: string; label: string }[] = [
  { id: "settings-providers", label: "AI Providers" },
  { id: "settings-research", label: "Research" },
  { id: "settings-region", label: "Region & locale" },
  { id: "settings-interface", label: "Interface" },
  { id: "settings-keybindings", label: "Keybindings" },
  { id: "settings-advanced", label: "Advanced" },
];

/** Jump chips under the page head — the cure for the settings wall. */
function SectionNav() {
  return (
    <nav aria-label="Settings sections" className="flex flex-wrap gap-2">
      {SECTION_NAV.map(({ id, label }) => (
        <button
          key={id}
          type="button"
          onClick={() =>
            document.getElementById(id)?.scrollIntoView?.({ behavior: "smooth", block: "start" })
          }
          className="border-charcoal-700 text-charcoal-400 hover:text-charcoal-100 hover:bg-charcoal-875 rounded-control text-micro h-6 border px-3 whitespace-nowrap"
        >
          {label}
        </button>
      ))}
    </nav>
  );
}

/** A top-level section head — section-size title over a hairline rule. */
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
    <header className="border-charcoal-800 mb-4 border-b pb-3">
      <h2 id={id} className="text-charcoal-100 text-section flex scroll-mt-6 items-center gap-2">
        {icon}
        {title}
      </h2>
      {hint && <p className="text-charcoal-400 text-caption mt-1">{hint}</p>}
    </header>
  );
}

/** A micro group header above a card, inside a section. */
function GroupLabel({ label, hint }: { label: string; hint?: string }) {
  return (
    <div className="mb-2">
      <p className="text-charcoal-500 text-micro">{label}</p>
      {hint && <p className="text-charcoal-400 text-caption mt-1">{hint}</p>}
    </div>
  );
}

/** ONE bordered card per group; rows divide with hairlines (never card-per-row). */
function Card({ className, children }: { className?: string; children: React.ReactNode }) {
  return (
    <div
      className={cn(
        "border-charcoal-700 divide-charcoal-800 flex flex-col divide-y rounded-none border",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** The one labelled setting row: label + hint left, a 32px-ladder control right.
 *  Declares its collapse step (R8 §3.4): when the row starves (≈360px panel),
 *  the control wraps BELOW the label as a unit, right-aligned — labels never
 *  crush against a fixed-width control, nothing overlaps. */
function SettingRow({
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
    <div className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-charcoal-100 text-body flex items-center gap-2">
          {icon}
          {label}
        </span>
        {hint && <span className="text-charcoal-400 text-caption mt-1">{hint}</span>}
      </div>
      <div className="ml-auto shrink-0">{children}</div>
    </div>
  );
}

/**
 * A readable monochrome switch (replaces the 8px `size-4` checkboxes). The real
 * checkbox stays in the tree (`sr-only`, `role="switch"`) so assistive tech and
 * the existing tests keep their contract; the visible track/thumb are styled
 * spans driven by `peer-checked`.
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

/** A labelled switch row inside a card. */
function ToggleRow({
  label,
  hint,
  checked,
  disabled,
  onChange,
  switchLabel,
}: {
  label: React.ReactNode;
  hint?: React.ReactNode;
  checked: boolean;
  disabled?: boolean;
  onChange: (next: boolean) => void;
  /** Accessible name for the switch (defaults to the visible label). */
  switchLabel: string;
}) {
  return (
    <div className="flex min-h-8 items-center justify-between gap-4 px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-charcoal-100 text-body">{label}</span>
        {hint && <span className="text-charcoal-400 text-caption mt-1">{hint}</span>}
      </div>
      <ToggleSwitch
        checked={checked}
        disabled={disabled}
        onChange={onChange}
        aria-label={switchLabel}
      />
    </div>
  );
}

/** Shared 32px-ladder text input styling (inset fill, 1px border). */
const inputClass =
  "border-charcoal-700 bg-charcoal-850 text-charcoal-100 placeholder:text-charcoal-500 rounded-control text-body focus:border-charcoal-500 h-8 border px-3 outline-none";

/**
 * Shared `<select>` styling for the preferences controls. `appearance-none`
 * strips the WKWebView OS-default chrome (so the neutral chevron below shows
 * through); `pr-6` reserves room for that chevron.
 */
const selectClass =
  "border-charcoal-700 bg-charcoal-850 text-charcoal-100 h-8 min-w-[12rem] appearance-none rounded-control border pr-6 pl-3 text-body outline-none focus:border-charcoal-500";

/**
 * A `<select>` wrapped in a `relative` container with a neutral chevron overlay
 * — the chevron replaces the suppressed native control glyph (`appearance-none`).
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

// ---------------------------------------------------------------------------
// AI Providers (BYOK keys + defaults + preference order)
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
      <div className="flex flex-col gap-6">
        <Card>
          {providers.map((provider) => {
            const keyState = status[provider.id] ?? "missing";
            const configured = keyState === "configured";
            const isDefault = defaultProviderId === provider.id;
            const needsKey = provider.requiresKey;
            return (
              <div
                key={provider.id}
                // Collapse order (R8 §3.4): at narrow widths the control
                // cluster wraps below the label as ONE unit (ml-auto keeps it
                // right-aligned) — columns stay aligned, nothing overlaps.
                className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3"
              >
                <div className="flex min-w-0 flex-col">
                  <span className="text-charcoal-100 text-body truncate">{provider.label}</span>
                  <span className="text-charcoal-400 text-caption mt-1 flex min-w-0 items-center gap-2">
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
                {/* Fixed-width slots so the cluster aligns row to row — a row
                    missing a control renders its slot empty, never collapses. */}
                <div className="ml-auto flex shrink-0 items-center gap-3">
                  <span className="flex w-20 justify-end">
                    {isDefault ? (
                      <span className="text-micro rounded-control bg-charcoal-850 text-charcoal-300 px-2 py-1 whitespace-nowrap">
                        default
                      </span>
                    ) : (
                      // Picking a default is a free preference (no key
                      // precondition), so it shows on every non-default row —
                      // not just the one provider that happens to need no key
                      // (regression-95 BUG-3).
                      <button
                        type="button"
                        onClick={() => {
                          setDefaultProviderId(provider.id);
                          // Persist immediately (into the autosave slot) so the
                          // choice survives relaunch even without a layout change.
                          void autosaveLayout();
                        }}
                        // R8 §3.5: a button label never wraps to two lines —
                        // "Set default" stays one line in its fixed w-20 slot.
                        className="text-micro text-charcoal-400 hover:text-charcoal-100 rounded-control h-6 px-1 whitespace-nowrap"
                      >
                        Set default
                      </button>
                    )}
                  </span>
                  <span className="flex w-28 justify-end">
                    {needsKey && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setDialogProvider(provider.id)}
                      >
                        <KeyRound className="size-3" aria-hidden="true" />
                        {configured ? "Update key" : "Add key"}
                      </Button>
                    )}
                  </span>
                  <span className="flex w-12 justify-end">
                    {needsKey && configured && (
                      <button
                        type="button"
                        aria-label={`Remove ${provider.label} key`}
                        onClick={() => void handleRemove(provider.id)}
                        className="text-charcoal-400 hover:text-negative rounded-control p-2"
                      >
                        <Trash2 className="size-3.5" aria-hidden="true" />
                      </button>
                    )}
                  </span>
                </div>
              </div>
            );
          })}
        </Card>

        <DefaultsGroup />
        <ProviderOrderGroup />
      </div>
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

/** Default agent / provider / model — the copilot's starting line-up. */
function DefaultsGroup() {
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

  useEffect(() => {
    void refreshAgents();
  }, [refreshAgents]);

  const agents: AgentSummary[] = [...firstParty, ...custom];
  const providerLabel = (id: LLMProviderId) => providers.find((p) => p.id === id)?.label ?? id;
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
    <div>
      <GroupLabel label="Defaults" hint="The persona, provider, and model the copilot starts on." />
      <Card>
        <SettingRow
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
        </SettingRow>

        <SettingRow
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
        </SettingRow>

        <SettingRow
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
        </SettingRow>
      </Card>
    </div>
  );
}

/** Provider preference order — the order providers are offered in pickers. */
function ProviderOrderGroup() {
  const providers = useLLMProvidersStore((s) => s.providers);
  const providerPreferenceOrder = useSettingsStore((s) => s.providerPreferenceOrder);
  const moveProviderPreference = useSettingsStore((s) => s.moveProviderPreference);

  const providerLabel = (id: LLMProviderId) => providers.find((p) => p.id === id)?.label ?? id;
  // Union the persisted order with the live providers so a provider added in a
  // later release still appears (appended), and a stale id drops off.
  const liveIds = new Set(providers.map((p) => p.id));
  const orderedProviderIds: LLMProviderId[] = [
    ...providerPreferenceOrder.filter((id) => liveIds.has(id)),
    ...providers.map((p) => p.id).filter((id) => !providerPreferenceOrder.includes(id)),
  ];

  return (
    <div>
      <GroupLabel
        label="Provider preference order"
        hint="The order providers are offered in pickers. Reorder to surface the ones you reach for first."
      />
      <Card>
        {orderedProviderIds.map((id, idx) => (
          <div key={id} className="flex min-h-8 items-center justify-between gap-4 px-4 py-2">
            <span className="text-charcoal-100 text-body flex items-center gap-2">
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
          </div>
        ))}
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Research (deep research + hardware capability)
// ---------------------------------------------------------------------------

/** One scored model row — a verdict chip + the reason. */
function FitRow({ model }: { model: ScoredModel }) {
  const meta = verdictMeta(model.verdict);
  return (
    <li className="flex min-h-8 items-center justify-between gap-4 px-4 py-2">
      <div className="min-w-0">
        <div className="text-charcoal-200 text-caption truncate">{model.name}</div>
        <div className="text-charcoal-500 text-caption truncate">{model.reason}</div>
      </div>
      <span className={cn("text-caption shrink-0 font-semibold", meta.className)}>
        {meta.label}
      </span>
    </li>
  );
}

// ---- R7 research search tiers (Track S) ------------------------------------

/** One T1 keyless engine's live breaker state (`GET /search/status` wire shape). */
interface T1EngineStatus {
  id: string;
  label: string;
  state: string;
  cooldown_remaining_s: number;
  detail: string;
}

/** The T1 tier-status payload — mirrors `sidecar/services/search/keyless.tier_status`. */
interface T1TierStatus {
  tier: string;
  available: boolean;
  engines: T1EngineStatus[];
}

/** Fetch the live T1 per-engine status, or `null` when the sidecar is unreachable. */
async function fetchT1TierStatus(): Promise<T1TierStatus | null> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL("/search/status", base).toString());
    if (!resp.ok) {
      return null;
    }
    return (await resp.json()) as T1TierStatus;
  } catch {
    return null;
  }
}

/**
 * Format the T1 per-engine status line — "DuckDuckGo — cooling down 24s ·
 * Brave — ok · Mojeek — ok". Honest per engine: `open` breaker = cooling down
 * with the remaining seconds, `half_open` = probing, else ok. Exported so the
 * formatting contract is locked by tests.
 */
export function t1EngineStatusLine(engines: T1EngineStatus[]): string {
  return engines
    .map((engine) => {
      if (engine.state === "open") {
        return `${engine.label} — cooling down ${Math.max(0, Math.round(engine.cooldown_remaining_s))}s`;
      }
      if (engine.state === "half_open") {
        return `${engine.label} — probing`;
      }
      return `${engine.label} — ok`;
    })
    .join(" · ");
}

/** Poll cadence for the T1 status line while the tier is selected and visible. */
const T1_STATUS_POLL_MS = 20_000;

/** The live T1 per-engine status line — tertiary text, polled every ~20s. */
function T1StatusLine() {
  const [status, setStatus] = useState<T1TierStatus | null | "loading">("loading");

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      // Skip the fetch while the window is hidden — the poll exists for a
      // visible status line, not background traffic.
      if (typeof document !== "undefined" && document.hidden) {
        return;
      }
      const next = await fetchT1TierStatus();
      if (alive) {
        setStatus(next);
      }
    };
    void tick();
    const interval = setInterval(() => void tick(), T1_STATUS_POLL_MS);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, []);

  if (status === "loading") {
    return <p className="text-charcoal-500 text-caption">Checking engine status…</p>;
  }
  if (status === null) {
    return (
      <p className="text-charcoal-500 text-caption">
        Engine status unavailable (sidecar not connected).
      </p>
    );
  }
  return (
    <p className="text-charcoal-500 text-caption" data-testid="t1-engine-status">
      {status.engines.length > 0 ? t1EngineStatusLine(status.engines) : "No engines reported."}
      {!status.available && (
        <span className="text-warning">
          {" "}
          All engines are cooling down — searches resume when the first recovers.
        </span>
      )}
    </p>
  );
}

/** The managed-SearXNG status payload — mirrors `searxng_manager.snapshot()`. */
interface SearxngStatus {
  state: string;
  detail: string | null;
  reason: string | null;
  port: number | null;
  url: string | null;
}

/** Fetch the T2 state machine's status, or `null` when the sidecar is unreachable. */
async function fetchSearxngStatus(): Promise<SearxngStatus | null> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL("/search/searxng/status", base).toString());
    if (!resp.ok) {
      return null;
    }
    return (await resp.json()) as SearxngStatus;
  } catch {
    return null;
  }
}

/** POST a T2 action (setup begins/retries; teardown removes); returns the new status. */
async function postSearxngAction(action: "setup" | "teardown"): Promise<SearxngStatus | null> {
  try {
    const base = await getSidecarBaseUrl();
    const resp = await fetch(new URL(`/search/searxng/${action}`, base).toString(), {
      method: "POST",
    });
    if (!resp.ok) {
      return null;
    }
    return (await resp.json()) as SearxngStatus;
  } catch {
    return null;
  }
}

/** Poll cadence while the T2 setup is in a transition state (pulling/starting). */
const SEARXNG_TRANSITION_POLL_MS = 3_000;

/**
 * The T2 guided one-click flow, driven VERBATIM off the sidecar state machine:
 * not_installed_docker → explain + install hint (plain-text URL, no external
 * nav); docker_present_not_setup → [Set up]; pulling/starting → progress
 * (poll ~3s); ready → green OK + [Remove]; error → reason + [Retry].
 */
function SearxngGuidedFlow() {
  const [status, setStatus] = useState<SearxngStatus | null | "loading">("loading");
  const [busy, setBusy] = useState(false);

  const state = status !== null && status !== "loading" ? status.state : null;
  const transitional = state === "pulling" || state === "starting";

  useEffect(() => {
    let alive = true;
    void fetchSearxngStatus().then((next) => {
      if (alive) {
        setStatus(next);
      }
    });
    return () => {
      alive = false;
    };
  }, []);

  // While the setup is pulling/starting, follow progress on a ~3s poll.
  useEffect(() => {
    if (!transitional) {
      return;
    }
    let alive = true;
    const interval = setInterval(() => {
      void fetchSearxngStatus().then((next) => {
        if (alive && next) {
          setStatus(next);
        }
      });
    }, SEARXNG_TRANSITION_POLL_MS);
    return () => {
      alive = false;
      clearInterval(interval);
    };
  }, [transitional]);

  async function runAction(action: "setup" | "teardown") {
    setBusy(true);
    try {
      const next = await postSearxngAction(action);
      setStatus(next ?? (await fetchSearxngStatus()));
    } finally {
      setBusy(false);
    }
  }

  if (status === "loading") {
    return <p className="text-charcoal-500 text-caption">Checking Docker…</p>;
  }
  if (status === null) {
    return (
      <p className="text-charcoal-500 text-caption">
        SearXNG status unavailable (sidecar not connected).
      </p>
    );
  }

  switch (status.state) {
    case "not_installed_docker":
      return (
        <div className="flex flex-col gap-1">
          <p className="text-charcoal-300 text-caption">
            SearXNG runs in a local Docker container, and Docker isn&rsquo;t available on this
            machine.
          </p>
          {/* Plain-text install hint — deliberately NOT a link (no external nav). */}
          <p className="text-charcoal-500 text-caption">
            Install Docker first — docs.docker.com/get-started/get-docker — then setup from here is
            one click.
          </p>
        </div>
      );
    case "docker_present_not_setup":
      return (
        <div className="flex items-center justify-between gap-4">
          <p className="text-charcoal-300 text-caption">
            Docker is ready. One click pulls the SearXNG image and starts a private local instance —
            searches then route through it automatically.
          </p>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void runAction("setup")}
          >
            Set up
          </Button>
        </div>
      );
    case "pulling":
      return (
        <p className="text-charcoal-300 text-caption" role="status">
          Pulling the SearXNG image…{" "}
          <span className="text-charcoal-500">
            {status.detail ?? "first run can take a few minutes"}
          </span>
        </p>
      );
    case "starting":
      return (
        <p className="text-charcoal-300 text-caption" role="status">
          Starting the instance…{" "}
          <span className="text-charcoal-500">{status.detail ?? "almost there"}</span>
        </p>
      );
    case "ready":
      return (
        <div className="flex items-center justify-between gap-4">
          <p className="text-positive text-caption flex min-w-0 items-center gap-1">
            <Check className="size-3 shrink-0" aria-hidden="true" />
            <span className="truncate">
              SearXNG is running{status.url ? ` at ${status.url}` : ""} — research searches use it
              automatically.
            </span>
          </p>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void runAction("teardown")}
          >
            <Trash2 className="size-3" aria-hidden="true" />
            Remove
          </Button>
        </div>
      );
    case "error":
      return (
        <div className="flex items-center justify-between gap-4">
          <p className="text-negative text-caption min-w-0" role="alert">
            Setup failed: {status.reason ?? "unknown error"}
          </p>
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void runAction("setup")}
          >
            <RotateCcw className="size-3" aria-hidden="true" />
            Retry
          </Button>
        </div>
      );
    default:
      // An unknown state (newer sidecar) — show it honestly rather than guessing.
      return (
        <p className="text-charcoal-500 text-caption">
          SearXNG state: {status.state}
          {status.detail ? ` — ${status.detail}` : ""}
        </p>
      );
  }
}

/** The t3 hosted engines — Firecrawl default (free credits), Exa per-request. */
const HOSTED_ENGINE_OPTIONS: {
  id: HostedSearchEngine;
  label: string;
  costLine: string;
}[] = [
  {
    id: "firecrawl",
    label: "Firecrawl",
    costLine:
      "The default engine. Starts on free credits; after those, each search bills through your OpenRouter account.",
  },
  {
    id: "exa",
    label: "Exa",
    costLine:
      "Exa bills ~$0.005 per search through your OpenRouter account — a documented rate that can drift.",
  },
];

/**
 * The t3 BYOK sub-mode picker: hosted via OpenRouter (engine + key presence)
 * or "Exa direct" (the user's own Exa API key, riding the legacy `byok-exa`
 * wire lane the sidecar maps onto the Exa backend).
 */
function ByokSearchControls() {
  const exaDirect = useSearchSettingsStore((s) => s.exaDirect);
  const setExaDirect = useSearchSettingsStore((s) => s.setExaDirect);

  return (
    <div className="flex flex-col gap-3">
      <div
        role="radiogroup"
        aria-label="BYOK search mode"
        className="border-charcoal-700 divide-charcoal-700 rounded-control flex h-8 max-w-xs divide-x overflow-hidden border"
      >
        <button
          type="button"
          role="radio"
          aria-checked={!exaDirect}
          onClick={() => setExaDirect(false)}
          className={cn(
            "text-micro flex-1 px-3 whitespace-nowrap",
            !exaDirect
              ? "bg-charcoal-875 text-lume"
              : "text-charcoal-400 hover:text-charcoal-200 bg-transparent",
          )}
        >
          Via OpenRouter
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={exaDirect}
          onClick={() => setExaDirect(true)}
          className={cn(
            "text-micro flex-1 px-3 whitespace-nowrap",
            exaDirect
              ? "bg-charcoal-875 text-lume"
              : "text-charcoal-400 hover:text-charcoal-200 bg-transparent",
          )}
        >
          Exa direct
        </button>
      </div>
      {exaDirect ? <ExaDirectControls /> : <HostedEngineControls />}
    </div>
  );
}

/**
 * The "Exa direct" key card: the legacy `vysted-search-exa:exa_api_key`
 * keychain slot keeps working — key presence is read straight from the OS
 * keychain (BYOK; never in a store), and the value never enters frontend
 * state beyond the controlled input.
 */
function ExaDirectControls() {
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
    <div className="flex flex-col gap-2">
      <p className="text-charcoal-500 text-caption">
        Searches call Exa&rsquo;s API directly on your own Exa key — no OpenRouter account needed.
        Billed by Exa per search. The key is stored in your OS keychain, never on disk or sent
        anywhere but Exa.
      </p>
      {exaConfigured === null ? (
        // Keychain read in flight — show a quiet checking state instead of
        // briefly flashing the "needs a key" form (which is misleading if a
        // key IS stored).
        <span className="text-charcoal-400 text-caption">Checking…</span>
      ) : exaConfigured ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-positive text-caption flex items-center gap-1">
            <Check className="size-3 shrink-0" aria-hidden="true" />
            Exa key configured — direct searches use it.
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
          {/* Exa direct is the active sub-mode but cannot run without a key —
              say so plainly rather than silently flooring. */}
          <p className="text-warning text-caption">
            Exa direct is selected but needs an Exa API key to run — add one below.
          </p>
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
              className={cn(inputClass, "min-w-0 flex-1")}
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
            <p className="text-negative text-caption" role="alert">
              {exaError}
            </p>
          )}
        </>
      )}
    </div>
  );
}

/** The t3 hosted-search controls: engine segmented control + key presence. */
function HostedEngineControls() {
  const hostedEngine = useSearchSettingsStore((s) => s.hostedEngine);
  const setHostedEngine = useSearchSettingsStore((s) => s.setHostedEngine);
  // Key PRESENCE only — the same keychain probe the AI Providers rows render
  // from (`provider-keys`); the key value never enters frontend state.
  const keyStatus = useProviderKeysStore((s) => s.status.openrouter);
  const refreshOne = useProviderKeysStore((s) => s.refreshOne);

  useEffect(() => {
    void refreshOne("openrouter");
  }, [refreshOne]);

  const active = HOSTED_ENGINE_OPTIONS.find((opt) => opt.id === hostedEngine);

  return (
    <div className="flex flex-col gap-2">
      <div
        role="radiogroup"
        aria-label="Hosted search engine"
        className="border-charcoal-700 divide-charcoal-700 rounded-control flex h-8 max-w-xs divide-x overflow-hidden border"
      >
        {HOSTED_ENGINE_OPTIONS.map((opt) => (
          <button
            key={opt.id}
            type="button"
            role="radio"
            aria-checked={hostedEngine === opt.id}
            onClick={() => setHostedEngine(opt.id)}
            className={cn(
              "text-micro flex-1 px-3 whitespace-nowrap",
              hostedEngine === opt.id
                ? "bg-charcoal-875 text-lume"
                : "text-charcoal-400 hover:text-charcoal-200 bg-transparent",
            )}
          >
            {opt.label}
          </button>
        ))}
      </div>
      <p className="text-charcoal-500 text-caption">{active?.costLine}</p>
      {keyStatus === "configured" ? (
        <p className="text-positive text-caption flex items-center gap-1">
          <Check className="size-3 shrink-0" aria-hidden="true" />
          OpenRouter key configured — hosted searches use it automatically.
        </p>
      ) : keyStatus === "missing" ? (
        <p className="text-warning text-caption">
          No OpenRouter key yet — add one under AI Providers above. Hosted search can&rsquo;t run
          without it.
        </p>
      ) : (
        <p className="text-charcoal-500 text-caption">
          Couldn&rsquo;t check the OS keychain for an OpenRouter key.
        </p>
      )}
    </div>
  );
}

/**
 * The t2 detail: the guided one-click managed flow plus the optional
 * "Advanced" custom-instance URL (empty = managed instance / autodetect).
 */
function SearxngTierDetail() {
  const searxngUrl = useSearchSettingsStore((s) => s.searxngUrl);
  const setSearxngUrl = useSearchSettingsStore((s) => s.setSearxngUrl);

  return (
    <div className="flex flex-col gap-3">
      <SearxngGuidedFlow />
      <div className="flex flex-col gap-1">
        <label htmlFor="settings-searxng-custom-url" className="text-charcoal-500 text-micro">
          Advanced: custom instance URL
        </label>
        <input
          id="settings-searxng-custom-url"
          type="url"
          value={searxngUrl}
          onChange={(e) => setSearxngUrl(e.target.value)}
          placeholder="http://localhost:8080"
          aria-label="SearXNG URL"
          className={cn(inputClass, "w-full max-w-sm")}
        />
        <p className="text-charcoal-500 text-caption">
          Optional. Leave blank to use the managed instance above (or autodetect localhost:8888 /
          :8080). A custom instance must enable the JSON output format and disable the limiter in
          its settings.yml.
        </p>
      </div>
    </div>
  );
}

/** The three research search tiers — names + one-line honest descriptions. */
const RESEARCH_TIER_OPTIONS: {
  id: ResearchTier;
  name: string;
  description: string;
}[] = [
  {
    id: "t1_local",
    name: "Local scraping (keyless)",
    description:
      "Scrapes DuckDuckGo, Brave, and Mojeek directly. Free, zero setup; engines rate-limit, so heavy runs slow down and rotate.",
  },
  {
    id: "t2_searxng",
    name: "Unlimited Research (local SearXNG)",
    description:
      "A managed SearXNG instance in local Docker — private, unmetered searches. Needs Docker on this machine.",
  },
  {
    id: "t3_hosted",
    name: "BYOK search (hosted or Exa direct)",
    description:
      "Your own key: OpenRouter-hosted web search (Firecrawl/Exa) or a direct Exa API key — the most reliable tier, and the only one that costs money per search.",
  },
];

/**
 * The R7 research search-tier picker (Track S): three 32px radio rows, the
 * selected tier expanding its live detail surface — T1's polled per-engine
 * status, T2's guided SearXNG state machine, T3's engine + key controls.
 */
function ResearchTierGroup() {
  const researchTier = useSearchSettingsStore((s) => s.researchTier);
  const setResearchTier = useSearchSettingsStore((s) => s.setResearchTier);

  return (
    <div>
      <GroupLabel
        label="Search tier"
        hint="Where web searches run. The keyless floor needs nothing; SearXNG runs unlimited and local; BYOK runs hosted via OpenRouter or direct on an Exa key."
      />
      <Card>
        <div
          role="radiogroup"
          aria-label="Research search tier"
          className="divide-charcoal-800 flex flex-col divide-y"
        >
          {RESEARCH_TIER_OPTIONS.map((option) => {
            const selected = researchTier === option.id;
            return (
              <div key={option.id}>
                <button
                  type="button"
                  role="radio"
                  aria-checked={selected}
                  onClick={() => setResearchTier(option.id)}
                  className={cn(
                    "flex min-h-8 w-full items-center justify-between gap-4 px-4 py-3 text-left",
                    selected ? "bg-charcoal-875" : "hover:bg-charcoal-875/50",
                  )}
                >
                  <span className="flex min-w-0 flex-col">
                    <span
                      className={cn(
                        "text-body",
                        selected ? "text-charcoal-100" : "text-charcoal-300",
                      )}
                    >
                      {option.name}
                    </span>
                    <span className="text-charcoal-400 text-caption mt-1">
                      {option.description}
                    </span>
                  </span>
                  <span
                    aria-hidden="true"
                    className={cn(
                      "rounded-control size-2 shrink-0",
                      selected ? "bg-charcoal-100" : "border-charcoal-600 border",
                    )}
                  />
                </button>
                {selected && (
                  <div className="border-charcoal-800 border-t px-4 py-3">
                    {option.id === "t1_local" && <T1StatusLine />}
                    {option.id === "t2_searxng" && <SearxngTierDetail />}
                    {option.id === "t3_hosted" && <ByokSearchControls />}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </Card>
    </div>
  );
}

/**
 * Research — how /deep works, plus the device's local-model fit gate.
 *
 * Deep research runs Vysted's own native IterResearch loop on the user's
 * configured model. There is no engine selector: native is the only
 * user-facing engine (the opt-in paid Perplexity backend is agent-selected
 * with its own key, never surfaced here). The hardware report (Track D)
 * detects the device and shows which local models it can run, gating the
 * heavy local paths (FINDINGS §2.5): on a 16 GB M1, local deep-research is
 * honestly marked "remote"; on a 32 GB+ box the same models flip to "runs
 * locally" with no change.
 *
 * R8 (settings-truth): the SEARCH-tier picker at the top is the ONE search
 * settings surface — t1 keyless / t2 managed SearXNG (+ optional custom
 * instance URL) / t3 BYOK (OpenRouter hosted, or "Exa direct" on the user's
 * own Exa key). Persisted in the search-settings bundle; the legacy
 * "Web search" section is gone.
 */
function ResearchSection() {
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
    <section aria-labelledby="settings-research">
      <SectionHeader
        id="settings-research"
        icon={<FlaskConical className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Research"
        hint="Where web searches run, how /deep and 'go deeper' work, and what this machine can run on-device."
      />
      <div className="flex flex-col gap-6">
        <ResearchTierGroup />
        <div>
          <GroupLabel label="Deep research" />
          <Card>
            <p className="text-charcoal-400 text-caption px-4 py-3 leading-relaxed">
              Deep research runs Vysted&rsquo;s own bounded{" "}
              <span className="text-charcoal-200">IterResearch</span> loop on your configured model
              — a multi-round search → read → reflect → synthesize pass that returns a cited brief.
              Always available, no extra key, no extra cost.
            </p>
          </Card>
        </div>

        <div>
          <GroupLabel
            label="Hardware & local models"
            hint="Heavy local paths (local deep-research, large local LLMs) enable only where the hardware earns it; everything else uses the keyless-remote path."
          />
          {report === "loading" && (
            <Card>
              <p className="text-charcoal-500 text-caption px-4 py-3">Detecting device…</p>
            </Card>
          )}
          {report === null && (
            <Card>
              <p className="text-charcoal-500 text-caption px-4 py-3">
                Hardware detection unavailable (sidecar not connected).
              </p>
            </Card>
          )}
          {report && report !== "loading" && (
            <div className="flex flex-col gap-3">
              <Card>
                <div className="px-4 py-3">
                  <div className="text-charcoal-100 text-body flex items-center gap-2">
                    <Cpu className="text-charcoal-300 size-3.5" aria-hidden="true" />
                    {report.device.chip}
                  </div>
                  <div className="text-charcoal-400 text-caption mt-1">
                    {report.device.ramGib} GiB RAM · {report.device.gpuBudgetGib} GiB GPU budget ·{" "}
                    {report.device.perfCores}P/{report.device.totalCores} cores ·{" "}
                    {report.device.osName} {report.device.osVersion}
                  </div>
                </div>
              </Card>
              {report.ollama.models.length > 0 && (
                <div>
                  <GroupLabel label="Installed local models (Ollama)" />
                  <Card>
                    <ul className="divide-charcoal-800 divide-y">
                      {report.ollama.models.map((m) => (
                        <FitRow key={m.name} model={m} />
                      ))}
                    </ul>
                  </Card>
                </div>
              )}
              <div>
                <GroupLabel label="Frontier deep-research models" />
                <Card>
                  <ul className="divide-charcoal-800 divide-y">
                    {report.referenceCandidates.map((m) => (
                      <FitRow key={m.name} model={m} />
                    ))}
                  </ul>
                </Card>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Region & locale
// ---------------------------------------------------------------------------

function RegionSection() {
  const region = useSettingsStore((s) => s.region);
  const setRegion = useSettingsStore((s) => s.setRegion);

  return (
    <section aria-labelledby="settings-region">
      <SectionHeader
        id="settings-region"
        icon={<Globe className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Region & locale"
        hint="Locale used for number formatting — a foundation for region-first data + feeds in a later release."
      />
      <Card>
        {/* Region / locale — Pass A item 8 foundation seam (defaults to US) */}
        <SettingRow label="Region" hint="Defaults to United States.">
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
        </SettingRow>
      </Card>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Interface (command palette · starter cockpit · appearance)
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

/** An ASCII-bracket toggle chip for the starter-cockpit panel picker —
 *  a 32px-ladder control, never an 8px checkbox. */
function StarterChip({
  panelId,
  label,
  checked,
  onChange,
}: {
  panelId: string;
  label: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label
      data-panel-id={panelId}
      title={label}
      className={cn(
        "rounded-control text-caption flex h-8 min-w-0 cursor-pointer items-center gap-2 border px-3 select-none",
        checked
          ? "border-charcoal-600 bg-charcoal-875 text-charcoal-100"
          : "border-charcoal-700 text-charcoal-400 hover:text-charcoal-200",
      )}
    >
      <input
        type="checkbox"
        aria-label={`Starter cockpit: ${label}`}
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="sr-only"
      />
      <span aria-hidden="true" className={checked ? "text-charcoal-300" : "text-charcoal-500"}>
        {checked ? "[x]" : "[ ]"}
      </span>
      <span className="truncate">{label}</span>
    </label>
  );
}

function InterfaceSection() {
  const paletteRecentsEnabled = useSettingsStore((s) => s.paletteRecentsEnabled);
  const setPaletteRecentsEnabled = useSettingsStore((s) => s.setPaletteRecentsEnabled);
  const paletteScopedToPanel = useSettingsStore((s) => s.paletteScopedToPanel);
  const setPaletteScopedToPanel = useSettingsStore((s) => s.setPaletteScopedToPanel);
  const starterCockpitPanelIds = useSettingsStore((s) => s.starterCockpitPanelIds);
  const toggleStarterCockpitPanel = useSettingsStore((s) => s.toggleStarterCockpitPanel);
  const themeKnobs = useSettingsStore((s) => s.themeKnobs);
  const setThemeKnobs = useSettingsStore((s) => s.setThemeKnobs);

  return (
    <section aria-labelledby="settings-interface">
      <SectionHeader
        id="settings-interface"
        icon={<LayoutPanelLeft className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Interface"
        hint="How the command palette, your first-run cockpit, and the dark language behave. These travel with Export / Import below."
      />
      <div className="flex flex-col gap-6">
        <div>
          <GroupLabel label="Command palette" />
          <Card>
            <ToggleRow
              label="Show recent commands"
              checked={paletteRecentsEnabled}
              onChange={setPaletteRecentsEnabled}
              switchLabel="Show recent commands"
            />
            <ToggleRow
              label="Scope to the focused panel first"
              checked={paletteScopedToPanel}
              onChange={setPaletteScopedToPanel}
              switchLabel="Scope to the focused panel first"
            />
          </Card>
        </div>

        {/* Starter-cockpit composition (FR-032) */}
        <div>
          <GroupLabel
            label="Starter cockpit"
            hint="The panels that open on first run, before you save your own layout."
          />
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(STARTER_PANEL_LABELS).map(([panelId, label]) => (
              <StarterChip
                key={panelId}
                panelId={panelId}
                label={label}
                checked={starterCockpitPanelIds.includes(panelId)}
                onChange={(next) => toggleStarterCockpitPanel(panelId, next)}
              />
            ))}
          </div>
        </div>

        {/* Theme knobs (dark-only) */}
        <div>
          <GroupLabel
            label="Appearance"
            hint="Vysted is dark-only by design. These tune the dark language."
          />
          <Card>
            <SettingRow label="Accent intensity">
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
            </SettingRow>
            <SettingRow label="Density">
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
            </SettingRow>
          </Card>
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
          className="border-warning/40 bg-warning/10 text-warning text-caption mb-4 flex items-start gap-2 rounded-none border px-3 py-2"
        >
          <AlertTriangle className="mt-1 size-3.5 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-medium">Conflicting bindings detected</p>
            {conflictList.map((c) => (
              <p key={c.keys} className="text-warning/90 mt-1">
                <span>{formatBinding(c.keys)}</span> is bound to{" "}
                {c.actionIds.map((id) => DEFAULT_KEYBINDINGS[id]?.label ?? id).join(" and ")}.
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-6">
        {CATEGORY_ORDER.map(({ id: category, label }) => {
          const group = entries.filter((e) => e.def.category === category);
          if (group.length === 0) {
            return null;
          }
          return (
            <div key={category}>
              <GroupLabel label={label} />
              <Card>
                {group.map(({ actionId, def, combo }) => {
                  const isRecording = recording === actionId;
                  const isOverridden = actionId in overrides;
                  const conflicted = conflictedActionIds.has(actionId);
                  return (
                    <div
                      key={actionId}
                      className={cn(
                        // Collapse order (R8 §3.4): the kbd/record cluster
                        // wraps below the label as a unit at narrow widths.
                        "flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3",
                        conflicted && "border-warning/50 border-l-2",
                      )}
                    >
                      <div className="flex min-w-0 flex-col">
                        <span className="text-charcoal-100 text-body">{def.label}</span>
                        <span className="text-charcoal-400 text-caption mt-1 truncate">
                          {def.description}
                        </span>
                      </div>
                      <div className="ml-auto flex shrink-0 items-center gap-2">
                        <kbd
                          aria-label={`${def.label} binding`}
                          className={cn(
                            // §3.5: the combo (or the recording prompt) never
                            // wraps inside the fixed-height chip.
                            "border-charcoal-700 bg-charcoal-850 rounded-control text-caption flex h-6 items-center border px-2 whitespace-nowrap",
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
                            "text-micro rounded-control h-6 px-2",
                            isRecording
                              ? "bg-charcoal-875 text-charcoal-200"
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
                    </div>
                  );
                })}
              </Card>
            </div>
          );
        })}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Advanced (integrations · layouts · modules · export/import · about)
// ---------------------------------------------------------------------------

function AdvancedSection() {
  return (
    <section aria-labelledby="settings-advanced">
      <SectionHeader
        id="settings-advanced"
        icon={<Package className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Advanced"
        hint="Broker integrations, saved layouts, module toggles, and settings portability."
      />
      <div className="flex flex-col gap-8">
        <IntegrationsSection />
        <LayoutsSection />
        <ModulesSection />
        <ExportImportSection />
        <AboutSection />
      </div>
    </section>
  );
}

/** A subsection head inside Advanced — title-size, still an aria region. */
function SubsectionHeader({ id, icon, title, hint }: Parameters<typeof SectionHeader>[0]) {
  return (
    <header className="mb-2">
      <h3 id={id} className="text-charcoal-100 text-panel-title flex items-center gap-2">
        {icon}
        {title}
      </h3>
      {hint && <p className="text-charcoal-400 text-caption mt-1">{hint}</p>}
    </header>
  );
}

function IntegrationsSection() {
  const openPanel = useWorkspaceStore((s) => s.openPanel);

  return (
    <section aria-labelledby="settings-integrations">
      <SubsectionHeader
        id="settings-integrations"
        icon={<Network className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Integrations"
        hint="Connect a broker for read-only positions, holdings & P&L the copilot can analyse over your real account."
      />
      <Card>
        <div className="flex min-h-8 items-center justify-between gap-4 px-4 py-3">
          <span className="text-charcoal-400 text-caption">
            Broker connections are managed in the Marketplace.
          </span>
          <Button size="sm" variant="outline" onClick={() => openPanel("marketplace-panel")}>
            Open Marketplace
          </Button>
        </div>
      </Card>
    </section>
  );
}

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
      <SubsectionHeader
        id="settings-layouts"
        icon={<LayoutPanelLeft className="text-charcoal-300 size-4" aria-hidden="true" />}
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
          className={cn(inputClass, "flex-1")}
        />
        <Button type="submit" size="sm" variant="outline" disabled={busy || newName.trim() === ""}>
          Save
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={() => void resetLayout()}>
          Reset to default
        </Button>
      </form>
      {error && <p className="text-negative text-caption mb-2">{error}</p>}
      {names === null ? (
        <p className="text-charcoal-400 text-caption">Loading layouts…</p>
      ) : names.length === 0 ? (
        <p className="text-charcoal-400 text-caption">
          No saved layouts yet — arrange your panels and save above.
        </p>
      ) : (
        <Card>
          {names.map((name) => (
            <div key={name} className="flex min-h-8 items-center justify-between gap-4 px-4 py-2">
              <span className="text-charcoal-100 text-body truncate">
                {name}
                {name === activeName && (
                  <span className="text-micro text-charcoal-500 ml-2">active</span>
                )}
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => void withBusy(() => loadWorkspace(name))}
                  className="text-micro text-charcoal-300 hover:text-charcoal-100 rounded-control h-6 px-1"
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
            </div>
          ))}
        </Card>
      )}
      <p className="text-charcoal-500 text-caption mt-2">
        Autosave slot: {AUTOSAVE_LAYOUT_NAME} (hidden; restored on launch)
      </p>
    </section>
  );
}

function ModulesSection() {
  const modules = useModulesStore((state) => state.modules);
  const enabled = useModulesStore((state) => state.enabled);
  const setModuleEnabled = useModulesStore((state) => state.setModuleEnabled);

  return (
    <section aria-labelledby="settings-modules">
      <SubsectionHeader
        id="settings-modules"
        icon={<Package className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Modules"
        hint="Disabled modules contribute no panels or ⌘K commands."
      />
      <Card>
        {modules.map((module) => {
          const isPlatform = module.id === PLATFORM_MODULE_ID;
          const isEnabled = enabled[module.id] !== false;
          return (
            <ToggleRow
              key={module.id}
              label={module.title}
              hint={
                <>
                  {module.panels.length} panel{module.panels.length === 1 ? "" : "s"} ·{" "}
                  {module.commands.length} command{module.commands.length === 1 ? "" : "s"}
                  {isPlatform ? " · always on" : ""}
                </>
              }
              checked={isEnabled}
              disabled={isPlatform}
              onChange={(next) => {
                if (isPlatform) return;
                setModuleEnabled(module.id, next);
              }}
              switchLabel={`${module.title} enabled`}
            />
          );
        })}
      </Card>
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
      <SubsectionHeader
        id="settings-export"
        icon={<Download className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Export / Import"
        hint="Carry your keybindings and preferences to another machine. Secrets are NEVER exported — re-enter your API keys via the keychain on the new machine."
      />
      <Card>
        <div className="flex flex-col gap-3 px-4 py-3">
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
          <p className="text-charcoal-500 text-caption">
            The export bundles your keybinding remaps and preferences (default agent, provider
            order, palette behaviour, starter cockpit, theme). API keys and broker credentials stay
            in your OS keychain and are never written to the file.
          </p>
          {status && (
            <p
              className={cn(
                "text-caption",
                status.kind === "ok" ? "text-positive" : "text-negative",
              )}
            >
              {status.message}
            </p>
          )}
        </div>
      </Card>
    </section>
  );
}

// ---------------------------------------------------------------------------
// About
// ---------------------------------------------------------------------------

function AboutSection() {
  return (
    <section aria-labelledby="settings-about">
      <SubsectionHeader
        id="settings-about"
        icon={<Info className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="About"
      />
      <Card>
        <div className="text-charcoal-300 text-caption flex flex-col gap-2 px-4 py-3">
          <p>
            Vysted <span className="text-charcoal-500">v{HOST_VERSION}</span> — an open-source,
            AI-native finance terminal.
          </p>
          <p className="text-charcoal-400">
            Plugin architecture · local-first · bring-your-own-keys. Your data, your keys, your
            machine — extend it like an IDE.
          </p>
        </div>
      </Card>
    </section>
  );
}
