import { useState } from "react";
import { ExternalLink, KeyRound, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { KEYCHAIN_NAMESPACES, setSecret } from "@/lib/keychain";
import { validateProvider } from "@/lib/provider-validation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { WARMING_UP } from "@/store/local-models";
import { useModelSelectionStore } from "@/store/model-selection";
import { useProviderKeysStore } from "@/store/provider-keys";
import type { LLMProviderId } from "../../../types/ai";
import { StepHeader, offline, openExternal } from "./shared";

/** The fast agentic default activated when an OpenRouter key is added (Track 1). */
export const OPENROUTER_DEFAULT_MODEL = "deepseek/deepseek-v4-flash";

/** Why pick each provider (one line) and where to get its key. */
const PROVIDER_INFO: Partial<Record<LLMProviderId, { why: string; keysUrl: string }>> = {
  openrouter: {
    why: "One key for nearly every model (Claude, GPT, Gemini, DeepSeek…). Best if you're unsure.",
    keysUrl: "https://openrouter.ai/keys",
  },
  anthropic: {
    why: "Claude models, straight from Anthropic.",
    keysUrl: "https://console.anthropic.com/settings/keys",
  },
  openai: {
    why: "GPT models, straight from OpenAI.",
    keysUrl: "https://platform.openai.com/api-keys",
  },
  gemini: {
    why: "Google's Gemini models; has a free allowance.",
    keysUrl: "https://aistudio.google.com/apikey",
  },
  groq: {
    why: "Very fast open models; has a free allowance.",
    keysUrl: "https://console.groq.com/keys",
  },
  deepseek: {
    why: "DeepSeek's low-cost models.",
    keysUrl: "https://platform.deepseek.com/api_keys",
  },
  xai: { why: "Grok models from xAI.", keysUrl: "https://console.x.ai" },
};

type Status = "idle" | "validating" | "invalid" | "offline" | "unreachable" | "warming" | "error";

/** Pick a provider, paste a key, check it live, then save it and make it the default. */
export function KeyStep({ onBack, onDone }: { onBack: () => void; onDone: () => void }) {
  const providers = useLLMProvidersStore((s) => s.providers);
  const refreshOne = useProviderKeysStore((s) => s.refreshOne);
  const keyed = providers
    .filter((p) => p.requiresKey)
    .sort((a, b) => Number(b.id === "openrouter") - Number(a.id === "openrouter"));
  const [providerId, setProviderId] = useState<LLMProviderId>(keyed[0]?.id ?? "openrouter");
  const [key, setKey] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const provider = keyed.find((p) => p.id === providerId);
  const label = provider?.label ?? providerId;
  const info = PROVIDER_INFO[providerId];

  async function save() {
    const value = key.trim();
    if (!value) return;
    setStatus("validating");
    const result = await validateProvider(providerId, { apiKey: value });
    if (!result.ok) {
      if (result.reason !== "unreachable") setStatus("invalid");
      else if (offline()) setStatus("offline");
      else if (useAppStore.getState().sidecarStatus !== "connected") setStatus("warming");
      else setStatus("unreachable");
      return;
    }
    try {
      await setSecret(KEYCHAIN_NAMESPACES.llmProvider(providerId), value);
      await refreshOne(providerId);
      useLLMProvidersStore.getState().setDefaultProviderId(providerId);
      if (providerId === "openrouter") {
        useModelSelectionStore.getState().setModel("openrouter", OPENROUTER_DEFAULT_MODEL);
      }
      onDone();
    } catch {
      setStatus("error");
    }
  }

  const message: Partial<Record<Status, string>> = {
    invalid: `${label} didn't accept that key. Check it was copied in full and try again.`,
    offline: "No internet connection. Connect and try again.",
    unreachable: `Couldn't reach ${label} to check the key. Your key wasn't rejected — try again in a moment.`,
    warming: WARMING_UP,
    error: "Couldn't save the key on this computer. Try again.",
  };

  return (
    <div className="flex flex-col gap-4 px-6 py-6">
      <StepHeader
        icon={<KeyRound className="text-charcoal-300 size-4" aria-hidden="true" />}
        title="Use my own API key"
        onBack={onBack}
      />
      <div
        role="radiogroup"
        aria-label="Provider"
        className="grid grid-cols-2 gap-2 sm:grid-cols-4"
      >
        {keyed.map((p) => (
          <button
            key={p.id}
            type="button"
            role="radio"
            aria-checked={p.id === providerId}
            onClick={() => {
              setProviderId(p.id);
              setStatus("idle");
            }}
            className={cn(
              "rounded-control text-caption border px-2 py-2 font-mono transition-colors",
              p.id === providerId
                ? "border-charcoal-400/60 text-charcoal-100 bg-charcoal-700/10"
                : "border-charcoal-700 text-charcoal-400 hover:text-charcoal-200",
            )}
          >
            {p.label}
          </button>
        ))}
      </div>
      {info && (
        <p className="text-charcoal-300 text-caption font-mono leading-relaxed">{info.why}</p>
      )}
      {info && (
        <button
          type="button"
          onClick={() => void openExternal(info.keysUrl)}
          className="border-charcoal-700 bg-charcoal-900 text-charcoal-200 rounded-control text-caption hover:border-charcoal-500/40 hover:text-charcoal-100 flex items-center gap-2 self-start border px-3 py-2 font-mono transition-colors"
        >
          <ExternalLink size={14} aria-hidden="true" />
          Get a {label} key — {info.keysUrl.replace(/^https:\/\//, "")}
        </button>
      )}

      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void save();
        }}
      >
        <input
          type="password"
          value={key}
          autoFocus
          onChange={(e) => {
            setKey(e.target.value);
            if (status !== "idle") setStatus("idle");
          }}
          placeholder="Paste your key"
          aria-label={`${label} API key`}
          className="border-charcoal-700 bg-charcoal-800 text-charcoal-100 placeholder:text-charcoal-500 rounded-control text-body focus:border-charcoal-500 h-8 border px-3 font-mono outline-none"
        />
        {message[status] && (
          <p role="alert" className="text-negative text-caption font-mono">
            {message[status]}
          </p>
        )}
        <div className="flex items-center justify-between gap-3 pt-1">
          <span className="text-charcoal-500 text-caption font-mono">
            Kept in this computer&apos;s secure password store. Only {label} sees it.
          </span>
          <Button type="submit" size="sm" disabled={status === "validating" || !key.trim()}>
            {status === "validating" ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" /> Checking…
              </>
            ) : (
              "Check & save →"
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}
