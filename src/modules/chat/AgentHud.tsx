"use client";

import { KNOWN_MODELS_BY_PROVIDER } from "@/store/model-selection";

import type { LLMProviderId, LLMProviderInfo } from "../../../types/ai";

/**
 * The active provider + model HUD (FR-004) — both always visible and switchable
 * by keyboard: the native `<select>`s are keyboard-driven (Tab to focus, arrows
 * to change). The persona (lens) is switched in the roster strip and the mode in
 * the mode bar (⌥1–⌥4); this HUD is the orthogonal provider/model axis. A "no
 * key" badge surfaces when the active provider has no configured BYOK key —
 * clicking it opens the key dialog for that provider.
 */
export function AgentHud({
  providers,
  provider,
  model,
  providerConfigured,
  onProviderChange,
  onModelChange,
  onKeyRequired,
}: {
  providers: LLMProviderInfo[];
  provider: LLMProviderId;
  model: string;
  providerConfigured: boolean;
  onProviderChange: (provider: LLMProviderId) => void;
  onModelChange: (model: string) => void;
  /** Called when the user clicks "no key" — should open the key entry dialog for the provider. */
  onKeyRequired?: (provider: LLMProviderId) => void;
}) {
  // Prefer the live, config-driven model list (served from the sidecar's
  // model_registry.json into the provider row); fall back to the static map
  // when the sidecar hasn't been reached yet.
  const providerInfo = providers.find((p) => p.id === provider);
  const known =
    providerInfo?.knownModels && providerInfo.knownModels.length > 0
      ? providerInfo.knownModels
      : (KNOWN_MODELS_BY_PROVIDER[provider] ?? []);
  const modelOptions = known.includes(model) ? known : [model, ...known];
  const selectClass =
    "bg-charcoal-800 text-charcoal-200 border-charcoal-700 max-w-[10rem] truncate rounded border px-1 py-0.5 font-mono text-[0.6rem] outline-none focus:ring-1 focus:ring-amber-400";
  return (
    <div className="border-charcoal-700 text-charcoal-400 flex items-center gap-1.5 border-b px-3 py-1 font-mono text-[0.6rem]">
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
      >
        {modelOptions.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>
      {!providerConfigured && (
        <button
          type="button"
          onClick={() => onKeyRequired?.(provider)}
          title="No BYOK key configured for this provider — click to add"
          className="text-warning rounded px-1 transition-colors hover:text-amber-300"
        >
          no key
        </button>
      )}
    </div>
  );
}
