"use client";

import { useMemo } from "react";

import { cn } from "@/lib/utils";
import { useAgentRunsStore } from "@/store/agent-runs";
import { useAppStore } from "@/store/app";
import { useLLMProvidersStore } from "@/store/llm-providers";
import { useModelForProvider } from "@/store/model-selection";

/**
 * Status chrome (FR-033) — surfaces the three live signals that were computed
 * but unrendered: sidecar connection state, the active provider/model, and the
 * count of running background agents. P1 wires the existing store signals into
 * the header; P2 polishes this into the minimal-dark status surface.
 */
export function StatusChrome() {
  const status = useAppStore((state) => state.sidecarStatus);
  const provider = useLLMProvidersStore((state) => state.defaultProviderId);
  const providers = useLLMProvidersStore((state) => state.providers);
  const model = useModelForProvider(provider);
  const runs = useAgentRunsStore((state) => state.runs);

  // Human label for the active provider (e.g. "OpenAI"), not its raw id.
  const providerLabel = provider
    ? (providers.find((p) => p.id === provider)?.label ?? provider)
    : "";
  // Join only the parts we actually have so we never render a leading " · ".
  const providerModel = [providerLabel, model].filter(Boolean).join(" · ");

  const activeRunCount = useMemo(
    () => runs.filter((r) => r.status === "running" || r.status === "paused").length,
    [runs],
  );

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
      <span className="flex items-center gap-1.5" title={`Sidecar: ${connLabel}`}>
        <span className={cn("size-1.5 rounded-full", dotClass)} aria-hidden />
        {connLabel}
      </span>
      {providerModel && (
        <>
          <span className="bg-charcoal-700 h-3 w-px" aria-hidden />
          <span
            className="text-charcoal-400 max-w-[13rem] truncate"
            title="Default provider / model (the agent panel shows the per-send effective provider)"
          >
            {providerModel}
          </span>
        </>
      )}
      {activeRunCount > 0 && (
        <span
          className="text-primary flex items-center gap-1"
          title={`${activeRunCount} agent run${activeRunCount === 1 ? "" : "s"} in progress`}
        >
          <span className="size-1.5 animate-pulse rounded-full bg-current" aria-hidden />
          {activeRunCount}
        </span>
      )}
    </div>
  );
}
