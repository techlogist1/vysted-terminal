"use client";

import { KNOWN_MODELS_BY_PROVIDER } from "@/store/model-selection";

import type { LLMProviderId, LLMProviderInfo } from "../../../types/ai";

/**
 * The active provider + model HUD (FR-004) — both always visible and switchable
 * by keyboard: the native `<select>`s are keyboard-driven (Tab to focus, arrows
 * to change). The persona (lens) is switched in the roster strip and the mode in
 * the mode bar (⌥1–⌥4); this HUD is the orthogonal provider/model axis. A "no
 * key" badge surfaces when the active provider has no configured BYOK key.
 */
export function AgentHud({
  providers,
  provider,
  model,
  providerConfigured,
  onProviderChange,
  onModelChange,
}: {
  providers: LLMProviderInfo[];
  provider: LLMProviderId;
  model: string;
  providerConfigured: boolean;
  onProviderChange: (provider: LLMProviderId) => void;
  onModelChange: (model: string) => void;
}) {
  const known = KNOWN_MODELS_BY_PROVIDER[provider] ?? [];
  const modelOptions = known.includes(model) ? known : [model, ...known];
  const selectClass =
    "bg-charcoal-800 text-charcoal-200 border-charcoal-700 max-w-[10rem] truncate rounded border px-1 py-0.5 font-mono text-[0.6rem] outline-none focus:ring-1 focus:ring-amber-400";
  return (
    <div className="border-charcoal-700 text-charcoal-400 flex items-center gap-1.5 border-b px-3 py-1 font-mono text-[0.6rem]">
      <span className="tracking-wide uppercase">Model</span>
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
        <span className="text-warning" title="No BYOK key configured for this provider">
          no key
        </span>
      )}
    </div>
  );
}
