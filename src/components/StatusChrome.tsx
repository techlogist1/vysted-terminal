"use client";

import { useEffect, useMemo, useState } from "react";

import { validateProvider } from "@/lib/sidecar-client";
import { cn } from "@/lib/utils";
import { useAgentRunsStore } from "@/store/agent-runs";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelForProvider } from "@/store/model-selection";
import { useProviderKeysStore } from "@/store/provider-keys";

/** Designed word forms for model-id tokens (law §3.1 — short forms live at the
 *  formatter, never CSS truncation). Unknown tokens fall back to Title-case. */
const BRAND_WORDS: Record<string, string> = {
  deepseek: "DeepSeek",
  openai: "OpenAI",
  gpt: "GPT",
  minimax: "MiniMax",
  llama: "Llama",
  qwen: "Qwen",
  qwq: "QwQ",
  claude: "Claude",
  gemini: "Gemini",
  gemma: "Gemma",
  mistral: "Mistral",
  mixtral: "Mixtral",
  ministral: "Ministral",
  kimi: "Kimi",
  glm: "GLM",
  grok: "Grok",
  phi: "Phi",
  tongyi: "Tongyi",
  devstral: "Devstral",
  codestral: "Codestral",
  nemotron: "Nemotron",
  hermes: "Hermes",
  deephermes: "DeepHermes",
};

/** Middle-trim budget: beyond this the formatter drops MIDDLE segments. */
const MODEL_LABEL_MAX = 24;

// --- D60: provider-readiness probe cache -------------------------------------
// The chip used to claim "Ollama (local) · qwen2.5:7b" with full confidence
// without ever checking the daemon exists. The probe result is cached at module
// level so re-mounts / re-renders never hammer the sidecar: a positive holds
// for 5 minutes, a negative re-probes after 30 s (so starting Ollama heals the
// chip without a restart).
const PROBE_TTL_OK_MS = 300_000;
const PROBE_TTL_FAIL_MS = 30_000;
const probeCache = new Map<string, { ok: boolean; at: number }>();

/** Test seam — clears the module-level probe cache between tests. */
export function __resetProviderProbeCacheForTests(): void {
  probeCache.clear();
}

/**
 * Reachability of the active default lane (D60), probed fire-and-forget so the
 * chip renders instantly and downgrades only on a CONFIRMED failure:
 *   - keyless providers (Ollama) → `validateProvider` (true only when the
 *     local daemon answers) — the exact check ChatSidebar gates sends with;
 *   - BYOK providers → the keychain key-status store ("missing" = not set up;
 *     "unknown" — e.g. outside the Tauri shell — never raises a false alarm).
 * Returns `true`/`null` for "render today's confident chip", `false` for the
 * honest muted state.
 */
function useProviderReady(provider: string | null | undefined, requiresKey: boolean): boolean | null {
  const sidecarStatus = useAppStore((state) => state.sidecarStatus);
  const keyStatus = useProviderKeysStore((s) => (provider ? s.status[provider] : undefined));
  const [reachable, setReachable] = useState<boolean | null>(null);

  useEffect(() => {
    if (!provider || requiresKey) {
      setReachable(null);
      return;
    }
    const cached = probeCache.get(provider);
    if (cached && Date.now() - cached.at < (cached.ok ? PROBE_TTL_OK_MS : PROBE_TTL_FAIL_MS)) {
      setReachable(cached.ok);
      return;
    }
    // Unknown while the probe is in flight — the chip stays confident (never
    // an alarmist flash) and downgrades only on a confirmed failure.
    setReachable(null);
    let cancelled = false;
    // Fire-and-forget: never blocks render; validateProvider never throws.
    void validateProvider(provider).then((ok) => {
      probeCache.set(provider, { ok, at: Date.now() });
      if (!cancelled) {
        setReachable(ok);
      }
    });
    return () => {
      cancelled = true;
    };
    // sidecarStatus is a deliberate dep: a probe that failed while the sidecar
    // was still binding re-runs once it connects (self-healing, TTL-bounded).
  }, [provider, requiresKey, sidecarStatus]);

  if (!provider) {
    return null;
  }
  if (requiresKey) {
    return keyStatus === "missing" ? false : null;
  }
  return reachable;
}

/**
 * Designed short form for a model id (law §3.1): "deepseek-v4-flash" →
 * "DeepSeek V4 Flash". The org prefix ("minimax/minimax-m3") drops, tokens get
 * brand capitalization (version tokens like v4/m3/72b uppercase), and a label
 * over budget trims MIDDLE segments ("Llama 3.1 70B … Free") — a meaningful
 * label never mid-word truncates ("DEEPSEEK-V4-FLA…" is the defect this kills).
 */
export function formatModelLabel(modelId: string): string {
  const id = (modelId.split("/").pop() ?? modelId).trim();
  if (!id) {
    return modelId;
  }
  const tokens = id.split(/[-_:\s]+/).filter(Boolean);
  const words = tokens.map((tok) => {
    const lc = tok.toLowerCase();
    if (BRAND_WORDS[lc]) {
      return BRAND_WORDS[lc];
    }
    if (/^\d/.test(lc)) {
      // Numeric tokens keep their shape; a parameter count gets its B ("72b").
      return lc.replace(/(\d)b$/, "$1B");
    }
    if (/^[a-z]+\d[\w.]*$/.test(lc) && lc.length <= 4) {
      // Short letter+digit version tokens: v4 → V4, m3 → M3, r1 → R1, k2 → K2.
      return lc.toUpperCase();
    }
    return lc.charAt(0).toUpperCase() + lc.slice(1);
  });
  let label = words.join(" ");
  if (label.length > MODEL_LABEL_MAX && words.length > 2) {
    // Trim MIDDLE segments, keeping the leading family and the trailing variant.
    const head = [words[0]];
    const tail = words[words.length - 1];
    let i = 1;
    while (
      i < words.length - 1 &&
      [...head, words[i], "…", tail].join(" ").length <= MODEL_LABEL_MAX
    ) {
      head.push(words[i]);
      i += 1;
    }
    label = [...head, "…", tail].join(" ");
  }
  return label;
}

/**
 * Status chrome (FR-033) — surfaces the three live signals that were computed
 * but unrendered: sidecar connection state, the active provider/model, and the
 * count of running background agents. R8: the model label is a DESIGNED short
 * form (formatter-level, never a mid-word ellipsis) sitting next to a provider
 * dot; at narrow window widths the label collapses to the dot alone (tooltip
 * keeps the full provider · model), and the active-runs chip's tooltip NAMES
 * the runs it is counting.
 */
export function StatusChrome() {
  const status = useAppStore((state) => state.sidecarStatus);
  const provider = useLLMProvidersStore((state) => state.defaultProviderId);
  const providers = useLLMProvidersStore((state) => state.providers);
  const model = useModelForProvider(provider);
  const runs = useAgentRunsStore((state) => state.runs);

  const providerMeta = provider ? providers.find((p) => p.id === provider) : undefined;
  // D60: probe the default lane's actual readiness instead of asserting it.
  const providerReady = useProviderReady(provider, providerMeta?.requiresKey ?? true);

  // Human label for the active provider (e.g. "OpenAI"), not its raw id.
  const providerLabel = provider ? (providerMeta?.label ?? provider) : "";
  // When the model id already names its provider ("deepseek-v4-flash" under
  // DeepSeek), the provider prefix is dead weight — show just the model.
  const modelNamesProvider =
    !!model && !!provider && model.toLowerCase().startsWith(provider.toLowerCase());
  const shortModel = model ? formatModelLabel(model) : "";
  // Join only the parts we actually have so we never render a leading " · ".
  const providerModel = modelNamesProvider
    ? shortModel
    : [providerLabel, shortModel].filter(Boolean).join(" · ");
  // The tooltip always carries the EXACT ids the short form stands for.
  const providerModelTitle = `Default ${[providerLabel, model].filter(Boolean).join(" · ")} (the agent panel shows the per-send effective provider)`;

  const activeRuns = useMemo(
    () => runs.filter((r) => r.status === "running" || r.status === "paused"),
    [runs],
  );
  const activeRunCount = activeRuns.length;

  const dotClass =
    status === "connected"
      ? "bg-positive"
      : status === "error"
        ? "bg-negative"
        : "bg-warning animate-pulse";
  const connLabel =
    status === "connected" ? "Connected" : status === "error" ? "Sidecar error" : "Connecting…";

  return (
    <div
      aria-label="Status"
      className="text-charcoal-500 text-micro flex items-center gap-3 font-mono leading-none"
    >
      <span className="flex items-center gap-2" title={`Sidecar: ${connLabel}`}>
        <span className={cn("size-2 rounded-full", dotClass)} aria-hidden />
        {connLabel}
      </span>
      {providerModel && providerReady === false && (
        <>
          <span className="bg-charcoal-700 h-3 w-px" aria-hidden />
          {/* D60: the default lane is CONFIRMED not ready — the chip says so,
              quietly (muted monochrome, no model claim we cannot back), and
              points at the fix. The verified state below stays byte-identical
              to today's confident chip. */}
          <span
            className="flex items-center gap-2"
            data-testid="provider-not-ready"
            title={`${providerLabel} is the default AI lane but it isn't ready — ${
              providerMeta?.requiresKey
                ? "no API key is stored. Add one in Settings → AI Providers."
                : "the local daemon isn't reachable. Start it or pick a provider in Settings → AI Providers."
            }`}
          >
            <span className="bg-charcoal-600 size-2 shrink-0 rounded-full" aria-hidden />
            <span className="hidden whitespace-nowrap min-[880px]:inline">
              {providerLabel} ·{" "}
              {providerMeta?.requiresKey ? "no API key" : "not running"} — set up in Settings
            </span>
          </span>
        </>
      )}
      {providerModel && providerReady !== false && (
        <>
          <span className="bg-charcoal-700 h-3 w-px" aria-hidden />
          {/* Provider dot + designed short model. Below 880px window width the
              label COLLAPSES to the dot alone (law §3.1 — collapse, never a
              mid-word clip); the tooltip keeps the full identity either way. */}
          <span className="flex items-center gap-2" title={providerModelTitle}>
            <span className="bg-charcoal-400 size-2 shrink-0 rounded-full" aria-hidden />
            <span className="text-charcoal-400 hidden whitespace-nowrap min-[880px]:inline">
              {providerModel}
            </span>
          </span>
        </>
      )}
      {activeRunCount > 0 && (
        <span
          /* The ONE reserved spotlight: the accent marks LIVE agent activity
             only (idle chrome is fully monochrome). The pulsing dot rides
             bg-current so it inherits this accent. */
          className="flex items-center gap-1 text-amber-400"
          title={`${activeRunCount} agent run${activeRunCount === 1 ? "" : "s"} in progress: ${activeRuns
            .map((r) => r.agentName)
            .join(", ")}`}
        >
          <span className="size-2 animate-pulse rounded-full bg-current" aria-hidden />
          {activeRunCount}
        </span>
      )}
    </div>
  );
}
