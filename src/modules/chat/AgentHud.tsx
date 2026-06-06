"use client";

import { Fragment } from "react";
import { RefreshCw } from "lucide-react";

import { buildModelGroups, modelOptionLabel } from "@/lib/model-options";
import { KNOWN_MODELS_BY_PROVIDER } from "@/store/model-selection";

import type { LLMModelOption, LLMProviderId, LLMProviderInfo } from "../../../types/ai";

/**
 * The active provider + model HUD (FR-004) — both always visible and switchable
 * by keyboard: the native `<select>`s are keyboard-driven (Tab to focus, arrows
 * to change). The persona (lens) is switched in the roster strip and the mode in
 * the mode bar (⌥1–⌥4); this HUD is the orthogonal provider/model axis.
 *
 * The model list is the LIVE provider catalog (`useModelCatalog`) when available,
 * falling back to the config-driven `knownModels` before it loads. Tool-calling
 * capable models are surfaced first and grouped; a non-tool-capable model is
 * marked (it would break the agent's host-actions). A "no key" badge surfaces
 * when the active provider has no configured BYOK key.
 */
export function AgentHud({
  providers,
  provider,
  model,
  providerConfigured,
  modelOptions,
  catalogNote,
  catalogLoading,
  onProviderChange,
  onModelChange,
  onKeyRequired,
  onRefreshModels,
}: {
  providers: LLMProviderInfo[];
  provider: LLMProviderId;
  model: string;
  providerConfigured: boolean;
  /** Live catalog options; empty/undefined before the first fetch resolves. */
  modelOptions?: LLMModelOption[];
  /** Honest one-line catalog status (e.g. "routable on your key · 245 tool-capable"). */
  catalogNote?: string | null;
  catalogLoading?: boolean;
  onProviderChange: (provider: LLMProviderId) => void;
  onModelChange: (model: string) => void;
  /** Called when the user clicks "no key" — should open the key entry dialog for the provider. */
  onKeyRequired?: (provider: LLMProviderId) => void;
  /** Force a live re-fetch of the model catalog (e.g. after adding a key). */
  onRefreshModels?: () => void;
}) {
  const providerInfo = providers.find((p) => p.id === provider);
  // Live catalog when present; otherwise the config-driven known list (and the
  // static map as the last resort before the sidecar is reached).
  const fallbackKnown =
    providerInfo?.knownModels && providerInfo.knownModels.length > 0
      ? providerInfo.knownModels
      : (KNOWN_MODELS_BY_PROVIDER[provider] ?? []);
  const baseOptions: LLMModelOption[] =
    modelOptions && modelOptions.length > 0
      ? modelOptions
      : fallbackKnown.map((id) => ({ id, label: id }));
  const { groups, selectedIsNoTools } = buildModelGroups(baseOptions, model);

  const selectClass =
    "bg-charcoal-800 text-charcoal-200 border-charcoal-700 h-8 max-w-[12rem] truncate rounded-control border px-3 font-mono text-caption outline-none focus:ring-1 focus:ring-amber-400";
  return (
    <div className="border-charcoal-700 text-charcoal-500 text-caption flex items-center gap-2 border-b px-3 py-2 font-mono">
      <span className="shrink-0 tracking-wide uppercase">Provider</span>
      <select
        aria-label="Active provider"
        value={provider}
        onChange={(event) => onProviderChange(event.target.value as LLMProviderId)}
        className={selectClass}
      >
        {providers.map((p) => (
          <option key={p.id} value={p.id}>
            {p.label}
          </option>
        ))}
      </select>
      <span className="text-charcoal-600 shrink-0">/</span>
      <select
        aria-label="Active model"
        value={model}
        onChange={(event) => onModelChange(event.target.value)}
        className={selectClass}
        title={catalogNote ?? undefined}
      >
        {groups.map((group, index) =>
          group.label ? (
            <optgroup key={group.label} label={group.label}>
              {group.options.map((option) => (
                <option key={option.id} value={option.id}>
                  {modelOptionLabel(option)}
                </option>
              ))}
            </optgroup>
          ) : (
            <Fragment key={`flat-${index}`}>
              {group.options.map((option) => (
                <option key={option.id} value={option.id}>
                  {modelOptionLabel(option)}
                </option>
              ))}
            </Fragment>
          ),
        )}
      </select>
      {onRefreshModels && (
        <button
          type="button"
          onClick={onRefreshModels}
          title={catalogNote ?? "Refresh model list"}
          aria-label="Refresh model list"
          className="hover:text-charcoal-200 rounded-control shrink-0 p-1 transition-colors"
        >
          <RefreshCw className={`size-3.5 ${catalogLoading ? "animate-spin" : ""}`} />
        </button>
      )}
      {selectedIsNoTools && (
        <span
          className="text-warning shrink-0"
          title="This model has no tool-calling — agent host-actions will fail. Pick a tool-capable model."
        >
          ⚠ no tools
        </span>
      )}
      {!providerConfigured && (
        <button
          type="button"
          onClick={() => onKeyRequired?.(provider)}
          title="No BYOK key configured for this provider — click to add"
          className="text-warning rounded-control px-1 transition-colors hover:text-amber-300"
        >
          no key
        </button>
      )}
    </div>
  );
}
