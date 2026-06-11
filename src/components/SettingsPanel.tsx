"use client";

import { type FunctionComponent, useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronDown,
  Download,
  KeyRound,
  RotateCcw,
  Trash2,
  Upload,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { KeyEntryDialog } from "@/components/KeyEntryDialog";
import { formatModelLabel } from "@/components/StatusChrome";
import { type Region, REGIONS } from "@/lib/region";
import { cn } from "@/lib/utils";
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
import { useContainerWidth } from "@/lib/use-container-width";
import {
  RESEARCH_MODEL_OPTIONS,
  type ResearchStop,
  useSearchSettingsStore,
} from "@/store/search-settings";
import { type SettingsBundle, useSettingsStore } from "@/store/settings";
import { AUTOSAVE_LAYOUT_NAME, isReservedLayoutName, useWorkspaceStore } from "@/store/workspace";
import type { LLMModelOption, LLMProviderId } from "../../types/ai";

/**
 * Settings — the discoverable control surface (Cursor-grade preferences,
 * FR-037/FR-038/FR-039, SC-011).
 *
 * R9 layout — a sectioned hierarchy instead of a wall; ONE search surface;
 * every control demonstrably round-trips (change → persist → reload →
 * applied) or it does not exist (the R9 settings-truth pass — the dead
 * Interface section and the unread provider-preference-order group died; see
 * the kill list in `verification/R9_DEFECT_CATALOGUE.md`):
 *
 *   Settings
 *   [jump nav: AI Providers · Research · Region & locale ·
 *              Keybindings · Advanced]
 *   ── AI Providers ──────────────────────────────────────────────
 *      key rows (one designed grid, so status text and buttons
 *      align row to row) · defaults (agent/provider/model)
 *   ── Research ──────────────────────────────────────────────────
 *      two tiers (Unlimited (Local) — managed SearXNG · Hosted
 *      research model — OpenRouter per-stop models) ·
 *      hardware & local models
 *   ── Region & locale ───────────────────────────────────────────
 *   ── Keybindings ───────────────────────────────────────────────
 *   ── Advanced ──────────────────────────────────────────────────
 *      integrations · layouts · modules · export/import · about
 *
 * Rows share ONE primitive (32px-control SettingRow inside a single bordered
 * card with hairline dividers — never a card per row); toggles are readable
 * switches, never 8px checkboxes. Opened from the toolbar gear, the
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
          <header className="flex flex-col gap-4">
            <div>
              <h1 className="text-charcoal-100 text-overview">Settings</h1>
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

const ICON_14 = "size-3.5"; // tokens-ok: the law's 14px icon step inside 28/32px controls (R9 §3)

const SECTION_NAV: { id: string; label: string; short: string }[] = [
  { id: "settings-providers", label: "AI Providers", short: "Providers" },
  { id: "settings-research", label: "Research", short: "Research" },
  { id: "settings-region", label: "Region & locale", short: "Region" },
  { id: "settings-keybindings", label: "Keybindings", short: "Keys" },
  { id: "settings-advanced", label: "Advanced", short: "Advanced" },
];

/**
 * Jump-nav collapse ladder (R8 §3.4): full labels → designed short labels →
 * one overflow menu. Steps are deterministic width gates measured on the nav's
 * own container, so chips NEVER wrap to a second line or clip mid-word.
 * Thresholds = the MEASURED chip-row widths (text-micro uppercase JetBrains
 * Mono, h-6, px-3, gap-2 — full row 578px, short row ≈432px) + slack.
 */
const NAV_FULL_MIN_W = 592;
const NAV_SHORT_MIN_W = 440;

/** Smooth-scroll one section head into view. */
function jumpToSection(id: string) {
  document.getElementById(id)?.scrollIntoView?.({ behavior: "smooth", block: "start" });
}

/** Jump chips under the page head — the cure for the settings wall. */
function SectionNav() {
  const { ref, width } = useContainerWidth<HTMLElement>();
  const [menuOpen, setMenuOpen] = useState(false);
  // null width = first paint: render full (overflow law — never the reverse flash).
  const step: "full" | "short" | "overflow" =
    width === null || width >= NAV_FULL_MIN_W
      ? "full"
      : width >= NAV_SHORT_MIN_W
        ? "short"
        : "overflow";

  if (step === "overflow") {
    return (
      <nav ref={ref} aria-label="Settings sections" className="relative flex gap-2">
        <button
          type="button"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen((open) => !open)}
          onBlur={(e) => {
            // Close when focus leaves the nav entirely (a menu item keeps it).
            if (!e.currentTarget.parentElement?.contains(e.relatedTarget)) {
              setMenuOpen(false);
            }
          }}
          className="border-charcoal-700 text-charcoal-400 hover:text-charcoal-100 hover:bg-charcoal-875 rounded-control text-micro h-6 border px-3 whitespace-nowrap"
        >
          Sections ⋯
        </button>
        {menuOpen && (
          <div
            role="menu"
            aria-label="Settings sections menu"
            className="border-charcoal-700 bg-charcoal-900 absolute top-7 left-0 z-10 flex min-w-40 flex-col border py-1"
          >
            {SECTION_NAV.map(({ id, label }) => (
              <button
                key={id}
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  jumpToSection(id);
                }}
                className="text-charcoal-300 hover:text-charcoal-100 hover:bg-charcoal-875 text-caption h-7 px-3 text-left whitespace-nowrap"
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </nav>
    );
  }

  return (
    <nav ref={ref} aria-label="Settings sections" className="flex gap-2">
      {SECTION_NAV.map(({ id, label, short }) => (
        <button
          key={id}
          type="button"
          onClick={() => jumpToSection(id)}
          className="border-charcoal-700 text-charcoal-400 hover:text-charcoal-100 hover:bg-charcoal-875 rounded-control text-micro h-6 border px-3 whitespace-nowrap"
        >
          {step === "full" ? label : short}
        </button>
      ))}
    </nav>
  );
}

/** A top-level section head — section-size title over a hairline rule. Quiet,
 *  Linear-grade: plain text, no decorative icon (hierarchy by size + color). */
function SectionHeader({ id, title, hint }: { id: string; title: string; hint?: string }) {
  return (
    <header className="border-charcoal-800 mb-4 border-b pb-3">
      <h2 id={id} className="text-charcoal-100 text-section scroll-mt-6">
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
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-charcoal-100 text-body">{label}</span>
        {hint && <span className="text-charcoal-400 text-caption mt-1">{hint}</span>}
      </div>
      <div className="ml-auto min-w-0 shrink-0">{children}</div>
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
    // Reference-grade proportions (Linear ≈ 36×20 track): a 20px track with a
    // 16px thumb, vertically centered in a 32px-tall hit area (≥24px target).
    <label
      className={cn(
        "relative inline-flex h-8 w-9 shrink-0 items-center",
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
        className="bg-charcoal-850 border-charcoal-700 peer-checked:bg-charcoal-600 peer-checked:border-charcoal-500 rounded-control h-5 w-9 border transition-colors peer-disabled:opacity-40"
      />
      <span
        aria-hidden="true"
        className="bg-charcoal-400 peer-checked:bg-charcoal-100 rounded-control absolute top-1/2 left-1 size-4 -translate-y-1/2 transition-transform peer-checked:translate-x-3 peer-disabled:opacity-40"
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
        className={cn(
          ICON_14,
          "text-charcoal-400 pointer-events-none absolute top-1/2 right-2 -translate-y-1/2",
        )}
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
                {/* basis-40 makes the wrap REAL on a compressed sliver: with
                    min-w-0 alone the name shrank to nothing while the fixed
                    control cluster overflowed the card (adversarial sweep) —
                    a declared base width forces the cluster onto line two. */}
                <div className="flex min-w-0 grow basis-40 flex-col">
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
                {/* ONE designed grid for every row (D2): fixed-width slots so
                    the default / key / remove columns align row to row — a row
                    missing a control renders its slot empty, never collapses. */}
                <div className="ml-auto flex shrink-0 items-center gap-3">
                  <span className="flex w-16 justify-end">
                    {isDefault ? (
                      // Short form + check state (V4: "SET DEFAULT" never
                      // wraps) — the active default reads as a quiet fact.
                      <span className="text-micro text-charcoal-200 flex h-6 items-center gap-1 whitespace-nowrap">
                        <Check className="size-3 shrink-0" aria-hidden="true" />
                        Default
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
                        aria-label={`Set ${provider.label} as default provider`}
                        // R8 §3.5: a button label never wraps to two lines —
                        // the SAME short form as the active state, one column.
                        className="text-micro text-charcoal-400 hover:text-charcoal-100 rounded-control h-6 px-1 whitespace-nowrap"
                      >
                        Default
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
                        <KeyRound aria-hidden="true" />
                        {configured ? "Update key" : "Add key"}
                      </Button>
                    )}
                  </span>
                  <span className="flex w-8 justify-end">
                    {needsKey && configured && (
                      <button
                        type="button"
                        aria-label={`Remove ${provider.label} key`}
                        onClick={() => void handleRemove(provider.id)}
                        className="text-charcoal-400 hover:text-negative rounded-control p-2"
                      >
                        <Trash2 className={ICON_14} aria-hidden="true" />
                      </button>
                    )}
                  </span>
                </div>
              </div>
            );
          })}
        </Card>

        <DefaultsGroup />
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
      : fallbackModelIds.map((id) => ({ id, label: formatModelLabel(id) }));
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
          hint="The persona the chat starts on — applies now and at every launch."
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
                <option value="">Raw chat (no persona)</option>
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

// ---- R9 research tiers (two tiers — built on Team A's store contract) -------

/** The managed-SearXNG status payload — mirrors `searxng_manager.snapshot()`. */
interface SearxngStatus {
  state: string;
  detail: string | null;
  reason: string | null;
  port: number | null;
  url: string | null;
}

/** Fetch the SearXNG state machine's status, or `null` when the sidecar is unreachable. */
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

/** POST a SearXNG action (setup begins/retries; teardown stops + removes). */
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

/** Poll cadence while the SearXNG setup is in a transition state (pulling/starting). */
const SEARXNG_TRANSITION_POLL_MS = 3_000;

/** Designed status-chip vocabulary per sidecar state (the brief's words, not
 *  the wire ids). Exported so the chip contract is locked by tests. */
export function searxngChipMeta(state: string): { label: string; className: string } {
  switch (state) {
    case "not_installed_docker":
      return { label: "Docker not found", className: "text-warning border-warning/40" };
    case "docker_present_not_setup":
      return { label: "Not set up", className: "text-charcoal-400 border-charcoal-700" };
    case "pulling":
      return { label: "Pulling", className: "text-charcoal-200 border-charcoal-600" };
    case "starting":
      return { label: "Starting", className: "text-charcoal-200 border-charcoal-600" };
    case "ready":
      return { label: "Ready", className: "text-positive border-positive/40" };
    case "error":
      return { label: "Error", className: "text-negative border-negative/40" };
    default:
      // An unknown state (newer sidecar) — name it honestly rather than guessing.
      return { label: state, className: "text-charcoal-400 border-charcoal-700" };
  }
}

/** The live status chip — micro-text, hairline border, state-keyed color. */
function SearxngStatusChip({ state }: { state: string }) {
  const meta = searxngChipMeta(state);
  return (
    <span
      data-testid="searxng-status-chip"
      className={cn(
        "text-micro rounded-control flex h-6 shrink-0 items-center border px-2 whitespace-nowrap",
        meta.className,
      )}
    >
      {meta.label}
    </span>
  );
}

/**
 * Tier A's managed-SearXNG flow, driven VERBATIM off the sidecar state
 * machine: a status chip + a container-health line + ONE primary action per
 * state (Set up → Stop; Retry on error; nothing while pulling/starting), the
 * Docker-missing state with honest copy (plain-text install hint, no external
 * nav), and — whenever the instance is not READY — the quiet truth line that
 * research is riding the limited keyless fallback meanwhile.
 */
function SearxngManagedFlow() {
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

  /** The quiet not-ready truth line (brief D1). */
  const fallbackNote = (
    <p className="text-charcoal-500 text-caption">
      Until set up, research uses limited keyless search.
    </p>
  );

  if (status === "loading") {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-charcoal-500 text-caption">Checking Docker…</p>
        {fallbackNote}
        <SearxngAdvancedUrl />
      </div>
    );
  }
  if (status === null) {
    return (
      <div className="flex flex-col gap-2">
        <p className="text-charcoal-500 text-caption">
          SearXNG status unavailable (sidecar not connected).
        </p>
        {fallbackNote}
        <SearxngAdvancedUrl />
      </div>
    );
  }

  // ONE primary action per state (brief D1): Set up → Stop; Retry on error.
  let action: { label: string; verb: "setup" | "teardown" } | null = null;
  if (status.state === "docker_present_not_setup") {
    action = { label: "Set up", verb: "setup" };
  } else if (status.state === "ready") {
    action = { label: "Stop", verb: "teardown" };
  } else if (status.state === "error") {
    action = { label: "Retry", verb: "setup" };
  }

  // The container-health line, honest per state.
  let healthLine: React.ReactNode;
  switch (status.state) {
    case "not_installed_docker":
      healthLine = (
        <span>
          SearXNG runs in a local Docker container, and Docker isn&rsquo;t available on this
          machine. {/* Plain-text install hint — deliberately NOT a link (no external nav). */}
          <span className="text-charcoal-500">
            Install Docker first — docs.docker.com/get-started/get-docker — then setup from here is
            one click.
          </span>
        </span>
      );
      break;
    case "docker_present_not_setup":
      healthLine =
        "Docker is ready. One click pulls the SearXNG image and starts a private local instance.";
      break;
    case "pulling":
      healthLine = (
        <span role="status">
          Pulling the SearXNG image…{" "}
          <span className="text-charcoal-500">
            {status.detail ?? "first run can take a few minutes"}
          </span>
        </span>
      );
      break;
    case "starting":
      healthLine = (
        <span role="status">
          Starting the instance…{" "}
          <span className="text-charcoal-500">{status.detail ?? "almost there"}</span>
        </span>
      );
      break;
    case "ready":
      healthLine = (
        <span className="text-positive">
          Running{status.url ? ` at ${status.url}` : ""} — research searches route through it
          automatically.
        </span>
      );
      break;
    case "error":
      healthLine = (
        <span className="text-negative" role="alert">
          Setup failed: {status.reason ?? "unknown error"}
        </span>
      );
      break;
    default:
      healthLine = (
        <span>
          SearXNG state: {status.state}
          {status.detail ? ` — ${status.detail}` : ""}
        </span>
      );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex min-h-8 flex-wrap items-center gap-x-3 gap-y-2">
        <SearxngStatusChip state={status.state} />
        <p className="text-charcoal-300 text-caption min-w-0 flex-1">{healthLine}</p>
        {action && (
          <Button
            size="sm"
            variant="outline"
            disabled={busy}
            onClick={() => void runAction(action.verb)}
          >
            {action.label}
          </Button>
        )}
      </div>
      {status.state !== "ready" && fallbackNote}
      <SearxngAdvancedUrl />
    </div>
  );
}

/**
 * The "Advanced" disclosure for a custom SearXNG instance URL. Kept because it
 * is wired end-to-end (store → `X-Vysted-Searxng-Url` header → sidecar
 * resolution under either tier); collapsed by default so the default flow
 * stays one chip + one button.
 */
function SearxngAdvancedUrl() {
  const searxngUrl = useSearchSettingsStore((s) => s.searxngUrl);
  const setSearxngUrl = useSearchSettingsStore((s) => s.setSearxngUrl);

  return (
    <details className="group">
      <summary className="text-charcoal-500 hover:text-charcoal-300 text-micro cursor-pointer list-none select-none">
        <span aria-hidden="true" className="mr-1 inline-block group-open:hidden">
          ▸
        </span>
        <span aria-hidden="true" className="mr-1 hidden group-open:inline-block">
          ▾
        </span>
        <span>Advanced: custom instance URL</span>
      </summary>
      <div className="mt-2 flex flex-col gap-1">
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
          Optional. Leave blank to use the managed instance above. A custom instance must enable the
          JSON output format and disable the limiter in its settings.yml.
        </p>
      </div>
    </details>
  );
}

/** Friendly per-stop row copy for the Tier B model rows. */
const RESEARCH_STOP_ROWS: { stop: ResearchStop; label: string; hint: string }[] = [
  { stop: "normal", label: "Normal", hint: "Quick checks and single questions." },
  { stop: "deep", label: "Deep", hint: "Multi-step research with reasoning." },
  { stop: "ultra", label: "Ultra", hint: "Exhaustive runs — can take minutes." },
];

/** Option list for one stop: the shared picker + the persisted value if it is
 *  a custom slug that dropped out of the list (never silently deselected). */
function stopOptions(current: string): { id: string; label: string }[] {
  const known = RESEARCH_MODEL_OPTIONS.some((o) => o.id === current);
  const base = RESEARCH_MODEL_OPTIONS.map((o) => ({ id: o.id, label: o.label }));
  return known ? base : [{ id: current, label: formatModelLabel(current) }, ...base];
}

/** One Tier B per-stop model row: stop label + live pricing micro-text left,
 *  the model select right. Pricing renders from Team A's verified constant. */
function ResearchModelRow({
  stop,
  label,
  hint,
}: {
  stop: ResearchStop;
  label: string;
  hint: string;
}) {
  const model = useSearchSettingsStore((s) => s.researchModels[stop]);
  const setResearchModel = useSearchSettingsStore((s) => s.setResearchModel);
  const active = RESEARCH_MODEL_OPTIONS.find((o) => o.id === model);

  return (
    <div className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
      <div className="flex min-w-0 flex-col">
        <span className="text-charcoal-100 text-body">{label}</span>
        <span className="text-charcoal-400 text-caption mt-1">{hint}</span>
        <span className="text-charcoal-500 text-micro mt-1">
          {active
            ? `${active.priceHint}${active.priceVerified ? "" : " · estimate"}`
            : "Custom model — pricing on its OpenRouter page"}
        </span>
      </div>
      <div className="ml-auto shrink-0">
        <Select
          aria-label={`${label} research model`}
          value={model}
          onChange={(e) => setResearchModel(stop, e.target.value)}
        >
          {stopOptions(model).map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>
    </div>
  );
}

/**
 * Tier B's controls: the OpenRouter key state (the SAME keychain probe and
 * entry dialog the AI-Providers rows use — key presence only, never the
 * value), then the three per-stop model rows. With no key there are NO dead
 * selects — the key CTA is the one control (brief D1).
 */
function ResearchModelControls() {
  const keyStatus = useProviderKeysStore((s) => s.status.openrouter);
  const refreshOne = useProviderKeysStore((s) => s.refreshOne);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    void refreshOne("openrouter");
  }, [refreshOne]);

  const keyDialog = (
    <KeyEntryDialog
      open={dialogOpen}
      providerId={dialogOpen ? "openrouter" : null}
      onOpenChange={setDialogOpen}
      onSaved={(id) => void refreshOne(id)}
    />
  );

  if (keyStatus !== "configured") {
    return (
      <div className="flex flex-col gap-2">
        {keyStatus === "unknown" ? (
          <p className="text-charcoal-500 text-caption">
            Couldn&rsquo;t check the OS keychain for an OpenRouter key.
          </p>
        ) : (
          <p className="text-charcoal-400 text-caption">
            Needs your OpenRouter API key — research stays on the local tier until one is added. The
            key lives in your OS keychain, never on disk.
          </p>
        )}
        <div>
          <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
            <KeyRound aria-hidden="true" />
            Add OpenRouter key
          </Button>
        </div>
        {keyDialog}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <p className="text-positive text-caption flex min-w-0 items-center gap-1">
          <Check className="size-3 shrink-0" aria-hidden="true" />
          <span className="truncate">OpenRouter key configured — research bills to it.</span>
        </p>
        <Button size="sm" variant="outline" onClick={() => setDialogOpen(true)}>
          Update key
        </Button>
      </div>
      <div className="border-charcoal-700 divide-charcoal-800 -mx-4 -mb-3 divide-y border-t">
        {RESEARCH_STOP_ROWS.map(({ stop, label, hint }) => (
          <ResearchModelRow key={stop} stop={stop} label={label} hint={hint} />
        ))}
      </div>
      {keyDialog}
    </div>
  );
}

/** One research-tier card: a radio-clear header (dot + name + two-line
 *  explanation) over the tier's always-visible controls — the V9 cure: the
 *  tier surface IS the controls, nothing hides behind the selection. */
function TierCard({
  selected,
  name,
  description,
  onSelect,
  children,
}: {
  selected: boolean;
  name: string;
  description: string;
  onSelect: () => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-none border",
        selected ? "border-charcoal-600" : "border-charcoal-700",
      )}
    >
      <button
        type="button"
        role="radio"
        aria-checked={selected}
        onClick={onSelect}
        className={cn(
          "flex w-full items-start gap-3 px-4 py-3 text-left",
          selected ? "bg-charcoal-875" : "hover:bg-charcoal-875/50",
        )}
      >
        <span
          aria-hidden="true"
          className={cn(
            "rounded-control mt-1 size-3 shrink-0 border",
            selected ? "border-charcoal-100 bg-charcoal-100" : "border-charcoal-600",
          )}
        />
        <span className="flex min-w-0 flex-col">
          <span
            className={cn(
              "text-body font-medium",
              selected ? "text-charcoal-100" : "text-charcoal-300",
            )}
          >
            {name}
          </span>
          <span className="text-charcoal-400 text-caption mt-1">{description}</span>
        </span>
      </button>
      <div className="border-charcoal-800 border-t px-4 py-3">{children}</div>
    </div>
  );
}

/**
 * The R9 two-tier research picker (defect V9: findable, radio-clear, two
 * visible tiers, no third anything). Tier A is the default — private local
 * SearXNG retrieval with the active chat model; Tier B routes research (and
 * only research) to a hosted research model on the user's OpenRouter key.
 */
function ResearchTierGroup() {
  const researchTier = useSearchSettingsStore((s) => s.researchTier);
  const setResearchTier = useSearchSettingsStore((s) => s.setResearchTier);

  return (
    <div role="radiogroup" aria-label="Research tier" className="flex flex-col gap-3">
      <TierCard
        selected={researchTier === "tier_a"}
        name="Unlimited (Local)"
        description="Private local search via SearXNG, paired with your active chat model. Unmetered and free — nothing leaves this machine but the pages it fetches."
        onSelect={() => setResearchTier("tier_a")}
      >
        <SearxngManagedFlow />
      </TierCard>
      <TierCard
        selected={researchTier === "tier_b"}
        name="Hosted research model"
        description="Purpose-built internet-native research via OpenRouter — research routes here at every depth regardless of chat model. Chat stays on your chat model."
        onSelect={() => setResearchTier("tier_b")}
      >
        <ResearchModelControls />
      </TierCard>
    </div>
  );
}

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
        title="Research"
        hint="Two ways to run research: unlimited private local search with your chat model, or a hosted research model on your own OpenRouter key."
      />
      <div className="flex flex-col gap-6">
        <ResearchTierGroup />
        <div>
          <GroupLabel
            label="Hardware & local models"
            hint="Heavy local paths (local deep-research, large local LLMs) enable only where the hardware earns it; everything else stays remote."
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
                  <div className="text-charcoal-100 text-body">{report.device.chip}</div>
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
        title="Keybindings"
        hint="Remap any shortcut. Press Record, then the new combination. Conflicts are flagged below — two actions on one combo both fire."
      />

      {conflictList.length > 0 && (
        <div
          role="alert"
          className="border-warning/40 bg-warning/10 text-warning text-caption mb-4 flex items-start gap-2 rounded-none border px-3 py-2"
        >
          <AlertTriangle className={cn(ICON_14, "mt-1 shrink-0")} aria-hidden="true" />
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
              {/* @container: the card is the query container so the row ladder
                  below keys off the PANEL's width, not the window's. */}
              <Card className="@container">
                {group.map(({ actionId, def, combo }) => {
                  const isRecording = recording === actionId;
                  const isOverridden = actionId in overrides;
                  const conflicted = conflictedActionIds.has(actionId);
                  return (
                    <div
                      key={actionId}
                      className={cn(
                        // Collapse ladder (R8 §3.4), uniform per CARD so row
                        // shapes never mix: above 576px card width the label
                        // column is flex-1 basis-0 — its copy never decides
                        // the wrap point, every row keeps its kbd/record
                        // cluster inline on one aligned column (D2). Below
                        // 576px ALL rows stack: the label takes basis-full and
                        // the cluster wraps under it as a unit (ml-auto keeps
                        // it right-aligned). The description's truncate is the
                        // genuine last resort at sub-stack starvation.
                        "flex min-h-8 flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3",
                        conflicted && "border-warning/50 border-l-2",
                      )}
                    >
                      <div className="flex min-w-0 flex-1 flex-col @max-[576px]:basis-full">
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
                          <RotateCcw className={ICON_14} aria-hidden="true" />
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
function SubsectionHeader({ id, title, hint }: Parameters<typeof SectionHeader>[0]) {
  return (
    <header className="mb-2">
      <h3 id={id} className="text-charcoal-100 text-panel-title">
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
                  <X className={ICON_14} aria-hidden="true" />
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
        title="Export / Import"
        hint="Carry your keybindings and preferences to another machine. Secrets are NEVER exported — re-enter your API keys via the keychain on the new machine."
      />
      <Card>
        <div className="flex flex-col gap-3 px-4 py-3">
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={handleExport}>
              <Download aria-hidden="true" />
              Export settings
            </Button>
            <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>
              <Upload aria-hidden="true" />
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
            The export bundles your keybinding remaps and preferences (default agent, region,
            research engine). API keys and broker credentials stay in your OS keychain and are never
            written to the file.
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
      <SubsectionHeader id="settings-about" title="About" />
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
